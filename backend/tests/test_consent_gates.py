"""
Characterization tests for the three consent gates.

Written 2026-09-12, deliberately BEFORE the ADR-163 migration (consent becomes
append-only events keyed `(recipient, channel, purpose)`; `email` moves to an
addressability table). Nothing covered consent before this file: the suite
stayed green with the gates intact *or* deleted, which is an uncomfortable
property for the most safety-critical path in the system.

These tests pin **behaviour that must survive the migration**, not the current
schema. They are written against the service functions rather than against
`RecipientDB.consent_status` directly wherever possible, so that after the
migration the assertions still describe what is required and only the fixture
helper (`_set_consent`) has to change.

The three gates, per ADR-163 §7 and the code as it stands:
  A. `find_by_criteria`  — the base query filters to consenting recipients, so
     non-consenting people never enter processing scope at all (GDPR + AI cost).
  B. `resolve_audience`  — a second "consent floor" AFTER manual pins are
     unioned back in. This one is load-bearing and easy to lose in a refactor:
     a pinned recipient is otherwise "always included", and the consent floor is
     the single documented exception (legal, non-negotiable).
  C. `execute_decision_slot` — refuses per-recipient decisioning outright, so a
     slot executed directly by recipient_id cannot spend AI budget on someone
     who may not be sent to.

Also pinned here: the email-deduplication behaviour in `find_by_criteria`, which
ADR-163's 2026-09-12 addendum moves into stage 1 of the exclusion stack. The
assertion ("one address yields one recipient") must hold before and after; only
its implementation site moves.

**Added 2026-09-13 with the P0 fix** (`TestSendTimeConsentRevocation`): a
recipient who opts out *after* the audience is frozen must not be sent to. This
file originally declared that out of scope because it needs a full send
fixture; it landed with the fix, as planned, and is the regression test the
2026-08-07 review ranked first. It exercises the ADR-163 §7 exclusion stack
through `send_send_instance` against the mock provider — stage 1
(addressability) and stage 2 (consent), each asserting the *recorded reason*
§8 requires, not merely that the send stopped.

Uses the real database, like test_overrides.py — fixtures create their own
throwaway recipients and delete them again, so nothing depends on seed ids.

Run with: pytest tests/test_consent_gates.py -v
"""
import uuid

import pytest

from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB
from app.audience.service import find_by_criteria, resolve_audience
from app.auth.service import ensure_default_brand
from app.database import SessionLocal
from app.decision.service import execute_decision_slot
from app.recipients.consent import is_consenting, record_consent
from app.recipients.db_models import (
    AddressabilityDB,
    ConsentEventDB,
    ConsentSyncLogDB,
    RecipientDB,
)
from app.delivery.service import brand_for_snapshot
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.delivery.service import send_send_instance
from app.recipients.service import (
    detect_consent_drift,
    suppress_recipient,
    sync_consent_from_crm,
)
from app.snapshots.db_models import SnapshotDB

# The states the gates must treat as non-consenting. "pending" is included
# deliberately: consent is opt-IN, so the absence of a decision is not consent.
NON_CONSENTING = ["opted_out", "pending"]


def _make_recipient(db, consent_status, email=None, language=None):
    """A throwaway recipient with a unique external_id, in a given consent state.

    This helper is the *only* thing the ADR-163 migration changed in this file,
    exactly as intended: consent used to be a column on the recipient and is now
    the latest event for `(recipient, email, marketing)`. Every assertion below
    is untouched, because what must be true did not change — only where the
    answer is stored.

    external_id is the identity key (it carries the unique constraint); the
    address deliberately is not — several recipients may share one, which is
    what the deduplication test exercises.
    """
    address = email or f"{uuid.uuid4()}@example.invalid"
    recipient = RecipientDB(
        external_id=f"test-consent-{uuid.uuid4()}",
        language=language,
        status="active",
    )
    db.add(recipient)
    db.flush()
    # Since phase B the addressability row is the ONLY place an address lives —
    # there is no column to set. A recipient without one is unreachable, which
    # is exactly what the stage-1 exclusion test deliberately constructs.
    db.add(
        AddressabilityDB(
            recipient_id=recipient.id,
            channel="email",
            value={"email": address},
            status="active",
            is_primary=True,
        )
    )
    db.flush()
    record_consent(
        db,
        recipient.id,
        consent_status,
        source="test",
        note="test_consent_gates fixture",
        commit=False,
    )
    db.flush()
    return recipient


