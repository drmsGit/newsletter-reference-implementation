"""A module's override is set field by field in one write (task-256).

ADR-178 point 2 makes "override here" a per-field act and point 6 resets one
field ("removes that key; if the dict empties, the row deactivates") or the
whole module. The API could only create (refused while one is active) and
reset the whole row, so a second field took reset + create: two transactions,
no version check. Now one PUT states the whole set; the module's `updated_at`
is its version (ADR-180 point 2), so a stale override write is a 409.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.audit import service as audit
from app.audit.db_models import AuditEventDB
from app.auth.permissions import CAMPAIGNS_MANAGE, OVERRIDES_MANAGE, VIEW
from app.campaigns.db_models import CampaignDB, DecisionSlotDB, ModuleInstanceDB, VariantDB
from app.content.db_models import ContentRecordDB
from app.overrides.db_models import ContentOverrideDB
from main import app
from tests.machine import editor, machine

client = TestClient(app, raise_server_exceptions=False)

# One editing machine per test: several writes as different machines would
# meet each other's fence (task-254).
pytestmark = pytest.mark.usefixtures("one_editor")


@pytest.fixture
def world(db, default_brand):
    campaign = CampaignDB(brand_id=default_brand.id, name=f"ovf-{uuid.uuid4().hex[:6]}")
    db.add(campaign); db.flush()
    variant = VariantDB(campaign_id=campaign.id, channel="email", name="v", status="draft")
    record = ContentRecordDB(title="r", content={"headline_medium": "H"}, status="active",
                             brand_id=default_brand.id)
    db.add_all([variant, record]); db.flush()
    slot = DecisionSlotDB(variant_id=variant.id, name="s", decision_type="content_recommendation",
                          decision_strategy="top_score")
    db.add(slot); db.flush()
    bound = ModuleInstanceDB(variant_id=variant.id, module_type="img_left", position=1,
                             content_record_id=record.id)
    slotted = ModuleInstanceDB(variant_id=variant.id, module_type="img_left", position=2,
                               decision_slot_id=slot.id)
    db.add_all([bound, slotted]); db.commit()
    yield {"campaign": campaign, "bound": bound, "slotted": slotted}
    db.rollback()
    ids = [bound.id, slotted.id]
    db.query(AuditEventDB).filter(AuditEventDB.subject_type == "override",
                                  AuditEventDB.detail["module_instance_id"].as_integer().in_(ids)).delete(
        synchronize_session=False)
    db.query(ContentOverrideDB).filter(ContentOverrideDB.module_instance_id.in_(ids)).delete(
        synchronize_session=False)
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.id.in_(ids)).delete(synchronize_session=False)
    db.query(DecisionSlotDB).filter(DecisionSlotDB.id == slot.id).delete()
    db.query(VariantDB).filter(VariantDB.id == variant.id).delete()
    db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
    db.query(ContentRecordDB).filter(ContentRecordDB.id == record.id).delete()
    db.commit()


def _put(module_id, fields, token=None, reason=None):
    with editor([OVERRIDES_MANAGE, CAMPAIGNS_MANAGE, VIEW]) as headers:
        if token is not None:
            headers = {**headers, "If-Match": token}
        return client.put(f"/overrides/modules/{module_id}",
                          json={"field_overrides": fields, "reason": reason}, headers=headers)


def _rows(db, module_id):
    db.expire_all()
    return [(o.field_overrides, o.active) for o in db.query(ContentOverrideDB)
            .filter(ContentOverrideDB.module_instance_id == module_id).order_by(ContentOverrideDB.id)]


def _token(campaign_id, module_id):
    with editor([VIEW]) as headers:
        composed = client.get(f"/campaigns/{campaign_id}/composition", headers=headers).json()
    return next(m for m in composed["variants"][0]["modules"] if m["id"] == module_id)["updated_at"]


def test_one_field_then_a_second_then_reset_one_then_reset_all(db, world):
    m = world["bound"].id
    first = _put(m, {"headline_medium": "Short"}, reason="Shorter for this send")
    assert first.status_code == 200, first.text
    assert first.json()["override"]["reason"] == "Shorter for this send"
    second = _put(m, {"headline_medium": "Short", "body_medium": "B"})
    assert second.status_code == 200, second.text
    # Changed in place: still one row, the same one.
    assert second.json()["override"]["id"] == first.json()["override"]["id"]
    assert _rows(db, m) == [({"headline_medium": "Short", "body_medium": "B"}, True)]

    assert _put(m, {"body_medium": "B"}).status_code == 200            # reset one field
    assert _rows(db, m) == [({"body_medium": "B"}, True)]
    emptied = _put(m, {})                                               # reset the module
    assert emptied.status_code == 200 and emptied.json()["override"] is None
    assert _rows(db, m) == [({"body_medium": "B"}, False)], "a reset deactivates, it does not delete"


def test_the_module_version_covers_its_override(db, world):
    m, c = world["bound"].id, world["campaign"].id
    token = _token(c, m)
    fresh = _put(m, {"headline_medium": "Mine"}, token)
    assert fresh.status_code == 200, fresh.text
    assert fresh.json()["module_updated_at"] != token, "an override write must move the module's version"
    assert _put(m, {"headline_medium": "Stale"}, token).status_code == 409
    assert _rows(db, m) == [({"headline_medium": "Mine"}, True)]
    assert _token(c, m) == fresh.json()["module_updated_at"]


def test_a_field_the_manifest_does_not_declare_is_refused(db, world):
    response = _put(world["bound"].id, {"colour": "red"})
    assert response.status_code == 400, response.text
    assert _rows(db, world["bound"].id) == []


def test_a_slot_bound_module_is_never_overridden(db, world):
    response = _put(world["slotted"].id, {"headline_medium": "Pinned"})
    assert response.status_code == 400, response.text
    assert "decision slot" in response.json()["detail"]
    assert _rows(db, world["slotted"].id) == []


def test_another_brands_module_is_not_found(world, foreign_api):
    with foreign_api([OVERRIDES_MANAGE]) as headers:
        response = client.put(f"/overrides/modules/{world['bound'].id}",
                              json={"field_overrides": {"headline_medium": "x"}}, headers=headers)
    assert response.status_code == 404


def test_each_write_is_audited_as_what_it_did(db, world):
    m = world["bound"].id
    for fields in ({"headline_medium": "A"}, {"headline_medium": "B"}, {}):
        assert _put(m, fields).status_code == 200
    actions = [e.action for e in db.query(AuditEventDB).filter(
        AuditEventDB.subject_type == "override",
        AuditEventDB.detail["module_instance_id"].as_integer() == m).order_by(AuditEventDB.id)]
    assert actions == [audit.OVERRIDE_CREATED, audit.OVERRIDE_CHANGED, audit.OVERRIDE_RESET]
