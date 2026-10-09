"""The scheduled-send sweep fires only the working brand's due sends (task-315).

`process_due_scheduled_sends` selected every due scheduled send across brands
and fired each with its own brand, while the route checked `sends.execute` in
the caller's working brand only. So a credential granted `sends.execute` in
brand A, called with A as its working brand, fired brand B's mail. Found by
the external review of 2026-10-09. Fixed by carrying the working brand into
the sweep (ADR-172), as every other list and action does: a deployment with
several brands runs its scheduler once per brand.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.auth import integrations as ints
from app.auth.db_models import IntegrationCredentialDB
from app.auth.permissions import SENDS_EXECUTE
from app.database import SessionLocal
from app.delivery import service as delivery
from app.delivery.db_models import SendInstanceDB
from app.snapshots.db_models import SnapshotDB
from main import app
from tests.machine import machine

api = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def fired(monkeypatch):
    """Record what the sweep fires instead of rendering and sending it."""
    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(delivery, "send_send_instance",
                        lambda db, *, send_instance_id, brand_id: calls.append((send_instance_id, brand_id)))
    return calls


@pytest.fixture
def due(db):
    """A due scheduled send in a given brand, removed afterwards."""
    snapshot = db.query(SnapshotDB).order_by(SnapshotDB.id).first()
    if snapshot is None:
        pytest.skip("no snapshot in this database")
    made: list[int] = []

    def make(brand_id: int) -> int:
        row = SendInstanceDB(brand_id=brand_id, snapshot_id=snapshot.id, status="scheduled",
                             name=f"task-315 {uuid.uuid4().hex[:6]}",
                             scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=5))
        db.add(row)
        db.commit()
        made.append(row.id)
        return row.id

    yield make
    db.query(SendInstanceDB).filter(SendInstanceDB.id.in_(made)).delete(synchronize_session=False)
    db.commit()


def test_the_sweep_fires_only_the_given_brands_sends(db, due, fired, default_brand, foreign_brand):
    mine, theirs = due(default_brand.id), due(foreign_brand.id)
    triggered = delivery.process_due_scheduled_sends(db, brand_id=default_brand.id)
    assert mine in triggered and theirs not in triggered
    assert (theirs, foreign_brand.id) not in fired


def test_the_brand_is_required(db):
    with pytest.raises(TypeError):
        delivery.process_due_scheduled_sends(db)


def test_a_credential_for_one_brand_cannot_fire_another_brands_sends(due, fired, default_brand, foreign_brand):
    """The review's reproduction, through the route."""
    mine, theirs = due(default_brand.id), due(foreign_brand.id)
    with machine([SENDS_EXECUTE], brand_id=default_brand.id) as headers:
        key_id = headers["Authorization"].split()[1].split(".")[0]
        session = SessionLocal()
        try:
            credential = session.query(IntegrationCredentialDB).filter_by(key_id=key_id).one()
            ints.set_unattended_sending(session, credential.integration_id, True)
        finally:
            session.close()
        response = api.post("/delivery/process-due", headers=headers)
    assert response.status_code == 200, response.text
    assert theirs not in response.json()["send_instance_ids"], "brand B's send fired on brand A's grant"
    assert mine in response.json()["send_instance_ids"]
    assert [sid for sid, _ in fired if sid == theirs] == []


def test_the_jinja_button_fires_only_the_working_brands_sends(db, due, fired, default_brand, foreign_brand):
    """The frozen UI's button calls the same sweep; it is scoped the same way."""
    from tests.test_api_guard import signed_in

    mine, theirs = due(default_brand.id), due(foreign_brand.id)
    with signed_in(db) as (client, _token, csrf):
        response = client.post("/ui/deliveries/process-due", data={"csrf_token": csrf}, follow_redirects=False)
    assert response.status_code == 303, response.text
    fired_ids = [sid for sid, _ in fired]
    assert mine in fired_ids and theirs not in fired_ids
