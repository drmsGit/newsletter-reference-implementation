"""A category score is a whole number from 1 to 10, for every caller (task-278).

ADR-080's addendum of 2026-10-04. Nothing enforced it: the service refused
only 0, the CSV import clamped (and turned 'abc' into 10), the Jinja form
allowed 1-100, and a score could only be changed by removing and re-adding the
category. Decided with the user 2026-10-05: the database holds the rule (a
CHECK, added by a migration that refuses and lists bad rows rather than
changing them), and a bad CSV score skips that one assignment and is listed.
"""
import uuid
from pathlib import Path

import psycopg2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.audit import service as audit
from app.audit.db_models import AuditEventDB
from app.auth import service as auth
from app.auth.permissions import CONTENT_MANAGE
from app.content.db_models import CategoryDB, ContentCategoryAssignmentDB, ContentRecordDB
from main import app
from tests.conftest import TEST_DATABASE_URL
from tests.machine import machine

api = TestClient(app, raise_server_exceptions=False)
TAG = f"score{uuid.uuid4().hex[:6]}"
MIGRATION = Path(__file__).resolve().parents[1] / "scripts" / "migrate_0031_category_score_range.sql"


@pytest.fixture
def world(db, default_brand):
    record = ContentRecordDB(title=f"{TAG} record", content={}, status="active", brand_id=default_brand.id)
    assigned, free = CategoryDB(name=f"{TAG} assigned"), CategoryDB(name=f"{TAG} free")
    db.add_all([record, assigned, free]); db.flush()
    assignment = ContentCategoryAssignmentDB(content_id=record.id, category_id=assigned.id, score=7)
    db.add(assignment); db.commit()
    w = {"record": record.id, "assigned": assigned.id, "free": free.id, "assignment": assignment.id}
    # Reading those ids after the commit opened a new transaction, which holds
    # a lock on the table until it ends. Ended here, or the migration test's
    # ALTER TABLE waits on it forever (it did, once).
    db.rollback()
    yield w
    db.rollback()
    db.query(AuditEventDB).filter(AuditEventDB.subject_type == "content",
                                  AuditEventDB.subject_id == w["record"]).delete()
    db.query(ContentCategoryAssignmentDB).filter(ContentCategoryAssignmentDB.content_id == w["record"]).delete()
    db.query(ContentRecordDB).filter(ContentRecordDB.id == w["record"]).delete()
    db.query(CategoryDB).filter(CategoryDB.id.in_([w["assigned"], w["free"]])).delete(synchronize_session=False)
    db.commit()


def _score(db, assignment_id):
    db.expire_all()
    return db.get(ContentCategoryAssignmentDB, assignment_id).score


