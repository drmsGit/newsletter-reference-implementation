"""The send route reports what actually happened (task-323).

`POST /delivery/send-instances/{id}/send` returned `{"status": "sent"}`
whatever the outcome, while the service had already stored the true one —
sent, partial_failed, failed or no_recipients (task-98). Found by the
external review of 2026-10-09: an error reported as success. The route now
returns the persisted outcome, and the held-send approval's message names it.
"""
from fastapi.testclient import TestClient

from app.auth import integrations as ints
from app.auth.db_models import IntegrationCredentialDB
from app.auth.permissions import SENDS_EXECUTE
from app.database import SessionLocal
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.delivery.providers import mock as mock_module
from app.delivery.providers.base import SendResult
from app.snapshots.service import create_snapshot_for_variant
from main import app
from tests import test_render_skip as _render_skip
from tests.machine import machine

api = TestClient(app, raise_server_exceptions=False)
db = _render_skip.db
world = _render_skip.world


def _planned(db, world, people) -> int:
    brand = world["brand"]
    variant = world["variant"](static=True, slots=0)
    snapshot = create_snapshot_for_variant(db, variant.id, brand_id=brand.id)
    world["made"]["snapshots"].append(snapshot.id)
    send = SendInstanceDB(snapshot_id=snapshot.id, brand_id=brand.id, name="task-323", status="draft", provider="mock")
    db.add(send)
    db.flush()
    world["made"]["sends"].append(send.id)
    for person in people:
        db.add(DeliveryExecutionDB(send_instance_id=send.id, recipient_id=person.id, status="created",
                                   provider="mock", channel="email", purpose="marketing"))
    db.commit()
    return send.id


def _fire(send_id: int, brand_id: int):
    with machine([SENDS_EXECUTE], brand_id=brand_id) as headers:
        key_id = headers["Authorization"].split()[1].split(".")[0]
        with SessionLocal() as session:
            credential = session.query(IntegrationCredentialDB).filter_by(key_id=key_id).one()
            ints.set_unattended_sending(session, credential.integration_id, True)
        return api.post(f"/delivery/send-instances/{send_id}/send", headers=headers)


def test_a_send_whose_every_delivery_failed_is_not_reported_sent(db, world, monkeypatch):
    send_id = _planned(db, world, [world["person"](), world["person"]()])
    monkeypatch.setattr(mock_module.MockProvider, "send",
                        lambda self, address, artifact: SendResult(success=False, message="rejected"))
    response = _fire(send_id, world["brand"].id)
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "failed"}


def test_a_partly_failed_send_says_so(db, world, monkeypatch):
    send_id = _planned(db, world, [world["person"](), world["person"]()])
    capture = mock_module.MockProvider.send
    calls = {"n": 0}

    def second_rejected(self, address, artifact):
        calls["n"] += 1
        return capture(self, address, artifact) if calls["n"] == 1 else SendResult(success=False, message="no")

    monkeypatch.setattr(mock_module.MockProvider, "send", second_rejected)
    assert _fire(send_id, world["brand"].id).json() == {"status": "partial_failed"}


def test_a_send_with_nobody_to_send_to_is_not_reported_sent(db, world):
    send_id = _planned(db, world, [])
    assert _fire(send_id, world["brand"].id).json() == {"status": "no_recipients"}


def test_a_successful_send_still_says_sent(db, world):
    send_id = _planned(db, world, [world["person"]()])
    assert _fire(send_id, world["brand"].id).json() == {"status": "sent"}


def test_an_approved_send_that_failed_is_not_announced_as_sent(db, world, monkeypatch):
    """The held-send approval runs the same send; its message names the outcome."""
    from app.approvals.actions import send_fire

    send_id = _planned(db, world, [world["person"]()])
    monkeypatch.setattr(mock_module.MockProvider, "send",
                        lambda self, address, artifact: SendResult(success=False, message="rejected"))
    result = send_fire.execute(db, {"send_instance_id": send_id}, brand_id=world["brand"].id)
    assert result.message.startswith("Failed:"), result.message
