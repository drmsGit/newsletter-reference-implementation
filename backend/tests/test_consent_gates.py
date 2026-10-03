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

from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB, AudienceRuleBlockDB
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
from app.rendering.frame import build_frame
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
        ensure_default_brand(db).id,
        source="test",
        note="test_consent_gates fixture",
        commit=False, purpose="marketing",
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
            """A manual member pin. It is **not** "always included" — an
            exclude block removes it since ADR-176 point 1 (2026-09-29), and
            the consent floor always could."""
            member = AudienceGroupMemberDB(
                group_id=group.id, recipient_id=recipient.id
            )
            self.session.add(member)
            self.session.flush()
            return member

        def send_to(self, recipient, group=None):
            """A frozen, ready-to-fire send instance targeting one recipient.

            Reuses an existing snapshot rather than rendering one: this test is
            about the consent gate, not about rendering, and building a snapshot
            would drag in the whole variant/module/storage path. The snapshot's
            variant supplies the subject and the decision slots, exactly as a
            real send does.

            **No `audience_group_id` is the point**, and it is deliberate
            rather than a shortcut: `reconcile_executions_to_audience` returns
            early without one, so nothing re-resolves and the send-time gate is
            the only thing under test. This fixture said
            `audience_resolution_mode="freeze"` for that job until 2026-09-29,
            when ADR-176 point 4 removed the mode; see the class docstring.
            """
            # **An EMAIL snapshot, specifically.** This picks up whatever is
            # already in the shared dev database, and `ORDER BY id DESC` was
            # unambiguous while every variant was email. Since ADR-160 point 4
            # gave variants a channel, the newest snapshot may belong to a push
            # variant — and `prepare_send_from_audience` derives the send's
            # channel from it, so these email-consent tests would silently
            # become push tests and every email-consenting recipient would be
            # excluded for having no device token. That is exactly what
            # happened the first time a push campaign was built by hand.
            from app.campaigns.db_models import VariantDB

            # **And a SENDABLE one.** Same lesson as the channel filter above,
            # arriving a second time: ADR-174 point 3's required-field check
            # refuses a send whose variant would render an empty required
            # field, and four of the dev database's fourteen variants do — a
            # `cta` with no label pointing nowhere. Taking "the newest email
            # snapshot" would make these consent tests fail for a rendering
            # reason, which is exactly the confusion the channel filter exists
            # to prevent. Picking the newest *complete* one keeps the fixture
            # about consent.
            from app.rendering.service import missing_required_fields

            snapshot = None
            for candidate in (
                self.session.query(SnapshotDB)
                .join(VariantDB, VariantDB.id == SnapshotDB.variant_id)
                .filter(VariantDB.channel == "email")
                .order_by(SnapshotDB.id.desc())
                .limit(50)
                .all()
            ):
                if not missing_required_fields(self.session, candidate.variant_id):
                    snapshot = candidate
                    break
            if snapshot is None:
                # **Build one rather than skip.** An earlier version of this
                # filter skipped, which silently stopped five real consent
                # tests from running — a worse outcome than the failure it was
                # avoiding. The required-field gate gets to refuse; it does not
                # get to quietly delete coverage of something else.
                #
                # Zero modules is deliberate: a variant with none declares no
                # required fields, so it passes the gate without dragging in
                # the module and storage path this fixture's docstring is at
                # pains to avoid. These tests assert who is excluded, never
                # what the mail says.
                from app.campaigns.db_models import CampaignDB

                brand = ensure_default_brand(self.session)
                campaign = CampaignDB(
                    brand_id=brand.id, name=f"consent-gate-{uuid.uuid4()}",
                )
                self.session.add(campaign)
                self.session.flush()
                variant = VariantDB(
                    campaign_id=campaign.id, channel="email",
                    name="consent-gate fixture", status="draft",
                )
                self.session.add(variant)
                self.session.flush()
                snapshot = SnapshotDB(
                    variant_id=variant.id,
                    # A real frame (ADR-183): a frameless snapshot is refused at
                    # send time, which these consent tests must get past.
                    render_context=build_frame(self.session, variant.id),
                )
                self.session.add(snapshot)
                self.session.flush()

            send_instance = SendInstanceDB(
                snapshot_id=snapshot.id,
                # Derived the same way the service derives it, so the fixture
                # cannot drift from what a real send would record.
                brand_id=brand_for_snapshot(self.session, snapshot.id),
                name=f"test-consent-send-{uuid.uuid4()}",
                status="draft",
                provider="mock",
                # Group-backed only when a test asks. Without one,
                # `reconcile_executions_to_audience` returns early and the
                # send-time gate is the only thing that can drop a recipient —
                # which is what every test in this file but one wants.
                audience_group_id=group.id if group is not None else None,
            )
            self.session.add(send_instance)
            self.session.flush()
            created_sends.append(send_instance.id)

            execution = DeliveryExecutionDB(
                send_instance_id=send_instance.id,
                recipient_id=recipient.id,
                status="created",
                provider="mock",
                # The email consent gate is what this file tests.
                channel="email",
                purpose="marketing",
            )
            self.session.add(execution)
            self.session.flush()
            self.session.commit()
            return send_instance, execution

        def also_send_to(self, send_instance, recipient):
            """A second execution on an existing send.

            Only the duplicate-address test needs this: two recipient rows
            sharing one inbox have to be on the *same* send for stage 1 to see
            them together, since deduplication is per resolution and not
            global.
            """
            execution = DeliveryExecutionDB(
                send_instance_id=send_instance.id,
                recipient_id=recipient.id,
                status="created",
                provider="mock",
                # The email consent gate is what this file tests.
                channel="email",
                purpose="marketing",
            )
            self.session.add(execution)
            self.session.flush()
            self.session.commit()
            return execution

    tracker = Tracker(session)
    session.commit()
    try:
        yield tracker
    finally:
        session.rollback()
        if created_sends:
            session.query(DeliveryExecutionDB).filter(
                DeliveryExecutionDB.send_instance_id.in_(created_sends)
            ).delete(synchronize_session=False)
            session.query(SendInstanceDB).filter(
                SendInstanceDB.id.in_(created_sends)
            ).delete(synchronize_session=False)
        # Groups after sends: `send_instances.audience_group_id` is a FK,
        # and a group-backed send holds the group until it is gone.
        if created_groups:
            session.query(AudienceRuleBlockDB).filter(
                AudienceRuleBlockDB.group_id.in_(created_groups)
            ).delete(synchronize_session=False)
            session.query(AudienceGroupMemberDB).filter(
                AudienceGroupMemberDB.group_id.in_(created_groups)
            ).delete(synchronize_session=False)
            session.query(AudienceGroupDB).filter(
                AudienceGroupDB.id.in_(created_groups)
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

        found = find_by_criteria(db.session, _brand(db.session), channel="email", language="test-lang-in")

        assert recipient.id in {r.id for r in found}

    @pytest.mark.parametrize("consent_status", NON_CONSENTING)
    def test_non_consenting_recipient_is_excluded(self, db, consent_status):
        recipient = db.recipient(consent_status, language="test-lang-out")
        db.session.commit()

        found = find_by_criteria(db.session, _brand(db.session), channel="email", language="test-lang-out")

        assert recipient.id not in {r.id for r in found}, (
            f"a recipient with consent_status={consent_status!r} reached the "
            "resolved audience — consent is opt-in, so anything that is not an "
            "explicit grant must be excluded"
        )


class TestGateB_ChannelDecidesWhoIsInTheAudience:
    """`resolve_audience` requires a channel, and the channel changes the answer.

    Consent is keyed `(recipient, brand, channel, purpose)`, so resolving the
    same group for email and for push returns different people. Until
    2026-09-27 the parameter carried `= DEFAULT_CHANNEL`, so a caller that
    forgot it silently consent-gated on email — the recorded cause of a push
    send resolving to nobody. The default is gone for the same reason
    `VariantDB.channel` never had one.

    These tests pin the *property*, not the signature: a test that only
    asserted `TypeError` on a missing argument would pass against a function
    that took the channel and ignored it.
    """

    def test_a_recipient_consenting_only_to_email_is_absent_from_push(self, db):
        group = db.group()
        recipient = db.recipient("opted_in")  # email consent, by the fixture
        db.pin(group, recipient)
        db.session.commit()

        for_email = resolve_audience(db.session, group.id, channel="email")
        for_push = resolve_audience(db.session, group.id, channel="push")

        assert recipient.id in {r.id for r in for_email}
        assert recipient.id not in {r.id for r in for_push}, (
            "a recipient who consented to email appeared in the push audience. "
            "Consent is per channel, so the channel is not a delivery detail — "
            "it decides membership, which is why the parameter has no default"
        )

    def test_consent_on_one_channel_does_not_leak_to_the_other(self, db):
        group = db.group()
        recipient = db.recipient("opted_in")
        record_consent(
            db.session,
            recipient.id,
            "opted_in",
            ensure_default_brand(db.session).id,
            source="test",
            channel="push",
            note="channel-scoping test",
            commit=False, purpose="marketing",
        )
        db.pin(group, recipient)
        db.session.commit()

        for_push = resolve_audience(db.session, group.id, channel="push")

        assert recipient.id in {r.id for r in for_push}, (
            "an explicit push consent did not put the recipient in the push "
            "audience — the consent lookup is not reading the channel it was "
            "given"
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

        resolved = resolve_audience(db.session, group.id, channel="email")

        assert recipient.id in {r.id for r in resolved}

    @pytest.mark.parametrize("consent_status", NON_CONSENTING)
    def test_pinned_non_consenting_recipient_is_still_dropped(
        self, db, consent_status
    ):
        group = db.group()
        recipient = db.recipient(consent_status)
        db.pin(group, recipient)
        db.session.commit()

        resolved = resolve_audience(db.session, group.id, channel="email")

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


class TestAddressabilityIsAnsweredAtSendTime:
    """One address yields one recipient — but the answer moved layers.

    `RecipientDB` carries no uniqueness constraint on an address and ADR-163's
    2026-09-12 addendum point 3 rejected adding one, because two recipient rows
    legitimately sharing an inbox is a real case. That addendum put the
    deduplication in **stage 1 of the exclusion stack**, and this file's header
    said so while the code did it in `find_by_criteria` instead: *"the assertion
    must hold before and after; only its implementation site moves."*

    **It moved on 2026-09-29** (task-233), because the old site was wrong in two
    directions at once — it narrowed *exclude* block criteria, so an
    unaddressable recipient could not be excluded from an audience at all, and
    it resolved *email* addresses whatever channel was asked about, so a
    push-only recipient could not be included either.

    So the pair below asserts both halves of the new split: membership does not
    ask whether you are reachable, and the send does.
    """

    def test_a_recipient_with_no_address_still_resolves_into_the_audience(self, db):
        """The behaviour change, pinned on the side that changed.

        Before 2026-09-29 this recipient was dropped by `find_by_criteria`, and
        the test here asserted exactly that. Membership now answers "who did the
        manager mean" and leaves "who can be reached" to stage 1 — see
        `TestSendTimeConsentRevocation.test_unaddressable_recipient_is_excluded_at_stage_one`,
        which is where that person is now dropped, with a recorded reason rather
        than a log line.
        """
        recipient = db.recipient("opted_in", language="test-lang-noaddr")
        db.session.query(AddressabilityDB).filter(
            AddressabilityDB.recipient_id == recipient.id
        ).delete(synchronize_session=False)
        db.session.commit()

        found = find_by_criteria(
            db.session, _brand(db.session), channel="email",
            language="test-lang-noaddr",
        )

        assert recipient.id in {r.id for r in found}, (
            "an unreachable recipient was filtered out of a membership query — "
            "the filter that did this is what made an exclude block unable to "
            "reach a pinned recipient (task-233)"
        )

    def test_two_recipients_sharing_an_address_yield_one_at_send(self, db):
        """The assertion that had to survive the move, now made where it lives.

        And it gains something the old site could not give: the loser is
        *recorded* as excluded with a stated reason, which is what ADR-163
        point 8 asks for. Under the old deduplication they simply were not in
        the list, and nobody could answer why."""
        shared = f"shared-{uuid.uuid4()}@example.invalid"
        first = db.recipient("opted_in", email=shared, language="test-lang-dupe")
        second = db.recipient("opted_in", email=shared, language="test-lang-dupe")
        send_instance, first_execution = db.send_to(first)
        second_execution = db.also_send_to(send_instance, second)
        db.session.commit()

        send_send_instance(
            db.session, send_instance.id, brand_id=send_instance.brand_id)
        db.session.refresh(first_execution)
        db.session.refresh(second_execution)

        statuses = {first_execution.status, second_execution.status}
        assert "excluded" in statuses, (
            "two recipient rows sharing one address both went out — the same "
            "inbox received the send twice"
        )
        assert statuses != {"excluded"}, (
            "both were excluded, so the shared inbox received nothing at all"
        )
        loser = (
            second_execution if second_execution.status == "excluded"
            else first_execution
        )
        assert "addressability" in (loser.exclusion_reason or ""), (
            "the duplicate was dropped without a recorded reason, which is the "
            "silent loss ADR-163 point 8 exists to prevent"
        )
        assert "duplicate" in (loser.exclusion_reason or "")


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
            db.session, recipient.external_id, "opted_in", _brand(db.session), note="test", purpose="marketing"
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
            db.session, recipient.external_id, "opted_in", _brand(db.session), note="test", purpose="marketing"
        )

        assert _drift_for(db.session, recipient.id) == []

    def test_provider_suppression_shows_as_platform_ahead(self, db):
        recipient = db.recipient("opted_in")
        db.session.commit()
        sync_consent_from_crm(
            db.session, recipient.external_id, "opted_in", _brand(db.session), note="test", purpose="marketing"
        )

        assert suppress_recipient(db.session, recipient.id, _brand(db.session), reason="hard_bounce", purpose="marketing")

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

        assert suppress_recipient(db.session, recipient.id, _brand(db.session), reason="hard_bounce", purpose="marketing")
        assert not suppress_recipient(
            db.session, recipient.id, _brand(db.session), reason="hard_bounce", purpose="marketing"
        ), "a repeat bounce wrote a second opt-out event"

    def test_crm_reassertion_clears_drift_and_reopens_the_gate(self, db):
        recipient = db.recipient("opted_in")
        db.session.commit()
        sync_consent_from_crm(
            db.session, recipient.external_id, "opted_in", _brand(db.session), note="test", purpose="marketing"
        )
        suppress_recipient(db.session, recipient.id, _brand(db.session), reason="hard_bounce", purpose="marketing")
        assert _drift_for(db.session, recipient.id)

        # The CRM asserts again — the person re-subscribed, say.
        sync_consent_from_crm(
            db.session, recipient.external_id, "opted_in", _brand(db.session), note="test", purpose="marketing"
        )

        assert _drift_for(db.session, recipient.id) == []
        assert is_consenting(db.session, recipient.id, _brand(db.session), purpose="marketing"), (
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
            ensure_default_brand(db.session).id,
            source="test",
            channel="push",
            commit=False, purpose="marketing",
        )
        db.session.commit()

        suppress_recipient(db.session, recipient.id, _brand(db.session), reason="hard_bounce", purpose="marketing")

        assert not is_consenting(db.session, recipient.id, _brand(db.session), channel="email", purpose="marketing")
        assert is_consenting(db.session, recipient.id, _brand(db.session), channel="push", purpose="marketing"), (
            "an email bounce withdrew push consent — consent is per "
            "(channel, purpose) and a failure on one says nothing about another"
        )


class TestSendTimeConsentRevocation:
    """The P0: opting out after the executions are planned must stop the send.

    This is the regression test the 2026-08-07 review ranked first, and the one
    `test_consent_gates.py` originally declared out of scope because it needs a
    full send fixture. It lands with the fix, as planned.

    The defect it pins: a send materialises its `DeliveryExecutionDB` rows at
    plan time, with consent checked *then*. Before the ADR-163 point 7
    exclusion stack, nothing looked again, so a recipient who opted out between
    planning and sending was still handed to the provider.

    **What actually protects this test changed on 2026-09-29, and the old
    answer is no longer available.** It used to be `audience_resolution_mode`:
    the fixture said `"freeze"`, and the comment here said that was the point,
    because a `"rerun"` send re-resolves its audience and would drop the
    opted-out recipient by accident — passing while testing nothing. ADR-176
    point 4 makes every send re-resolve, so that protection is gone.

    **What replaces it: the fixture's send has no `audience_group_id`.**
    `reconcile_executions_to_audience` returns early for such a send, so
    nothing re-resolves and the send-time gate is the only thing between an
    opted-out recipient and the provider — which is also the real case, since
    executions can be created without a group. Verified by mutation on
    2026-09-29 in both directions: flipping the fixture's mode to `"rerun"`
    changes nothing, and neutering the gate fails all four tests here.

    Runs against the mock provider, so nothing leaves the machine.
    """

    def test_optout_after_planning_stops_the_send(self, db):
        recipient = db.recipient("opted_in")
        send_instance, execution = db.send_to(recipient)

        # The send is now planned: the execution row exists and consent was
        # good when it was created. The person then opts out.
        record_consent(
            db.session,
            recipient.id,
            "opted_out",
            ensure_default_brand(db.session).id,
            source="test",
            note="withdrew after the send was planned",
            commit=False, purpose="marketing",
        )
        db.session.commit()

        send_send_instance(
            db.session, send_instance.id, brand_id=send_instance.brand_id)
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

        send_send_instance(
            db.session, send_instance.id, brand_id=send_instance.brand_id)
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

        send_send_instance(
            db.session, send_instance.id, brand_id=send_instance.brand_id)
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
            db.session, recipient.id, "opted_out",
            ensure_default_brand(db.session).id, source="test", commit=False, purpose="marketing",
        )
        db.session.commit()

        send_send_instance(
            db.session, send_instance.id, brand_id=send_instance.brand_id)
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

        send_send_instance(
            db.session, send_instance.id, brand_id=send_instance.brand_id)
        db.session.refresh(execution)

        assert execution.status == "excluded"
        assert "addressability" in execution.exclusion_reason


