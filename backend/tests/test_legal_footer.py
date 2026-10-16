"""Every email carries its brand profile's legal details (task-357; ADR-194 and
its 2026-10-11 addenda).

A frame of version 3 freezes the variant's profile, and the email it renders
ends with the legal footer: the legal name and address, the imprint and privacy
links, and for a marketing message the unsubscribe line with the platform's
link. A send is refused while the frozen profile lacks a required field, or
while its snapshot predates profiles. Frames made before keep the old footer
line byte for byte, so what was sent still reconstructs exactly (ADR-183).
"""
import uuid

import pytest

from app.auth.service import ensure_default_brand
from app.brand_profiles import service as profiles
from app.brand_profiles.db_models import BrandProfileDB
from app.campaigns.db_models import CampaignDB, ModuleInstanceDB, VariantDB
from app.campaigns.service import create_campaign, create_module_for_variant, set_envelope_fields
from app.database import SessionLocal
from app.rendering import frame as frames
from app.rendering.frame import build_frame, profile_refusal, render_frame
from app.rendering.service import legal_footer_html

COMPLETE = {
    "legal_company_name": "Footer & Co GmbH",
    "legal_address": "Example Street 1\n10115 Example City",
    "imprint_url": "https://example.test/imprint",
    "privacy_url": "https://example.test/privacy",
    "unsubscribe_text": "Leave this list",
}


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def world(db):
    """An email variant with a subject and one button, on its own profile."""
    brand = ensure_default_brand(db)
    profile = BrandProfileDB(brand_id=brand.id, name=f"Footer {uuid.uuid4().hex[:6]}",
                             field_values=dict(COMPLETE))
    db.add(profile)
    db.commit()
    campaign = create_campaign(db, name=f"footer-{uuid.uuid4().hex[:6]}", brand_id=brand.id,
                               channel="email")
    variant = db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).one()
    variant.brand_profile_id = profile.id
    db.commit()
    set_envelope_fields(db, variant.id, {"subject": "Hello", "preheader": "Peek"}, brand_id=brand.id)
    create_module_for_variant(db, variant_id=variant.id, module_type="cta",
                              module_data={"label": "Go", "url": "https://example.test/go"},
                              brand_id=brand.id)
    yield {"brand": brand, "variant": variant, "profile": profile, "campaign": campaign}
    db.rollback()
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant.id).delete()
    db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).delete()
    db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
    db.query(BrandProfileDB).filter(BrandProfileDB.id == profile.id).delete()
    db.commit()


# --- the frame freezes the profile -------------------------------------------

def test_a_frame_freezes_the_variants_profile(db, world):
    frame = build_frame(db, world["variant"].id)
    assert frame["frame_version"] >= 3, "a profile is frozen from version 3 on"
    frozen = frame["brand_profile"]
    assert (frozen["id"], frozen["name"], frozen["language"], frozen["kind"]) == (
        world["profile"].id, world["profile"].name, "en", "marketing")
    assert frozen["values"] == COMPLETE


def test_a_later_profile_edit_does_not_reach_the_frame(db, world):
    frame = build_frame(db, world["variant"].id)
    world["profile"].field_values = {**COMPLETE, "legal_company_name": "Renamed GmbH"}
    db.commit()
    artifact, _ = render_frame(db, frame)
    assert "Footer &amp; Co GmbH" in artifact.body and "Renamed" not in artifact.body


def test_a_variant_without_a_profile_freezes_the_brand_default(db, world):
    world["variant"].brand_profile_id = None
    db.commit()
    frame = build_frame(db, world["variant"].id)
    assert frame["brand_profile"]["id"] == profiles.default_profile(db, world["brand"].id).id


# --- what the footer says ----------------------------------------------------

def _frozen(values=None, language="en", kind="marketing"):
    return {"id": 1, "name": "x", "language": language, "kind": kind,
            "values": dict(COMPLETE if values is None else values)}


def test_the_footer_names_the_sender_and_links_imprint_and_privacy():
    html = legal_footer_html(_frozen(), unsubscribe_url="https://app.test/unsubscribe/tok")
    assert "Footer &amp; Co GmbH" in html, "values are escaped"
    assert "Example Street 1" in html and "10115 Example City" in html
    assert '<a href="https://example.test/imprint">Imprint</a>' in html
    assert '<a href="https://example.test/privacy">Privacy</a>' in html
    assert '<a href="https://app.test/unsubscribe/tok">Leave this list</a>' in html


def test_the_labels_follow_the_profiles_language():
    html = legal_footer_html(_frozen(language="de"))
    assert ">Impressum</a>" in html and ">Datenschutz</a>" in html
    # Any language without its own labels reads English.
    assert ">Imprint</a>" in legal_footer_html(_frozen(language="fr"))


def test_without_a_link_the_unsubscribe_text_is_absent_or_plain():
    # A message that carries no unsubscribe (a preview) shows no line.
    assert "Leave this list" not in legal_footer_html(_frozen())
    # A test send shows the wording, unlinked: it has no token.
    plain = legal_footer_html(_frozen(), unsubscribe_unlinked=True)
    assert "Leave this list" in plain and "/unsubscribe/" not in plain


