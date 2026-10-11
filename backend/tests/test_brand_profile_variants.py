"""A variant chooses its brand profile (task-350; ADR-194 points 1 and 4).

A new variant starts on its brand's default. A manager picks another of the
same brand's profiles; another brand's is refused. A copy keeps the profile
inside one brand and takes the target brand's default across brands. A
variant built without one (the seed, older code) reads as the default.
"""
import uuid
from contextlib import contextmanager

import pytest

from app.audit.db_models import AuditEventDB
from app.brand_profiles import service as profiles
from app.brand_profiles.db_models import BrandProfileDB
from app.campaigns import duplication
from app.campaigns.db_models import CampaignDB, DecisionSlotDB, ModuleInstanceDB, VariantDB
from app.campaigns.service import create_campaign
from app.database import SessionLocal
from tests.test_api_guard import signed_in


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def admin(db):
    with signed_in(db) as (cookied, _token, csrf):
        yield cookied, {"X-CSRF-Token": csrf}


@pytest.fixture
def campaigns(db):
    """Campaigns made by a test, removed with everything under them."""
    made: list[int] = []
    yield made
    db.rollback()
    for campaign_id in made:
        variant_ids = [v.id for v in db.query(VariantDB).filter(VariantDB.campaign_id == campaign_id)]
        if variant_ids:
            db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id.in_(variant_ids)).delete(
                synchronize_session=False)
            db.query(DecisionSlotDB).filter(DecisionSlotDB.variant_id.in_(variant_ids)).delete(
                synchronize_session=False)
            db.query(VariantDB).filter(VariantDB.id.in_(variant_ids)).delete(synchronize_session=False)
        db.query(CampaignDB).filter(CampaignDB.id == campaign_id).delete()
    db.commit()


@pytest.fixture
def profile(db, default_brand):
    """A second profile in the default brand."""
    made = []

    def make(name="Calm"):
        row = BrandProfileDB(brand_id=default_brand.id, name=f"{name} {uuid.uuid4().hex[:6]}",
                             field_values={"unsubscribe_text": "Unsubscribe"})
        db.add(row)
        db.commit()
        made.append(row.id)
        return row

    yield make
    db.rollback()
    db.query(VariantDB).filter(VariantDB.brand_profile_id.in_(made)).update(
        {"brand_profile_id": None}, synchronize_session=False)
    db.query(BrandProfileDB).filter(BrandProfileDB.id.in_(made)).delete(synchronize_session=False)
    db.commit()


def _new_campaign(db, campaigns, brand_id):
    made = create_campaign(db, name=f"Profile test {uuid.uuid4().hex[:6]}", brand_id=brand_id,
                           channel="email")
    campaigns.append(made.id)
    return made


def test_a_new_campaigns_variant_starts_on_the_default(db, campaigns, default_brand):
    made = _new_campaign(db, campaigns, default_brand.id)
    assert made.variants[0].brand_profile_id == profiles.default_profile(db, default_brand.id).id


def test_a_new_variant_starts_on_the_default_or_the_chosen_one(db, campaigns, default_brand, profile):
    calm = profile()
    campaign = _new_campaign(db, campaigns, default_brand.id)
    with admin(db) as (cookied, headers):
        plain = cookied.post(f"/campaigns/{campaign.id}/variants", json={"name": "B"}, headers=headers)
        chosen = cookied.post(f"/campaigns/{campaign.id}/variants",
                              json={"name": "C", "brand_profile_id": calm.id}, headers=headers)
    assert plain.status_code == 200, plain.text
    assert plain.json()["brand_profile_id"] == profiles.default_profile(db, default_brand.id).id
    assert chosen.json()["brand_profile_id"] == calm.id


def test_another_brands_profile_is_refused(db, campaigns, default_brand, foreign_brand):
    foreign = profiles.ensure_default_profile(db, foreign_brand.id)
    campaign = _new_campaign(db, campaigns, default_brand.id)
    variant_id = campaign.variants[0].id
    with admin(db) as (cookied, headers):
        created = cookied.post(f"/campaigns/{campaign.id}/variants",
                               json={"name": "X", "brand_profile_id": foreign.id}, headers=headers)
        updated = cookied.put(f"/campaigns/variants/{variant_id}",
                              json={"name": "A", "brand_profile_id": foreign.id}, headers=headers)
    assert created.status_code == 422, created.text
    assert updated.status_code == 422, updated.text
    db.expire_all()
    assert db.get(VariantDB, variant_id).brand_profile_id != foreign.id


