"""The accountability log's first slice (ADR-153).

**These tests go over HTTP, all of them.** The log is written from routes, not
services — the route knows who is acting and the service layer takes a database
session, not a request. So a test that calls `audit.record` directly would prove
the table works and nothing about whether anything writes to it, which is the
gap that has hidden four separate defects in this project.

Scope of the slice, and what is deliberately absent: ADR-153 point 2's homeless
events (sign-in, role grants and removals, deactivation) plus brand creation.
NOT point 4's exports and bulk reads, and NOT point 6's aggregated
authentication failures.
"""
import uuid

import pytest

from app.audit import service as audit
from app.audit.db_models import AuditEventDB
from app.auth import service as auth
from app.auth.db_models import BrandDB, RoleAssignmentDB, RoleDB, SessionDB, UserDB
from app.database import SessionLocal


@pytest.fixture
def db():
    session = SessionLocal()
    auth.bootstrap(session)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def admin_client(db, monkeypatch):
    """A signed-in Admin, and the audit rows they generate cleaned up after."""
    from fastapi.testclient import TestClient

    from main import app

    monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
    admin = (
        db.query(UserDB)
        .join(RoleAssignmentDB, RoleAssignmentDB.user_id == UserDB.id)
        .join(RoleDB, RoleDB.id == RoleAssignmentDB.role_id)
        .filter(RoleDB.key == "admin", UserDB.is_active.is_(True))
        .first()
    )
    if admin is None:
        pytest.skip("no active admin in this database to act as")

    token = auth.create_session(db, admin)
    client = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
    client.cookies.set(auth.SESSION_COOKIE, token)
    started = db.query(AuditEventDB).count()

    yield client, token, admin, started

    db.query(AuditEventDB).filter(AuditEventDB.id > 0).filter(
        AuditEventDB.actor_id == admin.id
    ).delete()
    db.query(SessionDB).filter(
        SessionDB.token_hash == auth.hash_secret(token)
    ).delete()
    db.commit()


@pytest.fixture
def temp_user(db):
    created: list[int] = []

    def make() -> UserDB:
        user = auth.create_user(
            db, email=f"audit-{uuid.uuid4().hex[:10]}@example.invalid", role_key="viewer"
        )
        created.append(user.id)
        return user

    yield make

    for user_id in created:
        db.query(AuditEventDB).filter(
            AuditEventDB.subject_type == "user", AuditEventDB.subject_id == user_id
        ).delete()
        db.query(SessionDB).filter(SessionDB.user_id == user_id).delete()
        db.query(RoleAssignmentDB).filter(RoleAssignmentDB.user_id == user_id).delete()
        db.query(UserDB).filter(UserDB.id == user_id).delete()
    db.commit()


