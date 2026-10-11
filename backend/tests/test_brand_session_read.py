"""Reading the working brand's logo must not create a profile (task-356)."""
from app.auth import service as auth
from app.auth.db_models import RoleAssignmentDB, RoleDB
from app.brand_profiles.db_models import BrandProfileDB
from tests.test_api_guard import signed_in
from tests.test_brand_profile_model import made_brand  # noqa: F401


def test_reading_a_session_does_not_create_a_missing_default_profile(db, made_brand):  # noqa: F811
    brand = made_brand()
    with signed_in(db) as (_client, token, _csrf):
        user = auth.user_for_token(db, token)
        admin = db.query(RoleDB).filter_by(key="admin").one()
        db.add(RoleAssignmentDB(user_id=user.id, role_id=admin.id, brand_id=brand.id))
        db.commit()
        auth.set_session_brand(db, token, brand.id)
        # Legacy/imported brands may have no profile. Remove only this test
        # brand's profile after setup, so the read is the operation exercised.
        db.query(BrandProfileDB).filter_by(brand_id=brand.id).delete()
        db.commit()

        summary = auth.current_brand_summary(db, token)

        assert summary["id"] == brand.id
        assert summary["logo"] is None and summary["logo_alt"] is None
        assert db.query(BrandProfileDB).filter_by(brand_id=brand.id).count() == 0
