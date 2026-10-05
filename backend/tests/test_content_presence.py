"""An empty push field is absent, not blank — on every write path (task-50, B18).

An absent push field means nothing was written for push; a stored `""`
would make a record look prepared for a channel nobody prepared it for
(`PRESENCE_SIGNIFICANT_GROUPS`). Readiness itself is a person's mark since
ADR-174, not field presence. The Jinja form and `PATCH` already honoured that; `POST
/content/` and `PUT /content/{id}` stored the client's dict verbatim, so the
SPA — the client that replaces the Jinja UI — would have broken it.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.permissions import CONTENT_MANAGE, VIEW
from app.auth.service import ensure_default_brand
from app.content import service
from app.content.db_models import ContentRecordDB
from app.database import SessionLocal
from main import app
from tests.machine import machine

client = TestClient(app, raise_server_exceptions=False)
PUSH = ("push_title", "push_body", "push_image_url", "push_link")


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def titles(db):
    """Titles a test used; their records are removed afterwards."""
    used = []
    yield used
    db.rollback()
    for title in used:
        db.query(ContentRecordDB).filter(ContentRecordDB.title == title).delete()
    db.commit()


def _title(titles):
    title = f"presence-{uuid.uuid4().hex[:8]}"
    titles.append(title)
    return title


def _stored(db, title):
    db.expire_all()
    return db.query(ContentRecordDB).filter(ContentRecordDB.title == title).one().content


class TestThePureRule:
    def test_every_empty_push_field_is_removed(self):
        cleaned = service.without_empty_presence_fields(
            {"headline_medium": "Hi", **{name: "" for name in PUSH}})
        assert cleaned == {"headline_medium": "Hi"}

    def test_whitespace_counts_as_empty_and_kept_values_are_stripped(self):
        cleaned = service.without_empty_presence_fields(
            {"push_title": "   ", "push_body": "  Go.  "})
        assert cleaned == {"push_body": "Go."}

    def test_email_fields_are_stored_as_written_even_when_empty(self):
        cleaned = service.without_empty_presence_fields(
            {"body_medium": "", "button_label": "  Buy  ", "unknown_key": ""})
        assert cleaned == {"body_medium": "", "button_label": "  Buy  ", "unknown_key": ""}

    def test_the_input_is_not_mutated(self):
        original = {"push_title": ""}
        service.without_empty_presence_fields(original)
        assert original == {"push_title": ""}

    def test_none_is_tolerated(self):
        assert service.without_empty_presence_fields(None) == {}


class TestTheJsonWritePaths:
    def test_post_drops_empty_push_fields(self, db, titles):
        title = _title(titles)
        with machine([VIEW, CONTENT_MANAGE]) as headers:
            response = client.post("/content/", headers=headers, json={
                "title": title,
                "content": {"headline_medium": "Email only", "push_title": "",
                            "push_body": "  "},
            })
        assert response.status_code == 200, response.text
        assert "push_title" not in response.json()["content"]
        stored = _stored(db, title)
        assert stored == {"headline_medium": "Email only"}, stored

    def test_post_keeps_a_push_field_that_has_a_value(self, db, titles):
        title = _title(titles)
        with machine([VIEW, CONTENT_MANAGE]) as headers:
            client.post("/content/", headers=headers, json={
                "title": title,
                "content": {"headline_medium": "Both", "push_title": " Ready "},
            })
        assert _stored(db, title)["push_title"] == "Ready"

    def test_put_drops_empty_push_fields_too(self, db, titles):
        title = _title(titles)
        brand = ensure_default_brand(db)
        record = service.create_content(
            db, title=title, brand_id=brand.id,
            content={"headline_medium": "x", "push_title": "Real"},
        )
        with machine([VIEW, CONTENT_MANAGE]) as headers:
            response = client.put(f"/content/{record.id}", headers=headers, json={
                "title": title,
                "content": {"headline_medium": "x", "push_title": ""},
            })
        assert response.status_code == 200, response.text
        assert "push_title" not in _stored(db, title)
