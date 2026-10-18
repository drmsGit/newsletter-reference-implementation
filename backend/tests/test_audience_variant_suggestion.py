"""A suggested audience is made per variant: its topics and its language
(ADR-188 addendum 2026-10-18).

An English and a German variant of one campaign used to suggest the same
campaign-wide audience. Now each variant's suggestion reads that variant's
content only, and every suggested rule carries the variant's language inside
it (AND within a rule, ADR-188 point 1), so it narrows rather than adds.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.audience import service as audience
from app.audience.db_models import AudienceGroupDB, AudienceRuleBlockDB
from app.auth import service as auth
from app.auth.db_models import BrandDB
from app.brand_profiles.db_models import BrandProfileDB
from app.brand_profiles.service import create_profile
from app.campaigns.db_models import CampaignDB, VariantDB
from app.content.db_models import CategoryDB
from app.database import SessionLocal
from main import app

TAG = f"varsug-{uuid.uuid4().hex[:6]}"
URL = "/api/audience-groups/suggested"


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def world(db, default_brand):
    b = default_brand.id
    nature, wellness = CategoryDB(name=f"{TAG} Nature"), CategoryDB(name=f"{TAG} Wellness")
    db.add_all([nature, wellness]); db.flush()
    english = create_profile(db, b, name=f"{TAG} English", language="en")
    campaign = CampaignDB(brand_id=b, name=f"{TAG}-campaign")
    db.add(campaign); db.flush()
    german = VariantDB(campaign_id=campaign.id, channel="email", name="Deutsch", status="draft")
    in_english = VariantDB(campaign_id=campaign.id, channel="email", name="English", status="draft",
                           brand_profile_id=english.id)
    db.add_all([german, in_english]); db.commit()
    yield {"brand": b, "nature": nature.id, "wellness": wellness.id, "campaign": campaign,
           "german": german, "english": in_english}
    db.rollback()
    groups = [g for (g,) in db.query(AudienceGroupDB.id).filter(AudienceGroupDB.source_campaign_id == campaign.id)]
    db.execute(text("DELETE FROM audit_events WHERE subject_type = 'audience_group' AND subject_id = ANY(:ids)"),
               {"ids": groups or [0]})
    db.query(AudienceRuleBlockDB).filter(AudienceRuleBlockDB.group_id.in_(groups)).delete(synchronize_session=False)
    db.query(AudienceGroupDB).filter(AudienceGroupDB.id.in_(groups)).delete(synchronize_session=False)
    db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).delete(synchronize_session=False)
    db.query(CampaignDB).filter_by(id=campaign.id).delete(synchronize_session=False)
    db.query(BrandProfileDB).filter_by(id=english.id).delete(synchronize_session=False)
    db.query(CategoryDB).filter(CategoryDB.id.in_([nature.id, wellness.id])).delete(synchronize_session=False)
    db.commit()


@pytest.fixture
def topics(world, monkeypatch):
    """Each variant's content ranked: the English one is about Wellness only."""
    asked: list[list[int]] = []

    def scores(_db, variant_ids):
        asked.append(sorted(variant_ids))
        ranked = []
        if world["german"].id in variant_ids:
            ranked.append({"category_id": world["nature"], "category_name": "Nature", "content_score": 9})
        ranked.append({"category_id": world["wellness"], "category_name": "Wellness", "content_score": 5})
        return ranked

    monkeypatch.setattr(audience, "content_category_scores", scores)
    return asked


def _rules(db, group_id):
    return sorted((b.criteria for b in db.query(AudienceRuleBlockDB).filter_by(group_id=group_id)),
                  key=lambda c: c["categories"][0]["category_id"])


