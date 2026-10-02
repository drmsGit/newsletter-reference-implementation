"""The audience list's counts over JSON (task-50, B26; ADR-176 point 5).

A group resolves to different people per channel, so the count exists only
for a channel the caller names; without one there is no count. The Jinja list
shows an email figure as if it were the group's size (task-116) — this is the
shape the React list gets instead.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB
from app.auth.permissions import VIEW
from app.auth.service import ensure_default_brand
from app.database import SessionLocal
from app.recipients.consent import record_consent
from app.recipients.db_models import ConsentEventDB, RecipientDB
from main import app
from tests.machine import machine

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def group(db):
    """Three pinned members: one consenting to email only, two to push only.
    Asymmetric on purpose — with one each, a count that ignored the channel
    would still come out right on both."""
    brand = ensure_default_brand(db)
    group = AudienceGroupDB(brand_id=brand.id, name=f"counts-{uuid.uuid4().hex[:8]}")
    db.add(group)
    db.flush()
    people = []
    for channel in ("email", "push", "push"):
        recipient = RecipientDB(external_id=f"counts-{uuid.uuid4()}", status="active")
        db.add(recipient)
        db.flush()
        record_consent(db, recipient.id, "opted_in", brand.id, channel=channel,
                       source="test", note="counts", commit=False)
        db.add(AudienceGroupMemberDB(group_id=group.id, recipient_id=recipient.id))
        people.append(recipient.id)
    db.commit()
    yield group.id
    db.rollback()
    db.query(AudienceGroupMemberDB).filter(AudienceGroupMemberDB.group_id == group.id).delete()
    db.query(AudienceGroupDB).filter(AudienceGroupDB.id == group.id).delete()
    db.query(ConsentEventDB).filter(ConsentEventDB.recipient_id.in_(people)).delete(
        synchronize_session=False)
    db.query(RecipientDB).filter(RecipientDB.id.in_(people)).delete(synchronize_session=False)
    db.commit()


def _row(params, group_id):
    with machine([VIEW]) as headers:
        response = client.get("/api/audience-groups/", params=params, headers=headers)
    assert response.status_code == 200, response.text
    return next(r for r in response.json() if r["id"] == group_id)


def test_the_count_is_per_channel_and_says_which(group):
    email, push = _row({"channel": "email"}, group), _row({"channel": "push"}, group)
    assert (email["recipient_count"], email["count_channel"]) == (1, "email")
    assert (push["recipient_count"], push["count_channel"]) == (2, "push")


def test_without_a_channel_there_is_no_count_only_pins(group):
    row = _row({}, group)
    assert row["recipient_count"] is None and row["count_channel"] is None
    assert row["pinned_count"] == 3


def test_an_unregistered_channel_is_refused(group):
    with machine([VIEW]) as headers:
        response = client.get("/api/audience-groups/", params={"channel": "pigeon"},
                              headers=headers)
    assert response.status_code == 422, response.text
