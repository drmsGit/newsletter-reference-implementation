"""The brand-profile API (task-350 slice 1a; ADR-194 and its 2026-10-11 addendum).

A brand's profiles are listed, read, created, edited, duplicated, made the
default and deleted in the working brand. Every write is a person's act under
`brand_profiles.manage` (addendum point 9); transactional profiles are refused
until their guard exists (point 7); the audit names the fields that changed and
never their values (point 8). Deleting a profile moves the variants using it to
the default, with a notice saying so (ADR-194 point 1).
"""
import json
import uuid
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.audit.db_models import AuditEventDB
from app.auth import service as auth
from app.auth.db_models import RoleDB, RolePermissionDB
from app.auth.permissions import BRAND_PROFILES_MANAGE, VIEW
from app.brand_profiles import service as profiles, structure
from app.brand_profiles.db_models import BrandProfileDB
from app.campaigns.db_models import CampaignDB, VariantDB
from app.database import SessionLocal
from main import app
from tests.machine import machine
from tests.test_api_guard import signed_in

client = TestClient(app, raise_server_exceptions=False)

LEGAL = {
    "legal_company_name": "Example GmbH",
    "legal_address": "Example Street 1\n12345 Example City",
    "imprint_url": "https://example.test/imprint",
    "privacy_url": "https://example.test/privacy",
}


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def restore_profiles(db, default_brand):
    """Put the default brand's profiles back as they were: other tests (and the
    seed's send) read its default."""
    before = {
        p.id: (p.name, p.language, p.kind, p.is_default, dict(p.field_values or {}))
        for p in db.query(BrandProfileDB).filter(BrandProfileDB.brand_id == default_brand.id)
    }
    variants = {v.id: (v.brand_profile_id, v.brand_profile_notice) for v in db.query(VariantDB)}
    yield
    db.rollback()
    for v in db.query(VariantDB):
        if v.id in variants:
            v.brand_profile_id, v.brand_profile_notice = variants[v.id]
    db.flush()
    db.query(BrandProfileDB).filter(BrandProfileDB.brand_id == default_brand.id).update(
        {"is_default": False}, synchronize_session=False)
    db.flush()
    db.query(BrandProfileDB).filter(
        BrandProfileDB.brand_id == default_brand.id, BrandProfileDB.id.notin_(list(before)),
    ).delete(synchronize_session=False)
    for profile in db.query(BrandProfileDB).filter(BrandProfileDB.id.in_(list(before))):
        (profile.name, profile.language, profile.kind, profile.is_default,
         profile.field_values) = before[profile.id]
    db.commit()


@contextmanager
def admin(db):
    with signed_in(db) as (cookied, _token, csrf):
        yield cookied, {"X-CSRF-Token": csrf}


@contextmanager
def person_with(db, permissions):
    """A person whose only role carries exactly `permissions`."""
    role = auth.create_role(db, key=f"bp-{uuid.uuid4().hex[:6]}", name="profile test")
    auth.set_role_permissions(db, role.id, permissions)
    user = auth.create_user(db, email=f"bp-{uuid.uuid4().hex[:8]}@example.invalid",
                            role_key=role.key)
    token = auth.create_session(db, user)
    cookied = TestClient(app, raise_server_exceptions=False)
    cookied.cookies.set(auth.SESSION_COOKIE, token)
    try:
        yield cookied, {"X-CSRF-Token": auth.csrf_token_for(token)}
    finally:
        db.rollback()
        for table in ("login_codes", "auth_sessions", "role_assignments"):
            db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
        db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
        db.query(RolePermissionDB).filter(RolePermissionDB.role_id == role.id).delete()
        db.query(RoleDB).filter(RoleDB.id == role.id).delete()
        db.commit()


@pytest.fixture
def setup_file(tmp_path, monkeypatch):
    """Declare extra profile fields for one test."""
    path = tmp_path / "brand_profile.json"
    monkeypatch.setattr(structure, "PROFILE_PATH", path)
    structure._loaded_mtime = None

    def write(fields: dict):
        path.write_text(json.dumps({"fields": fields}))
        structure._loaded_mtime = None

    write({})
    yield write
    structure._loaded_mtime = None


def _create(cookied, headers, name="Black Friday", **body):
    return cookied.post("/brand-profiles/", json={"name": name, **body}, headers=headers)


