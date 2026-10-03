"""Catalogue edits have a version, an audit trail and an honest publish state (task-257).

The variant editor saves catalogue fields on blur (design pass D1). Without a
token two managers editing one record silently overwrite each other; content
edits were not audited (ADR-153 point 4); a send uses the latest *published*
version, so the editor must be able to say when an edit is not in it yet
(design pass D5); and publishing took its author from the request body.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.audit import service as audit
from app.audit.db_models import AuditEventDB
from app.auth import service as auth
from app.auth.permissions import CONTENT_MANAGE, VIEW
from app.content.db_models import ContentRecordDB, ContentVersionDB
from main import app
from tests.machine import machine

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def record(db, default_brand):
    row = ContentRecordDB(title=f"ce-{uuid.uuid4().hex[:6]}", content={"headline_medium": "H"},
                          status="active", brand_id=default_brand.id)
    db.add(row); db.commit()
    yield row
    db.rollback()
    db.query(AuditEventDB).filter(AuditEventDB.subject_type == "content",
                                  AuditEventDB.subject_id == row.id).delete()
    db.query(ContentVersionDB).filter(ContentVersionDB.content_record_id == row.id).delete()
    db.query(ContentRecordDB).filter(ContentRecordDB.id == row.id).delete()
    db.commit()


def _call(method, url, token=None, **kw):
    with machine([CONTENT_MANAGE, VIEW]) as headers:
        if token is not None:
            headers = {**headers, "If-Match": token}
        return getattr(client, method)(url, headers=headers, **kw)


def _detail(record):
    response = _call("get", f"/content/{record.id}")
    assert response.status_code == 200, response.text
    return response.json()


def _patch(record, value, token=None):
    return _call("patch", f"/content/{record.id}", token,
                 json={"content": {"headline_medium": value}, "groups": ["email"]})


class TestVersionToken:
    def test_a_stale_patch_is_refused_and_changes_nothing(self, db, record):
        token = _detail(record)["updated_at"]
        fresh = _patch(record, "Mine", token)
        assert fresh.status_code == 200, fresh.text
        assert fresh.json()["updated_at"] != token, "an edit must move the record's version"
        assert _patch(record, "Stale", token).status_code == 409
        assert _detail(record)["content"]["headline_medium"] == "Mine"
        assert _patch(record, "Untokened").status_code == 200, "a write without a token still works"

    def test_a_stale_put_is_refused(self, record):
        token = _detail(record)["updated_at"]
        assert _patch(record, "Mine", token).status_code == 200
        response = _call("put", f"/content/{record.id}", token,
                         json={"title": record.title, "content": {"headline_medium": "Stale"}})
        assert response.status_code == 409, response.text


class TestPublishState:
    def test_unpublished_then_published_then_edited(self, record):
        before = _detail(record)
        assert (before["latest_version_number"], before["unpublished_changes"]) == (None, True)

        assert _call("post", "/content/versions", json={"content_record_id": record.id}).status_code == 200
        published = _detail(record)
        assert (published["latest_version_number"], published["unpublished_changes"]) == (1, False)

        assert _patch(record, "Fixed typo").status_code == 200
        edited = _detail(record)
        assert (edited["latest_version_number"], edited["unpublished_changes"]) == (1, True)


class TestAudit:
    def test_an_edit_and_a_publish_are_audited_with_the_machine_as_actor(self, db, record):
        assert _patch(record, "New").status_code == 200
        published = _call("post", "/content/versions",
                          json={"content_record_id": record.id, "created_by": "Somebody Else"})
        assert published.status_code == 200, published.text
        entries = db.query(AuditEventDB).filter(AuditEventDB.subject_type == "content",
                                                AuditEventDB.subject_id == record.id) \
            .order_by(AuditEventDB.id).all()
        assert [e.action for e in entries] == [audit.CONTENT_UPDATED, audit.CONTENT_PUBLISHED]
        assert entries[0].detail["fields"] == ["headline_medium"]
        assert {e.actor_type for e in entries} == {audit.ACTOR_INTEGRATION}
        # The author is the caller, whatever the body says (task-243's rule).
        assert published.json()["created_by"].startswith("integration:apitest-")

    def test_the_jinja_forms_audit_and_name_the_signed_in_person(self, db, record, default_brand):
        user = auth.create_user(db, email=f"ce-{uuid.uuid4().hex[:8]}@example.invalid",
                                role_key="admin", brand_id=default_brand.id)
        token = auth.create_session(db, user)
        page = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
        page.cookies.set(auth.SESSION_COOKIE, token)
        csrf = auth.csrf_token_for(token)
        try:
            edited = page.post(f"/ui/content/{record.id}/edit",
                               data={"csrf_token": csrf, "title": record.title, "headline_medium": "Jinja"})
            published = page.post(f"/ui/content/{record.id}/publish-version",
                                  data={"csrf_token": csrf, "created_by": "Somebody Else"})
            assert edited.status_code == 303 and published.status_code == 303
            actions = [(e.action, e.actor_id) for e in db.query(AuditEventDB).filter(
                AuditEventDB.subject_type == "content", AuditEventDB.subject_id == record.id)
                .order_by(AuditEventDB.id)]
            assert actions == [(audit.CONTENT_UPDATED, user.id), (audit.CONTENT_PUBLISHED, user.id)]
            version = db.query(ContentVersionDB).filter(ContentVersionDB.content_record_id == record.id).one()
            assert version.created_by == auth.actor_label(user)
        finally:
            db.rollback()
            for table in ("login_codes", "auth_sessions", "role_assignments"):
                db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
            db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
            db.commit()
