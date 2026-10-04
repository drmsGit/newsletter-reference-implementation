"""A module's data holds only the fields its manifest declares, as text (task-253).

`module_data` was stored as whatever dict the caller sent. Overrides already
refused undeclared keys; module data did not. ADR-177 keeps `required` and
lengths advisory while editing (completeness is shown in the editor), so a
missing field or a long one is still accepted. An undeclared key or a value
that is not text is refused, naming the field, in the shape FastAPI uses for
its own validation errors so the client reads one kind of 422.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth import service as auth
from app.auth.permissions import CAMPAIGNS_MANAGE
from app.campaigns.db_models import CampaignDB, ModuleInstanceDB, VariantDB
from main import app
from tests.machine import editor, machine

client = TestClient(app, raise_server_exceptions=False)

# One editing machine per test: several writes as different machines would
# meet each other's fence (task-254).
pytestmark = pytest.mark.usefixtures("one_editor")


@pytest.fixture
def variant(db, default_brand):
    campaign = CampaignDB(brand_id=default_brand.id, name=f"mdata-{uuid.uuid4().hex[:6]}")
    db.add(campaign); db.flush()
    variant = VariantDB(campaign_id=campaign.id, channel="email", name="v", status="draft")
    db.add(variant); db.commit()
    yield variant
    db.rollback()
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant.id).delete()
    db.query(VariantDB).filter(VariantDB.id == variant.id).delete()
    db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
    db.commit()


def _create(variant, module_data):
    with editor([CAMPAIGNS_MANAGE]) as headers:
        return client.post(f"/campaigns/variants/{variant.id}/modules",
                           json={"module_type": "cta", "module_data": module_data}, headers=headers)


def _stored(db, variant):
    db.expire_all()
    return [m.module_data for m in db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant.id)]


class TestCreate:
    def test_an_undeclared_field_is_refused_and_named(self, db, variant):
        response = _create(variant, {"label": "Go", "colour": "red"})
        assert response.status_code == 422, response.text
        [error] = response.json()["detail"]
        assert error["loc"] == ["body", "module_data", "colour"]
        assert _stored(db, variant) == []

    def test_a_value_that_is_not_text_is_refused_and_named(self, db, variant):
        response = _create(variant, {"label": 7})
        assert response.status_code == 422, response.text
        assert [e["loc"][-1] for e in response.json()["detail"]] == ["label"]
        assert _stored(db, variant) == []

    def test_every_bad_field_is_named_at_once(self, db, variant):
        response = _create(variant, {"label": ["x"], "colour": "red"})
        assert sorted(e["loc"][-1] for e in response.json()["detail"]) == ["colour", "label"]

    def test_missing_required_and_empty_values_are_still_accepted(self, db, variant):
        # cta requires label and url; ADR-177 keeps that advisory while editing.
        response = _create(variant, {"url": None})
        assert response.status_code == 200, response.text
        assert _stored(db, variant) == [{"url": None}]

    def test_declared_text_is_stored(self, db, variant):
        assert _create(variant, {"label": "Go", "url": "https://example.invalid"}).status_code == 200


def test_an_update_is_checked_too(db, variant):
    created = _create(variant, {"label": "Go"})
    assert created.status_code == 200, created.text
    with editor([CAMPAIGNS_MANAGE]) as headers:
        response = client.put(f"/campaigns/modules/{created.json()['id']}",
                              json={"module_type": "cta", "module_data": {"colour": "red"}}, headers=headers)
    assert response.status_code == 422, response.text
    assert _stored(db, variant) == [{"label": "Go"}]


def test_the_jinja_form_shows_the_refusal(db, variant, default_brand):
    user = auth.create_user(db, email=f"mdata-{uuid.uuid4().hex[:8]}@example.invalid",
                            role_key="admin", brand_id=default_brand.id)
    token = auth.create_session(db, user)
    page = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
    page.cookies.set(auth.SESSION_COOKIE, token)
    try:
        response = page.post(
            f"/ui/campaigns/{variant.campaign_id}/variants/{variant.id}/modules",
            data={"csrf_token": auth.csrf_token_for(token), "module_type": "cta",
                  "module_data_json": '{"colour": "red"}'})
        assert response.status_code == 303
        assert "error=" in response.headers["location"] and "colour" in response.headers["location"]
        assert _stored(db, variant) == []
    finally:
        db.rollback()
        for table in ("login_codes", "auth_sessions", "role_assignments"):
            db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
        db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
        db.commit()
