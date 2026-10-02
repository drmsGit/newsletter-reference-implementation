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


class TestB21B22DecisionSlotStats:
    @pytest.fixture
    def slot(self, db, default_brand):
        from app.campaigns.db_models import DecisionResolutionDB, DecisionSlotDB
        from app.content.db_models import ContentRecordDB

        variant = _variant(db, default_brand)
        slot = DecisionSlotDB(variant_id=variant.id, name="s", decision_type="content_recommendation",
                              decision_strategy="top_score")
        a = ContentRecordDB(title="A", content={}, status="active", brand_id=default_brand.id)
        b = ContentRecordDB(title="B", content={}, status="active", brand_id=default_brand.id)
        db.add_all([slot, a, b]); db.flush()
        for content, reason in ((a, "fit"), (a, "fit"), (a, "fit"), (b, "fallback")):
            db.add(DecisionResolutionDB(decision_slot_id=slot.id, content_record_id=content.id,
                                        reason=reason, score=1.0))
        db.commit()
        yield slot, a, b
        db.query(DecisionResolutionDB).filter(DecisionResolutionDB.decision_slot_id == slot.id).delete()
        db.query(DecisionSlotDB).filter(DecisionSlotDB.id == slot.id).delete()
        db.query(ContentRecordDB).filter(ContentRecordDB.id.in_([a.id, b.id])).delete(
            synchronize_session=False)
        db.commit()

    def test_the_list_carries_the_counts(self, slot):
        s, _, _ = slot
        with machine([VIEW]) as headers:
            rows = client.get("/campaigns/decision-slots", headers=headers).json()
        row = next(r for r in rows if r["id"] == s.id)
        assert (row["resolution_count"], row["unique_content_count"]) == (4, 2)

    def test_the_stats_carry_share_and_reasons(self, slot):
        s, a, _ = slot
        with machine([VIEW]) as headers:
            body = client.get(f"/campaigns/decision-slots/{s.id}/stats", headers=headers).json()
        top = body["top_content"][0]
        assert (top["content_id"], top["selection_count"], top["share"]) == (a.id, 3, 75.0)
        assert body["reasons"][0] == {"reason": "fit", "count": 3}
        assert body["summary"]["resolution_count"] == 4

    def test_another_brands_slot_is_absent_and_not_found(self, db, foreign_brand):
        from app.campaigns.db_models import DecisionSlotDB

        variant = _variant(db, foreign_brand)
        foreign = DecisionSlotDB(variant_id=variant.id, name="f", decision_type="content_recommendation",
                                 decision_strategy="top_score")
        db.add(foreign); db.commit()
        try:
            with machine([VIEW]) as headers:
                rows = client.get("/campaigns/decision-slots", headers=headers).json()
                stats = client.get(f"/campaigns/decision-slots/{foreign.id}/stats", headers=headers)
            assert foreign.id not in {r["id"] for r in rows}
            assert stats.status_code == 404
        finally:
            db.query(DecisionSlotDB).filter(DecisionSlotDB.id == foreign.id).delete()
            db.commit()

    def test_the_jinja_pages_still_render_from_the_service(self, db, slot):
        from app.auth import service as auth

        s, _, _ = slot
        user = auth.create_user(db, email=f"rm-{uuid.uuid4().hex[:8]}@example.invalid", role_key="viewer")
        token = auth.create_session(db, user)
        page_client = TestClient(app, raise_server_exceptions=False)
        page_client.cookies.set(auth.SESSION_COOKIE, token)
        try:
            listing = page_client.get("/ui/decisions")
            detail = page_client.get(f"/ui/decisions/slots/{s.id}")
            assert listing.status_code == 200 and detail.status_code == 200, detail.text[:300]
            assert "75.0" in detail.text, "the share no longer reaches the page"
        finally:
            from sqlalchemy import text

            db.rollback()
            for table in ("auth_sessions", "role_assignments"):
                db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
            db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
            db.commit()
