"""Default changes must use the locked current state (task-350, ADR-194)."""
from app.brand_profiles import service as profiles
from app.brand_profiles.db_models import BrandProfileDB
from app.database import SessionLocal
from tests.test_brand_profile_model import made_brand  # noqa: F401


def test_default_change_after_another_session_changes_the_default(db, made_brand):  # noqa: F811
    brand = made_brand()
    second = profiles.create_profile(db, brand.id, name="Second")
    third = profiles.create_profile(db, brand.id, name="Third")
    brand_id, second_id, third_id = brand.id, second.id, third.id

    with SessionLocal() as stale:
        # Hold the identity-map objects, as a request that read profiles before
        # a competing request committed would. The later lock must refresh them.
        previously_read = stale.query(BrandProfileDB).filter_by(brand_id=brand_id).all()
        assert sum(p.is_default for p in previously_read) == 1
        profiles.make_default(db, second_id, brand_id)
        assert not next(p for p in previously_read if p.id == second_id).is_default

        changed = profiles.make_default(stale, third_id, brand_id)
        assert changed.id == third_id

    db.expire_all()
    defaults = db.query(BrandProfileDB).filter_by(brand_id=brand_id, is_default=True).all()
    assert [p.id for p in defaults] == [third_id]