class TestAssigning:
    @pytest.mark.parametrize("score", [0, 11, -1, 100])
    def test_the_api_refuses_a_score_outside_1_to_10_with_a_field_error(self, world, score):
        with machine([CONTENT_MANAGE]) as headers:
            response = api.post(f"/content/{world['record']}/categories",
                                json={"category_id": world["free"], "score": score}, headers=headers)
        assert response.status_code == 422, response.text
        assert response.json()["detail"][0]["loc"][-1] == "score"

    @pytest.mark.parametrize("score", [1, 10])
    def test_the_ends_of_the_range_are_accepted(self, db, world, score):
        with machine([CONTENT_MANAGE]) as headers:
            response = api.post(f"/content/{world['record']}/categories",
                                json={"category_id": world["free"], "score": score}, headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["score"] == score

    def test_the_service_refuses_too_so_no_plane_can_slip_past(self, db, world, default_brand):
        from app.content.service import assign_category_to_content

        with pytest.raises(ValueError, match="from 1 to 10"):
            assign_category_to_content(db, world["record"], world["free"], 11, brand_id=default_brand.id)

    def test_the_jinja_form_refuses_and_stores_nothing(self, db, world, default_brand):
        user = auth.create_user(db, email=f"{TAG}-{uuid.uuid4().hex[:6]}@example.invalid",
                                role_key="admin", brand_id=default_brand.id)
        token = auth.create_session(db, user)
        page = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
        page.cookies.set(auth.SESSION_COOKIE, token)
        try:
            response = page.post(f"/ui/content/{world['record']}/assign-category",
                                 data={"csrf_token": auth.csrf_token_for(token),
                                       "category_id": world["free"], "score": 15})
            assert response.status_code == 303 and "error=" in response.headers["location"]
            assert db.query(ContentCategoryAssignmentDB).filter_by(
                content_id=world["record"], category_id=world["free"]).count() == 0
        finally:
            db.rollback()
            db.query(AuditEventDB).filter(AuditEventDB.actor_id == user.id).delete()
            for table in ("login_codes", "auth_sessions", "role_assignments"):
                db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
            db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
            db.commit()


class TestChangingAScoreInPlace:
    def _patch(self, world, score, headers, assignment=None):
        return api.patch(f"/content/{world['record']}/assignments/{assignment or world['assignment']}",
                         json={"score": score}, headers=headers)

    def test_the_score_changes_and_the_change_is_audited_from_and_to(self, db, world):
        with machine([CONTENT_MANAGE]) as headers:
            response = self._patch(world, 3, headers)
        assert response.status_code == 200, response.text
        assert response.json()["score"] == 3 and _score(db, world["assignment"]) == 3
        [entry] = db.query(AuditEventDB).filter(AuditEventDB.action == audit.CONTENT_CATEGORY_SCORE_CHANGED,
                                                AuditEventDB.subject_id == world["record"]).all()
        assert entry.detail == {"category_id": world["assigned"], "category": f"{TAG} assigned",
                                "from": 7, "to": 3}
        assert entry.actor_type == audit.ACTOR_INTEGRATION

    def test_setting_the_same_score_records_nothing(self, db, world):
        with machine([CONTENT_MANAGE]) as headers:
            assert self._patch(world, 7, headers).status_code == 200
        assert db.query(AuditEventDB).filter(AuditEventDB.action == audit.CONTENT_CATEGORY_SCORE_CHANGED,
                                             AuditEventDB.subject_id == world["record"]).count() == 0

    @pytest.mark.parametrize("score", [0, 11])
    def test_outside_the_range_is_refused_and_nothing_changes(self, db, world, score):
        with machine([CONTENT_MANAGE]) as headers:
            assert self._patch(world, score, headers).status_code == 422
        assert _score(db, world["assignment"]) == 7

    def test_another_brands_assignment_and_an_unknown_one_are_not_found(self, db, world, foreign_api):
        with foreign_api([CONTENT_MANAGE]) as headers:
            assert self._patch(world, 3, headers).status_code == 404
        with machine([CONTENT_MANAGE]) as headers:
            assert self._patch(world, 3, headers, assignment=999999999).status_code == 404
        assert _score(db, world["assignment"]) == 7


class TestTheDatabaseHoldsTheRule:
    def test_a_direct_insert_outside_the_range_is_refused(self, db, world):
        db.add(ContentCategoryAssignmentDB(content_id=world["record"], category_id=world["free"], score=11))
        with pytest.raises(IntegrityError, match="ck_content_category_assignments_score_range"):
            db.commit()
        db.rollback()

    def test_the_migration_refuses_and_lists_a_bad_row_and_changes_nothing(self, world):
        """Run against this test database inside a transaction that is rolled
        back: drop the constraint, plant a bad row, run 0031. It must stop
        naming the row, and must not have added the constraint."""
        connection = psycopg2.connect(TEST_DATABASE_URL)
        try:
            with connection.cursor() as cursor:
                cursor.execute("ALTER TABLE content_category_assignments "
                               "DROP CONSTRAINT ck_content_category_assignments_score_range")
                cursor.execute("UPDATE content_category_assignments SET score = 15 WHERE id = %s",
                               (world["assignment"],))
                cursor.execute("SAVEPOINT before_migration")
                with pytest.raises(psycopg2.Error) as refused:
                    cursor.execute(MIGRATION.read_text())
                cursor.execute("ROLLBACK TO SAVEPOINT before_migration")
                cursor.execute("SELECT count(*) FROM pg_constraint "
                               "WHERE conname = 'ck_content_category_assignments_score_range'")
                assert cursor.fetchone()[0] == 0, "it added the constraint despite the bad row"
            message = str(refused.value)
            assert f"assignment {world['assignment']}" in message and "score 15" in message
            assert "nothing was changed" in message
        finally:
            connection.rollback()
            connection.close()


class TestTheCsvImport:
    def test_a_bad_score_is_left_out_and_returned_not_clamped_or_guessed(self):
        from scripts.import_content_csv import parse_categories

        parsed, refused = parse_categories("Beach:15|City:abc|Nature|Food:0|Hiking:7")
        assert parsed == [("Nature", 10), ("Hiking", 7)]
        assert refused == ["Beach:15", "City:abc", "Food:0"]

    def test_the_import_lists_what_it_skipped(self, tmp_path, monkeypatch, capsys, db):
        from scripts import import_content_csv

        category = db.query(CategoryDB).order_by(CategoryDB.id).first()
        csv = tmp_path / "scores.csv"
        csv.write_text("title,headline_medium,body_medium,categories\n"
                       f"{TAG} imported,H,B,{category.name}:15|{category.name}:abc\n")
        monkeypatch.setattr("sys.argv", ["import_content_csv.py", str(csv), "--dry-run"])
        assert import_content_csv.main() == 0
        out = capsys.readouterr().out
        assert "scores outside 1-10 or not a number" in out
        assert f"{category.name}:15" in out and f"{category.name}:abc" in out
        assert db.query(ContentRecordDB).filter(ContentRecordDB.title == f"{TAG} imported").count() == 0