def test_an_empty_unsubscribe_text_shows_no_line():
    values = {k: v for k, v in COMPLETE.items() if k != "unsubscribe_text"}
    html = legal_footer_html(_frozen(values), unsubscribe_url="https://app.test/unsubscribe/tok")
    assert "/unsubscribe/" not in html


def test_a_frame_render_ends_with_the_footer_and_keeps_the_one_click_header(db, world):
    frame = build_frame(db, world["variant"].id)
    artifact, _ = render_frame(db, frame, unsubscribe={"url": "https://app.test/unsubscribe/tok",
                                                       "brand": "Ignored"})
    assert '<a href="https://app.test/unsubscribe/tok">Leave this list</a>' in artifact.body
    assert "You receive this from" not in artifact.body, "the legacy line is for old frames only"
    assert artifact.envelope["list_unsubscribe"] == "https://app.test/unsubscribe/tok"


def test_an_older_frame_keeps_the_legacy_line_byte_for_byte(db, world):
    """Deliveries sent before profiles rebuild to their stored hash (ADR-183)."""
    from app.subscriptions.texts import footer_html

    frame = build_frame(db, world["variant"].id)
    frame["frame_version"] = 2
    del frame["brand_profile"]
    artifact, _ = render_frame(db, frame, unsubscribe={"url": "https://app.test/u/tok", "brand": "Acme"})
    assert footer_html("Acme", "https://app.test/u/tok") in artifact.body
    assert "Imprint" not in artifact.body


def test_the_legacy_line_never_changes():
    """texts.py is not in the template fingerprint: a change here would break
    the hash of every delivery sent with this line, while the layout still
    reported as unchanged. This literal is the line as sent since ADR-191."""
    from app.subscriptions.texts import footer_html

    assert footer_html("Acme", "https://app.test/u/tok") == (
        '<p style="font-size:12px;color:#666666;text-align:center;margin:24px 0 0;">'
        'You receive this from Acme. <a href="https://app.test/u/tok">Unsubscribe</a>.</p>'
    )


def test_the_footer_template_is_part_of_the_fingerprint(monkeypatch, tmp_path):
    """Editing the footer must show as a layout change, never a silent one."""
    import shutil

    from app.modules import registry

    copy = tmp_path / "modules"
    shutil.copytree(registry.MODULES_DIR, copy)
    monkeypatch.setattr(frames, "MODULES_DIR", copy)
    before = frames.templates_fingerprint("email")
    footer = copy / "email" / "_legal_footer.html"
    footer.write_text(footer.read_text() + "<!-- edited -->")
    assert frames.templates_fingerprint("email") != before


# --- refusals -----------------------------------------------------------------

def test_a_complete_profile_is_not_refused(db, world):
    assert profile_refusal(build_frame(db, world["variant"].id)) is None


def test_a_missing_field_is_refused_by_its_label(db, world):
    world["profile"].field_values = {k: v for k, v in COMPLETE.items() if k != "imprint_url"}
    db.commit()
    reason = profile_refusal(build_frame(db, world["variant"].id))
    assert reason is not None and "Imprint" in reason and "new snapshot" in reason


def test_a_frame_from_before_profiles_is_refused(db, world):
    frame = build_frame(db, world["variant"].id)
    frame["frame_version"] = 2
    del frame["brand_profile"]
    assert "before brand profiles" in profile_refusal(frame)


def test_a_push_frame_needs_no_profile(db, world):
    frame = build_frame(db, world["variant"].id)
    frame.update(channel="push", frame_version=2)
    frame.pop("brand_profile")
    assert profile_refusal(frame) is None


@pytest.fixture
def planned(db, world):
    """A send of the world's variant to one consenting recipient, not yet fired.
    Made after a test has shaped the profile, so its snapshot freezes that."""
    from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
    from app.recipients.consent import record_consent
    from app.recipients.db_models import AddressabilityDB, ConsentEventDB, RecipientDB
    from app.snapshots.db_models import SnapshotDB
    from app.snapshots.service import create_snapshot_for_variant

    made = {}

    def plan():
        brand = world["brand"]
        snapshot = create_snapshot_for_variant(db, world["variant"].id, brand_id=brand.id)
        recipient = RecipientDB(external_id=f"footer-{uuid.uuid4()}", status="active")
        db.add(recipient); db.flush()
        db.add(AddressabilityDB(recipient_id=recipient.id, channel="email",
                                value={"email": f"{uuid.uuid4().hex[:8]}@example.invalid"},
                                status="active", is_primary=True))
        record_consent(db, recipient.id, "opted_in", brand.id, channel="email",
                       purpose="marketing", source="test", commit=False)
        send = SendInstanceDB(snapshot_id=snapshot.id, brand_id=brand.id, name="footer send",
                              status="draft", provider="mock")
        db.add(send); db.flush()
        execution = DeliveryExecutionDB(send_instance_id=send.id, recipient_id=recipient.id,
                                        status="created", provider="mock", channel="email",
                                        purpose="marketing")
        db.add(execution); db.commit()
        made.update(send=send, snapshot=snapshot, recipient=recipient, execution=execution)
        return send

    yield plan
    db.rollback()
    if made:
        db.query(DeliveryExecutionDB).filter(DeliveryExecutionDB.send_instance_id == made["send"].id).delete()
        db.query(SendInstanceDB).filter(SendInstanceDB.id == made["send"].id).delete()
        db.query(SnapshotDB).filter(SnapshotDB.id == made["snapshot"].id).delete()
        rid = made["recipient"].id
        db.query(ConsentEventDB).filter(ConsentEventDB.recipient_id == rid).delete()
        db.query(AddressabilityDB).filter(AddressabilityDB.recipient_id == rid).delete()
        db.query(RecipientDB).filter(RecipientDB.id == rid).delete()
        db.commit()


