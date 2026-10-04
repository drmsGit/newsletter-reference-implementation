"""A module is filled from a new decision slot in one write (task-264, slice 7).

Variant Editor interview 1.3: a slot is configured on its module, in place.
Creating a slot and binding the module to it were two writes, and a failure
between them left a slot nothing used. One POST now does both, states the
module's version (ADR-180 point 2), and is audited.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.audit import service as audit
from app.audit.db_models import AuditEventDB
from app.auth.permissions import CAMPAIGNS_MANAGE, VIEW
from app.campaigns.db_models import CampaignDB, DecisionSlotDB, ModuleInstanceDB, VariantDB
from app.content.db_models import ContentRecordDB
from main import app
from tests.machine import editor, machine

client = TestClient(app, raise_server_exceptions=False)

# One editing machine per test: several writes as different machines would
# meet each other's fence (task-254).
pytestmark = pytest.mark.usefixtures("one_editor")


@pytest.fixture
def world(db, default_brand):
    campaign = CampaignDB(brand_id=default_brand.id, name=f"att-{uuid.uuid4().hex[:6]}")
    db.add(campaign); db.flush()
    variant = VariantDB(campaign_id=campaign.id, channel="email", name="v", status="draft")
    record = ContentRecordDB(title="r", content={}, status="active", brand_id=default_brand.id)
    db.add_all([variant, record]); db.flush()
    catalogue = ModuleInstanceDB(variant_id=variant.id, module_type="img_left", position=1,
                                 content_record_id=record.id)
    static = ModuleInstanceDB(variant_id=variant.id, module_type="cta", position=2, module_data={})
    db.add_all([catalogue, static]); db.commit()
    yield {"campaign": campaign, "variant": variant, "catalogue": catalogue, "static": static}
    db.rollback()
    db.query(AuditEventDB).filter(AuditEventDB.subject_type.in_(["decision_slot", "module"]),
                                  AuditEventDB.detail["variant_id"].as_integer() == variant.id).delete(
        synchronize_session=False)
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant.id).delete()
    db.query(DecisionSlotDB).filter(DecisionSlotDB.variant_id == variant.id).delete()
    db.query(VariantDB).filter(VariantDB.id == variant.id).delete()
    db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
    db.query(ContentRecordDB).filter(ContentRecordDB.id == record.id).delete()
    db.commit()


def _attach(module_id, token=None, **body):
    with editor([CAMPAIGNS_MANAGE, VIEW]) as headers:
        if token is not None:
            headers = {**headers, "If-Match": token}
        return client.post(f"/campaigns/modules/{module_id}/decision-slot", json=body, headers=headers)


def _token(campaign_id, module_id):
    with editor([VIEW]) as headers:
        composed = client.get(f"/campaigns/{campaign_id}/composition", headers=headers).json()
    return next(m for m in composed["variants"][0]["modules"] if m["id"] == module_id)["updated_at"]


def test_a_catalogue_module_gets_a_new_slot_and_is_bound_to_it(db, world):
    m = world["catalogue"]
    response = _attach(m.id, _token(world["campaign"].id, m.id), decision_strategy="recipient_top_score")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["slot"]["variant_id"] == world["variant"].id
    assert body["slot"]["decision_strategy"] == "recipient_top_score"
    # The strategy's declared defaults are filled in, as on any slot create.
    assert body["slot"]["strategy_config"]["preference_score_weight"] == 10
    db.expire_all()
    module = db.get(ModuleInstanceDB, m.id)
    assert (module.decision_slot_id, module.content_record_id) == (body["slot"]["id"], None)
    assert body["module"]["updated_at"] != m.updated_at.isoformat()


def test_a_stale_module_version_is_refused_and_no_slot_is_left_behind(db, world):
    m = world["catalogue"]
    token = _token(world["campaign"].id, m.id)
    with editor([CAMPAIGNS_MANAGE]) as headers:
        client.put(f"/campaigns/modules/{m.id}", json={"module_type": "img_left"}, headers=headers)
    assert _attach(m.id, token).status_code == 409
    assert db.query(DecisionSlotDB).filter(DecisionSlotDB.variant_id == world["variant"].id).count() == 0


def test_a_static_module_takes_no_slot(db, world):
    response = _attach(world["static"].id)
    assert response.status_code == 400, response.text
    assert db.query(DecisionSlotDB).filter(DecisionSlotDB.variant_id == world["variant"].id).count() == 0


def test_an_unknown_strategy_is_refused_and_leaves_nothing(db, world):
    assert _attach(world["catalogue"].id, decision_strategy="no_such").status_code == 400
    assert db.query(DecisionSlotDB).filter(DecisionSlotDB.variant_id == world["variant"].id).count() == 0


def test_another_brands_module_is_not_found(world, foreign_api):
    with foreign_api([CAMPAIGNS_MANAGE]) as headers:
        response = client.post(f"/campaigns/modules/{world['catalogue'].id}/decision-slot",
                               json={}, headers=headers)
    assert response.status_code == 404


def test_it_is_audited_as_both_writes(db, world):
    response = _attach(world["catalogue"].id)
    assert response.status_code == 200, response.text
    actions = {e.action for e in db.query(AuditEventDB).filter(
        AuditEventDB.detail["variant_id"].as_integer() == world["variant"].id)}
    assert {audit.DECISION_SLOT_CREATED, audit.MODULE_UPDATED} <= actions