class TestReading:
    def test_the_structure_lists_the_core_first(self, db):
        with admin(db) as (cookied, headers):
            fields = cookied.get("/brand-profiles/structure").json()
        assert [f["name"] for f in fields][:5] == [
            "legal_company_name", "legal_address", "imprint_url", "privacy_url", "unsubscribe_text"]
        unsubscribe = next(f for f in fields if f["name"] == "unsubscribe_text")
        assert unsubscribe["required_for"] == ["marketing"] and unsubscribe["core"] is True

    def test_the_list_puts_the_default_first_and_says_what_is_missing(self, db):
        with admin(db) as (cookied, headers):
            _create(cookied, headers, name="Aab complete",
                    field_values={**LEGAL, "unsubscribe_text": "Unsubscribe"})
            _create(cookied, headers, name="Aaa incomplete", field_values={"imprint_url": LEGAL["imprint_url"]})
            page = cookied.get("/brand-profiles/").json()
        first, second, third = page["items"][:3]
        # The default leads whatever its name; the rest follow by name.
        assert first["is_default"]
        assert (second["name"], third["name"]) == ("Aaa incomplete", "Aab complete")
        assert second["complete"] is False
        assert second["missing"] == ["legal_company_name", "legal_address", "privacy_url",
                                     "unsubscribe_text"]
        assert third["complete"] is True and third["missing"] == []

    def test_another_brands_profile_is_not_found(self, db, foreign_brand):
        other = profiles.ensure_default_profile(db, foreign_brand.id)
        with admin(db) as (cookied, headers):
            assert cookied.get(f"/brand-profiles/{other.id}").status_code == 404
            response = cookied.put(f"/brand-profiles/{other.id}",
                                   json={"name": "Taken", "field_values": {}}, headers=headers)
            assert response.status_code == 404


