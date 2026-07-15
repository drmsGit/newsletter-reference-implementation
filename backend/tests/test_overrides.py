"""
Tests for the content overrides module (the functional override layer).

Uses FastAPI TestClient against the real database — no mocks.
Assumes the normal seed (reset_all_data.sql), which provides:
  - content_records id=1 (Mallorca), id=2 (Rome)
  - module id=5  = img_left, decision-slot driven, no seed override (clean target)
  - module id=1  = hero, references content_record 1 (static content, cms:false)
  - module id=3  = cta, no content record / no decision slot (not overrideable)
  - module id=2  = img_left, already carries the seed's one active override

Overrides are field edits only. Swapping the whole content record is not an
override — for-all means "use static content"; segment-targeted content belongs
to the separate guaranteed-placement concept.

Run with: pytest tests/test_overrides.py -v
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from app.database import SessionLocal
from app.overrides.db_models import ContentOverrideDB

client = TestClient(app)

DECISION_MODULE = 5      # img_left via decision slot, no seed override
STATIC_MODULE = 1        # hero, references content record 1
NON_CONTENT_MODULE = 3   # cta, no content ref


def _delete_override(override_id: int) -> None:
    db = SessionLocal()
    try:
        db.query(ContentOverrideDB).filter(ContentOverrideDB.id == override_id).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def field_override():
    """Case 1: a field override on the clean decision module. Cleans up after."""
    response = client.post("/overrides/", json={
        "module_instance_id": DECISION_MODULE,
        "field_overrides": {"headline_medium": "This could interest you"},
        "overridden_by": "test@example.com",
        "reason": "Consistent headline across the personalized picks",
    })
    assert response.status_code == 200, response.text
    data = response.json()
    yield data
    _delete_override(data["id"])


class TestCreateFieldOverride:
    def test_creates_on_decision_module(self, field_override):
        data = field_override
        assert data["module_instance_id"] == DECISION_MODULE
        assert data["field_overrides"]["headline_medium"] == "This could interest you"
        assert data["active"] is True

    def test_creates_on_static_content_module(self):
        # Case 3: field override on a manually-selected content record (hero).
        response = client.post("/overrides/", json={
            "module_instance_id": STATIC_MODULE,
            "field_overrides": {"headline": "A tighter hero headline"},
            "overridden_by": "test@example.com",
        })
        assert response.status_code == 200, response.text
        _delete_override(response.json()["id"])


class TestRejectedOverrides:
    def test_override_on_non_content_module_rejected(self):
        response = client.post("/overrides/", json={
            "module_instance_id": NON_CONTENT_MODULE,
            "field_overrides": {"label": "x"},
            "overridden_by": "test@example.com",
        })
        assert response.status_code == 400
        assert "doesn't render a content record or decision slot" in response.json()["detail"]

    def test_empty_override_rejected(self):
        response = client.post("/overrides/", json={
            "module_instance_id": DECISION_MODULE,
            "overridden_by": "test@example.com",
        })
        assert response.status_code == 400
        assert "must set field_overrides" in response.json()["detail"]

    def test_unknown_field_key_rejected(self):
        response = client.post("/overrides/", json={
            "module_instance_id": DECISION_MODULE,
            "field_overrides": {"not_a_real_field": "x"},
            "overridden_by": "test@example.com",
        })
        assert response.status_code == 400
        assert "not in the" in response.json()["detail"]

    def test_second_active_on_same_module_rejected(self, field_override):
        response = client.post("/overrides/", json={
            "module_instance_id": DECISION_MODULE,
            "field_overrides": {"body_medium": "another edit"},
            "overridden_by": "test@example.com",
        })
        assert response.status_code == 400
        assert "already has an active override" in response.json()["detail"]


class TestGetAndList:
    def test_get_existing(self, field_override):
        response = client.get(f"/overrides/{field_override['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == field_override["id"]

    def test_get_nonexistent_returns_404(self):
        assert client.get("/overrides/999999").status_code == 404

    def test_filter_by_module_and_active(self, field_override):
        response = client.get(f"/overrides/?module_instance_id={DECISION_MODULE}&active=true")
        assert response.status_code == 200
        results = response.json()
        assert all(r["module_instance_id"] == DECISION_MODULE and r["active"] for r in results)
        assert any(r["id"] == field_override["id"] for r in results)


class TestResetAndOutcome:
    def test_reset_deactivates(self, field_override):
        response = client.post(f"/overrides/{field_override['id']}/reset")
        assert response.status_code == 200
        data = response.json()
        assert data["active"] is False
        assert data["reverted_at"] is not None

    def test_reset_frees_the_module(self, field_override):
        client.post(f"/overrides/{field_override['id']}/reset")
        response = client.post("/overrides/", json={
            "module_instance_id": DECISION_MODULE,
            "field_overrides": {"headline_medium": "new one"},
            "overridden_by": "test@example.com",
        })
        assert response.status_code == 200, response.text
        _delete_override(response.json()["id"])

    def test_outcome_delta_merges(self, field_override):
        oid = field_override["id"]
        client.patch(f"/overrides/{oid}/outcome", json={"outcome_delta": {"system_open_rate": 0.21}})
        response = client.patch(f"/overrides/{oid}/outcome", json={"outcome_delta": {"override_open_rate": 0.18}})
        assert response.status_code == 200
        delta = response.json()["outcome_delta"]
        assert delta["system_open_rate"] == 0.21 and delta["override_open_rate"] == 0.18

    def test_outcome_nonexistent_returns_404(self):
        response = client.patch("/overrides/999999/outcome", json={"outcome_delta": {"x": 1}})
        assert response.status_code == 404
