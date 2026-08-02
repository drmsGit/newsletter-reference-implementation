"""
Tests for the content overrides module (the functional override layer).

Uses FastAPI TestClient against the real database — no mocks.
Fixtures are resolved by shape (see _find_module), not by seed id — these tests
run against the shared dev database, where hardcoded ids rot as soon as someone
deletes a module while building a campaign.

Previously assumed the seed (reset_all_data.sql) provided:
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
from app.campaigns.db_models import ModuleInstanceDB, VariantDB
from app.content.db_models import ContentRecordDB
from app.email_modules.registry import get_manifest
from app.overrides.db_models import ContentOverrideDB

client = TestClient(app)

def _find_module(**criteria) -> int:
    """Resolve a module instance by its *properties* rather than a fixed id.

    These tests used to hardcode seed ids (1, 3, 5). That is fragile against a
    shared dev database: deleting a module while building a campaign silently
    broke the suite, which is what happened here — ids 1 and 3 no longer exist.
    Selecting on the shape a test actually needs keeps it honest whatever the
    database contains.
    """
    db = SessionLocal()
    try:
        query = db.query(ModuleInstanceDB.id)
        if criteria.get("content"):
            query = query.filter(ModuleInstanceDB.content_record_id.isnot(None))
        else:
            query = query.filter(ModuleInstanceDB.content_record_id.is_(None))
        if criteria.get("slot"):
            query = query.filter(ModuleInstanceDB.decision_slot_id.isnot(None))
        else:
            query = query.filter(ModuleInstanceDB.decision_slot_id.is_(None))
        row = query.order_by(ModuleInstanceDB.id.asc()).first()
        if row is None:
            pytest.skip(
                f"no module instance matching {criteria} in this database",
                allow_module_level=True,
            )
        return row[0]
    finally:
        db.close()


def _allowed_field(module_id: int) -> str:
    """An override key this module's manifest actually accepts.

    Field names are per module type ('headline' on a hero, 'headline_medium' on
    an img_right), so a hardcoded field is as brittle as a hardcoded id — the
    test would fail on manifest grounds while looking like an override bug.
    """
    db = SessionLocal()
    try:
        module = db.query(ModuleInstanceDB).filter(ModuleInstanceDB.id == module_id).first()
        manifest = get_manifest(module.module_type) if module else None
        # Same source the service validates against: manifest.variables.
        fields = sorted(v.name for v in getattr(manifest, "variables", None) or [])
        if not fields:
            pytest.skip(
                f"module {module_id} has no overridable fields",
                allow_module_level=True,
            )
        return fields[0]
    finally:
        db.close()


# A module driven by a decision slot, and one that renders neither a content
# record nor a slot (so overriding it must be rejected). The static-content case
# gets its own throwaway module — see the static_module fixture.
DECISION_MODULE = _find_module(slot=True)
NON_CONTENT_MODULE = _find_module()


@pytest.fixture
def static_module():
    """A throwaway module bound to a static content record, removed afterwards.

    Built rather than found: the only pre-existing module with a content record
    is the one the seed already overrides, and a test that creates an override
    needs a clean target. Creating it also means this test no longer depends on
    the database happening to contain a suitable module.
    """
    db = SessionLocal()
    try:
        variant_row = db.query(VariantDB.id).order_by(VariantDB.id.asc()).first()
        content_row = (
            db.query(ContentRecordDB.id)
            .filter(ContentRecordDB.status == "active")
            .order_by(ContentRecordDB.id.asc())
            .first()
        )
        if variant_row is None or content_row is None:
            pytest.skip("no variant or active content record to build a module from")
        module = ModuleInstanceDB(
            variant_id=variant_row[0],
            module_type="img_right",
            position=9999,
            content_record_id=content_row[0],
            module_data={},
        )
        db.add(module)
        db.commit()
        module_id = module.id
    finally:
        db.close()

    yield module_id, _allowed_field(module_id)

    db = SessionLocal()
    try:
        db.query(ContentOverrideDB).filter(
            ContentOverrideDB.module_instance_id == module_id
        ).delete()
        db.query(ModuleInstanceDB).filter(ModuleInstanceDB.id == module_id).delete()
        db.commit()
    finally:
        db.close()


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

    def test_creates_on_static_content_module(self, static_module):
        # Case 3: field override on a manually-selected content record.
        module_id, field = static_module
        response = client.post("/overrides/", json={
            "module_instance_id": module_id,
            "field_overrides": {field: "A tighter headline"},
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
