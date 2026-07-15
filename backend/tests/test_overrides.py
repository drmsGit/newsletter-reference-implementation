"""
Tests for the content overrides module (the functional override layer).

Uses FastAPI TestClient against the real database — no mocks.
Assumes the normal seed (reset_all_data.sql), which provides:
  - content_records id=1 (Mallorca), id=2 (Rome), id=3 (Tenerife)
  - module_instances: id=2 and id=5 are img_left (cms:true); id=1 is hero (cms:false)
  - module id=2 already carries the seed's one active override, so tests use the
    otherwise-clean cms module id=5.

Run with: pytest tests/test_overrides.py -v
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from app.database import SessionLocal
from app.overrides.db_models import ContentOverrideDB

client = TestClient(app)

CONTENT_SYSTEM = 1     # Mallorca — what the system would have chosen
CONTENT_OVERRIDE = 2   # Rome — what the manager chose
CMS_MODULE_ID = 5      # variant 2's img_left, no seed override on it
STATIC_MODULE_ID = 1   # hero, cms:false — overrides must be refused here


def _delete_override(override_id: int) -> None:
    db = SessionLocal()
    try:
        db.query(ContentOverrideDB).filter(ContentOverrideDB.id == override_id).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def record_pin_override():
    """Creates a record-pin override on the clean cms module, cleans up after."""
    response = client.post("/overrides/", json={
        "module_instance_id": CMS_MODULE_ID,
        "override_content_record_id": CONTENT_OVERRIDE,
        "system_content_record_id": CONTENT_SYSTEM,
        "overridden_by": "test@example.com",
        "reason": "City weekend fits the spring campaign better",
    })
    assert response.status_code == 200, response.text
    data = response.json()
    yield data
    _delete_override(data["id"])


class TestCreateContentOverride:
    def test_creates_record_pin(self, record_pin_override):
        data = record_pin_override
        assert data["module_instance_id"] == CMS_MODULE_ID
        assert data["override_content_record_id"] == CONTENT_OVERRIDE
        assert data["system_content_record_id"] == CONTENT_SYSTEM
        assert data["field_overrides"] is None
        assert data["active"] is True
        assert data["reverted_at"] is None
        assert data["outcome_delta"] is None
        assert "id" in data and "created_at" in data

    def test_creates_field_override(self):
        response = client.post("/overrides/", json={
            "module_instance_id": CMS_MODULE_ID,
            "field_overrides": {"headline_medium": "A shorter headline"},
            "overridden_by": "test@example.com",
        })
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["field_overrides"]["headline_medium"] == "A shorter headline"
        assert data["override_content_record_id"] is None
        _delete_override(data["id"])

    def test_rejects_empty_override(self):
        response = client.post("/overrides/", json={
            "module_instance_id": CMS_MODULE_ID,
            "overridden_by": "test@example.com",
        })
        assert response.status_code == 400
        assert "change something" in response.json()["detail"]

    def test_rejects_unknown_field_key(self):
        response = client.post("/overrides/", json={
            "module_instance_id": CMS_MODULE_ID,
            "field_overrides": {"not_a_real_field": "x"},
            "overridden_by": "test@example.com",
        })
        assert response.status_code == 400
        assert "not in the" in response.json()["detail"]

    def test_rejects_non_cms_module(self):
        response = client.post("/overrides/", json={
            "module_instance_id": STATIC_MODULE_ID,
            "override_content_record_id": CONTENT_OVERRIDE,
            "overridden_by": "test@example.com",
        })
        assert response.status_code == 400
        assert "not a CMS-backed" in response.json()["detail"]

    def test_rejects_second_active_on_same_module(self, record_pin_override):
        response = client.post("/overrides/", json={
            "module_instance_id": CMS_MODULE_ID,
            "override_content_record_id": CONTENT_OVERRIDE,
            "overridden_by": "test@example.com",
        })
        assert response.status_code == 400
        assert "already has an active override" in response.json()["detail"]


class TestGetContentOverride:
    def test_get_existing(self, record_pin_override):
        override_id = record_pin_override["id"]
        response = client.get(f"/overrides/{override_id}")
        assert response.status_code == 200
        assert response.json()["id"] == override_id

    def test_get_nonexistent_returns_404(self):
        assert client.get("/overrides/999999").status_code == 404


class TestListContentOverrides:
    def test_filter_by_module_instance(self, record_pin_override):
        response = client.get(f"/overrides/?module_instance_id={CMS_MODULE_ID}")
        assert response.status_code == 200
        results = response.json()
        assert all(r["module_instance_id"] == CMS_MODULE_ID for r in results)
        assert any(r["id"] == record_pin_override["id"] for r in results)

    def test_filter_by_active(self, record_pin_override):
        response = client.get("/overrides/?active=true")
        assert response.status_code == 200
        assert all(r["active"] is True for r in response.json())


class TestResetContentOverride:
    def test_reset_deactivates(self, record_pin_override):
        override_id = record_pin_override["id"]
        response = client.post(f"/overrides/{override_id}/reset")
        assert response.status_code == 200
        data = response.json()
        assert data["active"] is False
        assert data["reverted_at"] is not None

    def test_reset_frees_the_module_for_a_new_override(self, record_pin_override):
        # After reset, the one-active-per-module slot is free again.
        client.post(f"/overrides/{record_pin_override['id']}/reset")
        response = client.post("/overrides/", json={
            "module_instance_id": CMS_MODULE_ID,
            "override_content_record_id": CONTENT_OVERRIDE,
            "overridden_by": "test@example.com",
        })
        assert response.status_code == 200, response.text
        _delete_override(response.json()["id"])

    def test_reset_nonexistent_returns_404(self):
        assert client.post("/overrides/999999/reset").status_code == 404


class TestRecordOutcomeDelta:
    def test_patch_outcome_merges(self, record_pin_override):
        override_id = record_pin_override["id"]
        client.patch(f"/overrides/{override_id}/outcome", json={
            "outcome_delta": {"system_open_rate": 0.21}
        })
        response = client.patch(f"/overrides/{override_id}/outcome", json={
            "outcome_delta": {"override_open_rate": 0.18}
        })
        assert response.status_code == 200
        delta = response.json()["outcome_delta"]
        # Both keys survive — incremental merge, not wholesale replace.
        assert delta["system_open_rate"] == 0.21
        assert delta["override_open_rate"] == 0.18

    def test_patch_outcome_nonexistent_returns_404(self):
        response = client.patch("/overrides/999999/outcome", json={
            "outcome_delta": {"system_open_rate": 0.21}
        })
        assert response.status_code == 404
