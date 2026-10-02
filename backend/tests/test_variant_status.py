"""A variant's status is `draft` or `ready`, nothing else (task-203).

Settled in the Variant Editor design interview, Q4.6: `approved` belongs to the
send, `sent` to send instances, `archived` to the data-lifecycle ADR. Constrained
in code the way `CONTENT_STATUSES` is; existing rows are not rewritten.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.permissions import CAMPAIGNS_MANAGE, VIEW
from app.auth.service import ensure_default_brand
from app.campaigns.db_models import CampaignDB, VariantDB
from app.campaigns.service import VARIANT_STATUSES, create_variant_for_campaign
from app.database import SessionLocal
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
def campaign(db):
    brand = ensure_default_brand(db)
    row = CampaignDB(brand_id=brand.id, name=f"vstatus-{uuid.uuid4().hex[:6]}")
    db.add(row); db.commit()
    yield row
    db.rollback()
    db.query(VariantDB).filter(VariantDB.campaign_id == row.id).delete()
    db.query(CampaignDB).filter(CampaignDB.id == row.id).delete()
    db.commit()


def test_the_vocabulary_is_exactly_two_values():
    assert set(VARIANT_STATUSES) == {"draft", "ready"}


@pytest.mark.parametrize("status", ["sent", "approved", "archived", "anything"])
def test_the_service_refuses_any_other_status(db, campaign, status):
    with pytest.raises(ValueError, match="variant status"):
        create_variant_for_campaign(db, campaign.id, name="v", channel="email",
                                    status=status, brand_id=campaign.brand_id)
    assert db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).count() == 0


@pytest.mark.parametrize("status", ["draft", "ready"])
def test_the_two_statuses_are_accepted(db, campaign, status):
    variant = create_variant_for_campaign(db, campaign.id, name="v", channel="email",
                                          status=status, brand_id=campaign.brand_id)
    assert variant.status == status


def test_the_api_answers_422_for_another_status(campaign):
    with machine([VIEW, CAMPAIGNS_MANAGE]) as headers:
        response = client.post(f"/campaigns/{campaign.id}/variants",
                               json={"name": "v", "channel": "email", "status": "sent"},
                               headers=headers)
    assert response.status_code == 422, response.text
