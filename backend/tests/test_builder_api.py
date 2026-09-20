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
from app.campaigns.service import brand_of_variant
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
        from app.campaigns.service import brand_of_variant

        return create_module_for_variant(
            db, variant_id=variant.id, module_type="cta",
            module_data={"label": "Original"},
            brand_id=brand_of_variant(db, variant.id),
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


class TestPatchingADecisionSlotLeavesTunedSettingsAlone:
    """Inventory B16, closed 2026-09-20 — and narrower than it was described.

    The inventory said the risk was the category picker's "empty means all".
    It was not: `_normalize_section` fills `category_ids` with its `[]` default
    and both strategies read `if category_ids:`, so an empty list and an absent
    key already behave identically. That half is presentation — two form inputs
    for one field, which a JSON client does not have.

    The real risk is `strategy_config`. A declared key that is absent is filled
    with its **spec default**, so replacing the section wholesale does not
    leave it alone — it resets it. `recipient_top_score` has two tunable
    weights, and a client editing the candidate filter with PUT silently undoes
    whatever a manager set.

    The Jinja form never had the problem because it round-trips both sections
    as pre-populated JSON. A JSON client has no such hidden state, which is why
    the rule had to become explicit instead of remaining a property of a form.
    """

    @pytest.fixture
    def tuned_slot(self, db, variant):
        from app.campaigns.service import create_decision_slot_for_variant

        slot = create_decision_slot_for_variant(
            db, variant_id=variant.id, name="tuned",
            decision_strategy="recipient_top_score",
            candidate_filter={"category_ids": [1]},
            strategy_config={"content_score_weight": 0.9,
                             "preference_score_weight": 0.1},
            brand_id=brand_of_variant(db, variant.id),
        )
        return slot

    def test_patching_the_filter_keeps_the_tuned_weights(self, db, tuned_slot, api):
        from app.campaigns.db_models import DecisionSlotDB

        response = client.patch(
            f"/campaigns/decision-slots/{tuned_slot.id}",
            json={"candidate_filter": {"category_ids": [2]}},
            headers=api,
        )
        assert response.status_code == 200, response.text

        db.expire_all()
        stored = db.query(DecisionSlotDB).filter(
            DecisionSlotDB.id == tuned_slot.id).first()
        assert stored.candidate_filter["category_ids"] == [2]
        assert stored.strategy_config["content_score_weight"] == 0.9, (
            "the tuned weight was reset by an edit that never mentioned it"
        )

    def test_put_still_replaces_and_that_is_deliberate(self, db, tuned_slot, api):
        """Pinned so the difference between the verbs is a decision.

        PUT replaces, and replacing a section means every declared key it omits
        comes back as its default. The route says so and points at PATCH.
        """
        from app.campaigns.db_models import DecisionSlotDB

        response = client.put(
            f"/campaigns/decision-slots/{tuned_slot.id}",
            json={"decision_strategy": "recipient_top_score",
                  "candidate_filter": {"category_ids": [2]}},
            headers=api,
        )
        assert response.status_code == 200, response.text

        db.expire_all()
        stored = db.query(DecisionSlotDB).filter(
            DecisionSlotDB.id == tuned_slot.id).first()
        assert stored.strategy_config["content_score_weight"] != 0.9

    def test_an_empty_category_list_and_an_absent_one_agree(self, db, tuned_slot, api):
        """The half that was never broken, pinned so nobody 'fixes' it.

        Both mean "consider every category". If they ever stop agreeing, the
        form's remove-the-key behaviour and the API's send-an-empty-list
        behaviour start meaning different things, and only one of them is
        documented.
        """
        from app.campaigns.db_models import DecisionSlotDB

        assert client.patch(
            f"/campaigns/decision-slots/{tuned_slot.id}",
            json={"candidate_filter": {"category_ids": []}}, headers=api,
        ).status_code == 200

        db.expire_all()
        stored = db.query(DecisionSlotDB).filter(
            DecisionSlotDB.id == tuned_slot.id).first()
        assert (stored.candidate_filter or {}).get("category_ids", []) == []

    def test_an_unknown_strategy_is_refused_rather_than_stored(self, db, tuned_slot, api):
        assert client.patch(
            f"/campaigns/decision-slots/{tuned_slot.id}",
            json={"decision_strategy": "astrology"}, headers=api,
        ).status_code == 400
