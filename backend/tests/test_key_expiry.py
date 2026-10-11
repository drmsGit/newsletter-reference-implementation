"""An integration's key may expire (task-344; ADR-166, second addenda of
2026-10-09 and 2026-10-11).

Set in days when the key is issued, or never. An expired key is refused
exactly like a revoked one; the list shows each key's expiry and marks one
that expires within 14 days. Bringing an expiry forward is free, pushing it
later or removing it needs every grant the integration has. A new key's form
is pre-filled with the days the newest key was given.
"""
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.audit.db_models import AuditEventDB
from app.auth import integrations as ints
from app.auth import service as auth
from app.auth.db_models import IntegrationCredentialDB, IntegrationDB, IntegrationGrantDB
from app.auth.permissions import SENDS_EXECUTE, VIEW
from app.database import SessionLocal
from tests.test_api_guard import signed_in


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def integration(db, default_brand):
    made = ints.create_integration(db, name=f"expiry-{uuid.uuid4().hex[:6]}")
    ints.grant(db, made.id, VIEW, default_brand.id)
    yield made
    db.rollback()
    db.query(IntegrationCredentialDB).filter(IntegrationCredentialDB.integration_id == made.id).delete()
    db.query(IntegrationGrantDB).filter(IntegrationGrantDB.integration_id == made.id).delete()
    db.query(AuditEventDB).filter(AuditEventDB.subject_type == "integration",
                                  AuditEventDB.subject_id == made.id).delete(synchronize_session=False)
    db.query(IntegrationDB).filter(IntegrationDB.id == made.id).delete()
    db.commit()


def _age(db, credential, days):
    """Move a key's expiry `days` into the past (negative: the future)."""
    credential.expires_at = auth.now() - timedelta(days=days)
    db.commit()


# --- issuing and refusing ---------------------------------------------------------

def test_a_key_without_expiry_lives_as_today(db, integration):
    credential, secret = ints.issue_credential(db, integration.id, "no expiry")
    assert credential.expires_at is None and credential.expires_in_days is None
    assert ints.authenticate(db, credential.key_id, secret) is not None


def test_a_key_with_expiry_stores_the_date_and_the_days(db, integration):
    credential, _ = ints.issue_credential(db, integration.id, "90 days", expires_in_days=90)
    assert credential.expires_in_days == 90
    assert timedelta(days=89, hours=23) < credential.expires_at - credential.created_at <= timedelta(days=90, minutes=1)


@pytest.mark.parametrize("days", [0, -1, 3651])
def test_days_outside_the_range_are_refused(db, integration, days):
    with pytest.raises(ValueError):
        ints.issue_credential(db, integration.id, "bad", expires_in_days=days)


def test_an_expired_key_is_refused_exactly_like_a_revoked_one(db, integration):
    expired, expired_secret = ints.issue_credential(db, integration.id, "expired", expires_in_days=30)
    _age(db, expired, 1)
    revoked, revoked_secret = ints.issue_credential(db, integration.id, "revoked")
    ints.revoke_credential(db, revoked.id, integration_id=integration.id)
    assert ints.authenticate(db, expired.key_id, expired_secret) is None
    assert ints.authenticate(db, revoked.key_id, revoked_secret) is None
    # And through the API, the same answer for both.
    from fastapi.testclient import TestClient

    from main import app

    api = TestClient(app, raise_server_exceptions=False)
    answers = [api.get("/campaigns/", headers={"Authorization": f"Bearer {key}.{secret}", "X-Brand": "1"})
               for key, secret in ((expired.key_id, expired_secret), (revoked.key_id, revoked_secret))]
    assert answers[0].status_code == answers[1].status_code == 401
    assert answers[0].json() == answers[1].json()


# --- the list ------------------------------------------------------------------------

def _listed(db, integration_id):
    with signed_in(db) as (cookied, _token, _csrf):
        listed = cookied.get("/integrations").json()
    return next(i for i in listed if i["id"] == integration_id)


