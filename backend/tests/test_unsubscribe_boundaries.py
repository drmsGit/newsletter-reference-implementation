"""Unsubscribe scope boundaries and atomic failure/retry (task-56; ADR-191)."""
import pytest
from fastapi.testclient import TestClient

from app.delivery.db_models import DeliveryExecutionDB
from app.recipients.consent import MARKETING, latest_consent_status, record_consent
from app.recipients.db_models import ConsentEventDB
from main import app
from tests import test_render_skip as fixtures

db = fixtures.db
world = fixtures.world
api = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def message(db, world):
    person = world["person"]("email")
    world["send"](world["variant"]("email", static=True, slots=0), [person])
    db.expire_all()
    execution = db.query(DeliveryExecutionDB).filter_by(recipient_id=person.id).order_by(
        DeliveryExecutionDB.id.desc()
    ).first()
    assert execution.status == "sent"
    assert execution.unsubscribe_token
    return person, f"/unsubscribe/{execution.unsubscribe_token}"


def test_default_opt_out_preserves_other_channels_purposes_and_people(db, world, message, foreign_brand):
    person, path = message
    other = world["person"]("email")
    cells = [
        (world["brand"].id, "push", MARKETING),
        (world["brand"].id, "email", "transactional"),
        (foreign_brand.id, "email", MARKETING),
        (foreign_brand.id, "push", "transactional"),
    ]
    for brand, channel, purpose in cells:
        record_consent(db, person.id, "opted_in", brand, source="test", channel=channel, purpose=purpose)

    response = api.post(path, data={"scope": "brand"})
    assert response.status_code == 200, response.text
    db.expire_all()
    assert latest_consent_status(db, person.id, world["brand"].id, channel="email", purpose=MARKETING) == "opted_out"
    for brand, channel, purpose in cells:
        assert latest_consent_status(db, person.id, brand, channel=channel, purpose=purpose) == "opted_in"
    assert latest_consent_status(db, other.id, world["brand"].id, channel="email", purpose=MARKETING) == "opted_in"


def test_everything_failure_rolls_back_all_cells_then_retry_is_idempotent(
    db, world, message, foreign_brand, monkeypatch
):
    from app.channels.registry import list_channels
    from app.settings import service as settings
    from app.subscriptions import service

    person, path = message
    old_option = settings.get_unsubscribe_offer_everything(db)
    settings.set_unsubscribe_offer_everything(db, True)
    record_consent(db, person.id, "opted_in", foreign_brand.id, source="test", channel="push", purpose=MARKETING)
    record_consent(db, person.id, "opted_in", world["brand"].id, source="test", channel="email", purpose="transactional")
    before = db.query(ConsentEventDB).filter_by(recipient_id=person.id).count()
    real_write = service.record_consent
    writes = []

    def fail_after_second_write(*args, **kwargs):
        event = real_write(*args, **kwargs)
        writes.append(event.id)
        if len(writes) == 2:
            raise RuntimeError("injected failure after two consent cells")
        return event

    try:
        with monkeypatch.context() as failed:
            failed.setattr(service, "record_consent", fail_after_second_write)
            response = api.post(path, data={"scope": "everything"})
        assert response.status_code == 500
        assert len(writes) == 2
        db.expire_all()
        assert db.query(ConsentEventDB).filter_by(recipient_id=person.id).count() == before, "partial opt-outs committed"

        retry = api.post(path, data={"scope": "everything"})
        assert retry.status_code == 200, retry.text
        db.expire_all()
        for brand in (world["brand"].id, foreign_brand.id):
            for channel in list_channels():
                assert latest_consent_status(db, person.id, brand, channel=channel.name, purpose=MARKETING) == "opted_out"
        assert latest_consent_status(db, person.id, world["brand"].id, channel="email", purpose="transactional") == "opted_in"
        after = db.query(ConsentEventDB).filter_by(recipient_id=person.id).count()
        assert api.post(path, data={"scope": "everything"}).status_code == 200
        db.expire_all()
        assert db.query(ConsentEventDB).filter_by(recipient_id=person.id).count() == after
    finally:
        db.rollback()
        settings.set_unsubscribe_offer_everything(db, old_option)
