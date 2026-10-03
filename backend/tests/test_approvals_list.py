"""The approval inbox narrows and pages (task-209).

Manager Workflow interview Q1.3: one flat list, newest first, with filters by
action type and by requester — ADR-166 point 3 makes the requester a durable
actor, so "what did Acme Agency send" is a question the data can answer.

**The status rule moved into SQL** so paging pages the right rows; until then
`list_for_brand` loaded everything and filtered in Python. Expiry is read from
`expires_at` (ADR-142 §4), so `test_the_sql_status_agrees_with_effective_status`
holds the two implementations of "expired" to the same answers — the drift the
`is_expired` docstring warns about.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.approvals import service as approvals
from app.approvals.db_models import PendingActionDB
from app.auth import service as auth
from app.auth.permissions import VIEW
from app.database import SessionLocal
from main import app
from tests.machine import machine

client = TestClient(app, raise_server_exceptions=False)
NOW = datetime.now(timezone.utc)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def rows(db):
    """Six requests, oldest first, across two actions, two requesters and every
    status shape — including a `pending` row whose deadline has passed and one
    that expires exactly now (the boundary)."""
    brand = auth.ensure_default_brand(db)
    spec = [
        # (action_key, requester type, requester id, stored status, expires in)
        ("send.fire", "integration", 5, "pending", timedelta(hours=1)),
        ("content.ready", "user", 1, "pending", timedelta(hours=1)),
        ("send.fire", "user", 1, "pending", -timedelta(hours=1)),   # expired by timestamp
        ("content.ready", "integration", 5, "approved", timedelta(hours=1)),
        ("send.fire", "integration", 6, "failed", timedelta(hours=1)),
        ("content.ready", "user", 2, "pending", timedelta(0)),       # expires right now
    ]
    made = []
    for index, (key, by_type, by_id, status, ttl) in enumerate(spec):
        row = PendingActionDB(
            action_key=f"listtest.{key}", payload={}, summary=f"row {index}",
            requested_by_type=by_type, requested_by_id=by_id,
            subject_type="listtest", subject_id=10_000 + index, brand_id=brand.id,
            status=status, expires_at=NOW + ttl,
            created_at=NOW - timedelta(minutes=60 - index),
            decided_at=None if status == "pending" else NOW,
        )
        db.add(row)
        made.append(row)
    db.commit()
    yield made
    db.rollback()
    db.query(PendingActionDB).filter(PendingActionDB.id.in_([r.id for r in made])).delete(
        synchronize_session=False)
    db.commit()


def _ours(found, rows):
    ids = {r.id for r in rows}
    return [r.id for r in found if r.id in ids]


def test_the_sql_status_agrees_with_effective_status(db, rows):
    for status in ("pending", "decided", "all"):
        listed = set(_ours(approvals.list_for_brand(db, rows[0].brand_id, status, at=NOW), rows))
        expected = {
            r.id for r in rows
            if status == "all"
            or (status == "pending") == (approvals.effective_status(r, NOW) == "pending")
        }
        assert listed == expected, status


def test_filtered_by_action_type(db, rows):
    found = approvals.list_for_brand(db, rows[0].brand_id, "all",
                                     action_key="listtest.send.fire")
    assert _ours(found, rows) == [rows[4].id, rows[2].id, rows[0].id]


def test_filtered_by_requester(db, rows):
    found = approvals.list_for_brand(db, rows[0].brand_id, "all",
                                     requested_by_type="integration", requested_by_id=5)
    assert _ours(found, rows) == [rows[3].id, rows[0].id]
    by_type = approvals.list_for_brand(db, rows[0].brand_id, "all", requested_by_type="user")
    assert _ours(by_type, rows) == [rows[5].id, rows[2].id, rows[1].id]


def test_pages_are_newest_first_and_do_not_overlap(db, rows):
    key = dict(action_key=None, requested_by_type=None)
    first = approvals.list_for_brand(db, rows[0].brand_id, "all", limit=2, offset=0, **key)
    second = approvals.list_for_brand(db, rows[0].brand_id, "all", limit=2, offset=2, **key)
    assert len(first) == 2 and len(second) == 2
    assert not {r.id for r in first} & {r.id for r in second}
    stamps = [r.created_at for r in first + second]
    assert stamps == sorted(stamps, reverse=True)


def test_over_json_the_filters_and_paging_reach_the_query(db, rows):
    with machine([VIEW]) as headers:
        response = client.get("/approvals/", headers=headers, params={
            "status": "all", "action_key": "listtest.content.ready",
            "requested_by_type": "user", "limit": 1, "offset": 0,
        })
    assert response.status_code == 200, response.text
    body = response.json()
    assert [r["id"] for r in body["items"]] == [rows[5].id], "newest matching row only"
    # ADR-185: the total counts the whole filtered set, not the page.
    assert body["total"] >= 1 and (body["limit"], body["offset"]) == (1, 0)
    with machine([VIEW]) as headers:
        refused = client.get("/approvals/", headers=headers, params={"limit": 500})
    assert refused.status_code == 422, "the page size has a ceiling"


class TestFilterOptions:
    """GET /approvals/filter-options (2026-10-03): what the inbox can be narrowed
    by, drawn only from this brand's own requests — Q1.3's "what did Acme Agency
    send" needs the requester by NAME, and the integrations list is
    `integrations.manage` only. Decided with the user: names are shown to anyone
    who may view the inbox."""

    def test_it_offers_this_brands_actions_and_requesters_by_name(self, db, rows):
        from app.auth.db_models import IntegrationDB, UserDB

        person = UserDB(email="filters-person@example.invalid", display_name="Sam Planner",
                        is_active=True)
        integration = IntegrationDB(name="Acme Agency")
        db.add_all([person, integration])
        db.commit()
        rows[0].requested_by_type, rows[0].requested_by_id = "integration", integration.id
        rows[1].requested_by_type, rows[1].requested_by_id = "user", person.id
        db.commit()
        try:
            with machine([VIEW]) as headers:
                response = client.get("/approvals/filter-options", headers=headers)
            assert response.status_code == 200, response.text
            body = response.json()
            actions = {a["key"]: a["label"] for a in body["actions"]}
            assert {"listtest.send.fire", "listtest.content.ready"} <= set(actions)
            # An action no module describes any more still has a label: its key.
            assert actions["listtest.send.fire"] == "listtest.send.fire"
            named = {(r["type"], r["id"]): r["name"] for r in body["requesters"]}
            assert named[("integration", integration.id)] == "Acme Agency"
            assert named[("user", person.id)] == "Sam Planner"
            # A requester that no longer exists is still offered, named honestly.
            assert named[("integration", 6)] == "integration #6"
        finally:
            db.rollback()
            db.query(UserDB).filter(UserDB.id == person.id).delete()
            db.query(IntegrationDB).filter(IntegrationDB.id == integration.id).delete()
            db.commit()

    def test_another_brands_requests_are_not_offered(self, db, rows):
        from app.auth.db_models import BrandDB

        other = BrandDB(key="filters-other", name="Filters other")
        db.add(other)
        db.commit()
        foreign = PendingActionDB(
            action_key="listtest.foreign.only", payload={}, summary="theirs",
            requested_by_type="integration", requested_by_id=99, subject_type="listtest",
            subject_id=20_000, brand_id=other.id, status="pending",
            expires_at=NOW + timedelta(hours=1),
        )
        db.add(foreign)
        db.commit()
        try:
            with machine([VIEW]) as headers:
                body = client.get("/approvals/filter-options", headers=headers).json()
            assert "listtest.foreign.only" not in {a["key"] for a in body["actions"]}
            assert ("integration", 99) not in {(r["type"], r["id"]) for r in body["requesters"]}
        finally:
            db.rollback()
            db.query(PendingActionDB).filter(PendingActionDB.id == foreign.id).delete()
            db.query(BrandDB).filter(BrandDB.id == other.id).delete()
            db.commit()


class TestDecisionHistory:
    """The history screen (Manager Workflow Q1.6: log and queue stay separate).

    Decided requests are listed by when they ENDED — decided, or expired — newest
    first, not by when they were asked for; and each row names who asked and who
    decided, so the history reads without a second lookup.
    """

    def test_decided_requests_come_newest_ending_first(self, db, rows):
        # rows[2] lapsed by timestamp an hour ago and has no decided_at;
        # rows[3] and rows[4] were decided "now".
        # rows[3] was ASKED before rows[4] but DECIDED after it, so creation
        # order and ending order disagree — only the ending order passes.
        rows[3].decided_at = NOW - timedelta(minutes=1)
        rows[4].decided_at = NOW - timedelta(minutes=5)
        db.commit()
        found = approvals.list_for_brand(db, rows[0].brand_id, "decided", at=NOW)
        # Ended: rows[5] expired exactly at NOW, rows[3] decided 1 min before,
        # rows[4] 5 min before, rows[2] expired an hour before.
        assert _ours(found, rows) == [rows[5].id, rows[3].id, rows[4].id, rows[2].id]

    def test_rows_name_who_asked_and_who_decided(self, db, rows):
        from app.auth.db_models import UserDB

        decider = UserDB(email="history-decider@example.invalid", display_name="Robin Approver",
                         is_active=True)
        db.add(decider)
        db.commit()
        rows[3].decided_by_type, rows[3].decided_by_id = "user", decider.id
        db.commit()
        try:
            with machine([VIEW]) as headers:
                body = client.get("/approvals/", headers=headers,
                                  params={"status": "decided", "action_key": "listtest.content.ready",
                                          "limit": 200}).json()["items"]
            mine = next(r for r in body if r["id"] == rows[3].id)
            assert mine["decided_by_name"] == "Robin Approver"
            assert mine["requested_by_name"] == "integration #5"
            lapsed = next(r for r in body if r["id"] == rows[5].id)
            assert lapsed["decided_by_name"] is None, "an expired request was decided by nobody"
        finally:
            db.rollback()
            db.query(UserDB).filter(UserDB.id == decider.id).delete()
            db.commit()