@pytest.fixture
def db():
    session = SessionLocal()
    created_recipients = []
    created_groups = []
    created_sends = []

    class Tracker:
        def __init__(self, session):
            self.session = session

        def recipient(self, consent_status, email=None, language=None):
            record = _make_recipient(self.session, consent_status, email, language)
            created_recipients.append(record.id)
            return record

        def group(self, name="test-consent-group"):
            group = AudienceGroupDB(
                name=f"{name}-{uuid.uuid4()}",
                brand_id=ensure_default_brand(self.session).id,
            )
            self.session.add(group)
            self.session.flush()
            created_groups.append(group.id)
            return group

        def pin(self, group, recipient):
            """A manual member pin — 'always included', except consent."""
            member = AudienceGroupMemberDB(
                group_id=group.id, recipient_id=recipient.id
            )
            self.session.add(member)
            self.session.flush()
            return member

        def send_to(self, recipient):
            """A frozen, ready-to-fire send instance targeting one recipient.

            Reuses an existing snapshot rather than rendering one: this test is
            about the consent gate, not about rendering, and building a snapshot
            would drag in the whole variant/module/storage path. The snapshot's
            variant supplies the subject and the decision slots, exactly as a
            real send does.

            `audience_resolution_mode="freeze"` is the point — it is the mode
            where the defect lives. A "rerun" send re-resolves its audience and
            would filter the opt-out out by accident, which is why the P0 hid
            for as long as it did.
            """
            snapshot = (
                self.session.query(SnapshotDB)
                .order_by(SnapshotDB.id.desc())
                .first()
            )
            if snapshot is None:
                pytest.skip("no snapshot in this database to send from")

            send_instance = SendInstanceDB(
                snapshot_id=snapshot.id,
                # Derived the same way the service derives it, so the fixture
                # cannot drift from what a real send would record.
                brand_id=brand_for_snapshot(self.session, snapshot.id),
                name=f"test-consent-send-{uuid.uuid4()}",
                status="draft",
                provider="mock",
                audience_resolution_mode="freeze",
            )
            self.session.add(send_instance)
            self.session.flush()
            created_sends.append(send_instance.id)

            execution = DeliveryExecutionDB(
                send_instance_id=send_instance.id,
                recipient_id=recipient.id,
                status="created",
                provider="mock",
            )
            self.session.add(execution)
            self.session.flush()
            self.session.commit()
            return send_instance, execution

    tracker = Tracker(session)
    session.commit()
    try:
        yield tracker
    finally:
        session.rollback()
        if created_groups:
            session.query(AudienceGroupMemberDB).filter(
                AudienceGroupMemberDB.group_id.in_(created_groups)
            ).delete(synchronize_session=False)
            session.query(AudienceGroupDB).filter(
                AudienceGroupDB.id.in_(created_groups)
            ).delete(synchronize_session=False)
        if created_sends:
            session.query(DeliveryExecutionDB).filter(
                DeliveryExecutionDB.send_instance_id.in_(created_sends)
            ).delete(synchronize_session=False)
            session.query(SendInstanceDB).filter(
                SendInstanceDB.id.in_(created_sends)
            ).delete(synchronize_session=False)
        if created_recipients:
            # Consent events, sync logs and addresses are FK-bound to the
            # recipient, so they go first or the delete below fails.
            session.query(ConsentSyncLogDB).filter(
                ConsentSyncLogDB.recipient_id.in_(created_recipients)
            ).delete(synchronize_session=False)
            session.query(ConsentEventDB).filter(
                ConsentEventDB.recipient_id.in_(created_recipients)
            ).delete(synchronize_session=False)
            session.query(AddressabilityDB).filter(
                AddressabilityDB.recipient_id.in_(created_recipients)
            ).delete(synchronize_session=False)
            session.query(RecipientDB).filter(
                RecipientDB.id.in_(created_recipients)
            ).delete(synchronize_session=False)
        session.commit()
        session.close()


