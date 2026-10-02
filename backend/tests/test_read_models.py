"""JSON read models the Jinja UI computed on its own (task-50, remaining rows).

Each class is one row of `docs/react-migration-inventory.md`, tested at the
JSON route the SPA will call. Cross-brand cases use the foreign brand, never
the default one (conftest's rule).
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.ai.db_models import AIRunDB
from app.auth.permissions import VIEW
from app.campaigns.db_models import CampaignDB, VariantDB
from main import app
from tests.machine import machine

client = TestClient(app, raise_server_exceptions=False)


def _variant(db, brand):
    campaign = CampaignDB(brand_id=brand.id, name=f"rm-{uuid.uuid4().hex[:6]}")
    db.add(campaign); db.flush()
    variant = VariantDB(campaign_id=campaign.id, channel="email", name="v", status="draft")
    db.add(variant); db.commit()
    return variant


class TestC7SuggestionsReadBack:
    @pytest.fixture
    def runs(self, db, default_brand):
        variant = _variant(db, default_brand)
        good = AIRunDB(task_key="subject_preheader", provider="mock", model="m", status="ok",
                       target_type="variant", target_id=variant.id, input_tokens=10, output_tokens=5,
                       output_text="SUBJECT: One\nPREHEADER: First\nSUBJECT: Two\nPREHEADER: Second")
        refusal = AIRunDB(task_key="subject_preheader", provider="mock", status="ok",
                          target_type="variant", target_id=variant.id,
                          output_text="I would have to invent specifics to write these.")
        db.add_all([good, refusal]); db.commit()
        yield variant, good, refusal
        db.query(AIRunDB).filter(AIRunDB.target_id == variant.id).delete()
        db.commit()

    def test_options_come_back_with_their_cost(self, runs):
        variant, good, _ = runs
        with machine([VIEW]) as headers:
            body = client.get(f"/campaigns/variants/{variant.id}/suggestions", headers=headers).json()
        by_id = {r["run_id"]: r for r in body}
        assert by_id[good.id]["options"] == [
            {"subject": "One", "preheader": "First"}, {"subject": "Two", "preheader": "Second"}]
        assert (by_id[good.id]["input_tokens"], by_id[good.id]["output_tokens"]) == (10, 5)

    def test_a_refusal_comes_back_as_the_reply(self, runs):
        variant, _, refusal = runs
        with machine([VIEW]) as headers:
            body = client.get(f"/campaigns/variants/{variant.id}/suggestions", headers=headers).json()
        run = next(r for r in body if r["run_id"] == refusal.id)
        assert run["options"] == [] and "invent specifics" in run["reply"]

    def test_another_brands_variant_is_not_found(self, db, foreign_brand):
        variant = _variant(db, foreign_brand)
        with machine([VIEW]) as headers:
            response = client.get(f"/campaigns/variants/{variant.id}/suggestions", headers=headers)
        assert response.status_code == 404