def test_picking_a_profile_stores_it_clears_the_notice_and_is_audited(
        db, campaigns, default_brand, profile):
    calm = profile()
    campaign = _new_campaign(db, campaigns, default_brand.id)
    variant = db.get(VariantDB, campaign.variants[0].id)
    variant.brand_profile_notice = "Its profile was deleted."
    db.commit()
    with admin(db) as (cookied, headers):
        response = cookied.put(f"/campaigns/variants/{variant.id}",
                               json={"name": "A", "brand_profile_id": calm.id}, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["brand_profile_id"] == calm.id
    assert response.json()["brand_profile_notice"] is None
    entry = (db.query(AuditEventDB).filter(AuditEventDB.subject_type == "variant",
                                          AuditEventDB.subject_id == variant.id)
             .order_by(AuditEventDB.id.desc()).first())
    assert entry.detail["brand_profile_id"] == calm.id


def test_renaming_without_a_profile_leaves_it_and_its_notice(db, campaigns, default_brand, profile):
    calm = profile()
    campaign = _new_campaign(db, campaigns, default_brand.id)
    variant = db.get(VariantDB, campaign.variants[0].id)
    variant.brand_profile_id, variant.brand_profile_notice = calm.id, "Kept until a manager picks."
    db.commit()
    with admin(db) as (cookied, headers):
        body = cookied.put(f"/campaigns/variants/{variant.id}", json={"name": "Renamed"},
                           headers=headers).json()
    assert (body["brand_profile_id"], body["brand_profile_notice"]) == (
        calm.id, "Kept until a manager picks.")


def test_the_composition_names_the_profile_and_what_it_misses(db, campaigns, default_brand):
    campaign = _new_campaign(db, campaigns, default_brand.id)
    variant = db.get(VariantDB, campaign.variants[0].id)
    variant.brand_profile_id = None          # as the seed builds it
    db.commit()
    with admin(db) as (cookied, headers):
        composed = cookied.get(f"/campaigns/{campaign.id}/composition").json()
    shown = composed["variants"][0]["brand_profile"]
    default = profiles.default_profile(db, default_brand.id)
    assert (shown["id"], shown["name"], shown["is_default"]) == (default.id, default.name, True)
    assert shown["missing"] == profiles.missing(default) and shown["notice"] is None


def test_a_copy_inside_the_brand_keeps_the_profile(db, campaigns, default_brand, profile):
    calm = profile()
    campaign = _new_campaign(db, campaigns, default_brand.id)
    source = db.get(VariantDB, campaign.variants[0].id)
    source.brand_profile_id = calm.id
    db.commit()
    report = duplication.duplicate_variant(db, variant_id=source.id, brand_id=default_brand.id,
                                           principal=None, enforced=False)
    assert db.get(VariantDB, report.variant_id).brand_profile_id == calm.id


def test_a_copy_into_another_brand_takes_its_default(db, campaigns, default_brand, profile, temp_brand):
    calm = profile()
    target = temp_brand("profile-target")
    campaign = _new_campaign(db, campaigns, default_brand.id)
    source = db.get(VariantDB, campaign.variants[0].id)
    source.brand_profile_id = calm.id
    db.commit()
    report = duplication.duplicate_campaign(
        db, campaign_id=campaign.id, target_brand_id=target.id, name="Across",
        content_mode=duplication.COPY, principal=None, enforced=False)
    campaigns.append(report.campaign_id)
    [copied] = db.query(VariantDB).filter(VariantDB.campaign_id == report.campaign_id).all()
    assert copied.brand_profile_id == profiles.default_profile(db, target.id).id


def test_a_row_pointing_at_another_brands_profile_shows_the_default(
        db, campaigns, default_brand, foreign_brand):
    """No service writes this; a row edited by hand must still never show a
    look its brand does not own."""
    foreign = profiles.ensure_default_profile(db, foreign_brand.id)
    campaign = _new_campaign(db, campaigns, default_brand.id)
    variant = db.get(VariantDB, campaign.variants[0].id)
    variant.brand_profile_id = foreign.id
    db.commit()
    try:
        with admin(db) as (cookied, headers):
            shown = cookied.get(f"/campaigns/{campaign.id}/composition").json()["variants"][0]
        assert shown["brand_profile"]["id"] == profiles.default_profile(db, default_brand.id).id
    finally:
        variant.brand_profile_id = None
        db.commit()
