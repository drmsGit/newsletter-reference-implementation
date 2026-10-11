"""Transactional brand profiles (task-355; ADR-195, ADR-194).

A send whose snapshot's profile is transactional records purpose
"transactional" and skips the marketing opt-in check, at planning and at send
time. It still excludes unaddressable recipients and anyone the provider
suppressed (a hard bounce or complaint for that brand and channel, on any
purpose). It carries no unsubscribe line or one-click header. Creating or
marking a transactional profile needs its own permission, a duplicate stays
transactional only for a holder, and a transactional profile is never the
default.
"""
import uuid
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB
from app.audience.service import add_member, create_group
from app.audit.db_models import AuditEventDB
from app.auth import service as auth
from app.auth.db_models import RoleDB, RolePermissionDB
from app.auth.permissions import BRAND_PROFILES_MANAGE, BRAND_PROFILES_TRANSACTIONAL, VIEW
from app.auth.service import ensure_default_brand
from app.brand_profiles import service as profiles
from app.brand_profiles.db_models import BrandProfileDB
from app.campaigns.db_models import CampaignDB, ModuleInstanceDB, VariantDB
from app.campaigns.service import create_campaign, create_module_for_variant, set_envelope_fields
from app.database import SessionLocal
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.delivery.exclusion import STAGE_SUPPRESSION
from app.recipients.consent import MARKETING, TRANSACTIONAL, record_consent
from app.recipients.db_models import AddressabilityDB, ConsentEventDB, RecipientDB
from app.snapshots.db_models import SnapshotDB
from main import app
from tests.test_api_guard import signed_in

LEGAL = {
    "legal_company_name": "Receipts GmbH",
    "legal_address": "Example Street 1",
    "imprint_url": "https://example.test/imprint",
    "privacy_url": "https://example.test/privacy",
    "unsubscribe_text": "Unsubscribe",
}


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def admin(db):
    with signed_in(db) as (cookied, _token, csrf):
        yield cookied, {"X-CSRF-Token": csrf}


@contextmanager
def person_with(db, permissions):
    role = auth.create_role(db, key=f"tx-{uuid.uuid4().hex[:6]}", name="transactional test")
    auth.set_role_permissions(db, role.id, permissions)
    user = auth.create_user(db, email=f"tx-{uuid.uuid4().hex[:8]}@example.invalid", role_key=role.key)
    token = auth.create_session(db, user)
    cookied = TestClient(app, raise_server_exceptions=False)
    cookied.cookies.set(auth.SESSION_COOKIE, token)
    try:
        yield cookied, {"X-CSRF-Token": auth.csrf_token_for(token)}
    finally:
        db.rollback()
        for table in ("login_codes", "auth_sessions", "role_assignments"):
            db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
        db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
        db.query(RolePermissionDB).filter(RolePermissionDB.role_id == role.id).delete()
        db.query(RoleDB).filter(RoleDB.id == role.id).delete()
        db.commit()


@pytest.fixture(autouse=True)
def drop_test_profiles(db, default_brand):
    before = {p.id for p in db.query(BrandProfileDB).filter(BrandProfileDB.brand_id == default_brand.id)}
    yield
    db.rollback()
    db.query(VariantDB).filter(VariantDB.brand_profile_id.notin_(before)).update(
        {"brand_profile_id": None}, synchronize_session=False)
    db.query(BrandProfileDB).filter(BrandProfileDB.brand_id == default_brand.id,
                                    BrandProfileDB.id.notin_(before)).delete(synchronize_session=False)
    db.commit()


def _create(cookied, headers, kind="transactional", name=None):
    return cookied.post("/brand-profiles/", json={"name": name or f"Receipts {uuid.uuid4().hex[:6]}",
                                                  "language": "en", "kind": kind, "field_values": LEGAL},
                        headers=headers)


# --- who may make a profile transactional ------------------------------------

