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

NOT covered here, deliberately: the open P0 — a recipient opted out *after* the
audience was frozen is still sent to, because `send_send_instance` re-checks
nothing. That needs a full send-instance fixture and is the regression test for
the P0 fix itself; it belongs with that fix, in the ordered-stack shape
ADR-163 §8 prescribes.

Uses the real database, like test_overrides.py — fixtures create their own
throwaway recipients and delete them again, so nothing depends on seed ids.

Run with: pytest tests/test_consent_gates.py -v
"""
import uuid

import pytest

from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB
from app.audience.service import find_by_criteria, resolve_audience
from app.database import SessionLocal
from app.decision.service import execute_decision_slot
from app.recipients.consent import record_consent
from app.recipients.db_models import (
    AddressabilityDB,
    ConsentEventDB,
    RecipientDB,
)

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
    address deliberately is not, which is what the deduplication test exercises.
    """
    recipient = RecipientDB(
        external_id=f"test-consent-{uuid.uuid4()}",
        email=email or f"{uuid.uuid4()}@example.invalid",
        language=language,
        status="active",
    )
    db.add(recipient)
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

    class Tracker:
        def __init__(self, session):
            self.session = session

        def recipient(self, consent_status, email=None, language=None):
            record = _make_recipient(self.session, consent_status, email, language)
            created_recipients.append(record.id)
            return record

        def group(self, name="test-consent-group"):
            group = AudienceGroupDB(name=f"{name}-{uuid.uuid4()}")
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
        if created_recipients:
            # Consent events and addresses are FK-bound to the recipient, so
            # they go first or the delete below fails.
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