def test_the_list_shows_expiry_counts_only_live_keys_and_marks_soon(db, integration):
    soon, _ = ints.issue_credential(db, integration.id, "soon", expires_in_days=10)
    expired, _ = ints.issue_credential(db, integration.id, "expired", expires_in_days=30)
    _age(db, expired, 1)
    ints.issue_credential(db, integration.id, "forever")
    shown = _listed(db, integration.id)
    assert shown["live_keys"] == 2, "an expired key is not live"
    assert shown["expiring_soon"] is True
    by_label = {c["label"]: c for c in shown["credentials"]}
    assert by_label["soon"]["expiring_soon"] is True and by_label["soon"]["expires_at"]
    assert by_label["forever"]["expires_at"] is None and by_label["forever"]["expiring_soon"] is False


def test_the_form_is_prefilled_from_the_newest_key(db, integration):
    ints.issue_credential(db, integration.id, "old", expires_in_days=30)
    ints.issue_credential(db, integration.id, "new", expires_in_days=90)
    assert _listed(db, integration.id)["suggested_expiry_days"] == 90


# --- changing an existing key ---------------------------------------------------------

@pytest.fixture
def outsider(db):
    """A person with integrations.manage who does NOT hold the integration's grants."""
    user = auth.create_user(db, email=f"exp-{uuid.uuid4().hex[:8]}@example.invalid", role_key="admin")
    yield user
    db.rollback()
    for table in ("login_codes", "auth_sessions", "role_assignments"):
        db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
    db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
    db.commit()


@pytest.fixture
def foreign_integration(db, foreign_brand):
    made = ints.create_integration(db, name=f"expiry-f-{uuid.uuid4().hex[:6]}")
    ints.grant(db, made.id, SENDS_EXECUTE, foreign_brand.id)
    yield made
    db.rollback()
    db.query(IntegrationCredentialDB).filter(IntegrationCredentialDB.integration_id == made.id).delete()
    db.query(IntegrationGrantDB).filter(IntegrationGrantDB.integration_id == made.id).delete()
    db.query(IntegrationDB).filter(IntegrationDB.id == made.id).delete()
    db.commit()


def test_shortening_is_free_and_lengthening_or_removing_is_gated(db, outsider, foreign_integration):
    credential, _ = ints.issue_credential(db, foreign_integration.id, "agency", expires_in_days=90)
    # Brought forward: allowed without the integration's grants.
    assert ints.set_credential_expiry_by_person(db, outsider, foreign_integration.id, credential.id, 30)
    db.refresh(credential)
    assert credential.expires_in_days == 30
    # Pushed later, or removed: refused.
    with pytest.raises(ints.GrantForbidden):
        ints.set_credential_expiry_by_person(db, outsider, foreign_integration.id, credential.id, 365)
    with pytest.raises(ints.GrantForbidden):
        ints.set_credential_expiry_by_person(db, outsider, foreign_integration.id, credential.id, None)


def test_adding_an_expiry_to_a_key_without_one_is_free(db, outsider, foreign_integration):
    credential, _ = ints.issue_credential(db, foreign_integration.id, "forever")
    assert ints.set_credential_expiry_by_person(db, outsider, foreign_integration.id, credential.id, 7)
    db.refresh(credential)
    assert credential.expires_at is not None


def test_the_change_is_audited_through_the_api(db, integration):
    credential, _ = ints.issue_credential(db, integration.id, "agency", expires_in_days=90)
    before = credential.expires_at.isoformat()
    with signed_in(db) as (cookied, _token, csrf):
        response = cookied.put(f"/integrations/{integration.id}/keys/{credential.id}/expiry",
                               json={"expires_in_days": 30}, headers={"X-CSRF-Token": csrf})
    assert response.status_code == 200, response.text
    entry = (db.query(AuditEventDB).filter(AuditEventDB.action == "integration.key_expiry_set",
                                           AuditEventDB.subject_id == integration.id)
             .order_by(AuditEventDB.id.desc()).first())
    assert entry.detail["credential_id"] == credential.id
    assert entry.detail["from"] == before and entry.detail["to"] is not None


def test_a_key_can_be_issued_with_days_through_the_api(db, integration):
    with signed_in(db) as (cookied, _token, csrf):
        response = cookied.post(f"/integrations/{integration.id}/keys",
                                json={"label": "api", "expires_in_days": 14}, headers={"X-CSRF-Token": csrf})
    assert response.status_code == 201, response.text
    assert response.json()["credential"]["expires_in_days"] == 14