def _brand(session) -> int:
    """The default brand, which every fixture in this file belongs to.

    Consent is keyed by brand since the ADR-163 addendum of 2026-09-15, so a
    test asserting "this person is gated out" has to say gated out of WHAT.
    These fixtures are single-brand deliberately: the gates' behaviour is the
    subject here, and brand-crossing has its own tests in test_brand_scoping.
    """
    return ensure_default_brand(session).id


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


class TestSendTimeAudienceReResolution:
    """ADR-176 point 4: every send re-resolves its audience before firing.

    **This is what makes point 1 mean anything.** Point 1 changed the resolver
    so an exclude block removes a hand-pinned recipient; without point 4 that
    would have been true of the resolver and false of the send, because a send
    materialises its executions when it is planned. A rule that reads as a
    safety and is not one is the worst available combination, which is why the
    two points shipped together.

    The send here carries `audience_resolution_mode="freeze"` **on purpose**.
    That value can no longer be written — `prepare_send_from_audience` refuses
    it by name — but five rows in the development database still hold it,
    because they record how those sends were planned and rewriting them would
    falsify history. So the question this class answers is the one an existing
    row asks: does a send planned as frozen re-resolve anyway? It does, and
    nothing but this test says so.
    """

    def test_an_exclusion_written_after_planning_removes_the_recipient(self, db):
        """Fired through `send_send_instance`, not by calling the reconciler.
        **The call site is what changed** — the reconciler already worked, and
        was skipped unless the mode said "rerun". A test that calls it directly
        would pass with that condition back in place."""
        recipient = db.recipient("opted_in", language="rr-excl")
        group = db.group("reresolve")
        db.pin(group, recipient)
        send_instance, execution = db.send_to(recipient, group=group)
        execution_id = execution.id

        # Planned as frozen, the way a row written before 2026-09-29 was, and
        # the exclusion arrives *between* planning and firing — the only
        # interesting moment. Excluding before planning would be caught by
        # `resolve_audience` and would prove nothing about the send path.
        send_instance.audience_resolution_mode = "freeze"
        db.session.add(AudienceRuleBlockDB(
            group_id=group.id, kind="exclude",
            criteria={"language": "rr-excl"},
            source="manual", position=0,
        ))
        db.session.commit()

        send_send_instance(
            db.session, send_instance.id, brand_id=send_instance.brand_id)

        survivors = {e.id for e in db.session.query(DeliveryExecutionDB).filter(
            DeliveryExecutionDB.send_instance_id == send_instance.id
        ).all()}
        assert execution_id not in survivors, (
            "an exclusion segment written after the send was planned did not "
            "remove the recipient — ADR-176 point 4. The send was planned as "
            "'freeze', which is exactly the row that must re-resolve anyway."
        )

    def test_the_recipient_is_there_without_an_exclusion(self, db):
        """Without this the test above passes against a reconciler that drops
        everybody, or a pin that never resolved. Same shape as the pair in
        `test_audience_api.TestExcludeBeatsPin`, for the same reason."""
        recipient = db.recipient("opted_in", language="rr-keep")
        group = db.group("reresolve-keep")
        db.pin(group, recipient)
        send_instance, execution = db.send_to(recipient, group=group)
        execution_id = execution.id
        send_instance.audience_resolution_mode = "freeze"
        db.session.commit()

        send_send_instance(
            db.session, send_instance.id, brand_id=send_instance.brand_id)

        survivors = {e.id for e in db.session.query(DeliveryExecutionDB).filter(
            DeliveryExecutionDB.send_instance_id == send_instance.id
        ).all()}
        assert execution_id in survivors, (
            "re-resolution dropped a consenting, pinned recipient that no "
            "exclude block touched, so the exclusion test proves nothing"
        )