class TestGateA_AudienceResolutionScope:
    """find_by_criteria: non-consenting recipients never enter processing scope.

    This is the gate that exists for two stated reasons at once — GDPR (running
    the decision engine over someone's data is itself processing) and cost (no
    AI/token spend on people who cannot be sent to). Both survive the migration.
    """

    def test_opted_in_recipient_is_resolvable(self, db):
        recipient = db.recipient("opted_in", language="test-lang-in")
        db.session.commit()

        found = find_by_criteria(db.session, language="test-lang-in")

        assert recipient.id in {r.id for r in found}

    @pytest.mark.parametrize("consent_status", NON_CONSENTING)
    def test_non_consenting_recipient_is_excluded(self, db, consent_status):
        recipient = db.recipient(consent_status, language="test-lang-out")
        db.session.commit()

        found = find_by_criteria(db.session, language="test-lang-out")

        assert recipient.id not in {r.id for r in found}, (
            f"a recipient with consent_status={consent_status!r} reached the "
            "resolved audience — consent is opt-in, so anything that is not an "
            "explicit grant must be excluded"
        )


class TestGateB_ConsentFloorBeatsManualPins:
    """resolve_audience: the consent floor overrides a manual pin.

    The most easily-lost rule in the system. A manual pin is documented as
    'always included' — exclude blocks cannot remove it — and the consent floor
    is the single exception, because the reason is legal rather than editorial.
    A refactor that applies consent only inside find_by_criteria (Gate A) would
    silently reintroduce this, since pins never pass through that function.
    """

    def test_pinned_opted_in_recipient_is_included(self, db):
        group = db.group()
        recipient = db.recipient("opted_in")
        db.pin(group, recipient)
        db.session.commit()

        resolved = resolve_audience(db.session, group.id)

        assert recipient.id in {r.id for r in resolved}

    @pytest.mark.parametrize("consent_status", NON_CONSENTING)
    def test_pinned_non_consenting_recipient_is_still_dropped(
        self, db, consent_status
    ):
        group = db.group()
        recipient = db.recipient(consent_status)
        db.pin(group, recipient)
        db.session.commit()

        resolved = resolve_audience(db.session, group.id)

        assert recipient.id not in {r.id for r in resolved}, (
            "a manually pinned recipient bypassed the consent floor. Pins beat "
            "exclude blocks by design, but never consent — this is the one "
            "documented exception and it is a legal requirement, not a "
            "preference"
        )


class TestGateC_DecisioningRefusesNonConsenting:
    """execute_decision_slot: refuses to run for a non-consenting recipient.

    Belt-and-braces behind Gate A, because a slot can be executed directly by
    recipient_id. Today the refusal is a bare ValueError, which is precisely why
    `send_send_instance` swallows it (`except ValueError: pass`) and the P0
    compliance defect reads as a rendering behaviour. ADR-163 §8 requires typed
    exceptions plus a recorded exclusion reason; when that lands, this test
    should assert the typed exception instead of ValueError, but the *behaviour*
    it pins — decisioning must not run — is unchanged.
    """

    @pytest.mark.parametrize("consent_status", NON_CONSENTING)
    def test_refuses_for_non_consenting_recipient(self, db, consent_status):
        recipient = db.recipient(consent_status)
        db.session.commit()

        slot_id = _any_decision_slot_id(db.session)

        with pytest.raises(ValueError) as excinfo:
            execute_decision_slot(
                db.session, slot_id, recipient_id=recipient.id
            )

        # The reason must be recoverable, not merely "something went wrong" —
        # this is the property ADR-163 §8 turns into a recorded exclusion.
        assert "not opted-in" in str(excinfo.value), (
            "decisioning refused the recipient but the refusal does not say it "
            "was about consent; a caller cannot distinguish it from 'strategy "
            "resolved nothing', which is the root of the P0"
        )