class TestWriting:
    def test_a_profile_is_created_and_read_back(self, db):
        with admin(db) as (cookied, headers):
            response = _create(cookied, headers, field_values={**LEGAL, "unsubscribe_text": "Leave"})
            assert response.status_code == 201, response.text
            body = cookied.get(f"/brand-profiles/{response.json()['id']}").json()
        assert body["field_values"]["unsubscribe_text"] == "Leave"
        assert (body["language"], body["kind"], body["is_default"]) == ("en", "marketing", False)

    def test_a_name_is_unique_within_the_brand(self, db):
        with admin(db) as (cookied, headers):
            assert _create(cookied, headers, name="Calm").status_code == 201
            assert _create(cookied, headers, name="Calm").status_code == 409

    def test_transactional_is_refused_until_its_guard_exists(self, db):
        with admin(db) as (cookied, headers):
            response = _create(cookied, headers, kind="transactional")
        assert response.status_code == 422 and "task-355" not in response.text
        assert "transactional" in response.text.lower()

    @pytest.mark.parametrize("values, field", [
        ({"glow": "x"}, "glow"),                                  # not declared
        ({"imprint_url": "example.test/imprint"}, "imprint_url"),  # a url is http(s)
        ({"colour_primary": "red"}, "colour_primary"),            # a colour is #rgb or #rrggbb
        ({"size_body": "16"}, "size_body"),                       # a size has a unit
        ({"count": "many"}, "count"),                             # a number is a number
    ])
    def test_bad_values_are_refused_per_field(self, db, setup_file, values, field):
        setup_file({
            "colour_primary": {"type": "colour", "label": "Primary"},
            "size_body": {"type": "size", "label": "Body size"},
            "count": {"type": "number", "label": "Count"},
        })
        with admin(db) as (cookied, headers):
            response = _create(cookied, headers, field_values=values)
        assert response.status_code == 422, response.text
        assert [e["loc"][-1] for e in response.json()["detail"]] == [field]

    def test_good_typed_values_are_kept(self, db, setup_file):
        setup_file({
            "colour_primary": {"type": "colour", "label": "Primary"},
            "size_body": {"type": "size", "label": "Body size"},
            "count": {"type": "number", "label": "Count"},
        })
        values = {"colour_primary": "#1A2b3c", "size_body": "16px", "count": 3}
        with admin(db) as (cookied, headers):
            response = _create(cookied, headers, field_values=values)
        assert response.status_code == 201, response.text
        assert response.json()["field_values"] == values

    def test_an_edit_replaces_the_values_and_an_empty_one_is_dropped(self, db):
        with admin(db) as (cookied, headers):
            created = _create(cookied, headers, field_values=LEGAL).json()
            response = cookied.put(
                f"/brand-profiles/{created['id']}",
                json={"name": "Renamed", "field_values": {**LEGAL, "imprint_url": ""}},
                headers={**headers, "If-Match": created["updated_at"]},
            )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["name"] == "Renamed" and "imprint_url" not in body["field_values"]
        assert body["missing"] == ["imprint_url", "unsubscribe_text"]

    def test_an_edit_on_a_stale_read_is_refused(self, db):
        with admin(db) as (cookied, headers):
            created = _create(cookied, headers).json()
            first = cookied.put(f"/brand-profiles/{created['id']}",
                                json={"name": "One", "field_values": {}},
                                headers={**headers, "If-Match": created["updated_at"]})
            assert first.status_code == 200
            second = cookied.put(f"/brand-profiles/{created['id']}",
                                 json={"name": "Two", "field_values": {}},
                                 headers={**headers, "If-Match": created["updated_at"]})
        assert second.status_code == 409

    def test_duplicating_copies_the_values_under_a_free_name(self, db):
        with admin(db) as (cookied, headers):
            created = _create(cookied, headers, name="Flashy", field_values=LEGAL).json()
            one = cookied.post(f"/brand-profiles/{created['id']}/duplicate", headers=headers)
            two = cookied.post(f"/brand-profiles/{created['id']}/duplicate", headers=headers)
        assert one.status_code == 201, one.text
        assert one.json()["name"] == "Flashy (copy)" and two.json()["name"] == "Flashy (copy 2)"
        assert one.json()["field_values"] == LEGAL and one.json()["is_default"] is False

    def test_making_another_profile_the_default_moves_the_mark(self, db, default_brand):
        with admin(db) as (cookied, headers):
            created = _create(cookied, headers).json()
            response = cookied.post(f"/brand-profiles/{created['id']}/make-default", headers=headers)
        assert response.status_code == 200, response.text
        db.expire_all()
        defaults = db.query(BrandProfileDB).filter(
            BrandProfileDB.brand_id == default_brand.id, BrandProfileDB.is_default.is_(True)).all()
        assert [p.id for p in defaults] == [created["id"]]


    def test_the_mark_moves_back_to_an_older_profile(self, db, default_brand):
        """The old mark must go before the new one is set, or the one-default
        index refuses the write. Updates are flushed in id order, so only a
        move to an OLDER profile shows whether that order is kept on purpose."""
        original = profiles.default_profile(db, default_brand.id)
        with admin(db) as (cookied, headers):
            created = _create(cookied, headers).json()
            cookied.post(f"/brand-profiles/{created['id']}/make-default", headers=headers)
            response = cookied.post(f"/brand-profiles/{original.id}/make-default", headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["is_default"] is True


class TestDeleting:
    def test_the_default_cannot_be_deleted(self, db, default_brand):
        default = profiles.default_profile(db, default_brand.id)
        with admin(db) as (cookied, headers):
            response = cookied.delete(f"/brand-profiles/{default.id}", headers=headers)
        assert response.status_code == 409
        assert "default" in response.json()["detail"]

    def test_variants_using_it_fall_back_to_the_default_with_a_notice(self, db, default_brand):
        variant = (db.query(VariantDB).join(CampaignDB, CampaignDB.id == VariantDB.campaign_id)
                   .filter(CampaignDB.brand_id == default_brand.id).order_by(VariantDB.id).first())
        with admin(db) as (cookied, headers):
            created = _create(cookied, headers, name="Short-lived").json()
            variant.brand_profile_id = created["id"]
            db.commit()
            response = cookied.delete(f"/brand-profiles/{created['id']}", headers=headers)
        assert response.status_code == 200, response.text
        assert response.json() == {"variants_moved": 1}
        db.expire_all()
        assert variant.brand_profile_id == profiles.default_profile(db, default_brand.id).id
        assert "Short-lived" in variant.brand_profile_notice
        assert db.get(BrandProfileDB, created["id"]) is None


class TestWhoMayWrite:
    def test_a_machine_holding_the_permission_is_refused(self, db):
        with machine([VIEW, BRAND_PROFILES_MANAGE]) as headers:
            response = client.post("/brand-profiles/", json={"name": "Machine-made"}, headers=headers)
        assert response.status_code == 403, response.text

    def test_a_person_without_the_permission_is_refused(self, db):
        with person_with(db, [VIEW]) as (cookied, headers):
            assert _create(cookied, headers).status_code == 403
            # Reading is `view`, like every other screen.
            assert cookied.get("/brand-profiles/").status_code == 200

    def test_a_person_with_it_may_write(self, db):
        with person_with(db, [VIEW, BRAND_PROFILES_MANAGE]) as (cookied, headers):
            assert _create(cookied, headers).status_code == 201

    def test_a_profile_says_whether_the_reader_may_manage(self, db, default_brand):
        default = profiles.default_profile(db, default_brand.id)
        with person_with(db, [VIEW]) as (cookied, _):
            assert cookied.get(f"/brand-profiles/{default.id}").json()["may_manage"] is False
        with admin(db) as (cookied, _):
            assert cookied.get(f"/brand-profiles/{default.id}").json()["may_manage"] is True
        with machine([VIEW, BRAND_PROFILES_MANAGE]) as headers:
            body = client.get(f"/brand-profiles/{default.id}", headers=headers).json()
        assert body["may_manage"] is False, "a machine never may, whatever it holds"


class TestTheAudit:
    def test_an_edit_records_which_fields_changed_never_their_values(self, db):
        with admin(db) as (cookied, headers):
            created = _create(cookied, headers, field_values=LEGAL).json()
            cookied.put(
                f"/brand-profiles/{created['id']}",
                json={"name": created["name"],
                      "field_values": {**LEGAL, "legal_address": "Write to legal@example.test"}},
                headers=headers,
            )
        entries = (db.query(AuditEventDB)
                   .filter(AuditEventDB.subject_type == "brand_profile",
                           AuditEventDB.subject_id == created["id"])
                   .order_by(AuditEventDB.id).all())
        assert [e.action for e in entries] == ["brand_profile.created", "brand_profile.updated"]
        assert entries[1].detail == {"changed": ["legal_address"]}
        assert "legal@" not in json.dumps([e.detail for e in entries])