class TestTheHomelessEventsAreRecorded:
    """ADR-153 point 2: these have no domain record anywhere.

    Without this log they are "simply not recorded" — and brand grants were
    built last week with no trace of who granted what to whom.
    """

    def test_granting_a_role_is_recorded(self, db, admin_client, temp_user):
        client, token, admin, _ = admin_client
        user = temp_user()
        role = db.query(RoleDB).filter(RoleDB.key == "manager").first()
        brand = auth.ensure_default_brand(db)

        response = client.post(
            f"/ui/users/{user.id}/roles",
            data={
                "role_id": role.id,
                "brand_id": brand.id,
                "csrf_token": auth.csrf_token_for(token),
            },
        )
        assert response.status_code == 303
        db.expire_all()

        events = audit.events_for_subject(db, "user", user.id)
        grants = [e for e in events if e.action == audit.ROLE_GRANTED]
        assert grants, "granting a role left no audit entry"
        entry = grants[0]
        assert entry.actor_id == admin.id, "the entry does not name who granted it"
        assert entry.brand_id == brand.id
        assert entry.detail["role_id"] == role.id

    def test_revoking_a_role_records_what_was_removed(self, db, admin_client, temp_user):
        """The grant is read BEFORE revoking, or the entry says nothing useful."""
        client, token, admin, _ = admin_client
        user = temp_user()
        role = db.query(RoleDB).filter(RoleDB.key == "manager").first()
        brand = auth.ensure_default_brand(db)
        auth.assign_role(db, user.id, role.id, brand_id=brand.id)
        grant = (
            db.query(RoleAssignmentDB)
            .filter(
                RoleAssignmentDB.user_id == user.id,
                RoleAssignmentDB.role_id == role.id,
            )
            .first()
        )

        client.post(
            f"/ui/users/assignments/{grant.id}/remove",
            data={"csrf_token": auth.csrf_token_for(token)},
        )
        db.expire_all()

        revoked = [
            e for e in audit.events_for_subject(db, "user", user.id)
            if e.action == audit.ROLE_REVOKED
        ]
        assert revoked, "revoking a role left no audit entry"
        assert revoked[0].detail is not None, (
            "the entry recorded no detail — after the row is deleted it could "
            "only say 'some assignment was removed', which is not accountability"
        )
        assert revoked[0].detail["role_id"] == role.id

    def test_deactivating_a_user_is_recorded_and_distinguishable(
        self, db, admin_client, temp_user
    ):
        client, token, admin, _ = admin_client
        user = temp_user()

        client.post(
            f"/ui/users/{user.id}/active",
            data={"active": "", "csrf_token": auth.csrf_token_for(token)},
        )
        client.post(
            f"/ui/users/{user.id}/active",
            data={"active": "1", "csrf_token": auth.csrf_token_for(token)},
        )
        db.expire_all()

        actions = [e.action for e in audit.events_for_subject(db, "user", user.id)]
        assert audit.USER_DEACTIVATED in actions
        assert audit.USER_REACTIVATED in actions, (
            "deactivation and reactivation share an action name, so the log "
            "cannot tell which way somebody moved an account"
        )

    def test_creating_a_brand_is_recorded_against_the_new_brand(self, db, admin_client):
        client, token, admin, _ = admin_client
        key = f"audit-{uuid.uuid4().hex[:8]}"

        client.post(
            "/ui/brands",
            data={"key": key, "name": "Audited Brand",
                  "csrf_token": auth.csrf_token_for(token)},
        )
        db.expire_all()
        brand = db.query(BrandDB).filter(BrandDB.key == key).first()
        try:
            assert brand is not None
            entries = audit.events_for_subject(db, "brand", brand.id)
            assert entries, "creating a brand left no audit entry"
            assert entries[0].brand_id == brand.id, (
                "the entry was filed under the actor's working brand rather "
                "than the brand it created, so every creation reads as an "
                "event in brand 1"
            )
        finally:
            db.query(AuditEventDB).filter(
                AuditEventDB.subject_type == "brand", AuditEventDB.subject_id == brand.id
            ).delete()
            db.query(BrandDB).filter(BrandDB.id == brand.id).delete()
            db.commit()


