"""The manager app shows the working brand's logo, from its default brand
profile (task-356; ADR-194 point 12, narrowed by the user to the logo only:
the app keeps one palette and its fonts per installation)."""
import uuid

import pytest
from sqlalchemy import text

from app.auth import service as auth
from app.auth.db_models import RoleAssignmentDB, RoleDB
from app.brand_profiles import service as profiles
from tests.test_api_guard import signed_in


@pytest.fixture
def logos(db, default_brand, foreign_brand):
    """Each brand's default profile with its own logo, put back afterwards."""
    saved = {}
    for brand, logo in ((default_brand, "https://cdn.example.test/main.png"),
                        (foreign_brand, "https://cdn.example.test/other.png")):
        profile = profiles.default_profile(db, brand.id)
        saved[profile.id] = dict(profile.field_values or {})
        profile.field_values = {**profile.field_values, "logo": logo, "logo_alt": f"{brand.name} logo"}
    db.commit()
    yield {"main": default_brand, "other": foreign_brand}
    db.rollback()
    for profile_id, values in saved.items():
        profile = db.get(type(profiles.default_profile(db, default_brand.id)), profile_id)
        if profile is not None:
            profile.field_values = values
    db.commit()


def test_the_session_carries_the_working_brands_logo(db, logos):
    with signed_in(db) as (cookied, _token, _csrf):
        brand = cookied.get("/auth/session").json()["brand"]
    assert brand["logo"] == "https://cdn.example.test/main.png"
    assert brand["logo_alt"] == f"{logos['main'].name} logo"


def test_switching_brand_switches_the_logo(db, logos):
    user = auth.create_user(db, email=f"logo-{uuid.uuid4().hex[:8]}@example.invalid", role_key="admin")
    admin = db.query(RoleDB).filter(RoleDB.key == "admin").one()
    db.add(RoleAssignmentDB(user_id=user.id, role_id=admin.id, brand_id=logos["other"].id))
    db.commit()
    token = auth.create_session(db, user)
    try:
        assert auth.current_brand_summary(db, token)["logo"] == "https://cdn.example.test/main.png"
        auth.set_session_brand(db, token, logos["other"].id)
        assert auth.current_brand_summary(db, token)["logo"] == "https://cdn.example.test/other.png"
    finally:
        db.rollback()
        for table in ("login_codes", "auth_sessions", "role_assignments"):
            db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
        db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
        db.commit()


def test_without_a_logo_the_session_says_none(db, default_brand):
    profile = profiles.default_profile(db, default_brand.id)
    assert not (profile.field_values or {}).get("logo")
    with signed_in(db) as (cookied, _token, _csrf):
        brand = cookied.get("/auth/session").json()["brand"]
    assert brand["logo"] is None
