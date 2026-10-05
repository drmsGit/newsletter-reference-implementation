"""A record's readiness per channel, and machine ready (task-283).

ADR-174 and ADR-179, their addenda of 2026-10-05, decided with the user
(task-282): a row per (record, channel) a person marked ready, with who and
when; machine ready on the record, off for a new one; a person marks
directly, an integration's mark is refused until task-206 can hold it, and an
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


class TestAnIntegration:
    def test_its_mark_is_refused_until_it_can_be_held(self, db, record):
        with machine([CONTENT_MANAGE]) as headers:
            assert api.put(f"/content/{record}/readiness/push", headers=headers).status_code == 403
        assert db.query(ContentChannelReadinessDB).filter_by(content_id=record).count() == 0

    def test_it_may_unmark_directly_and_that_is_audited(self, db, record, person):
        client, csrf, _ = person
        client.put(f"/content/{record}/readiness/email", headers=csrf)
        with machine([CONTENT_MANAGE]) as headers:
            assert api.delete(f"/content/{record}/readiness/email", headers=headers).status_code == 204
            assert api.delete(f"/content/{record}/readiness/email", headers=headers).status_code == 204
        assert db.query(ContentChannelReadinessDB).filter_by(content_id=record).count() == 0
        [entry] = _entries(db, audit.CONTENT_READY_UNMARKED, record)
        assert entry.actor_type == audit.ACTOR_INTEGRATION and entry.detail["channel"] == "email"

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