def test_a_send_from_an_incomplete_profile_is_refused_before_anything_moves(db, world, planned):
    from app.delivery.service import send_send_instance

    world["profile"].field_values = {k: v for k, v in COMPLETE.items() if k != "legal_address"}
    db.commit()
    send = planned()
    with pytest.raises(ValueError, match="Address"):
        send_send_instance(db, send.id, brand_id=world["brand"].id)
    db.refresh(send)
    assert send.status == "draft", "the refusal came after the send was claimed"


def test_the_reviewer_is_told_the_same(db, world, planned):
    from app.approvals.actions.send_fire import describe

    world["profile"].field_values = {k: v for k, v in COMPLETE.items() if k != "privacy_url"}
    db.commit()
    send = planned()
    described = describe(db, {"send_instance_id": send.id}, brand_id=world["brand"].id)
    assert described.blocked_reason is not None and "Privacy" in described.blocked_reason


def test_a_sent_email_carries_the_footer_and_rebuilds_to_its_hash(db, world, planned):
    from app.delivery.db_models import DeliveryExecutionDB
    from app.delivery.service import reconstruct_delivery, send_send_instance

    send = planned()
    send_send_instance(db, send.id, brand_id=world["brand"].id)
    execution = db.query(DeliveryExecutionDB).filter(DeliveryExecutionDB.send_instance_id == send.id).one()
    assert execution.status == "sent"
    # Changed after the send: the rebuild must still say exactly what went out.
    world["profile"].field_values = {**COMPLETE, "legal_company_name": "Changed later GmbH"}
    db.commit()
    rebuilt = reconstruct_delivery(db, execution.id, brand_id=world["brand"].id)
    assert "Footer &amp; Co GmbH" in rebuilt["body"] and "Changed later" not in rebuilt["body"]
    assert "/unsubscribe/" in rebuilt["body"]
    assert rebuilt["hash_matches"] is True


# --- test sends -----------------------------------------------------------------

def test_a_test_send_carries_the_footer_with_the_wording_unlinked(db, world, monkeypatch):
    from app.delivery.providers import mock as mock_module
    from app.delivery.service import send_test_email

    captured = {}
    original = mock_module.MockProvider.send

    def capture(self, address, artifact):
        captured["artifact"] = artifact
        return original(self, address, artifact)

    monkeypatch.setattr(mock_module.MockProvider, "send", capture)
    result = send_test_email(db, to="someone@example.invalid", subject="Test", provider="mock",
                             brand_id=world["brand"].id, variant_id=world["variant"].id)
    assert result.success, result.message
    body = captured["artifact"].body
    assert "Footer &amp; Co GmbH" in body and ">Imprint</a>" in body
    assert "Leave this list" in body and "/unsubscribe/" not in body
    assert "list_unsubscribe" not in (captured["artifact"].envelope or {})


def test_a_test_send_from_an_incomplete_profile_is_refused(db, world, monkeypatch):
    from app.delivery.providers import mock as mock_module
    from app.delivery.service import send_test_email

    def must_not_send(self, address, artifact):
        raise AssertionError("an email went out from an incomplete profile")

    monkeypatch.setattr(mock_module.MockProvider, "send", must_not_send)
    world["profile"].field_values = {k: v for k, v in COMPLETE.items() if k != "legal_company_name"}
    db.commit()
    result = send_test_email(db, to="someone@example.invalid", subject="Test", provider="mock",
                             brand_id=world["brand"].id, variant_id=world["variant"].id)
    assert result.success is False and "Legal company name" in result.message


def test_the_version_decides_not_the_presence_of_a_profile(db, world):
    """A frame below version 3 renders and refuses as an old frame even if it
    held a profile key: the version is what says which footer it was sent with."""
    from app.subscriptions.texts import footer_html

    frame = {**build_frame(db, world["variant"].id), "frame_version": 2}
    artifact, _ = render_frame(db, frame, unsubscribe={"url": "https://app.test/u/tok", "brand": "Acme"})
    assert footer_html("Acme", "https://app.test/u/tok") in artifact.body
    assert "before brand profiles" in profile_refusal(frame)