def test_a_variant_suggestion_reads_that_variant_and_carries_its_language(db, world, topics):
    group = audience.create_suggested_group_for_variant(db, world["english"].id, brand_id=world["brand"])
    assert topics == [[world["english"].id]], "the English variant's content only"
    assert group.source_variant_id == world["english"].id
    assert group.source_campaign_id == world["campaign"].id
    min_score = audience.DEFAULT_SUGGESTION_MIN_SCORE
    assert _rules(db, group.id) == [
        {"categories": [{"category_id": world["wellness"], "min_score": min_score}], "language": ["en"]}]


def test_a_variant_without_its_own_profile_takes_the_brands_default_language(db, world, topics):
    default_language = db.query(BrandProfileDB).filter_by(brand_id=world["brand"], is_default=True).one().language
    group = audience.create_suggested_group_for_variant(db, world["german"].id, brand_id=world["brand"])
    assert {tuple(rule["language"]) for rule in _rules(db, group.id)} == {(default_language,)}
    assert len(_rules(db, group.id)) == 2


def test_recalculating_follows_the_variant_and_keeps_its_language(db, world, topics):
    group = audience.create_suggested_group_for_variant(db, world["english"].id, brand_id=world["brand"])
    db.query(AudienceRuleBlockDB).filter_by(group_id=group.id).delete(); db.commit()
    audience.recalculate_suggested_blocks(db, group.id, brand_id=world["brand"])
    db.expire_all()
    assert topics[-1] == [world["english"].id]
    assert [rule["language"] for rule in _rules(db, group.id)] == [["en"]]


def test_a_campaign_suggestion_stays_campaign_wide_without_a_language(db, world, topics):
    group = audience.create_suggested_group_for_campaign(db, world["campaign"].id, world["campaign"].name,
                                                         brand_id=world["brand"])
    assert topics[-1] == sorted([world["german"].id, world["english"].id])
    assert group.source_variant_id is None
    assert all("language" not in rule for rule in _rules(db, group.id))


@pytest.fixture
def person(db, default_brand):
    user = auth.create_user(db, email=f"{TAG}-{uuid.uuid4().hex[:6]}@example.invalid",
                            role_key="admin", brand_id=default_brand.id)
    token = auth.create_session(db, user)
    client = TestClient(app, raise_server_exceptions=False)
    client.cookies.set(auth.SESSION_COOKIE, token)
    yield client, {"X-CSRF-Token": auth.csrf_token_for(token)}
    db.rollback()
    db.execute(text("DELETE FROM audit_events WHERE actor_id = :u AND actor_type = 'user'"), {"u": user.id})
    for table in ("login_codes", "auth_sessions", "role_assignments"):
        db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
    db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
    db.commit()


def test_the_route_takes_a_variant_and_names_the_group_after_it(world, topics, person):
    client, csrf = person
    made = client.post(URL, json={"variant_id": world["english"].id}, headers=csrf)
    assert made.status_code == 201, made.text
    assert made.json()["name"] == f"{TAG}-campaign · English — suggested audience"
    assert made.json()["source_variant_id"] == world["english"].id


@pytest.mark.parametrize("body", [{}, {"campaign_id": 1, "variant_id": 1}])
def test_the_route_wants_exactly_one_source(world, person, body):
    client, csrf = person
    assert client.post(URL, json=body, headers=csrf).status_code == 422


def test_another_brands_variant_answers_as_absent(db, world, topics, person):
    other = BrandDB(key=f"{TAG}-other", name=f"{TAG} Other")
    db.add(other); db.flush()
    campaign = CampaignDB(brand_id=other.id, name=f"{TAG}-foreign")
    db.add(campaign); db.flush()
    variant = VariantDB(campaign_id=campaign.id, channel="email", name="X", status="draft")
    db.add(variant); db.commit()
    try:
        client, csrf = person
        assert client.post(URL, json={"variant_id": variant.id}, headers=csrf).status_code == 404
    finally:
        db.query(VariantDB).filter_by(id=variant.id).delete()
        db.query(CampaignDB).filter_by(id=campaign.id).delete()
        db.query(BrandDB).filter_by(id=other.id).delete()
        db.commit()
