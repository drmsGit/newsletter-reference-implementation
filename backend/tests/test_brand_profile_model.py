"""Every brand always has exactly one default profile (task-350, ADR-194).

The default is what a variant uses unless a manager picks another, what a
deleted profile falls back to, and what a brand made yesterday must already
have. Profiles go with their brand: they are its own look, not something that
belongs to a person or a send, so they never block deleting it.
"""
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.auth import service as auth
from app.auth.db_models import BrandDB
from app.brand_profiles import service as profiles
from app.brand_profiles.db_models import BrandProfileDB


@pytest.fixture
def made_brand(db):
    """A brand made the way the app makes one, removed afterwards."""
    made = []

    def make():
        brand = auth.create_brand(db, key=f"bp-{uuid.uuid4().hex[:8]}", name="Profile test")
        made.append(brand.id)
        return brand

    yield make
    db.rollback()
    for brand_id in made:
        db.query(BrandProfileDB).filter(BrandProfileDB.brand_id == brand_id).delete()
        db.query(BrandDB).filter(BrandDB.id == brand_id).delete()
    db.commit()


def _profiles(db, brand_id):
    return db.query(BrandProfileDB).filter(BrandProfileDB.brand_id == brand_id).all()


def test_a_new_brand_starts_with_one_default_profile(db, made_brand):
    brand = made_brand()

    [profile] = _profiles(db, brand.id)
    assert profile.is_default and profile.name == "Default"
    assert (profile.language, profile.kind) == ("en", "marketing")
    # The wording a marketing email needs is filled; the legal details are the
    # company's to fill, so a fresh profile is honestly incomplete.
    assert profile.field_values == {"unsubscribe_text": "Unsubscribe"}
    assert "legal_company_name" in profiles.missing(profile)


def test_the_default_brand_has_one_too(db, default_brand):
    assert profiles.default_profile(db, default_brand.id).is_default


def test_ensuring_the_default_twice_makes_one(db, made_brand):
    brand = made_brand()
    first = profiles.ensure_default_profile(db, brand.id)
    again = profiles.ensure_default_profile(db, brand.id)

    assert first.id == again.id and len(_profiles(db, brand.id)) == 1


def test_a_brand_made_without_one_gets_it_when_asked(db, temp_brand):
    """Rows built directly (fixtures, older code) still find a default."""
    brand = temp_brand()
    assert _profiles(db, brand.id) == []

    assert profiles.default_profile(db, brand.id).is_default


def test_the_database_refuses_a_second_default(db, made_brand):
    brand = made_brand()
    db.add(BrandProfileDB(brand_id=brand.id, name="Another", is_default=True))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_the_database_refuses_an_unknown_kind(db, made_brand):
    brand = made_brand()
    db.add(BrandProfileDB(brand_id=brand.id, name="Odd", kind="newsletter"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_profiles_do_not_block_deleting_their_brand(db, made_brand):
    brand = made_brand()
    db.add(BrandProfileDB(brand_id=brand.id, name="Black Friday"))
    db.commit()

    assert auth.delete_brand(db, brand.id) is None
    db.expire_all()
    assert db.get(BrandDB, brand.id) is None
    assert _profiles(db, brand.id) == [], "the brand's profiles outlived it"


def test_profiles_are_not_counted_as_holding_a_brand():
    held = {f"{t.name}.{c.name}" for t, c in auth.brand_holders()}
    assert "brand_profiles.brand_id" not in held
