"""The group preview over JSON (task-50, B27; ADR-163's rider, ADR-176 point 5).

The preview's count must be the send's own answer: the resolved audience goes
through the send's exclusion stack, and who drops is counted by stage rather
than swallowed. Fixture, by design:
  - `reachable`: consented to email, has an address      -> reached
  - `no_address`: consented to email, no address row     -> dropped, addressability
  - `no_consent`: no consent at all                      -> never resolved
All three share a language, so one include block matches them.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.audience import service as audience
from app.audience.db_models import AudienceGroupDB, AudienceRuleBlockDB
from app.auth import service as auth
from app.auth.permissions import VIEW
from app.database import SessionLocal
from app.recipients.consent import record_consent
from app.recipients.db_models import AddressabilityDB, ConsentEventDB, RecipientDB
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
def world(db, default_brand):
    language = f"lx-{uuid.uuid4().hex[:6]}"
    people = {}
    for name, consent, address in (
        ("reachable", True, True), ("no_address", True, False), ("no_consent", False, True),
    ):
        recipient = RecipientDB(external_id=f"prev-{uuid.uuid4()}", status="active",
                                language=language)
        db.add(recipient)
        db.flush()
        if address:
            db.add(AddressabilityDB(recipient_id=recipient.id, channel="email",
                                    value={"email": f"{uuid.uuid4().hex[:8]}@example.invalid"},
                                    status="active", is_primary=True))
        if consent:
            record_consent(db, recipient.id, "opted_in", default_brand.id, channel="email",
                           source="test", note="preview", commit=False)
        people[name] = recipient
    group = AudienceGroupDB(brand_id=default_brand.id, name=f"prev-{uuid.uuid4().hex[:8]}")
    db.add(group)
    db.commit()
    audience.add_block(db, group.id, kind="include", criteria={"language": language},
                       label="by language", brand_id=default_brand.id)
    yield {"group": group, "people": people}
    db.rollback()
    ids = [r.id for r in people.values()]
    db.query(AudienceRuleBlockDB).filter(AudienceRuleBlockDB.group_id == group.id).delete()
    db.query(AudienceGroupDB).filter(AudienceGroupDB.id == group.id).delete()
    db.query(ConsentEventDB).filter(ConsentEventDB.recipient_id.in_(ids)).delete(
        synchronize_session=False)
    db.query(AddressabilityDB).filter(AddressabilityDB.recipient_id.in_(ids)).delete(
        synchronize_session=False)
    db.query(RecipientDB).filter(RecipientDB.id.in_(ids)).delete(synchronize_session=False)
    db.commit()


def _preview(group_id, channel="email", brand_id=None):
    with machine([VIEW], brand_id=brand_id) as headers:
        return client.get(f"/api/audience-groups/{group_id}/preview",
                          params={"channel": channel} if channel else {}, headers=headers)


def test_the_preview_counts_what_the_send_would_reach(world):
    response = _preview(world["group"].id)
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["resolved_count"], body["reachable_count"], body["unreachable_count"]) == (2, 1, 1)
    assert body["dropped_by_stage"] == {"addressability": 1}
    assert [r["recipient_id"] for r in body["sample"]] == [world["people"]["reachable"].id]
    assert body["sample"][0]["address"].endswith("@example.invalid")


def test_each_block_carries_its_own_count(world):
    block = _preview(world["group"].id).json()["blocks"][0]
    assert (block["kind"], block["label"]) == ("include", "by language")
    assert block["count"] == 2, "the block counts consenting matches on the channel"


def test_another_channel_is_another_audience(world):
    body = _preview(world["group"].id, channel="push").json()
    assert (body["resolved_count"], body["reachable_count"]) == (0, 0)
    assert body["blocks"][0]["count"] == 0, "the block count is the channel's too"


def test_there_is_no_channel_less_preview(world):
    assert _preview(world["group"].id, channel=None).status_code == 422
    assert _preview(world["group"].id, channel="pigeon").status_code == 422


def test_another_brands_group_is_not_found(world, foreign_api):
    with foreign_api([VIEW]) as headers:
        response = client.get(f"/api/audience-groups/{world['group'].id}/preview",
                              params={"channel": "email"}, headers=headers)
    assert response.status_code == 404


def test_the_jinja_page_shows_the_same_numbers(db, world):
    from sqlalchemy import text

    user = auth.create_user(db, email=f"prev-{uuid.uuid4().hex[:8]}@example.invalid",
                            role_key="viewer")
    token = auth.create_session(db, user)
    page_client = TestClient(app, raise_server_exceptions=False)
    page_client.cookies.set(auth.SESSION_COOKIE, token)
    try:
        page = page_client.get(f"/ui/audience-groups/{world['group'].id}")
        assert page.status_code == 200, page.text[:300]
        # The same figures as the JSON preview: 1 reachable, 1 unreachable, a
        # block matching 2.
        assert "1 recipient(s) net" in page.text
        assert "1 unreachable" in " ".join(page.text.split())
        assert '<td class="text-end">2</td>' in page.text
    finally:
        db.rollback()
        for table in ("auth_sessions", "role_assignments"):
            db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
        db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
        db.commit()