class TestAddressDeduplication:
    """One address yields one recipient.

    RecipientDB.email carries no unique constraint, so a bad import can produce
    two rows for one inbox; find_by_criteria dedupes so a segment preview does
    not double-count and a send does not arrive twice.

    ADR-163's 2026-09-12 addendum moves this into stage 1 of the exclusion stack
    (recorded rather than silent), and rejects a uniqueness constraint because
    two recipients legitimately sharing an address is a real case. The assertion
    here must therefore still hold after the migration — only where it happens
    changes.
    """

    def test_recipient_with_no_address_is_excluded(self, db):
        """Consent is not enough — you also have to be reachable.

        Stage 1 of the ADR-163 point 7 stack is addressability: a valid,
        non-expired address for this channel. A fully opted-in recipient with no
        address row is not addressable, and previously would have been handed to
        the provider as an empty string.
        """
        recipient = db.recipient("opted_in", language="test-lang-noaddr")
        db.session.query(AddressabilityDB).filter(
            AddressabilityDB.recipient_id == recipient.id
        ).delete(synchronize_session=False)
        db.session.commit()

        found = find_by_criteria(db.session, language="test-lang-noaddr")

        assert recipient.id not in {r.id for r in found}, (
            "a recipient with consent but no address resolved into the "
            "audience — they are not reachable on this channel"
        )

    def test_two_recipients_sharing_an_address_yield_one(self, db):
        shared = f"shared-{uuid.uuid4()}@example.invalid"
        first = db.recipient("opted_in", email=shared, language="test-lang-dupe")
        second = db.recipient("opted_in", email=shared, language="test-lang-dupe")
        db.session.commit()

        found = find_by_criteria(db.session, language="test-lang-dupe")

        matching = [r for r in found if r.id in {first.id, second.id}]
        assert len(matching) == 1, (
            "two recipient rows sharing one address both resolved — the same "
            "inbox would receive the send twice"
        )