class TestTheLogIsEvidence:

    def test_an_audit_failure_never_breaks_the_action(self, db):
        """A log entry that cannot write must not roll back what it records.

        This is the failure mode that gets audit logging switched off in
        production: a grant refused because its entry would not save. `record`
        swallows the database's refusal and logs at error instead.

        **A real refusal, not a stand-in.** This used to monkeypatch `db.add` to
        raise RuntimeError; since task-22 only a database error is swallowed,
        and a value too long for its column is a genuine one — it also runs
        the savepoint for real.
        """
        before = audit.failure_count()

        assert audit.record(db, "x" * 200, actor_id=1) is None, (
            "a refused audit write raised instead of returning None"
        )
        assert audit.failure_count() == before + 1, "the failure was not counted"

    def test_a_failed_entry_leaves_the_callers_uncommitted_work_alone(self, db):
        """task-22, the P1. `record` used to `db.rollback()` the CALLER's
        session — with `commit=False`, exactly when the caller still holds
        uncommitted work. Now only the savepoint around the entry is undone."""
        marker = f"audit.task22.{uuid.uuid4().hex[:8]}"
        db.add(AuditEventDB(actor_type=audit.ACTOR_USER, action=marker))   # the caller's work

        audit.record(db, "x" * 200, commit=False)
        db.commit()

        try:
            assert db.query(AuditEventDB).filter(AuditEventDB.action == marker).count() == 1, (
                "the caller's uncommitted work was rolled back by a failed audit write"
            )
        finally:
            db.query(AuditEventDB).filter(AuditEventDB.action == marker).delete()
            db.commit()

    def test_with_commit_the_callers_work_is_committed_anyway(self, db):
        """The action still happens; only its log entry is missing."""
        marker = f"audit.task22.{uuid.uuid4().hex[:8]}"
        db.add(AuditEventDB(actor_type=audit.ACTOR_USER, action=marker))

        audit.record(db, "x" * 200, commit=True)

        db.expire_all()
        try:
            assert db.query(AuditEventDB).filter(AuditEventDB.action == marker).count() == 1
        finally:
            db.query(AuditEventDB).filter(AuditEventDB.action == marker).delete()
            db.commit()

    def test_a_bug_in_the_calling_code_is_not_swallowed(self, db, monkeypatch):
        """Only "the database refused the write" is swallowed. Anything else is
        a bug, and a bug that reads as a log line while the app keeps working
        is how a broken audit trail goes unnoticed."""
        def explode(*args, **kwargs):
            raise RuntimeError("not a database error")

        monkeypatch.setattr(db, "add", explode)
        with pytest.raises(RuntimeError):
            audit.record(db, audit.SIGNED_IN, actor_id=1)

    def test_writes_are_append_only_in_shape(self):
        """No status, no updated_at, nothing a later write could change.

        An audit entry that can be edited is not evidence, and the cheapest
        guarantee is a table with nothing to edit.
        """
        columns = set(AuditEventDB.__table__.columns.keys())
        assert "updated_at" not in columns
        assert "status" not in columns
        assert columns == {
            "id", "actor_type", "actor_id", "action",
            "subject_type", "subject_id", "brand_id", "detail", "created_at",
        }

    def test_the_table_has_no_foreign_keys(self):
        """ADR-153 point 5's asymmetry, enforced by the absence of a constraint.

        An entry attributing an action to an operator must survive the erasure
        of any recipient. A foreign key would either block that deletion or
        cascade it, and both destroy the record the log exists to keep.
        """
        assert not list(AuditEventDB.__table__.foreign_keys), (
            "the audit log gained a foreign key — an entry must be able to "
            "outlive what it references"
        )


class TestTheActorIsReadStrictly:
    """task-23. `record_from_request` read the middleware's attributes through
    `getattr(..., None)`. The middleware sets them on every request, so the
    default was never needed — and it meant renaming one would turn every
    actor into NULL silently, in the one field this table exists for."""

    def _request(self, **state):
        from types import SimpleNamespace

        return SimpleNamespace(state=SimpleNamespace(**state))

    def test_a_missing_middleware_attribute_raises_rather_than_writing_null(self, db):
        request = self._request(current_brand=None)   # no current_user: as if renamed

        with pytest.raises(AttributeError):
            audit.record_from_request(request, db, audit.SIGNED_IN)

    def test_an_anonymous_request_still_writes_an_honest_null_actor(self, db):
        """None is a real answer — enforcement off, nobody signed in — and
        recording "no actor" beats attributing the action to somebody."""
        marker = f"audit.task23.{uuid.uuid4().hex[:8]}"
        event = audit.record_from_request(
            self._request(current_user=None, current_brand=None), db, marker)
        try:
            assert event is not None and event.actor_id is None
        finally:
            db.query(AuditEventDB).filter(AuditEventDB.action == marker).delete()
            db.commit()

    def test_without_a_resolved_working_brand_the_session_brand_is_used(self, db):
        """`working_brand_id` keeps its default on purpose: only the JSON guard
        sets it, so on the Jinja plane its absence is ordinary."""
        marker = f"audit.task23.{uuid.uuid4().hex[:8]}"
        event = audit.record_from_request(
            self._request(current_user={"id": 7}, current_brand={"id": 3}), db, marker)
        try:
            assert (event.actor_id, event.brand_id) == (7, 3)
        finally:
            db.query(AuditEventDB).filter(AuditEventDB.action == marker).delete()
            db.commit()
