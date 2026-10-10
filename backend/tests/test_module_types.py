"""A module's type is one its channel accepts, and never the envelope (task-249).

Create checked the type against the variant's channel; update overwrote it
with no check, so a PUT could turn an email module into push's notification or
a type nobody declared (ADR-161 point 7: a channel is the manifests it
accepts). Both accepted the channel's envelope type as an ordinary module,
appended where `set_envelope_fields` never looks: subject and preheader are
written through the variant (ADR-162 point 1), and only there.

Each refusal has a control beside it, so a test cannot pass because the route
refuses everything.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.permissions import CAMPAIGNS_MANAGE
from app.campaigns.db_models import CampaignDB, ModuleInstanceDB, VariantDB
from main import app
from tests.machine import editor, machine

client = TestClient(app, raise_server_exceptions=False)

# One editing machine per test: several writes as different machines would
# meet each other's fence (task-254).
pytestmark = pytest.mark.usefixtures("one_editor")


@pytest.fixture
def variant(db, default_brand):
    campaign = CampaignDB(brand_id=default_brand.id, name=f"types-{uuid.uuid4().hex[:6]}")
    db.add(campaign); db.flush()
    variant = VariantDB(campaign_id=campaign.id, channel="email", name="v", status="draft")
    db.add(variant); db.commit()
    yield variant
    db.rollback()
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant.id).delete()
    db.query(VariantDB).filter(VariantDB.id == variant.id).delete()
    db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
    db.commit()


def _types(db, variant):
    db.expire_all()
    return [m.module_type for m in db.query(ModuleInstanceDB)
            .filter(ModuleInstanceDB.variant_id == variant.id).order_by(ModuleInstanceDB.position)]


def _create(variant, module_type):
    with editor([CAMPAIGNS_MANAGE]) as headers:
        return client.post(f"/campaigns/variants/{variant.id}/modules",
                           json={"module_type": module_type}, headers=headers)


def _put(module_id, module_type):
    with editor([CAMPAIGNS_MANAGE]) as headers:
        return client.put(f"/campaigns/modules/{module_id}",
                          json={"module_type": module_type}, headers=headers)


class TestCreate:
    def test_the_envelope_type_is_refused_as_a_module(self, db, variant):
        response = _create(variant, "envelope")
        assert response.status_code == 400, response.text
        assert "subject" in response.json()["detail"]
        assert _types(db, variant) == []

    def test_a_content_type_is_added(self, db, variant):
        assert _create(variant, "img_left").status_code == 200
        assert _types(db, variant) == ["img_left"]


class TestUpdate:
    @pytest.fixture
    def module(self, variant):
        response = _create(variant, "img_left")
        assert response.status_code == 200, response.text
        return response.json()["id"]

    @pytest.mark.parametrize("module_type", ["notification", "no_such_module", "envelope"])
    def test_a_type_the_channel_does_not_accept_as_a_module_is_refused(self, db, variant, module, module_type):
        response = _put(module, module_type)
        assert response.status_code == 400, response.text
        assert _types(db, variant) == ["img_left"]

    def test_another_type_of_the_same_channel_is_accepted(self, db, variant, module):
        assert _put(module, "img_right").status_code == 200
        assert _types(db, variant) == ["img_right"]


def test_the_limit_counts_the_same_modules_on_create_as_in_the_composition(db, variant, monkeypatch):
    """No channel has both a module limit and an envelope today, so give email
    a limit of one: with the envelope present, one content module must still
    fit, as the composition read already says."""
    import app.campaigns.service as service
    from app.auth.service import ensure_default_brand
    from app.channels import registry

    monkeypatch.setattr(service, "max_modules_for", lambda channel: 1)
    monkeypatch.setattr(registry, "max_modules_for", lambda channel: 1)
    brand_id = ensure_default_brand(db).id
    service.set_envelope_fields(db, variant.id, {"subject": "Hello"}, brand_id=brand_id)

    [composed] = service.campaign_composition(db, variant.campaign_id, brand_id=brand_id)["variants"]
    assert composed["can_add_module"] is True
    assert _create(variant, "img_left").status_code == 200
    second = _create(variant, "img_right")
    assert second.status_code == 400, second.text
    assert _types(db, variant) == ["envelope", "img_left"]
