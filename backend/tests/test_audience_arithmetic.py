"""How an audience's number was arrived at (task-213).

Manager Workflow interview Q4.3: a manager trusts an audience by its
arithmetic — matched by the rules, not agreed to the channel, added by hand,
removed by exclusion segments, hand-added without agreement — and the total
that will receive. Always per channel (Q4.4; ADR-176 point 5). `resolve_audience`
computed every term and returned only the final list.

The user, 2026-10-06: people who match the rules but have not agreed to the
channel are **counted, never listed**, and only among people this brand has a
consent record with — a recipient is not a brand's, so "everyone on the
platform" would count another brand's contacts.

Fixture (one language L for the include block, one M for the exclude block):
  ruled        L, agreed email                     -> in
  ruled_pinned L, agreed email, also pinned        -> in (counted once, by the rules)
  pinned       other language, agreed, pinned     -> in (added by hand)
  pinned_out   M, agreed, pinned                   -> removed by exclusion (hand-added)
  ruled_out    L and M, agreed                     -> removed by exclusion
  not_agreed   L, opted out of email, brand-known  -> not agreed (count only)
  pinned_no    other language, pinned, no consent  -> hand-added without agreement
  stranger     L, consent with another brand only  -> not counted at all
  excluded_only M, agreed, neither ruled nor pinned -> matched by an exclusion, removed from nothing
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
    L, M = f"l-{uuid.uuid4().hex[:6]}", f"m-{uuid.uuid4().hex[:6]}"
    plan = {
        "ruled": (L, "opted_in", False), "ruled_pinned": (L, "opted_in", True),
        "pinned": ("xx", "opted_in", True), "pinned_out": (M, "opted_in", True),
        "ruled_out": (L, "opted_in", False), "not_agreed": (L, "opted_out", False),
        "pinned_no": ("xx", None, True), "stranger": (L, "foreign", False),
        "excluded_only": (M, "opted_in", False),
    }
    people = {}
    group = AudienceGroupDB(brand_id=default_brand.id, name=f"arith-{uuid.uuid4().hex[:8]}")
    db.add(group); db.flush()
    for name, (language, consent, pinned) in plan.items():
        r = RecipientDB(external_id=f"arith-{uuid.uuid4()}", status="active", language=language)
        db.add(r); db.flush()
        if consent == "foreign":
            record_consent(db, r.id, "opted_in", foreign_brand.id, channel="email", source="test",
                           note="arith", commit=False, purpose="marketing")
        elif consent:
            record_consent(db, r.id, consent, default_brand.id, channel="email", source="test",
                           note="arith", commit=False, purpose="marketing")
        if pinned:
            db.add(AudienceGroupMemberDB(group_id=group.id, recipient_id=r.id))
        people[name] = r
    db.commit()
    # ruled_out matches the exclusion by a second criterion: status.
    db.query(RecipientDB).filter_by(id=people["ruled_out"].id).update({"status": "paused"}); db.commit()
    audience.add_block(db, group.id, kind="include", criteria={"language": L}, label="L",
                       brand_id=default_brand.id)
    audience.add_block(db, group.id, kind="exclude", criteria={"language": M}, label="M",
                       brand_id=default_brand.id)
    audience.add_block(db, group.id, kind="exclude", criteria={"status": "paused"}, label="paused",
                       brand_id=default_brand.id)
    yield {"group": group, "people": people, "brand": default_brand.id}
    db.rollback()
    ids = [r.id for r in people.values()]
    db.query(AudienceRuleBlockDB).filter(AudienceRuleBlockDB.group_id == group.id).delete()
    db.query(AudienceGroupMemberDB).filter(AudienceGroupMemberDB.group_id == group.id).delete()
    db.query(AudienceGroupDB).filter(AudienceGroupDB.id == group.id).delete()
    db.query(ConsentEventDB).filter(ConsentEventDB.recipient_id.in_(ids)).delete(synchronize_session=False)
    db.query(RecipientDB).filter(RecipientDB.id.in_(ids)).delete(synchronize_session=False)
    db.commit()


EXPECTED = {
    "matched_rules": 4,         # ruled, ruled_pinned, ruled_out, not_agreed (stranger is not this brand's)
    "not_agreed": 1,            # not_agreed
    "added_by_hand": 3,         # pinned, pinned_out, pinned_no (ruled_pinned came by the rules)
    "removed_by_exclusion": 2,  # pinned_out, ruled_out
    "removed_hand_added": 1,    # pinned_out
    "dropped_by_consent": 1,    # pinned_no
    "total": 3,                 # ruled, ruled_pinned, pinned
}


def test_the_arithmetic_names_every_term_and_adds_up(db, world):
    numbers = audience.audience_arithmetic(db, world["group"].id, channel="email")
    assert numbers == EXPECTED
    assert (numbers["matched_rules"] - numbers["not_agreed"] + numbers["added_by_hand"]
            - numbers["removed_by_exclusion"] - numbers["dropped_by_consent"]) == numbers["total"]


def test_its_total_is_the_audience_the_send_resolves(db, world):
    resolved = audience.resolve_audience(db, world["group"].id, channel="email")
    assert {r.id for r in resolved} == {world["people"][n].id for n in ("ruled", "ruled_pinned", "pinned")}
    assert len(resolved) == audience.audience_arithmetic(db, world["group"].id, channel="email")["total"]


def test_it_is_per_channel(db, world):
    """Nobody here agreed to push: the rules match nobody who agreed, the
    brand-known L people have not agreed to push, every hand-add drops."""
    numbers = audience.audience_arithmetic(db, world["group"].id, channel="push")
    assert numbers["total"] == 0
    assert numbers["not_agreed"] == numbers["matched_rules"] == 4
    assert numbers["added_by_hand"] == 4
    # Since 2026-10-11 (ADR-176 point 1, Codex doc-16) an exclude rule removes
    # a hand-added person whether or not they agreed, so the one the exclusion
    # catches counts there, and three drop for consent. The terms still add up.
    assert (numbers["removed_by_exclusion"], numbers["dropped_by_consent"]) == (1, 3)


def test_the_preview_carries_it(world):
    with machine([VIEW]) as headers:
        body = client.get(f"/api/audience-groups/{world['group'].id}/preview",
                          params={"channel": "email"}, headers=headers).json()
    assert body["arithmetic"] == EXPECTED
    assert body["arithmetic"]["total"] == body["resolved_count"]
