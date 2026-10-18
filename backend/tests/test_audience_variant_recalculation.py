"""A surviving suggested rule follows its variant's current language (ADR-188)."""
from uuid import uuid4

from app.audience import service as audience
from app.audience.db_models import AudienceGroupDB, AudienceRuleBlockDB
from app.brand_profiles.db_models import BrandProfileDB
from app.brand_profiles.service import create_profile, update_profile
from app.campaigns.db_models import CampaignDB, VariantDB
from app.content.db_models import CategoryDB


def test_recalculate_refreshes_language_on_a_surviving_topic(db, default_brand, monkeypatch):
    tag = uuid4().hex
    profile = create_profile(db, default_brand.id, name=f"Recalculate {tag}", language="en")
    campaign = CampaignDB(brand_id=default_brand.id, name=f"Recalculate {tag}")
    category = CategoryDB(name=f"Recalculate {tag}")
    db.add_all([campaign, category])
    db.flush()
    variant = VariantDB(campaign_id=campaign.id, channel="email", name="Newsletter",
                        status="draft", brand_profile_id=profile.id)
    db.add(variant)
    db.commit()
    campaign_id, category_id, profile_id = campaign.id, category.id, profile.id
    monkeypatch.setattr(audience, "content_category_scores", lambda _db, _ids: [
        {"category_id": category_id, "category_name": category.name, "content_score": 9},
    ])
    try:
        group = audience.create_suggested_group_for_variant(db, variant.id, brand_id=default_brand.id)
        original = db.query(AudienceRuleBlockDB).filter_by(group_id=group.id).one()
        assert original.criteria["language"] == ["en"]
        original_categories = original.criteria["categories"]

        update_profile(db, profile_id, default_brand.id, name=profile.name, language="de",
                       field_values=profile.field_values)
        audience.recalculate_suggested_blocks(db, group.id, brand_id=default_brand.id)
        db.expire_all()
        rules = db.query(AudienceRuleBlockDB).filter_by(group_id=group.id).all()
        assert [rule.criteria for rule in rules] == [
            {"categories": original_categories, "language": ["de"]},
        ]
    finally:
        db.rollback()
        groups = [row.id for row in db.query(AudienceGroupDB).filter_by(source_campaign_id=campaign_id)]
        db.query(AudienceRuleBlockDB).filter(AudienceRuleBlockDB.group_id.in_(groups)).delete(synchronize_session=False)
        db.query(AudienceGroupDB).filter(AudienceGroupDB.id.in_(groups)).delete(synchronize_session=False)
        db.query(VariantDB).filter_by(campaign_id=campaign_id).delete(synchronize_session=False)
        db.query(CampaignDB).filter_by(id=campaign_id).delete(synchronize_session=False)
        db.query(BrandProfileDB).filter_by(id=profile_id).delete(synchronize_session=False)
        db.query(CategoryDB).filter_by(id=category_id).delete(synchronize_session=False)
        db.commit()
