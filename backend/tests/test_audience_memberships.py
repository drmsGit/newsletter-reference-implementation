"""Which audience groups one person is in, and why (task-214).

Manager Workflow interview Q4.5: the recipient screen answers "why did Anna
get this". Rule-based membership is never stored — only hand-adds are rows —
so the user decided (2026-10-06) to work it out on request, for that one
person, per channel, as of now, with the reason; nothing is stored, so
audience membership stays derived (ADR-093). "In" must be exactly "in the
audience a send would resolve".

Fixture: language L (group A includes L, excludes status "paused"; group B
includes language L too, nothing excluded; group C, another rule, matches
nobody here) and a foreign brand's group that also includes L.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.audience import service as audience
from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB, AudienceRuleBlockDB
from app.auth.permissions import VIEW
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
def world(db, default_brand, foreign_brand):
    L = f"l-{uuid.uuid4().hex[:6]}"
    people = {}
    for name, consent, status in (("anna", "opted_in", "active"), ("paused", "opted_in", "paused"),
                                  ("refused", "opted_out", "active"), ("pinned", "opted_in", "active")):
        r = RecipientDB(external_id=f"mem-{uuid.uuid4()}", status=status,
                        language=L if name != "pinned" else "xx")
        db.add(r); db.flush()
        record_consent(db, r.id, consent, default_brand.id, channel="email", source="test",
                       note="mem", commit=False, purpose="marketing")
        people[name] = r
    groups = {}
    for key, brand in (("A", default_brand.id), ("B", default_brand.id), ("C", default_brand.id),
                       ("F", foreign_brand.id)):
        g = AudienceGroupDB(brand_id=brand, name=f"mem-{key}-{uuid.uuid4().hex[:6]}")
        db.add(g); db.flush()
        groups[key] = g
    db.add(AudienceGroupMemberDB(group_id=groups["A"].id, recipient_id=people["pinned"].id))
    db.commit()
    b = default_brand.id
    audience.add_block(db, groups["A"].id, kind="include", criteria={"language": L}, label="Language L", brand_id=b)
    audience.add_block(db, groups["A"].id, kind="exclude", criteria={"status": "paused"}, label="Paused", brand_id=b)
    audience.add_block(db, groups["B"].id, kind="include", criteria={"language": L}, label="Also L", brand_id=b)
    audience.add_block(db, groups["C"].id, kind="include", criteria={"language": "zz-none"}, label="Nobody", brand_id=b)
    audience.add_block(db, groups["F"].id, kind="include", criteria={"language": L}, label="Foreign L",
                       brand_id=foreign_brand.id)
    yield {"people": people, "groups": groups, "brand": b}
    db.rollback()
    ids = [g.id for g in groups.values()]
    db.query(AudienceRuleBlockDB).filter(AudienceRuleBlockDB.group_id.in_(ids)).delete(synchronize_session=False)
    db.query(AudienceGroupMemberDB).filter(AudienceGroupMemberDB.group_id.in_(ids)).delete(synchronize_session=False)
    db.query(AudienceGroupDB).filter(AudienceGroupDB.id.in_(ids)).delete(synchronize_session=False)
    pids = [r.id for r in people.values()]
    db.query(ConsentEventDB).filter(ConsentEventDB.recipient_id.in_(pids)).delete(synchronize_session=False)
    db.query(RecipientDB).filter(RecipientDB.id.in_(pids)).delete(synchronize_session=False)
    db.commit()


def _of(rows, group):
    return next((r for r in rows if r["group_id"] == group.id), None)


def test_a_rule_match_says_which_rule(db, world):
    rows = audience.audience_memberships(db, world["people"]["anna"].id, brand_id=world["brand"], channel="email")
    a = _of(rows, world["groups"]["A"])
    assert a["member"] is True
    assert a["reasons"] == [{"kind": "rule", "label": "Language L"}]
    assert _of(rows, world["groups"]["B"])["reasons"] == [{"kind": "rule", "label": "Also L"}]


def test_a_hand_add_says_so(db, world):
    rows = audience.audience_memberships(db, world["people"]["pinned"].id, brand_id=world["brand"], channel="email")
    assert [(r["group_id"], r["member"], r["reasons"]) for r in rows] == [
        (world["groups"]["A"].id, True, [{"kind": "pinned", "label": None}])]


def test_an_exclusion_says_which_and_leaves_them_out(db, world):
    rows = audience.audience_memberships(db, world["people"]["paused"].id, brand_id=world["brand"], channel="email")
    a = _of(rows, world["groups"]["A"])
    assert a["member"] is False
    assert a["reasons"] == [{"kind": "rule", "label": "Language L"}, {"kind": "excluded", "label": "Paused"}]


def test_not_having_agreed_leaves_them_out_and_says_so(db, world):
    rows = audience.audience_memberships(db, world["people"]["refused"].id, brand_id=world["brand"], channel="email")
    a = _of(rows, world["groups"]["A"])
    assert a["member"] is False
    assert a["reasons"] == [{"kind": "rule", "label": "Language L"}, {"kind": "not_agreed", "label": "email"}]


def test_groups_that_do_not_touch_them_and_other_brands_are_left_out(db, world):
    rows = audience.audience_memberships(db, world["people"]["anna"].id, brand_id=world["brand"], channel="email")
    assert {r["group_id"] for r in rows} == {world["groups"]["A"].id, world["groups"]["B"].id}


def test_it_is_per_channel(db, world):
    """Nobody here agreed to push: every touching group says not agreed."""
    rows = audience.audience_memberships(db, world["people"]["anna"].id, brand_id=world["brand"], channel="push")
    assert [r["member"] for r in rows] == [False, False]
    assert all(r["reasons"][-1] == {"kind": "not_agreed", "label": "push"} for r in rows)


@pytest.mark.parametrize("person", ["anna", "paused", "refused", "pinned"])
@pytest.mark.parametrize("channel", ["email", "push"])
def test_in_means_in_what_a_send_resolves(db, world, person, channel):
    rid = world["people"][person].id
    rows = audience.audience_memberships(db, rid, brand_id=world["brand"], channel=channel)
    for key in ("A", "B", "C"):
        group = world["groups"][key]
        resolved = rid in {r.id for r in audience.resolve_audience(db, group.id, channel)}
        row = _of(rows, group)
        assert (row is not None and row["member"]) == resolved, (person, key)


def test_the_route_answers_for_the_working_brand(world):
    rid = world["people"]["anna"].id
    with machine([VIEW]) as headers:
        body = client.get(f"/recipients/{rid}/audience-groups", params={"channel": "email"}, headers=headers)
        missing = client.get("/recipients/99999999/audience-groups", params={"channel": "email"}, headers=headers)
        no_channel = client.get(f"/recipients/{rid}/audience-groups", headers=headers)
    assert body.status_code == 200, body.text
    assert body.json()["total"] == 2
    assert [(g["group_name"], g["member"]) for g in body.json()["items"]] == sorted(
        [(world["groups"]["A"].name, True), (world["groups"]["B"].name, True)])
    assert missing.status_code == 404
    assert no_channel.status_code == 422, "there is no channel-less answer (ADR-176 point 5)"
