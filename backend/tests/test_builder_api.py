"""Editing the builder over JSON — the half of ADR-002 that had drifted.

A variant, a module and a decision slot could each be **created and deleted**
over the API and not **edited**, while the Jinja UI has had all three since it
was built. The campaign/variant builder is the first screen of the React MVP,
so the gap made that screen impossible to write against the API — and it was
invisible because nobody had compared the two surfaces capability by
capability.

Runs against the isolated test database and removes what it creates.
"""
import uuid

import pytest
from sqlalchemy import text

from app.auth import service as auth
from app.campaigns.db_models import CampaignDB, DecisionSlotDB, ModuleInstanceDB, VariantDB
from app.campaigns.service import create_module_for_variant
from app.database import SessionLocal
from tests.machine import machine
from tests.test_api_guard import client

TAG = "builderapi"


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def variant(db):
    brand = auth.ensure_default_brand(db)
    campaign = CampaignDB(brand_id=brand.id, name=f"{TAG}-{uuid.uuid4().hex[:8]}")
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    row = VariantDB(campaign_id=campaign.id, name="Variant A", channel="email")
    db.add(row)
    db.commit()
    db.refresh(row)
    try:
        yield row
    finally:
        db.rollback()
        db.execute(text("DELETE FROM decision_slots WHERE variant_id = :v"), {"v": row.id})
        db.execute(text("DELETE FROM module_instances WHERE variant_id = :v"), {"v": row.id})
        db.query(VariantDB).filter(VariantDB.id == row.id).delete()
        db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
        db.commit()


@pytest.fixture
def api():
    from app.auth.permissions import CAMPAIGNS_MANAGE, VIEW

    with machine([VIEW, CAMPAIGNS_MANAGE]) as headers:
        yield headers


class TestEditingAVariant:

    def test_a_rename_lands(self, db, variant, api):
        response = client.put(
            f"/campaigns/variants/{variant.id}",
            json={"name": "Renamed over the API"}, headers=api,
        )

        assert response.status_code == 200, response.text
        db.refresh(variant)
        assert variant.name == "Renamed over the API"

    def test_envelope_copy_goes_to_the_module_not_a_column(self, db, variant, api):
        """`subject` and `preheader` stopped being columns in migration 0012.

        The payload still names them because they are what a caller means; the
        service writes them through `set_envelope_fields`, into the `header`
        module ADR-162 point 1 put them in.
        """
        from app.rendering.service import envelope_fields_for_variant

        client.put(
            f"/campaigns/variants/{variant.id}",
            json={
                "name": variant.name,
                "subject": "Written over JSON",
                "preheader": "And its preheader",
            },
            headers=api,
        )

        fields = envelope_fields_for_variant(db, variant.id, variant.channel)
        assert fields.get("subject") == "Written over JSON"
        assert not hasattr(variant, "subject"), (
            "if this column comes back, the write path has two homes again"
        )

    def test_a_missing_variant_is_404_not_a_silent_no_op(self, api):
        response = client.put(
            "/campaigns/variants/99999999", json={"name": "x"}, headers=api,
        )
        assert response.status_code == 404


class TestEditingAModule:

    @pytest.fixture
    def module(self, db, variant):
        return create_module_for_variant(
            db, variant_id=variant.id, module_type="cta",
            module_data={"label": "Original"},
        )

    def test_static_data_can_be_changed(self, db, variant, module, api):
        response = client.put(
            f"/campaigns/modules/{module.id}",
            json={"module_type": "cta", "module_data": {"label": "Edited"}},
            headers=api,
        )

        assert response.status_code == 200, response.text
        row = db.query(ModuleInstanceDB).filter(
            ModuleInstanceDB.id == module.id
        ).first()
        db.refresh(row)
        assert row.module_data["label"] == "Edited"

    def test_position_is_not_editable_here(self, db, variant, module, api):
        """Reordering is a different act with its own uniqueness constraint, so
        it keeps its own endpoint. A payload naming position is ignored rather
        than honoured, which is why the model does not accept one."""
        before = module.position

        client.put(
            f"/campaigns/modules/{module.id}",
            json={"module_type": "cta", "position": 99}, headers=api,
        )

        row = db.query(ModuleInstanceDB).filter(
            ModuleInstanceDB.id == module.id
        ).first()
        db.refresh(row)
        assert row.position == before

    def test_naming_both_a_record_and_a_slot_is_refused(self, db, variant, module, api):
        """The database refuses it, not this route.

        `ck_module_instances_content_or_decision_slot` exists because rendering
        silently prefers the content record and ignores the slot — a wrong
        answer with no error, which is why the rule lives where it cannot be
        forgotten.
        """
        slot = DecisionSlotDB(variant_id=variant.id, name="A slot")
        db.add(slot)
        db.commit()
        db.refresh(slot)

        content = db.execute(text(
            "SELECT id FROM content_records LIMIT 1"
        )).scalar()
        if content is None:
            pytest.skip("no content record in the test database")

        response = client.put(
            f"/campaigns/modules/{module.id}",
            json={
                "module_type": "cms",
                "content_record_id": content,
                "decision_slot_id": slot.id,
            },
            headers=api,
        )

        assert response.status_code >= 400, (
            "a module naming both a content record and a slot was accepted"
        )


class TestEditingADecisionSlot:

    @pytest.fixture
    def slot(self, db, variant):
        row = DecisionSlotDB(
            variant_id=variant.id, name="Main slot",
            decision_strategy="top_score",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def test_strategy_and_config_can_be_changed(self, db, variant, slot, api):
        response = client.put(
            f"/campaigns/decision-slots/{slot.id}",
            json={
                "decision_strategy": "recipient_top_score",
                "strategy_config": {"preference_score_weight": 10},
            },
            headers=api,
        )

        assert response.status_code == 200, response.text
        db.refresh(slot)
        assert slot.decision_strategy == "recipient_top_score"
        assert slot.strategy_config["preference_score_weight"] == 10

    def test_an_unregistered_strategy_is_refused(self, db, variant, slot, api):
        """**Validated against the registry rather than stored on trust.**

        An unknown strategy resolves nothing at send time and reports it as
        graceful degradation under ADR-086 — the right answer for a strategy
        that found no candidates and the wrong one for a typo, which would then
        look like a content problem forever.
        """
        response = client.put(
            f"/campaigns/decision-slots/{slot.id}",
            json={"decision_strategy": "top_scoer"}, headers=api,
        )

        assert response.status_code == 400
        assert "not a registered decision strategy" in response.json()["detail"]
        db.refresh(slot)
        assert slot.decision_strategy == "top_score", "the typo was stored anyway"