class TestThePermission:
    def test_without_it_a_transactional_profile_is_refused(self, db):
        with person_with(db, [VIEW, BRAND_PROFILES_MANAGE]) as (cookied, headers):
            assert _create(cookied, headers).status_code == 403
            assert _create(cookied, headers, kind="marketing").status_code == 201

    def test_with_it_one_is_created_and_audited_with_its_kind(self, db):
        with person_with(db, [VIEW, BRAND_PROFILES_MANAGE, BRAND_PROFILES_TRANSACTIONAL]) as (cookied, headers):
            response = _create(cookied, headers)
        assert response.status_code == 201, response.text
        assert response.json()["kind"] == "transactional"
        entry = db.query(AuditEventDB).filter(AuditEventDB.subject_type == "brand_profile",
                                              AuditEventDB.subject_id == response.json()["id"]).one()
        assert entry.detail["kind"] == "transactional"

    def test_marking_an_existing_profile_transactional_needs_it_too(self, db):
        with person_with(db, [VIEW, BRAND_PROFILES_MANAGE]) as (cookied, headers):
            created = _create(cookied, headers, kind="marketing").json()
            refused = cookied.put(f"/brand-profiles/{created['id']}",
                                  json={"name": created["name"], "kind": "transactional",
                                        "field_values": LEGAL}, headers=headers)
        assert refused.status_code == 403
        assert db.get(BrandProfileDB, created["id"]).kind == "marketing"

    def test_the_single_read_says_whether_the_reader_may_mark_it(self, db, default_brand):
        default = profiles.default_profile(db, default_brand.id)
        with person_with(db, [VIEW, BRAND_PROFILES_MANAGE]) as (cookied, _):
            assert cookied.get(f"/brand-profiles/{default.id}").json()["may_mark_transactional"] is False
        with admin(db) as (cookied, _):
            assert cookied.get(f"/brand-profiles/{default.id}").json()["may_mark_transactional"] is True

    def test_a_copy_stays_transactional_only_for_a_holder(self, db):
        with admin(db) as (cookied, headers):
            source = _create(cookied, headers).json()
        with person_with(db, [VIEW, BRAND_PROFILES_MANAGE]) as (cookied, headers):
            copy = cookied.post(f"/brand-profiles/{source['id']}/duplicate", headers=headers).json()
        with admin(db) as (cookied, headers):
            kept = cookied.post(f"/brand-profiles/{source['id']}/duplicate", headers=headers).json()
        assert copy["kind"] == "marketing" and kept["kind"] == "transactional"


class TestNeverTheDefault:
    def test_a_transactional_profile_cannot_become_the_default(self, db):
        with admin(db) as (cookied, headers):
            created = _create(cookied, headers).json()
            response = cookied.post(f"/brand-profiles/{created['id']}/make-default", headers=headers)
        assert response.status_code == 409 and "transactional" in response.json()["detail"]

    def test_the_default_cannot_be_marked_transactional(self, db, default_brand):
        default = profiles.default_profile(db, default_brand.id)
        with admin(db) as (cookied, headers):
            response = cookied.put(f"/brand-profiles/{default.id}",
                                   json={"name": default.name, "kind": "transactional",
                                         "field_values": dict(default.field_values)}, headers=headers)
        assert response.status_code == 409
        db.expire_all()
        assert db.get(BrandProfileDB, default.id).kind == "marketing"


# --- the send --------------------------------------------------------------------

def _recipient(db, label):
    recipient = RecipientDB(external_id=f"tx-{label}-{uuid.uuid4().hex[:6]}", status="active")
    db.add(recipient)
    db.flush()
    db.add(AddressabilityDB(recipient_id=recipient.id, channel="email",
                            value={"email": f"{label}-{uuid.uuid4().hex[:6]}@example.invalid"},
                            status="active", is_primary=True))
    db.commit()
    return recipient


