"""A provider event and its mandatory effects are committed together (task-319).

`process_provider_webhook_event` committed the raw engagement event first and
applied its effects afterwards — signal contributions, and for a complaint or
hard bounce the opt-out (ADR-106, ADR-163). If an effect failed, the event was
already stored, so the provider's retry of the same event was answered
"duplicate" and the opt-out never landed: the person stayed mailable after
complaining. Found by the external review of 2026-10-09. The event and its
effects now commit as one transaction; a failure rolls all of it back, and the
provider's retry processes the event from the start.
"""
import uuid

import pytest

from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.insight.db_models import EngagementEventDB
from app.providers.adapters.resend import NormalizedEvent
from app.providers.service import process_provider_webhook_event
from app.recipients import service as recipients_service
from app.recipients.consent import is_consenting
from app.recipients.db_models import ConsentEventDB
from app.snapshots.service import create_snapshot_for_variant
from tests import test_render_skip as _render_skip

# Borrowed fixtures: a real variant, consenting recipients and a recording mock
# provider, all cleaned up afterwards.
db = _render_skip.db
world = _render_skip.world


@pytest.fixture
def sent(db, world):
    """One recipient with a sent execution carrying a provider message id."""
    brand = world["brand"]
    person = world["person"]()
    variant = world["variant"](static=True, slots=0)
    snapshot = create_snapshot_for_variant(db, variant.id, brand_id=brand.id)
    world["made"]["snapshots"].append(snapshot.id)
    send = SendInstanceDB(snapshot_id=snapshot.id, brand_id=brand.id, name="task-319", status="sent", provider="mock")
    db.add(send)
    db.flush()
    world["made"]["sends"].append(send.id)
    message_id = f"msg-{uuid.uuid4().hex}"
    execution = DeliveryExecutionDB(send_instance_id=send.id, recipient_id=person.id, status="sent", provider="mock",
                                    channel="email", purpose="marketing", provider_message_id=message_id)
    db.add(execution)
    db.commit()
    yield person, brand, message_id, execution.id
    db.query(EngagementEventDB).filter(EngagementEventDB.delivery_execution_id == execution.id).delete()
    db.commit()


def _complaint(message_id: str, event_id: str) -> NormalizedEvent:
    return NormalizedEvent(provider="resend", provider_message_id=message_id, event_type="complaint",
                           provider_event_id=event_id, event_data={}, suppresses_consent=True)


def _consenting(db, person, brand) -> bool:
    db.expire_all()
    return is_consenting(db, person.id, brand.id, channel="email", purpose="marketing")


def test_a_complaint_whose_opt_out_failed_is_processed_again_on_retry(db, sent, monkeypatch):
    person, brand, message_id, _ = sent
    event = _complaint(message_id, f"evt-{uuid.uuid4().hex}")
    real = recipients_service.suppress_recipient

    def fails(*args, **kwargs):
        raise RuntimeError("database refused mid-way")

    monkeypatch.setattr(recipients_service, "suppress_recipient", fails)
    with pytest.raises(RuntimeError):
        process_provider_webhook_event(db, event)
    # No rollback here: the handler must leave the session clean itself, or a
    # caller reusing it would find the half-written event and call the retry
    # a duplicate.
    assert _consenting(db, person, brand), "the failed attempt must leave nothing behind"

    monkeypatch.setattr(recipients_service, "suppress_recipient", real)
    result = process_provider_webhook_event(db, event)       # the provider's retry
    assert result.status == "matched", "the retry was answered duplicate, so the opt-out never landed"
    assert not _consenting(db, person, brand), "the complaint did not opt the person out"


def test_a_completed_event_retried_is_a_duplicate_and_changes_nothing(db, sent):
    person, brand, message_id, _ = sent
    event = _complaint(message_id, f"evt-{uuid.uuid4().hex}")
    assert process_provider_webhook_event(db, event).status == "matched"
    count = db.query(ConsentEventDB).filter_by(recipient_id=person.id).count()

    assert process_provider_webhook_event(db, event).status == "duplicate"
    assert db.query(ConsentEventDB).filter_by(recipient_id=person.id).count() == count
    assert not _consenting(db, person, brand)
