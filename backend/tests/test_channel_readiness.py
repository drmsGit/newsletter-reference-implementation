"""A record's readiness per channel, and machine ready (task-283).

ADR-174 and ADR-179, their addenda of 2026-10-05, decided with the user
(task-282): a row per (record, channel) a person marked ready, with who and
when; machine ready on the record, off for a new one; a person marks
directly, an integration's mark is held for a person (task-206), and an
integration may unmark; machine ready is people only. The warning fires when
the record can fill no module of the channel. Migration 0032 sets existing
records machine ready and marks active ones ready for email — once.
"""
import uuid
from pathlib import Path

import psycopg2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.audit import service as audit
from app.audit.db_models import AuditEventDB
from app.auth import service as auth
from app.auth.permissions import CONTENT_MANAGE, VIEW
from app.content.db_models import ContentChannelReadinessDB, ContentRecordDB
from app.database import SessionLocal
from main import app
from tests.conftest import TEST_DATABASE_URL
from tests.machine import machine

api = TestClient(app, raise_server_exceptions=False)
TAG = f"ready{uuid.uuid4().hex[:6]}"
MIGRATION = Path(__file__).resolve().parents[1] / "scripts" / "migrate_0032_channel_readiness.sql"


@pytest.fixture
def record(db, default_brand):
    """A record with an image-module headline and no push copy."""
    row = ContentRecordDB(title=f"{TAG} record", content={"headline_medium": "Lisbon"},
                          status="active", brand_id=default_brand.id, machine_ready=True)
    db.add(row); db.commit()
    rid = row.id
    db.rollback()  # end the transaction reading `row.id` opened, so no lock is held
    yield rid
    db.rollback()
    db.query(AuditEventDB).filter(AuditEventDB.subject_type == "content",
                                  AuditEventDB.subject_id == rid).delete()
    db.query(ContentChannelReadinessDB).filter(ContentChannelReadinessDB.content_id == rid).delete()
    db.query(ContentRecordDB).filter(ContentRecordDB.id == rid).delete()
    db.commit()


@pytest.fixture
def person(db, default_brand):
    """A signed-in person on the JSON plane, as the React client is."""
    user = auth.create_user(db, email=f"{TAG}-{uuid.uuid4().hex[:6]}@example.invalid",
                            role_key="admin", brand_id=default_brand.id)
    token = auth.create_session(db, user)
    client = TestClient(app, raise_server_exceptions=False)
    client.cookies.set(auth.SESSION_COOKIE, token)
    csrf = {"X-CSRF-Token": auth.csrf_token_for(token)}
    email = user.email
    yield client, csrf, email
    db.rollback()
    db.query(AuditEventDB).filter(AuditEventDB.actor_type == audit.ACTOR_USER,
                                  AuditEventDB.actor_id == user.id).delete()
    for table in ("login_codes", "auth_sessions", "role_assignments"):
        db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
    db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
    db.commit()


def _detail(rid):
    with machine([VIEW]) as headers:
        return api.get(f"/content/{rid}", headers=headers).json()


def _entries(db, action, rid):
    return db.query(AuditEventDB).filter(AuditEventDB.action == action,
                                         AuditEventDB.subject_id == rid).all()


