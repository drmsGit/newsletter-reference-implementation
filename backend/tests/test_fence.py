"""The advisory fence on a variant (task-254, ADR-180 and its 2026-10-04 addendum).

Every composer write sets "blocked by X, last updated HH:MM"; it lapses 30
minutes after the last edit. For a person it is advisory: they edit anyway,
and may unblock any fence. For a machine it is binding: a write across
another actor's active fence is refused with 423, and a machine clears only
a fence it holds.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.audit import service as audit
from app.audit.db_models import AuditEventDB
from app.auth import service as auth
from app.auth.permissions import CAMPAIGNS_MANAGE, OVERRIDES_MANAGE, VIEW
from app.campaigns.db_models import CampaignDB, ModuleInstanceDB, VariantDB
from app.content.db_models import ContentRecordDB
from main import app
from tests.machine import machine

api = TestClient(app, raise_server_exceptions=False)
MACHINE = [CAMPAIGNS_MANAGE, OVERRIDES_MANAGE, VIEW]


@pytest.fixture
def world(db, default_brand):
    campaign = CampaignDB(brand_id=default_brand.id, name=f"fence-{uuid.uuid4().hex[:6]}")
    db.add(campaign); db.flush()
    variant = VariantDB(campaign_id=campaign.id, channel="email", name="v", status="draft")
    record = ContentRecordDB(title="r", content={}, status="active", brand_id=default_brand.id)
    db.add_all([variant, record]); db.flush()
    cta = ModuleInstanceDB(variant_id=variant.id, module_type="cta", position=1, module_data={"label": "Go"})
    hero = ModuleInstanceDB(variant_id=variant.id, module_type="img_left", position=2, content_record_id=record.id)
    db.add_all([cta, hero]); db.commit()
    yield {"campaign": campaign, "variant": variant, "cta": cta, "hero": hero}
    db.rollback()
    from app.overrides.db_models import ContentOverrideDB

    db.query(ContentOverrideDB).filter(ContentOverrideDB.module_instance_id == hero.id).delete()
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant.id).delete()
    db.query(VariantDB).filter(VariantDB.id == variant.id).delete()
    db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
    db.query(ContentRecordDB).filter(ContentRecordDB.id == record.id).delete()
    db.commit()


@pytest.fixture
def person(db, default_brand):
    """A signed-in manager on the JSON plane: session cookie plus CSRF header."""
    user = auth.create_user(db, email=f"fence-{uuid.uuid4().hex[:8]}@example.invalid",
                            role_key="admin", brand_id=default_brand.id)
    token = auth.create_session(db, user)
    client = TestClient(app, raise_server_exceptions=False)
    client.cookies.set(auth.SESSION_COOKIE, token)
    client.headers["X-CSRF-Token"] = auth.csrf_token_for(token)
    yield client, user
    db.rollback()
    for table in ("login_codes", "auth_sessions", "role_assignments"):
        db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
    db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
    db.commit()


def _rename(client, variant, name, headers=None):
    return client.put(f"/campaigns/variants/{variant.id}", json={"name": name}, headers=headers or {})


def _fence(client, campaign, headers=None):
    composed = client.get(f"/campaigns/{campaign.id}/composition", headers=headers or {}).json()
    return composed["variants"][0]["fence"]


def _lapse(db, variant):
    db.execute(text("UPDATE variants SET fenced_at = :t WHERE id = :v"),
               {"t": datetime.now(timezone.utc) - timedelta(minutes=31), "v": variant.id})
    db.commit()


def test_a_persons_edit_fences_the_variant_with_their_name(world, person):
    client, user = person
    assert _rename(client, world["variant"], "renamed").status_code == 200
    fence = _fence(client, world["campaign"])
    assert (fence["by"], fence["by_type"], fence["active"]) == (user.email, "user", True)


def test_a_machine_is_refused_across_a_persons_fence_and_nothing_changes(db, world, person):
    client, _ = person
    assert _rename(client, world["variant"], "theirs").status_code == 200
    with machine(MACHINE) as headers:
        refused = _rename(api, world["variant"], "mine", headers)
    assert refused.status_code == 423, refused.text
    db.expire_all()
    assert db.get(VariantDB, world["variant"].id).name == "theirs"


def test_a_lapsed_fence_holds_no_machine_off(db, world, person):
    client, _ = person
    assert _rename(client, world["variant"], "theirs").status_code == 200
    _lapse(db, world["variant"])
    with machine(MACHINE) as headers:
        assert _rename(api, world["variant"], "mine", headers).status_code == 200
        assert _fence(api, world["campaign"], headers)["by"].startswith("integration:")


def test_a_machine_passes_its_own_fence_and_not_another_machines(world):
    with machine(MACHINE) as first:
        assert _rename(api, world["variant"], "one", first).status_code == 200
        assert _rename(api, world["variant"], "two", first).status_code == 200
        with machine(MACHINE) as second:
            assert _rename(api, world["variant"], "three", second).status_code == 423


def test_a_person_is_never_stopped(world, person):
    client, user = person
    with machine(MACHINE) as headers:
        assert _rename(api, world["variant"], "machine", headers).status_code == 200
    assert _rename(client, world["variant"], "person").status_code == 200
    assert _fence(client, world["campaign"])["by"] == user.email


def test_unblock_a_person_clears_any_a_machine_only_its_own(db, world, person):
    client, user = person
    assert _rename(client, world["variant"], "theirs").status_code == 200
    url = f"/campaigns/variants/{world['variant'].id}/fence"
    with machine(MACHINE) as headers:
        assert api.delete(url, headers=headers).status_code == 423
        assert _rename(api, world["variant"], "still refused", headers).status_code == 423
    assert client.delete(url).status_code == 200
    assert _fence(client, world["campaign"]) is None
    [entry] = db.query(AuditEventDB).filter(AuditEventDB.action == audit.VARIANT_UNFENCED,
                                            AuditEventDB.subject_id == world["variant"].id).all()
    # Whose fence it was, by id — not the person's address (task-52).
    assert entry.detail["was"] == {"type": audit.ACTOR_USER, "id": user.id}
    with machine(MACHINE) as headers:
        assert _rename(api, world["variant"], "now mine", headers).status_code == 200
        assert api.delete(url, headers=headers).status_code == 200


def test_a_module_edit_fences_the_variant_without_moving_its_version(world, person):
    client, user = person
    before = client.get(f"/campaigns/{world['campaign'].id}/composition").json()["variants"][0]
    response = client.put(f"/campaigns/modules/{world['cta'].id}",
                          json={"module_type": "cta", "module_data": {"label": "Now"}})
    assert response.status_code == 200, response.text
    after = client.get(f"/campaigns/{world['campaign'].id}/composition").json()["variants"][0]
    assert after["fence"]["by"] == user.email
    assert after["variant"]["updated_at"] == before["variant"]["updated_at"], \
        "the fence must not move the variant's version token (task-110)"


def test_an_override_write_is_fenced_too(world, person):
    client, _ = person
    assert _rename(client, world["variant"], "theirs").status_code == 200
    with machine(MACHINE) as headers:
        response = api.put(f"/overrides/modules/{world['hero'].id}",
                           json={"field_overrides": {"headline_medium": "x"}}, headers=headers)
    assert response.status_code == 423, response.text


def test_another_brands_fenced_variant_answers_as_not_found(db, world, person, foreign_api):
    client, _ = person
    assert _rename(client, world["variant"], "theirs").status_code == 200
    with foreign_api(MACHINE) as headers:
        response = _rename(api, world["variant"], "probe", headers)
    assert response.status_code == 404, "a 423 would say the variant exists in another brand"


def test_the_old_forms_fence_too(db, world, default_brand):
    user = auth.create_user(db, email=f"fence-{uuid.uuid4().hex[:8]}@example.invalid",
                            role_key="admin", brand_id=default_brand.id)
    token = auth.create_session(db, user)
    page = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
    page.cookies.set(auth.SESSION_COOKIE, token)
    try:
        c, v = world["campaign"], world["variant"]
        page.post(f"/ui/campaigns/{c.id}/variants/{v.id}/edit",
                  data={"csrf_token": auth.csrf_token_for(token), "name": "jinja"})
        db.expire_all()
        assert db.get(VariantDB, v.id).fenced_by_label == user.email
    finally:
        db.rollback()
        for table in ("login_codes", "auth_sessions", "role_assignments"):
            db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
        db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
        db.commit()
