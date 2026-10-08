"""A recipient's interest signals over the API answer instead of failing.

Found by the CI linter's first run (task-105, ADR-190: F811, a name defined
twice): `app/recipients/models.py` declared `RecipientPreference` twice. The
second shape — category name, for the recipient page's activity read model —
replaced the first, which `GET /recipients/{id}/preferences` and
`POST /recipients/preferences` build with a recipient id, so both answered 500.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.recipients.db_models import RecipientDB, SignalContributionDB
from main import app
from tests.machine import machine

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def scratch():
    db = SessionLocal()
    recipient = RecipientDB(external_id=f"pref-{uuid.uuid4().hex[:8]}", status="active")
    db.add(recipient); db.commit()
    rid = recipient.id
    yield rid
    db.rollback()
    db.query(SignalContributionDB).filter_by(recipient_id=rid).delete()
    db.query(RecipientDB).filter_by(id=rid).delete()
    db.commit()
    db.close()


def test_a_preference_is_recorded_and_listed(scratch):
    with machine(["view", "recipients.manage"]) as headers:
        created = client.post("/recipients/preferences", headers=headers,
                              json={"recipient_id": scratch, "category_id": 1, "score": 4.0})
        assert created.status_code == 200, created.text
        assert created.json()["recipient_id"] == scratch and created.json()["category_id"] == 1
        listed = client.get(f"/recipients/{scratch}/preferences", headers=headers)
    assert listed.status_code == 200, listed.text
    assert [(p["category_id"], p["score"] > 0) for p in listed.json()] == [(1, True)]