class TestAPersonMarks:
    def test_a_mark_records_who_and_when_and_warns_when_no_module_can_use_it(self, db, record, person):
        client, csrf, email = person
        response = client.put(f"/content/{record}/readiness/push", headers=csrf)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["marked_by"] == email
        assert body["warning"] == "Marked ready for Push, but Notification title and Notification text are empty"
        [entry] = _entries(db, audit.CONTENT_READY_MARKED, record)
        assert (entry.actor_type, entry.detail) == (audit.ACTOR_USER, {"channel": "push"})
        assert [r["channel"] for r in _detail(record)["readiness"]] == ["push"]

    def test_marking_again_keeps_the_first_mark_and_records_nothing_new(self, db, record, person):
        client, csrf, _ = person
        first = client.put(f"/content/{record}/readiness/email", headers=csrf).json()
        again = client.put(f"/content/{record}/readiness/email", headers=csrf).json()
        assert again["marked_at"] == first["marked_at"]
        assert len(_entries(db, audit.CONTENT_READY_MARKED, record)) == 1

    def test_email_does_not_warn_when_one_module_can_use_it(self, record, person):
        client, csrf, _ = person
        assert client.put(f"/content/{record}/readiness/email", headers=csrf).json()["warning"] is None

    def test_email_warns_with_what_each_kind_of_module_needs(self, db, record, person):
        db.query(ContentRecordDB).filter(ContentRecordDB.id == record).update({"content": {}}); db.commit()
        client, csrf, _ = person
        warning = client.put(f"/content/{record}/readiness/email", headers=csrf).json()["warning"]
        assert warning == ("Marked ready for Email, but no Email module can use it: "
                           "Hero Banner needs Hero headline; Image Left, Image Right and Single Stack need Headline")

    def test_an_unknown_channel_and_another_brands_record_are_not_found(self, record, person, foreign_api):
        client, csrf, _ = person
        assert client.put(f"/content/{record}/readiness/fax", headers=csrf).status_code == 404
        with foreign_api([CONTENT_MANAGE]) as headers:
            assert api.delete(f"/content/{record}/readiness/email", headers=headers).status_code == 404


@pytest.fixture
def held(db, record):
    """The held requests a test raises for `record`, and their audit rows, removed after."""
    from app.approvals import service as approvals
    from app.approvals.db_models import PendingActionDB

    yield lambda: db.query(PendingActionDB).filter_by(action_key="content.mark_ready", subject_id=record).order_by(
        PendingActionDB.id).all()
    db.rollback()
    ids = [i for (i,) in db.query(PendingActionDB.id).filter_by(action_key="content.mark_ready", subject_id=record)]
    db.query(AuditEventDB).filter(AuditEventDB.subject_type == approvals.SUBJECT,
                                  AuditEventDB.subject_id.in_(ids)).delete(synchronize_session=False)
    db.query(PendingActionDB).filter(PendingActionDB.id.in_(ids)).delete(synchronize_session=False)
    db.commit()