@pytest.fixture
def world(db, default_brand):
    """A variant on a transactional profile, and an audience of four: one with
    no consent at all, one who opted out of marketing (CRM), one the provider
    suppressed after a bounce, one with a marketing opt-in."""
    brand = default_brand
    profile = BrandProfileDB(brand_id=brand.id, name=f"Receipts {uuid.uuid4().hex[:6]}",
                             kind="transactional", field_values=dict(LEGAL))
    db.add(profile)
    db.commit()
    campaign = create_campaign(db, name=f"Order mail {uuid.uuid4().hex[:6]}", brand_id=brand.id,
                               channel="email")
    variant = db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).one()
    variant.brand_profile_id = profile.id
    db.commit()
    set_envelope_fields(db, variant.id, {"subject": "Your order"}, brand_id=brand.id)
    create_module_for_variant(db, variant_id=variant.id, module_type="cta",
                              module_data={"label": "Track it", "url": "https://shop.test/track"},
                              brand_id=brand.id)
    people = {name: _recipient(db, name) for name in ("none", "crm_out", "bounced", "opted_in")}
    record_consent(db, people["crm_out"].id, "opted_out", brand.id, source="crm", purpose=MARKETING)
    record_consent(db, people["bounced"].id, "opted_out", brand.id, source="provider", purpose=MARKETING,
                   note="hard_bounce")
    record_consent(db, people["opted_in"].id, "opted_in", brand.id, source="crm", purpose=MARKETING)
    group = create_group(db, f"Buyers {uuid.uuid4().hex[:6]}", brand_id=brand.id)
    for person in people.values():
        add_member(db, group.id, person.id, brand_id=brand.id)
    made = {"snapshots": [], "sends": []}
    yield {"brand": brand, "variant": variant, "profile": profile, "people": people, "group": group,
           "made": made, "campaign": campaign}
    db.rollback()
    for send_id in made["sends"]:
        db.query(DeliveryExecutionDB).filter(DeliveryExecutionDB.send_instance_id == send_id).delete()
        db.query(SendInstanceDB).filter(SendInstanceDB.id == send_id).delete()
    db.query(SnapshotDB).filter(SnapshotDB.id.in_(made["snapshots"])).delete(synchronize_session=False)
    db.query(AudienceGroupMemberDB).filter(AudienceGroupMemberDB.group_id == group.id).delete()
    db.query(AudienceGroupDB).filter(AudienceGroupDB.id == group.id).delete()
    ids = [p.id for p in people.values()]
    db.query(ConsentEventDB).filter(ConsentEventDB.recipient_id.in_(ids)).delete(synchronize_session=False)
    db.query(AddressabilityDB).filter(AddressabilityDB.recipient_id.in_(ids)).delete(synchronize_session=False)
    db.query(RecipientDB).filter(RecipientDB.id.in_(ids)).delete(synchronize_session=False)
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant.id).delete()
    db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).delete()
    db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
    db.commit()


def _plan(db, world):
    from app.delivery.service import prepare_send_from_audience
    from app.snapshots.service import create_snapshot_for_variant

    snapshot = create_snapshot_for_variant(db, world["variant"].id, brand_id=world["brand"].id)
    world["made"]["snapshots"].append(snapshot.id)
    send = prepare_send_from_audience(db, snapshot.id, "Order mail", world["group"].id, "mock",
                                      brand_id=world["brand"].id)
    world["made"]["sends"].append(send.id)
    return send


def _executions(db, send):
    return {e.recipient_id: e for e in
            db.query(DeliveryExecutionDB).filter(DeliveryExecutionDB.send_instance_id == send.id)}


def test_planning_skips_the_opt_in_but_not_the_provider_suppression(db, world):
    send = _plan(db, world)
    people = world["people"]
    planned = _executions(db, send)
    assert set(planned) == {people["none"].id, people["crm_out"].id, people["opted_in"].id}, (
        "a marketing opt-out must not stop a receipt; a bounced address must")
    assert {e.purpose for e in planned.values()} == {TRANSACTIONAL}


def test_the_send_goes_out_without_unsubscribe_and_excludes_a_later_bounce(db, world, monkeypatch):
    from app.delivery.providers import mock as mock_module
    from app.delivery.service import send_send_instance
    from app.recipients.service import suppress_recipient

    send = _plan(db, world)
    people = world["people"]
    # Bounced after planning: the send-time stack must still catch it.
    suppress_recipient(db, people["none"].id, world["brand"].id, reason="hard_bounce",
                       purpose=TRANSACTIONAL)
    sent = []
    original = mock_module.MockProvider.send

    def capture(self, address, artifact):
        sent.append(artifact)
        return original(self, address, artifact)

    monkeypatch.setattr(mock_module.MockProvider, "send", capture)
    send_send_instance(db, send.id, brand_id=world["brand"].id)
    db.expire_all()
    executions = _executions(db, send)
    # The send re-resolves its audience first (ADR-176), whose floor already
    # leaves the provider-suppressed out, so the planned row is dropped; the
    # stack's own suppression stage is pinned below for sends without one.
    assert people["none"].id not in executions or executions[people["none"].id].status == "excluded"
    assert executions[people["crm_out"].id].status == "sent"
    assert len(sent) == 2
    for artifact in sent:
        assert "list_unsubscribe" not in (artifact.envelope or {})
        assert "/unsubscribe/" not in artifact.body and "Unsubscribe" not in artifact.body
        assert "Receipts GmbH" in artifact.body, "the legal details are on every email"