class TestASendIsNeverStrandedInSending:
    """task-14. The status transition to "sending" is the claim: once it is
    committed, the guard refuses every later attempt. An exception that
    escaped between the claim and the send loop used to leave the instance in
    "sending" forever, with nothing sent and no way back.

    Two halves, one test each. Read-only preflight — the snapshot, the
    provider, the channel — runs BEFORE the claim, so a refusal leaves the
    send as it was and retryable once fixed. Everything after the claim is
    inside one handler, so any exception moves the send to "failed", which the
    guard allows to be retried.

    Lives here because this file owns the send fixture.
    """

    def test_an_unsupported_provider_is_refused_before_the_claim(self, db):
        recipient = db.recipient("opted_in")
        send_instance, _ = db.send_to(recipient)
        send_instance.provider = "no-such-provider"
        db.session.commit()

        with pytest.raises(ValueError, match="Unsupported provider"):
            send_send_instance(db.session, send_instance.id, brand_id=send_instance.brand_id)
        db.session.rollback()
        db.session.refresh(send_instance)

        assert send_instance.status == "draft", (
            f"a refused provider left the send {send_instance.status!r} — it was "
            "claimed before a read-only check that could refuse it"
        )

        # And the way back exists: fix the configuration, send again.
        send_instance.provider = "mock"
        db.session.commit()
        send_send_instance(db.session, send_instance.id, brand_id=send_instance.brand_id)
        db.session.refresh(send_instance)
        assert send_instance.status in ("sent", "no_recipients", "partial_failed")

    def test_a_database_error_after_the_claim_leaves_the_send_failed_not_sending(
        self, db, monkeypatch
    ):
        """A REAL database error, deliberately. A plain Python exception would
        leave the session usable, and the handler's rollback would never be
        needed; a failed statement poisons the session, so a handler that only
        committed would itself raise and leave the send "sending" after all."""
        from sqlalchemy import text as sql
        from sqlalchemy.exc import ProgrammingError
        import app.delivery.service as delivery

        recipient = db.recipient("opted_in")
        send_instance, _ = db.send_to(recipient)
        db.session.commit()

        def broken_gate(session, *args, **kwargs):
            session.execute(sql("SELECT * FROM no_such_table_task14"))

        monkeypatch.setattr(delivery, "run_exclusion_stack", broken_gate)
        with pytest.raises(ProgrammingError):
            send_send_instance(db.session, send_instance.id, brand_id=send_instance.brand_id)
        monkeypatch.undo()

        db.session.rollback()
        db.session.refresh(send_instance)
        assert send_instance.status == "failed", (
            f"the send is {send_instance.status!r} after an error past the claim"
        )

        # Retryable: the guard refuses only sending and sent.
        send_send_instance(db.session, send_instance.id, brand_id=send_instance.brand_id)
        db.session.refresh(send_instance)
        assert send_instance.status in ("sent", "no_recipients", "partial_failed")

    def test_through_approvals_a_refusal_leaves_request_and_send_agreeing(self, db):
        """The entry's worse half: `send_fire` treats a ValueError as a clean
        refusal, so the request was recorded failed while the send stayed
        wedged. Now the send is untouched, and can be requested again."""
        from app.approvals.actions import send_fire

        recipient = db.recipient("opted_in")
        send_instance, _ = db.send_to(recipient)
        send_instance.provider = "no-such-provider"
        db.session.commit()

        result = send_fire.execute(
            db.session, {"send_instance_id": send_instance.id},
            brand_id=send_instance.brand_id,
        )
        db.session.rollback()
        db.session.refresh(send_instance)

        assert not result.ok
        assert send_instance.status == "draft"
