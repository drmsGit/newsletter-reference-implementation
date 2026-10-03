"""A module binds only its own brand's content and its own variant's slot (task-248).

`create_module_for_variant` and `update_module` scoped the variant to the
working brand and took `content_record_id` and `decision_slot_id` as given, and
rendering loads a bound record by id. So a manager in one brand could bind
another brand's record and preview or send it (ADR-150 point 8).

Every refusal has a control beside it: the same call with the brand's own
record or the variant's own slot succeeds, so a test cannot pass because the
route refuses everything. The foreign record lives in the foreign brand, never
the default one (conftest's rule).
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth import service as auth
from app.auth.permissions import CAMPAIGNS_MANAGE
from app.campaigns.db_models import CampaignDB, DecisionSlotDB, ModuleInstanceDB, VariantDB
from app.content.db_models import ContentRecordDB
from main import app
from tests.machine import machine

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def setup(db, default_brand, foreign_brand):
    campaign = CampaignDB(brand_id=default_brand.id, name=f"bind-{uuid.uuid4().hex[:6]}")
    db.add(campaign); db.flush()
    variant = VariantDB(campaign_id=campaign.id, channel="email", name="v", status="draft")
    other = VariantDB(campaign_id=campaign.id, channel="email", name="other", status="draft")
    own = ContentRecordDB(title="own", content={}, status="active", brand_id=default_brand.id)
    foreign = ContentRecordDB(title="foreign", content={}, status="active", brand_id=foreign_brand.id)
    db.add_all([variant, other, own, foreign]); db.flush()
    own_slot = DecisionSlotDB(variant_id=variant.id, name="own", decision_type="content_recommendation",
                              decision_strategy="top_score")
    other_slot = DecisionSlotDB(variant_id=other.id, name="other", decision_type="content_recommendation",
                                decision_strategy="top_score")
    db.add_all([own_slot, other_slot]); db.commit()
    yield {"campaign": campaign, "variant": variant, "own": own, "foreign": foreign,
           "own_slot": own_slot, "other_slot": other_slot}
    db.rollback()
    variant_ids = [variant.id, other.id]
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id.in_(variant_ids)).delete(
        synchronize_session=False)
    db.query(DecisionSlotDB).filter(DecisionSlotDB.variant_id.in_(variant_ids)).delete(
        synchronize_session=False)
    db.query(VariantDB).filter(VariantDB.id.in_(variant_ids)).delete(synchronize_session=False)
    db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
    db.query(ContentRecordDB).filter(ContentRecordDB.id.in_([own.id, foreign.id])).delete(
        synchronize_session=False)
    db.commit()


def _bindings(db, variant):
    db.expire_all()
    return [(m.content_record_id, m.decision_slot_id)
            for m in db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant.id)]


def _create(variant, **binding):
    with machine([CAMPAIGNS_MANAGE]) as headers:
        return client.post(f"/campaigns/variants/{variant.id}/modules",
                           json={"module_type": "img_left", **binding}, headers=headers)


class TestJsonCreate:
    def test_another_brands_record_is_refused(self, db, setup):
        response = _create(setup["variant"], content_record_id=setup["foreign"].id)
        assert response.status_code == 400, response.text
        assert _bindings(db, setup["variant"]) == []

    def test_the_brands_own_record_is_bound(self, db, setup):
        response = _create(setup["variant"], content_record_id=setup["own"].id)
        assert response.status_code == 200, response.text
        assert _bindings(db, setup["variant"]) == [(setup["own"].id, None)]

    def test_another_variants_slot_is_refused(self, db, setup):
        response = _create(setup["variant"], decision_slot_id=setup["other_slot"].id)
        assert response.status_code == 400, response.text
        assert _bindings(db, setup["variant"]) == []

    def test_the_variants_own_slot_is_bound(self, db, setup):
        response = _create(setup["variant"], decision_slot_id=setup["own_slot"].id)
        assert response.status_code == 200, response.text
        assert _bindings(db, setup["variant"]) == [(None, setup["own_slot"].id)]


class TestJsonUpdate:
    @pytest.fixture
    def module(self, setup):
        response = _create(setup["variant"], content_record_id=setup["own"].id)
        assert response.status_code == 200, response.text
        return response.json()["id"]

    def _put(self, module_id, **binding):
        with machine([CAMPAIGNS_MANAGE]) as headers:
            return client.put(f"/campaigns/modules/{module_id}",
                              json={"module_type": "img_left", **binding}, headers=headers)

    def test_rebinding_to_another_brands_record_is_refused(self, db, setup, module):
        response = self._put(module, content_record_id=setup["foreign"].id)
        assert response.status_code == 400, response.text
        assert _bindings(db, setup["variant"]) == [(setup["own"].id, None)]

    def test_rebinding_to_another_variants_slot_is_refused(self, db, setup, module):
        response = self._put(module, decision_slot_id=setup["other_slot"].id)
        assert response.status_code == 400, response.text
        assert _bindings(db, setup["variant"]) == [(setup["own"].id, None)]

    def test_rebinding_to_the_variants_own_slot_works(self, db, setup, module):
        response = self._put(module, decision_slot_id=setup["own_slot"].id)
        assert response.status_code == 200, response.text
        assert _bindings(db, setup["variant"]) == [(None, setup["own_slot"].id)]


@pytest.fixture
def person(db, default_brand):
    """An Admin of the default brand, signed in to the Jinja UI."""
    user = auth.create_user(db, email=f"bind-{uuid.uuid4().hex[:8]}@example.invalid",
                            role_key="admin", brand_id=default_brand.id)
    token = auth.create_session(db, user)
    page_client = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
    page_client.cookies.set(auth.SESSION_COOKIE, token)
    yield page_client, auth.csrf_token_for(token)
    db.rollback()
    for table in ("login_codes", "auth_sessions", "role_assignments"):
        db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
    db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
    db.commit()


class TestJinjaForms:
    def test_the_create_form_refuses_another_brands_record(self, db, setup, person):
        page_client, csrf = person
        c, v = setup["campaign"], setup["variant"]
        response = page_client.post(
            f"/ui/campaigns/{c.id}/variants/{v.id}/modules",
            data={"csrf_token": csrf, "module_type": "img_left",
                  "content_record_id": setup["foreign"].id})
        assert response.status_code == 303 and "error=" in response.headers["location"]
        assert _bindings(db, v) == []

    def test_the_edit_form_refuses_another_brands_record(self, db, setup, person):
        page_client, csrf = person
        c, v = setup["campaign"], setup["variant"]
        page_client.post(f"/ui/campaigns/{c.id}/variants/{v.id}/modules",
                         data={"csrf_token": csrf, "module_type": "img_left",
                               "content_record_id": setup["own"].id})
        [module] = db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == v.id).all()
        response = page_client.post(
            f"/ui/campaigns/{c.id}/variants/{v.id}/modules/{module.id}/edit",
            data={"csrf_token": csrf, "module_type": "img_left",
                  "content_record_id": setup["foreign"].id})
        assert response.status_code == 303 and "error=" in response.headers["location"]
        assert _bindings(db, v) == [(setup["own"].id, None)]
