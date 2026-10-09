"""Signal-side webhook effects roll back and retry exactly once (task-319)."""
import uuid

import pytest

from app.insight import service as insight
from app.insight.db_models import EngagementEventDB
from app.providers.adapters.resend import NormalizedEvent
from app.providers.service import process_provider_webhook_event
from app.recipients.db_models import SignalContributionDB
from tests import test_click_attribution as fixtures

db = fixtures.db
delivered = fixtures.delivered


def test_failure_after_signal_write_rolls_back_event_and_retries_once(db, delivered, monkeypatch):
    event_id = f"signal-rollback-{uuid.uuid4().hex}"
    recipient_id = delivered["recipient"].id
    event = NormalizedEvent(provider="resend", provider_message_id=delivered["message_id"],
                            event_type="click", provider_event_id=event_id,
                            event_data={"content_record_id": delivered["record"].id})
    real = insight.record_contribution

    def write_then_fail(*args, **kwargs):
        real(*args, **kwargs)
        raise RuntimeError("interrupted after signal write")

    monkeypatch.setattr(insight, "record_contribution", write_then_fail)
    with pytest.raises(RuntimeError, match="interrupted after signal write"):
        process_provider_webhook_event(db, event)
    # No caller rollback: the handler must clean up its own partial transaction.
    assert db.query(EngagementEventDB).filter_by(provider_event_id=event_id).count() == 0
    assert db.query(SignalContributionDB).filter_by(recipient_id=recipient_id).count() == 0

    monkeypatch.setattr(insight, "record_contribution", real)
    assert process_provider_webhook_event(db, event).status == "matched"
    [stored] = db.query(EngagementEventDB).filter_by(provider_event_id=event_id).all()
    [contribution] = db.query(SignalContributionDB).filter_by(recipient_id=recipient_id).all()
    assert contribution.event_id == stored.id
    assert contribution.channel == "email"
    assert process_provider_webhook_event(db, event).status == "duplicate"
    assert db.query(EngagementEventDB).filter_by(provider_event_id=event_id).count() == 1
    assert db.query(SignalContributionDB).filter_by(recipient_id=recipient_id).count() == 1
