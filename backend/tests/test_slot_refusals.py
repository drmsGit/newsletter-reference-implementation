"""A slot config the strategy rejects is refused, never a 500 (task-251).

`normalize_slot_config` raises `ValueError` for an undeclared key, a missing
required key or a wrong type. PATCH turned that into a 400; PUT did not, and
the Jinja slot-create form did not catch an unknown strategy either. Each
refusal has a control beside it.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth import service as auth
from app.auth.permissions import CAMPAIGNS_MANAGE
from app.campaigns.db_models import CampaignDB, DecisionSlotDB, VariantDB
from main import app
from tests.machine import machine

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def slot(db, default_brand):
    campaign = CampaignDB(brand_id=default_brand.id, name=f"slotref-{uuid.uuid4().hex[:6]}")
    db.add(campaign); db.flush()
    variant = VariantDB(campaign_id=campaign.id, channel="email", name="v", status="draft")
    db.add(variant); db.flush()
    slot = DecisionSlotDB(variant_id=variant.id, name="s", decision_type="content_recommendation",
                          decision_strategy="top_score")
    db.add(slot); db.commit()
    yield slot
    db.rollback()
    db.query(DecisionSlotDB).filter(DecisionSlotDB.variant_id == variant.id).delete()
    db.query(VariantDB).filter(VariantDB.id == variant.id).delete()
    db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
    db.commit()


def _put(slot, **body):
    with machine([CAMPAIGNS_MANAGE]) as headers:
        return client.put(f"/campaigns/decision-slots/{slot.id}",
                          json={"decision_strategy": "top_score", **body}, headers=headers)


def test_put_refuses_a_key_the_strategy_does_not_declare(slot):
    response = _put(slot, candidate_filter={"no_such_key": 1})
    assert response.status_code == 400, response.text
    assert "no_such_key" in response.json()["detail"]


def test_put_refuses_a_value_of_the_wrong_type(slot):
    response = _put(slot, candidate_filter={"category_ids": "seven"})
    assert response.status_code == 400, response.text


def test_put_accepts_a_config_the_strategy_declares(slot):
    response = _put(slot, candidate_filter={"category_ids": [1, 2]})
    assert response.status_code == 200, response.text
    assert response.json()["candidate_filter"] == {"category_ids": [1, 2]}


@pytest.fixture
def person(db, default_brand):
    user = auth.create_user(db, email=f"slotref-{uuid.uuid4().hex[:8]}@example.invalid",
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


@pytest.mark.parametrize("strategy,refused", [("no_such_strategy", True), ("top_score", False)])
def test_the_jinja_slot_form_shows_a_refusal_instead_of_failing(db, slot, person, strategy, refused):
    page_client, csrf = person
    variant = db.get(VariantDB, slot.variant_id)
    response = page_client.post(
        f"/ui/campaigns/{variant.campaign_id}/variants/{variant.id}/decision-slots",
        data={"csrf_token": csrf, "name": "new", "decision_strategy": strategy})
    assert response.status_code == 303, response.text[:300]
    assert ("error=" in response.headers["location"]) is refused
