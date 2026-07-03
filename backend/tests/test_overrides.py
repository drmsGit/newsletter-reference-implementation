"""
Tests for the override_events module.

Uses FastAPI TestClient against the real database — no mocks.
Requires the dev database to be running with at least:
  - content_records id=1, id=2
  - module_instances id=1
  - decision_slots id=1
  - send_instances id=1

Run with: pytest tests/test_overrides.py -v
"""
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

# IDs that exist in the dev database after normal seeding
CONTENT_SYSTEM = 1   # Mallorca Beach Walk — what the system would have chosen
CONTENT_OVERRIDE = 2  # Rome City Weekend — what the manager chose
MODULE_INSTANCE_ID = 2
DECISION_SLOT_ID = 1
SEND_INSTANCE_ID = 1


@pytest.fixture
def created_override():
    """Creates a content override event and returns the response JSON."""
    response = client.post("/overrides/", json={
        "override_type": "content",
        "module_instance_id": MODULE_INSTANCE_ID,
        "decision_slot_id": DECISION_SLOT_ID,
        "send_instance_id": SEND_INSTANCE_ID,
        "system_content_record_id": CONTENT_SYSTEM,
        "override_content_record_id": CONTENT_OVERRIDE,
        "overridden_by": "test@example.com",
        "reason": "City weekend fits the spring campaign better",
    })
    assert response.status_code == 200
    return response.json()


class TestCreateOverrideEvent:
    def test_creates_with_all_fields(self, created_override):
        data = created_override
        assert data["override_type"] == "content"
        assert data["module_instance_id"] == MODULE_INSTANCE_ID
        assert data["decision_slot_id"] == DECISION_SLOT_ID
        assert data["send_instance_id"] == SEND_INSTANCE_ID
        assert data["system_content_record_id"] == CONTENT_SYSTEM
        assert data["override_content_record_id"] == CONTENT_OVERRIDE
        assert data["overridden_by"] == "test@example.com"
        assert data["reason"] == "City weekend fits the spring campaign better"
        assert data["outcome_delta"] is None  # always null at creation
        assert "id" in data
        assert "created_at" in data

    def test_creates_without_optional_fields(self):
        response = client.post("/overrides/", json={
            "override_type": "content",
            "system_content_record_id": CONTENT_SYSTEM,
            "override_content_record_id": CONTENT_OVERRIDE,
            "overridden_by": "test@example.com",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["module_instance_id"] is None
        assert data["decision_slot_id"] is None
        assert data["send_instance_id"] is None
        assert data["reason"] is None
        assert data["outcome_delta"] is None


class TestGetOverrideEvent:
    def test_get_existing(self, created_override):
        override_id = created_override["id"]
        response = client.get(f"/overrides/{override_id}")
        assert response.status_code == 200
        assert response.json()["id"] == override_id

    def test_get_nonexistent_returns_404(self):
        response = client.get("/overrides/999999")
        assert response.status_code == 404


class TestListOverrideEvents:
    def test_list_returns_array(self, created_override):
        response = client.get("/overrides/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_filter_by_module_instance(self, created_override):
        response = client.get(f"/overrides/?module_instance_id={MODULE_INSTANCE_ID}")
        assert response.status_code == 200
        results = response.json()
        assert all(r["module_instance_id"] == MODULE_INSTANCE_ID for r in results)

    def test_filter_by_send_instance(self, created_override):
        response = client.get(f"/overrides/?send_instance_id={SEND_INSTANCE_ID}")
        assert response.status_code == 200
        results = response.json()
        assert all(r["send_instance_id"] == SEND_INSTANCE_ID for r in results)


class TestRecordOutcomeDelta:
    def test_patch_outcome_fills_delta(self, created_override):
        override_id = created_override["id"]
        outcome = {
            "outcome_delta": {
                "system_open_rate": 0.21,
                "override_open_rate": 0.18,
                "system_click_rate": 0.04,
                "override_click_rate": 0.03,
            }
        }
        response = client.patch(f"/overrides/{override_id}/outcome", json=outcome)
        assert response.status_code == 200
        data = response.json()
        assert data["outcome_delta"]["system_open_rate"] == 0.21
        assert data["outcome_delta"]["override_open_rate"] == 0.18

    def test_patch_outcome_nonexistent_returns_404(self):
        response = client.patch("/overrides/999999/outcome", json={
            "outcome_delta": {"system_open_rate": 0.21}
        })
        assert response.status_code == 404

    def test_patch_outcome_preserves_other_fields(self, created_override):
        override_id = created_override["id"]
        client.patch(f"/overrides/{override_id}/outcome", json={
            "outcome_delta": {"system_open_rate": 0.21}
        })
        response = client.get(f"/overrides/{override_id}")
        data = response.json()
        assert data["overridden_by"] == "test@example.com"
        assert data["reason"] == "City weekend fits the spring campaign better"
        assert data["system_content_record_id"] == CONTENT_SYSTEM