class TestConsentEventsAndDrift:
    """The consent write paths and directional drift (ADR-163 addendum points 2 and 4).

    Added after a smoke test found two defects here that the gate tests above
    could not see: a missing keyword argument on `sync_consent_from_crm`, and —
    more seriously — a "only write an event if the value changed" optimisation
    that left drift with no CRM baseline to compare against, making a provider
    suppression invisible. Both were in the one path whose entire job is to make
    a silent divergence loud.
    """

    def test_crm_assertion_is_recorded_even_when_unchanged(self, db):
        recipient = db.recipient("opted_in")
        db.session.commit()
        before = _event_count(db.session, recipient.id)

        sync_consent_from_crm(
            db.session, recipient.external_id, "opted_in", note="test"
        )

        assert _event_count(db.session, recipient.id) == before + 1, (
            "an unchanged CRM assertion wrote no event. It must: drift compares "
            "the effective state against the CRM's last assertion, so with no "
            "assertion recorded a later provider suppression is invisible — and "
            "the assertion is also the consent evidence"
        )

    def test_agreement_produces_no_drift(self, db):
        recipient = db.recipient("opted_in")
        db.session.commit()
        sync_consent_from_crm(
            db.session, recipient.external_id, "opted_in", note="test"
        )

        assert _drift_for(db.session, recipient.id) == []

    def test_provider_suppression_shows_as_platform_ahead(self, db):
        recipient = db.recipient("opted_in")
        db.session.commit()
        sync_consent_from_crm(
            db.session, recipient.external_id, "opted_in", note="test"
        )

        assert suppress_recipient(db.session, recipient.id, reason="hard_bounce")

        drift = _drift_for(db.session, recipient.id)
        assert len(drift) == 1, (
            "a provider suppressed someone the CRM still believes is opted-in "
            "and drift did not report it — this is the case the old code "
            "deliberately skipped a sync-log row to expose"
        )
        item = drift[0]
        assert item.direction.value == "platform_ahead"
        assert item.platform_consent_status.value == "opted_out"
        assert item.last_crm_consent_status.value == "opted_in"
        # Says *what* moved the platform, which is what tells an operator this
        # needs relaying outward rather than re-syncing inward.
        assert item.platform_source == "provider"

    def test_suppression_is_idempotent(self, db):
        recipient = db.recipient("opted_in")
        db.session.commit()

        assert suppress_recipient(db.session, recipient.id, reason="hard_bounce")
        assert not suppress_recipient(
            db.session, recipient.id, reason="hard_bounce"
        ), "a repeat bounce wrote a second opt-out event"

    def test_crm_reassertion_clears_drift_and_reopens_the_gate(self, db):
        recipient = db.recipient("opted_in")
        db.session.commit()
        sync_consent_from_crm(
            db.session, recipient.external_id, "opted_in", note="test"
        )
        suppress_recipient(db.session, recipient.id, reason="hard_bounce")
        assert _drift_for(db.session, recipient.id)

        # The CRM asserts again — the person re-subscribed, say.
        sync_consent_from_crm(
            db.session, recipient.external_id, "opted_in", note="test"
        )

        assert _drift_for(db.session, recipient.id) == []
        assert is_consenting(db.session, recipient.id), (
            "the newest event is the CRM's opt-in, so it must be back in force "
            "— latest wins, per cell"
        )

    def test_suppression_is_scoped_to_its_channel(self, db):
        """A bounce on email says nothing about push."""
        recipient = db.recipient("opted_in")
        record_consent(
            db.session,
            recipient.id,
            "opted_in",
            source="test",
            channel="push",
            commit=False,
        )
        db.session.commit()

        suppress_recipient(db.session, recipient.id, reason="hard_bounce")

        assert not is_consenting(db.session, recipient.id, channel="email")
        assert is_consenting(db.session, recipient.id, channel="push"), (
            "an email bounce withdrew push consent — consent is per "
            "(channel, purpose) and a failure on one says nothing about another"
        )