class TestAnIntegrationsMarkIsHeld:
    """ADR-174 point 4, built by task-206 (decided 2026-10-08, addenda to ADR-174
    and ADR-142 of that date): a machine's mark is a held request a person
    decides — one per record AND channel, with no deadline — and approving it
    records the approver as the one who marked it."""

    def test_it_is_held_not_applied(self, db, record, held):
        with machine([CONTENT_MANAGE]) as headers:
            response = api.put(f"/content/{record}/readiness/push", headers=headers)
        assert response.status_code == 202, response.text
        assert response.json()["detail"].startswith("Held for a person to approve: Mark content ready for a channel.")
        [row] = held()
        assert (row.status, row.subject_type, row.subject_id, row.subject_scope, row.expires_at) == (
            "pending", "content", record, "push", None)
        assert row.requested_by_type == audit.ACTOR_INTEGRATION
        assert db.query(ContentChannelReadinessDB).filter_by(content_id=record).count() == 0

    def test_one_request_per_channel_and_a_retry_is_the_same_request(self, record, held):
        with machine([CONTENT_MANAGE]) as headers:
            email = api.put(f"/content/{record}/readiness/email", headers=headers)
            first = api.put(f"/content/{record}/readiness/push", headers=headers).json()
            again = api.put(f"/content/{record}/readiness/push", headers=headers).json()
        assert email.status_code == 202, email.text
        assert first == again, "a retry answers with its own channel's request, not the record's other one"
        assert sorted(r.subject_scope for r in held()) == ["email", "push"]

    def test_the_reviewer_sees_the_record_the_channel_and_the_warning(self, record, held, person):
        client, csrf, _ = person
        with machine([CONTENT_MANAGE]) as headers:
            api.put(f"/content/{record}/readiness/push", headers=headers)
        [row] = held()
        detail = client.get(f"/approvals/{row.id}", headers=csrf).json()
        rows = dict((r["label"], r["value"]) for r in detail["rows"])
        assert (rows["Content"], rows["Channel"]) == (f"{TAG} record", "Push")
        assert detail["warnings"] == ["Marked ready for Push, but Notification title and Notification text are empty"]
        assert detail["blocked_reason"] is None, "the warning informs; it does not block"

    def test_approving_marks_it_with_the_approver_as_marker(self, db, record, held, person):
        client, csrf, email = person
        with machine([CONTENT_MANAGE]) as headers:
            api.put(f"/content/{record}/readiness/email", headers=headers)
            [row] = held()
            # Approved while the requesting integration still exists: once it
            # is gone, approving withdraws the request instead (task-331).
            response = client.post(f"/approvals/{row.id}/approve", headers=csrf, json={})
        assert response.status_code == 200 and response.json()["ok"], response.text
        mark = db.query(ContentChannelReadinessDB).filter_by(content_id=record, channel="email").one()
        assert mark.marked_by == email, "the person who approved asserted it"
        [entry] = _entries(db, audit.CONTENT_READY_MARKED, record)
        assert entry.actor_type == audit.ACTOR_USER
        assert entry.detail["channel"] == "email" and entry.detail["pending_action_id"] == row.id

    def test_rejecting_marks_nothing(self, db, record, held, person):
        client, csrf, _ = person
        with machine([CONTENT_MANAGE]) as headers:
            api.put(f"/content/{record}/readiness/email", headers=headers)
        [row] = held()
        assert client.post(f"/approvals/{row.id}/reject", headers=csrf, json={"reason": "not yet"}).status_code == 200
        assert db.query(ContentChannelReadinessDB).filter_by(content_id=record).count() == 0

    def test_a_request_without_its_channel_is_refused_not_held_under_no_scope(self, record, held):
        """An action that declares a scope and is given none would take the empty
        slot every unscoped action uses; refused instead, like a missing subject."""
        from app.approvals import service as approvals

        with pytest.raises(approvals.SubjectRequired):
            approvals.request_approval(
                SessionLocal(), "content.mark_ready", payload={"content_id": record}, summary="x",
                requested_by_type=audit.ACTOR_INTEGRATION, brand_id=1, subject_id=record)
        assert held() == []

    def test_another_brands_record_holds_nothing(self, record, held, foreign_api):
        with foreign_api([CONTENT_MANAGE]) as headers:
            response = api.put(f"/content/{record}/readiness/email", headers=headers)
        assert response.status_code == 409 and "not found" in response.text
        assert held() == []


class TestAnIntegration:

    def test_it_may_unmark_directly_and_that_is_audited(self, db, record, person):
        client, csrf, _ = person
        client.put(f"/content/{record}/readiness/email", headers=csrf)
        with machine([CONTENT_MANAGE]) as headers:
            assert api.delete(f"/content/{record}/readiness/email", headers=headers).status_code == 204
            assert api.delete(f"/content/{record}/readiness/email", headers=headers).status_code == 204
        assert db.query(ContentChannelReadinessDB).filter_by(content_id=record).count() == 0
        [entry] = _entries(db, audit.CONTENT_READY_UNMARKED, record)
        assert entry.actor_type == audit.ACTOR_INTEGRATION and entry.detail["channel"] == "email"
        assert "marked_by" not in entry.detail, "the marker's address stays out of the log (task-52)"

    def test_it_may_not_change_machine_ready(self, record):
        with machine([CONTENT_MANAGE]) as headers:
            response = api.put(f"/content/{record}/machine-ready", json={"machine_ready": False}, headers=headers)
        assert response.status_code == 403
        assert _detail(record)["machine_ready"] is True


