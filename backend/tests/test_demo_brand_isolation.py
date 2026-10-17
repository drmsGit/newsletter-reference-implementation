"""Demo-reset deletion is scoped to the removed brands (task-71; ADR-150/151)."""
from datetime import timedelta
from uuid import uuid4

from app.auth.db_models import (
    BrandDB, IntegrationDB, IntegrationGrantDB, RoleAssignmentDB, RoleDB, SessionDB, UserDB,
)
from app.auth.service import now
from app.demo.reset import remove_brands


def test_removing_a_brand_preserves_other_sessions_and_grants(db, default_brand):
    tag = uuid4().hex
    gone = BrandDB(key=f"gone-{tag}", name="Removed demo brand")
    user = UserDB(email=f"reset-{tag}@example.invalid", is_active=True)
    integration = IntegrationDB(name=f"Reset isolation {tag}")
    db.add_all([gone, user, integration])
    db.flush()
    role = db.query(RoleDB).filter_by(key="admin").one()
    expires = now() + timedelta(hours=1)
    sessions = [SessionDB(user_id=user.id, token_hash=uuid4().hex * 2,
                          brand_id=brand.id, expires_at=expires) for brand in [gone, default_brand]]
    roles = [RoleAssignmentDB(user_id=user.id, role_id=role.id, brand_id=brand.id)
             for brand in [gone, default_brand]]
    grants = [IntegrationGrantDB(integration_id=integration.id, permission="view", brand_id=brand.id)
              for brand in [gone, default_brand]]
    db.add_all([*sessions, *roles, *grants])
    db.flush()
    gone_id, kept_id, user_id, integration_id = gone.id, default_brand.id, user.id, integration.id
    session_ids = [s.id for s in sessions]
    role_ids = [r.id for r in roles]
    grant_ids = [g.id for g in grants]
    hashes = [s.token_hash for s in sessions]

    remove_brands(db, [gone_id])
    db.flush()
    db.expunge_all()
    assert db.get(BrandDB, gone_id) is None
    assert db.get(BrandDB, kept_id) is not None
    for index, expected_brand in enumerate([None, kept_id]):
        session = db.get(SessionDB, session_ids[index])
        assert session is not None
        assert session.brand_id == expected_brand
        assert session.token_hash == hashes[index]
        assert session.expires_at == expires and session.revoked_at is None
    assert db.get(RoleAssignmentDB, role_ids[0]) is None
    assert db.get(IntegrationGrantDB, grant_ids[0]) is None
    assert db.get(RoleAssignmentDB, role_ids[1]).brand_id == kept_id
    assert db.get(IntegrationGrantDB, grant_ids[1]).brand_id == kept_id
    assert db.get(UserDB, user_id).is_active
    assert db.get(IntegrationDB, integration_id).is_active

    # No obsolete brands is a no-op too; it must never clear every context.
    remove_brands(db, [])
    db.flush()
    db.expire_all()
    assert db.get(SessionDB, session_ids[1]).brand_id == kept_id
    assert db.get(RoleAssignmentDB, role_ids[1]).brand_id == kept_id
    assert db.get(IntegrationGrantDB, grant_ids[1]).brand_id == kept_id
