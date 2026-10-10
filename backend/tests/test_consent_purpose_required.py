"""A consent assertion must say what it is for (task-343).

Since task-42 every internal consent function requires a purpose — a silent
default is how consent for one purpose gets recorded as another. The API's
assertion still defaulted it to "marketing". Decided 2026-10-09 (business
baseline P2-E2): the API refuses an assertion without a purpose. Which purposes
exist stays with task-134.
"""
from fastapi.testclient import TestClient

from app.auth.permissions import RECIPIENTS_CONSENT
from app.recipients.db_models import ConsentEventDB, ConsentSyncLogDB
from main import app
from tests import test_render_skip as _render_skip
from tests.machine import machine

api = TestClient(app, raise_server_exceptions=False)
db = _render_skip.db
world = _render_skip.world


def _assert(world, **body):
    person = world["person"]()
    with machine([RECIPIENTS_CONSENT], brand_id=world["brand"].id) as headers:
        response = api.post(f"/recipients/{person.external_id}/consent", headers=headers, json={
            "consent_status": "opted_out", "brand_id": world["brand"].id, "source": "crm", **body})
    return person, response


def test_an_assertion_without_a_purpose_is_refused(db, world):
    person, response = _assert(world)
    try:
        assert response.status_code == 422, response.text
        assert any(error["loc"][-1] == "purpose" for error in response.json()["detail"])
        db.expire_all()
        assert db.query(ConsentEventDB).filter_by(recipient_id=person.id, status="opted_out").count() == 0
    finally:     # before the fix this was accepted and logged; the log must go first
        db.query(ConsentSyncLogDB).filter_by(recipient_id=person.id).delete()
        db.commit()


def test_an_assertion_with_a_purpose_is_recorded(db, world):
    person, response = _assert(world, purpose="marketing")
    try:
        assert response.status_code == 200, response.text
        db.expire_all()
        assert db.query(ConsentEventDB).filter_by(recipient_id=person.id, status="opted_out",
                                                 purpose="marketing").count() == 1
    finally:
        db.query(ConsentSyncLogDB).filter_by(recipient_id=person.id).delete()
        db.commit()


def test_the_published_contract_says_so():
    schema = app.openapi()["components"]["schemas"]["ConsentSyncRequest"]
    assert "purpose" in schema["required"]
    assert "default" not in schema["properties"]["purpose"]