class TestMachineReady:
    def test_a_person_turns_it_off_and_the_change_is_audited(self, db, record, person):
        client, csrf, _ = person
        response = client.put(f"/content/{record}/machine-ready", json={"machine_ready": False}, headers=csrf)
        assert response.json() == {"machine_ready": False}
        assert _detail(record)["machine_ready"] is False
        [entry] = _entries(db, audit.CONTENT_MACHINE_READY_CHANGED, record)
        assert (entry.detail["from"], entry.detail["to"]) == (True, False)

    def test_a_new_record_starts_not_machine_ready_and_ready_for_nothing(self, db, person):
        client, csrf, _ = person
        created = client.post("/content/", json={"title": f"{TAG} new", "content": {}}, headers=csrf).json()
        try:
            detail = _detail(created["id"])
            assert (detail["machine_ready"], detail["readiness"]) == (False, [])
        finally:
            db.query(AuditEventDB).filter(AuditEventDB.subject_id == created["id"]).delete()
            db.query(ContentRecordDB).filter(ContentRecordDB.id == created["id"]).delete()
            db.commit()


class TestTheList:
    def test_it_filters_by_readiness_and_says_per_row_what_a_record_is_ready_for(self, record, person):
        client, csrf, _ = person
        client.put(f"/content/{record}/readiness/push", headers=csrf)
        with machine([VIEW]) as headers:
            push = api.get("/content/", params={"ready_for": "push", "q": TAG}, headers=headers).json()
            email = api.get("/content/", params={"ready_for": "email", "q": TAG}, headers=headers).json()
        assert [r["id"] for r in push["items"]] == [record] and push["total"] == 1
        assert push["items"][0]["ready_for"] == ["push"]
        assert (email["items"], email["total"]) == ([], 0)


def test_deleting_a_record_takes_its_marks_with_it(db, record, person):
    client, csrf, _ = person
    client.put(f"/content/{record}/readiness/email", headers=csrf)
    from app.content.service import delete_content_record

    summary = delete_content_record(db, record, force=True, brand_id=auth.ensure_default_brand(db).id)
    assert summary["readiness_marks"] == 1
    assert db.query(ContentChannelReadinessDB).filter_by(content_id=record).count() == 0


def test_the_migration_backfills_once_and_never_marks_push():
    """Run 0032 on this test database inside a transaction that is rolled back:
    drop what it creates, plant an active and an inactive record, run it twice
    with a person's change in between. The backfill must not undo that change."""
    connection = psycopg2.connect(TEST_DATABASE_URL)
    try:
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE content_channel_readiness")
            cursor.execute("ALTER TABLE content_records DROP COLUMN machine_ready")
            cursor.execute("SELECT id FROM brands ORDER BY id LIMIT 1")
            brand = cursor.fetchone()[0]
            cursor.execute("INSERT INTO content_records (brand_id, title, content, status) VALUES "
                           "(%s, 'm-active', '{}', 'active'), (%s, 'm-inactive', '{}', 'inactive') RETURNING id",
                           (brand, brand))
            active, inactive = [row[0] for row in cursor.fetchall()]
            cursor.execute(MIGRATION.read_text())
            cursor.execute("SELECT machine_ready FROM content_records WHERE id IN (%s, %s)", (active, inactive))
            assert {row[0] for row in cursor.fetchall()} == {True}
            cursor.execute("SELECT content_id, channel FROM content_channel_readiness WHERE content_id IN (%s, %s)",
                           (active, inactive))
            assert cursor.fetchall() == [(active, "email")], "active only, email only"
            # A person switches it off and unmarks; running the file again changes neither.
            cursor.execute("UPDATE content_records SET machine_ready = false WHERE id = %s", (active,))
            cursor.execute("DELETE FROM content_channel_readiness WHERE content_id = %s", (active,))
            cursor.execute(MIGRATION.read_text())
            cursor.execute("SELECT machine_ready FROM content_records WHERE id = %s", (active,))
            assert cursor.fetchone()[0] is False
            cursor.execute("SELECT count(*) FROM content_channel_readiness WHERE content_id = %s", (active,))
            assert cursor.fetchone()[0] == 0
    finally:
        connection.rollback()
        connection.close()
