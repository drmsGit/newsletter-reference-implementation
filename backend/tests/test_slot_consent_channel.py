"""A decision slot checks consent on its own channel (task-321).

`execute_decision_slot` called `require_consent` without a channel, which
defaults to email. So a push slot refused a recipient consenting to push only
— and, since the send re-raises a consent refusal, failed a valid push send —
while an email-only recipient passed the gate for a push slot. Consent is per
channel and purpose (ADR-163); the slot's channel is its variant's. Found by
the external review of 2026-10-09.
"""
import pytest

from app.decision.service import execute_decision_slot as real_execute  # bound before the fixture's fake
from app.campaigns.db_models import DecisionSlotDB
from app.recipients.consent import ConsentDenied
from tests import test_render_skip as _render_skip

db = _render_skip.db
world = _render_skip.world


def _slot_of(db, variant) -> int:
    return db.query(DecisionSlotDB.id).filter(DecisionSlotDB.variant_id == variant.id).scalar()


def _decide(db, slot_id, recipient_id):
    """The real engine. 'Nothing to pick' (ValueError) is fine here; only a
    consent refusal is what these tests are about."""
    try:
        real_execute(db, slot_id, recipient_id=recipient_id)
    except ConsentDenied:
        raise
    except ValueError:
        pass


def test_a_push_slot_accepts_push_consent_alone(db, world):
    variant = world["variant"]("push", slots=1)
    person = world["person"]("push")
    _decide(db, _slot_of(db, variant), person.id)     # must not raise ConsentDenied


def test_email_consent_alone_does_not_satisfy_a_push_slot(db, world):
    variant = world["variant"]("push", slots=1)
    person = world["person"]("email")
    with pytest.raises(ConsentDenied):
        _decide(db, _slot_of(db, variant), person.id)


def test_a_push_send_with_a_personal_slot_completes(db, world, monkeypatch):
    monkeypatch.setattr("app.decision.service.execute_decision_slot", real_execute)
    variant = world["variant"]("push", slots=1)
    person = world["person"]("push")
    _, outcome = world["send"](variant, [person])     # raised ConsentDenied before the fix
    assert outcome[person.id][0] in ("sent", "excluded")