class TestSendTimeConsentRevocation:
    """The P0: opting out after the audience is frozen must stop the send.

    This is the regression test the 2026-08-07 review ranked first, and the one
    `test_consent_gates.py` originally declared out of scope because it needs a
    full send fixture. It lands with the fix, as planned.

    The defect it pins: a `freeze` send materialises its `DeliveryExecutionDB`
    rows at plan time, with consent checked *then*. Before the ADR-163 point 7
    exclusion stack, nothing looked again, so a recipient who opted out between
    planning and sending was still handed to the provider. Re-resolving the
    audience is not the fix — that is what `rerun` mode does, and it changes who
    is targeted. Freezing targeting must never freeze permission to contact.

    Runs against the mock provider, so nothing leaves the machine.
    """

    def test_optout_after_freeze_stops_the_send(self, db):
        recipient = db.recipient("opted_in")
        send_instance, execution = db.send_to(recipient)

        # The audience is now frozen: the execution row exists and consent was
        # good when it was created. The person then opts out.
        record_consent(
            db.session,
            recipient.id,
            "opted_out",
            source="test",
            note="withdrew after the audience was frozen",
            commit=False,
        )
        db.session.commit()

        send_send_instance(db.session, send_instance.id)
        db.session.refresh(execution)

        assert execution.status == "excluded", (
            "a recipient who opted out after the audience was frozen was still "
            "sent to — this is the P0, and the whole reason the send-time gate "
            f"exists (status was {execution.status!r})"
        )
        # Point 8: the reason has to be recorded, not merely acted on. A stack
        # that silently drops people reproduces the original defect one layer up.
        assert execution.exclusion_reason is not None
        assert "consent" in execution.exclusion_reason

    def test_consenting_recipient_still_sends(self, db):
        """The gate must not be a blanket refusal."""
        recipient = db.recipient("opted_in")
        send_instance, execution = db.send_to(recipient)

        send_send_instance(db.session, send_instance.id)
        db.session.refresh(execution)

        assert execution.status == "sent", (
            f"a fully consenting recipient was not sent to (status "
            f"{execution.status!r}, reason {execution.exclusion_reason!r})"
        )
        assert execution.exclusion_reason is None

    def test_parent_status_is_derived_not_declared(self, db):
        """P1: the send's own status must reflect what actually happened.

        `send_instance.status = "sent"` used to run unconditionally after the
        loop, so 100 failures out of 100 still reported a sent campaign. A
        provider failure returns SendResult(success=False) rather than raising,
        so nothing caught it.
        """
        recipient = db.recipient("opted_in")
        send_instance, execution = db.send_to(recipient)

        send_send_instance(db.session, send_instance.id)
        db.session.refresh(send_instance)

        assert send_instance.status == "sent"
        assert send_instance.sent_count == 1
        assert send_instance.failed_count == 0
        assert send_instance.excluded_count == 0

    def test_all_excluded_is_not_reported_as_sent(self, db):
        """The case the P1 entry predates.

        Every recipient excluded means nothing was delivered — but nothing
        failed either. Reporting `sent` would show a green send that delivered
        nothing, which is the class of lie the P1 fix exists to stop; reporting
        `failed` would invite a retry of something that worked correctly.
        """
        recipient = db.recipient("opted_in")
        send_instance, execution = db.send_to(recipient)
        record_consent(
            db.session, recipient.id, "opted_out", source="test", commit=False
        )
        db.session.commit()

        send_send_instance(db.session, send_instance.id)
        db.session.refresh(send_instance)

        assert send_instance.status == "no_recipients", (
            f"a send that delivered to nobody reported {send_instance.status!r}"
        )
        assert send_instance.sent_count == 0
        assert send_instance.failed_count == 0, (
            "an excluded recipient was counted as a delivery failure — "
            "exclusion is the stack working, not a delivery problem"
        )
        assert send_instance.excluded_count == 1

    def test_unaddressable_recipient_is_excluded_at_stage_one(self, db):
        """Stage 1 runs before stage 2, and says so in the reason.

        Being unreachable is a different fact from having refused contact, and
        the recorded reason has to tell them apart — that distinction is what
        the single-status model could not express.
        """
        recipient = db.recipient("opted_in")
        send_instance, execution = db.send_to(recipient)
        db.session.query(AddressabilityDB).filter(
            AddressabilityDB.recipient_id == recipient.id
        ).delete(synchronize_session=False)
        db.session.commit()

        send_send_instance(db.session, send_instance.id)
        db.session.refresh(execution)

        assert execution.status == "excluded"
        assert "addressability" in execution.exclusion_reason


def _event_count(session, recipient_id: int) -> int:
    return (
        session.query(ConsentEventDB)
        .filter(ConsentEventDB.recipient_id == recipient_id)
        .count()
    )


def _drift_for(session, recipient_id: int) -> list:
    return [d for d in detect_consent_drift(session) if d.recipient_id == recipient_id]


def _any_decision_slot_id(session) -> int:
    """A decision slot to execute against, resolved by shape not by seed id.

    Gate C refuses on consent *before* the strategy is looked up, so any slot
    exercises it — but there must be one in the database.
    """
    from app.campaigns.db_models import DecisionSlotDB

    row = (
        session.query(DecisionSlotDB.id)
        .order_by(DecisionSlotDB.id.asc())
        .first()
    )
    if row is None:
        pytest.skip("no decision slot in this database")
    return row[0]
