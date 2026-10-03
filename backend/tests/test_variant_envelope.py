"""A variant's subject and preheader arrive, and blank means empty (task-250).

`POST /campaigns/{id}/variants` accepted `subject` and `preheader` and never
passed them on, so they were lost without an error. And only the Jinja forms
trimmed whitespace: over JSON, `" "` was stored as a subject. Trimming now
happens in `set_envelope_fields`, the one place every path writes the envelope
through (ADR-162 point 1).
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.permissions import CAMPAIGNS_MANAGE
from app.campaigns.db_models import CampaignDB, ModuleInstanceDB, VariantDB
from main import app
from tests.machine import machine

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def campaign(db, default_brand):
    campaign = CampaignDB(brand_id=default_brand.id, name=f"env-{uuid.uuid4().hex[:6]}")
    db.add(campaign); db.commit()
    yield campaign
    db.rollback()
    variant_ids = [v.id for v in db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id)]
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id.in_(variant_ids)).delete(
        synchronize_session=False)
    db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).delete()
    db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
    db.commit()


def _create(campaign, **fields):
    with machine([CAMPAIGNS_MANAGE]) as headers:
        response = client.post(f"/campaigns/{campaign.id}/variants",
                               json={"name": "B", "channel": "email", **fields}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _envelope(db, variant_id):
    db.expire_all()
    module = (db.query(ModuleInstanceDB)
              .filter(ModuleInstanceDB.variant_id == variant_id, ModuleInstanceDB.module_type == "header")
              .one_or_none())
    return None if module is None else module.module_data


def test_subject_and_preheader_given_at_creation_are_kept(db, campaign):
    created = _create(campaign, subject="Spring is here", preheader="Three new routes")
    assert (created["subject"], created["preheader"]) == ("Spring is here", "Three new routes")
    assert _envelope(db, created["id"]) == {"subject": "Spring is here", "preheader": "Three new routes"}


def test_whitespace_is_trimmed_and_blank_is_empty_on_create(db, campaign):
    created = _create(campaign, subject="  Spring  ", preheader="   ")
    assert _envelope(db, created["id"]) == {"subject": "Spring"}


def test_whitespace_only_on_update_clears_the_envelope(db, campaign):
    created = _create(campaign, subject="Spring", preheader="Peek")
    with machine([CAMPAIGNS_MANAGE]) as headers:
        response = client.put(f"/campaigns/variants/{created['id']}",
                              json={"name": "B", "subject": " ", "preheader": "\t"}, headers=headers)
    assert response.status_code == 200, response.text
    assert _envelope(db, created["id"]) is None


def test_a_variant_created_without_them_has_no_envelope(db, campaign):
    assert _envelope(db, _create(campaign)["id"]) is None
