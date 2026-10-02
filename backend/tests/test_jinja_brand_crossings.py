"""Four Jinja routes that reached across the brand boundary (task-241, ADR-172).

Each test is a person working in the default brand, reaching for something in
a foreign one. Every fallback in this codebase returns the default brand, so
the target is always the foreign brand (conftest's rule).
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.ai.db_models import AIRunDB
from app.audience.db_models import AudienceGroupDB, AudienceRuleBlockDB
from app.auth import service as auth
from app.campaigns.db_models import CampaignDB, VariantDB
from app.content.db_models import CategoryDB, ContentCategoryAssignmentDB, ContentRecordDB
from main import app


@pytest.fixture
def person(db, default_brand):
    """An Admin of the default brand only, signed in to the Jinja UI."""
    user = auth.create_user(db, email=f"cross-{uuid.uuid4().hex[:8]}@example.invalid",
                            role_key="admin", brand_id=default_brand.id)
    token = auth.create_session(db, user)
    client = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
    client.cookies.set(auth.SESSION_COOKIE, token)
    yield client, auth.csrf_token_for(token)
    db.rollback()
    for table in ("login_codes", "auth_sessions", "role_assignments"):
        db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
    db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
    db.commit()


def _campaign(db, brand, name):
    campaign = CampaignDB(brand_id=brand.id, name=name)
    db.add(campaign); db.flush()
    variant = VariantDB(campaign_id=campaign.id, channel="email", name="v", status="draft")
    db.add(variant); db.commit()
    return campaign, variant


def test_s1_a_campaign_page_does_not_show_another_brands_ai_run(db, person, default_brand, foreign_brand):
    client, _csrf = person
    own, _ = _campaign(db, default_brand, f"own-{uuid.uuid4().hex[:6]}")
    _, foreign_variant = _campaign(db, foreign_brand, f"foreign-{uuid.uuid4().hex[:6]}")
    secret = f"FOREIGN-{uuid.uuid4().hex[:8]}"
    run = AIRunDB(task_key="subject_preheader", provider="mock", status="ok",
                  target_type="variant", target_id=foreign_variant.id,
                  output_text=f"SUBJECT: {secret}\nPREHEADER: x", input_tokens=1, output_tokens=1)
    db.add(run); db.commit()
    try:
        page = client.get(f"/ui/campaigns/{own.id}?ai_run={run.id}")
        assert page.status_code == 200, page.text[:300]
        assert secret not in page.text, "another brand's AI output rendered on this campaign"
    finally:
        db.query(AIRunDB).filter(AIRunDB.id == run.id).delete()
        db.commit()


def test_s2_suggest_audience_cannot_build_a_group_in_another_brand(db, person, foreign_brand):
    client, csrf = person
    foreign, _ = _campaign(db, foreign_brand, f"foreign-{uuid.uuid4().hex[:6]}")
    before = db.query(AudienceGroupDB).filter(AudienceGroupDB.brand_id == foreign_brand.id).count()
    client.post(f"/ui/campaigns/{foreign.id}/suggest-audience", data={"csrf_token": csrf})
    db.expire_all()
    after = db.query(AudienceGroupDB).filter(AudienceGroupDB.brand_id == foreign_brand.id).count()
    if after != before:  # a regression: remove it so the brand teardown can run
        groups = [g.id for g in db.query(AudienceGroupDB).filter(
            AudienceGroupDB.source_campaign_id == foreign.id)]
        db.query(AudienceRuleBlockDB).filter(AudienceRuleBlockDB.group_id.in_(groups)).delete(
            synchronize_session=False)
        db.query(AudienceGroupDB).filter(AudienceGroupDB.id.in_(groups)).delete(
            synchronize_session=False)
        db.commit()
    assert after == before, "a group was created in a brand this person holds nothing on"


def test_s3_a_category_assignment_in_another_brand_cannot_be_deleted(db, person, foreign_brand):
    client, csrf = person
    record = ContentRecordDB(title="foreign", content={}, status="active", brand_id=foreign_brand.id)
    category = CategoryDB(name=f"cross-{uuid.uuid4().hex[:6]}", type="main")
    db.add_all([record, category]); db.flush()
    assignment = ContentCategoryAssignmentDB(content_id=record.id, category_id=category.id, score=5)
    db.add(assignment); db.commit()
    assignment_id, category_id = assignment.id, category.id
    try:
        client.post(f"/ui/content/{record.id}/categories/{assignment_id}/delete",
                    data={"csrf_token": csrf})
        db.expire_all()
        assert db.get(ContentCategoryAssignmentDB, assignment_id) is not None, (
            "another brand's category assignment was deleted"
        )
    finally:
        db.rollback()
        db.query(ContentCategoryAssignmentDB).filter(
            ContentCategoryAssignmentDB.category_id == category_id).delete()
        db.query(CategoryDB).filter(CategoryDB.id == category_id).delete()
        db.commit()


def test_s4_the_send_test_picker_lists_only_this_brands_variants(db, person, foreign_brand):
    client, _csrf = person
    marker = f"foreign-campaign-{uuid.uuid4().hex[:6]}"
    _campaign(db, foreign_brand, marker)
    page = client.get("/ui/send-test")
    assert page.status_code == 200, page.text[:300]
    assert marker not in page.text, "the send-test picker listed another brand's campaign"


# --- the same rules, at the service, where a JSON route will call them --------

def test_an_ai_run_is_found_only_through_its_own_campaign(db, default_brand, foreign_brand):
    from app.ai.service import run_for_campaign

    own, own_variant = _campaign(db, default_brand, f"own-{uuid.uuid4().hex[:6]}")
    other, other_variant = _campaign(db, foreign_brand, f"foreign-{uuid.uuid4().hex[:6]}")
    run = AIRunDB(task_key="subject_preheader", provider="mock", status="ok",
                  target_type="variant", target_id=other_variant.id, output_text="")
    db.add(run); db.commit()
    try:
        assert run_for_campaign(db, run.id, own.id) is None
        assert run_for_campaign(db, run.id, other.id).id == run.id
    finally:
        db.query(AIRunDB).filter(AIRunDB.id == run.id).delete()
        db.commit()


def test_a_suggested_group_is_refused_for_another_brands_campaign(db, default_brand, foreign_brand):
    from app.audience.service import create_suggested_group_for_campaign

    foreign, _ = _campaign(db, foreign_brand, f"foreign-{uuid.uuid4().hex[:6]}")
    with pytest.raises(ValueError, match="not found"):
        create_suggested_group_for_campaign(db, foreign.id, foreign.name, brand_id=default_brand.id)


def test_an_assignment_is_deleted_only_through_its_own_record_in_the_brand(db, default_brand, foreign_brand):
    from app.content.service import delete_category_assignment

    record = ContentRecordDB(title="foreign", content={}, status="active", brand_id=foreign_brand.id)
    category = CategoryDB(name=f"cross-{uuid.uuid4().hex[:6]}", type="main")
    db.add_all([record, category]); db.flush()
    assignment = ContentCategoryAssignmentDB(content_id=record.id, category_id=category.id, score=5)
    db.add(assignment); db.commit()
    ids = (assignment.id, category.id, record.id)
    try:
        assert delete_category_assignment(db, record.id, ids[0], brand_id=default_brand.id) is False
        assert delete_category_assignment(db, record.id + 1, ids[0], brand_id=foreign_brand.id) is False
        assert delete_category_assignment(db, record.id, ids[0], brand_id=foreign_brand.id) is True
    finally:
        db.rollback()
        db.query(ContentCategoryAssignmentDB).filter(
            ContentCategoryAssignmentDB.category_id == ids[1]).delete()
        db.query(CategoryDB).filter(CategoryDB.id == ids[1]).delete()
        db.commit()
