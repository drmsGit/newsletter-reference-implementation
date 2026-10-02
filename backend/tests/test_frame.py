"""The snapshot frame (ADR-183): a composition frozen with its values.

Three properties carry the design, each pinned here:
  - **parity** — a frame of an unchanged variant renders exactly what the live
    send-mode render does (ADR-063: one intended output, two paths);
  - **frozen** — edits after the frame do not reach what it renders;
  - **recorded picks** — given the picks a send recorded, a re-render shows
    them even after the slot would now pick something else.
"""
import uuid

import pytest

from app.auth.service import ensure_default_brand
from app.campaigns.db_models import CampaignDB, DecisionResolutionDB, DecisionSlotDB, ModuleInstanceDB, VariantDB
from app.campaigns.service import (
    create_campaign, create_decision_slot_for_variant, create_module_for_variant,
)
from app.content.db_models import ContentRecordDB, ContentVersionDB
from app.content.service import create_content, create_content_version
from app.database import SessionLocal
from app.rendering.frame import build_frame, is_frame, render_frame
from app.rendering.service import render_variant_html


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _published(db, brand, headline):
    record = create_content(db, title=f"frame-{uuid.uuid4().hex[:6]}", brand_id=brand.id,
                            content={"headline_medium": headline, "body_medium": "Body"})
    create_content_version(db, content_record_id=record.id, created_by="test", brand_id=brand.id)
    return record


@pytest.fixture
def world(db):
    """An email variant: a header (subject), a content module, and a slot
    module with a global pick."""
    brand = ensure_default_brand(db)
    campaign = create_campaign(db, name=f"frame-{uuid.uuid4().hex[:6]}", brand_id=brand.id,
                               channel="email")
    variant = db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).one()
    fixed = _published(db, brand, "Fixed headline")
    picked = _published(db, brand, "Picked headline")
    later = _published(db, brand, "Later pick")
    create_module_for_variant(db, variant_id=variant.id, module_type="header",
                              module_data={"subject": "Hello", "preheader": "Peek"},
                              brand_id=brand.id)
    create_module_for_variant(db, variant_id=variant.id, module_type="img_right",
                              content_record_id=fixed.id, brand_id=brand.id)
    slot = create_decision_slot_for_variant(db, variant_id=variant.id, name="slot",
                                            brand_id=brand.id)
    create_module_for_variant(db, variant_id=variant.id, module_type="single_stack",
                              decision_slot_id=slot.id, brand_id=brand.id)
    db.add(DecisionResolutionDB(decision_slot_id=slot.id, content_record_id=picked.id))
    db.commit()
    yield {"brand": brand, "variant": variant, "fixed": fixed, "picked": picked,
           "later": later, "slot_id": slot.id}
    db.rollback()
    records = [fixed.id, picked.id, later.id]
    db.query(DecisionResolutionDB).filter(DecisionResolutionDB.decision_slot_id == slot.id).delete()
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant.id).delete()
    db.query(DecisionSlotDB).filter(DecisionSlotDB.id == slot.id).delete()
    db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).delete()
    db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
    db.query(ContentVersionDB).filter(ContentVersionDB.content_record_id.in_(records)).delete(
        synchronize_session=False)
    db.query(ContentRecordDB).filter(ContentRecordDB.id.in_(records)).delete(
        synchronize_session=False)
    db.commit()


def test_a_frame_says_what_it_is(db, world):
    frame = build_frame(db, world["variant"].id)
    assert is_frame(frame)
    kinds = [m["kind"] for m in frame["modules"]]
    assert kinds == ["static", "content", "slot"]
    assert frame["envelope"] == {"subject": "Hello", "preheader": "Peek"}
    content = frame["modules"][1]
    assert content["content_version_id"] is not None, "the version used is recorded"
    assert content["variables"]["headline_medium"] == "Fixed headline"


def test_parity_with_the_live_send_render(db, world):
    """ADR-063: the frame path and the live path give the same output."""
    artifact, picks = render_frame(db, build_frame(db, world["variant"].id))
    assert artifact.body == render_variant_html(db, world["variant"].id, mode="send")
    assert [p["content_record_id"] for p in picks] == [world["picked"].id]


def test_edits_after_the_frame_do_not_reach_it(db, world):
    frame = build_frame(db, world["variant"].id)
    # Edit everything the frame copied: the header, and a newly published version.
    header = db.query(ModuleInstanceDB).filter(
        ModuleInstanceDB.variant_id == world["variant"].id,
        ModuleInstanceDB.module_type == "header").one()
    header.module_data = {"subject": "Changed", "preheader": "Changed"}
    record = db.get(ContentRecordDB, world["fixed"].id)
    record.content = {"headline_medium": "Edited later", "body_medium": "x"}
    db.commit()
    create_content_version(db, content_record_id=record.id, created_by="test",
                           brand_id=world["brand"].id)

    artifact, _ = render_frame(db, frame)
    assert "Fixed headline" in artifact.body and "Edited later" not in artifact.body
    assert artifact.envelope["subject"] == "Hello"


def test_recorded_picks_survive_a_later_pick(db, world):
    frame = build_frame(db, world["variant"].id)
    _, picks = render_frame(db, frame)
    # The slot would now pick something else.
    db.add(DecisionResolutionDB(decision_slot_id=world["slot_id"], content_record_id=world["later"].id))
    db.commit()
    now_artifact, _ = render_frame(db, frame)
    replayed, _ = render_frame(db, frame, picks=picks)
    assert "Later pick" in now_artifact.body
    assert "Picked headline" in replayed.body and "Later pick" not in replayed.body