def test_a_marketing_send_still_needs_the_opt_in(db, world):
    """The same audience on a marketing profile: only the opted-in person."""
    world["variant"].brand_profile_id = profiles.default_profile(db, world["brand"].id).id
    db.commit()
    send = _plan(db, world)
    planned = _executions(db, send)
    assert set(planned) == {world["people"]["opted_in"].id}
    assert {e.purpose for e in planned.values()} == {MARKETING}


def test_the_approver_is_told_it_skips_the_opt_in(db, world):
    from app.approvals.actions.send_fire import describe

    send = _plan(db, world)
    described = describe(db, {"send_instance_id": send.id}, brand_id=world["brand"].id)
    assert any("opt-in" in w for w in described.warnings), described.warnings


def test_choosing_a_transactional_profile_is_audited_with_its_kind(db, world):
    with admin(db) as (cookied, headers):
        response = cookied.put(f"/campaigns/variants/{world['variant'].id}",
                               json={"name": "Variant A", "brand_profile_id": world["profile"].id},
                               headers=headers)
    assert response.status_code == 200, response.text
    entry = (db.query(AuditEventDB).filter(AuditEventDB.subject_type == "variant",
                                          AuditEventDB.subject_id == world["variant"].id)
             .order_by(AuditEventDB.id.desc()).first())
    assert entry.detail["brand_profile_kind"] == "transactional"


# --- provider suppression stops every send (ADR-195 point 2) -------------------

def test_a_bounce_on_a_receipt_also_stops_newsletters(db, world):
    """A dead address is dead either way: the opted-in person, bounced on a
    transactional mail, is not planned into a marketing send."""
    from app.recipients.service import suppress_recipient

    person = world["people"]["opted_in"]
    suppress_recipient(db, person.id, world["brand"].id, reason="hard_bounce", purpose=TRANSACTIONAL)
    world["variant"].brand_profile_id = profiles.default_profile(db, world["brand"].id).id
    db.commit()
    with pytest.raises(ValueError, match="0 consenting"):
        _plan(db, world)


def test_a_complaint_after_an_unsubscribe_is_still_recorded(db, world):
    """Otherwise the suppression rule has nothing to read, and receipts keep
    going to someone who complained."""
    from app.recipients.service import suppress_recipient

    person = world["people"]["crm_out"]          # already opted out of marketing, by the CRM
    suppress_recipient(db, person.id, world["brand"].id, reason="complaint", purpose=MARKETING)
    provider_events = (db.query(ConsentEventDB)
                       .filter(ConsentEventDB.recipient_id == person.id, ConsentEventDB.source == "provider")
                       .count())
    assert provider_events == 1
    # And a second report for the same cell adds nothing.
    suppress_recipient(db, person.id, world["brand"].id, reason="complaint", purpose=MARKETING)
    assert (db.query(ConsentEventDB)
            .filter(ConsentEventDB.recipient_id == person.id, ConsentEventDB.source == "provider")
            .count()) == 1
    planned = _executions(db, _plan(db, world))
    assert person.id not in planned


def test_the_stack_excludes_the_provider_suppressed_under_suppression(db, world):
    """Stage 3's first rule, on every purpose: the gate a send without an
    audience group relies on alone."""
    from app.delivery.exclusion import run_exclusion_stack

    people = world["people"]
    ids = {p.id for p in people.values()}
    for purpose in (TRANSACTIONAL, MARKETING):
        gate = run_exclusion_stack(db, ids, world["brand"].id, purpose=purpose)
        by_person = {e.recipient_id: e for e in gate.exclusions}
        assert by_person[people["bounced"].id].stage in (STAGE_SUPPRESSION, "consent")
        if purpose == TRANSACTIONAL:
            assert by_person[people["bounced"].id].stage == STAGE_SUPPRESSION
            assert gate.eligible == {people["none"].id, people["crm_out"].id, people["opted_in"].id}
        else:
            assert gate.eligible == {people["opted_in"].id}


def test_a_test_send_of_a_transactional_profile_has_no_unsubscribe_line(db, world, monkeypatch):
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
    assert "Receipts GmbH" in body and "Unsubscribe" not in body
