"""A variant's envelope arrives, and blank means empty (task-250, task-48).

`POST /campaigns/{id}/variants` accepted `subject` and `preheader` and never
passed them on, so they were lost without an error. And only the Jinja forms
trimmed whitespace: over JSON, `" "` was stored as a subject. Trimming now
happens in `set_envelope_fields`, the one place every path writes the envelope
through (ADR-162 point 1).

**Since task-48 the API carries `envelope`, a map of the fields the channel's
manifest declares**, not `subject`/`preheader`: those are email's envelope
fields, and a variant of any channel answered with them — a push variant with
two nulls. Email's map holds subject and preheader; push's is empty.
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
    with editor([CAMPAIGNS_MANAGE]) as headers:
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


def _update(variant_id, **body):
    with editor([CAMPAIGNS_MANAGE]) as headers:
        response = client.put(f"/campaigns/variants/{variant_id}", json={"name": "B", **body}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_the_envelope_given_at_creation_is_kept(db, campaign):
    created = _create(campaign, envelope={"subject": "Spring is here", "preheader": "Three new routes"})
    assert created["envelope"] == {"subject": "Spring is here", "preheader": "Three new routes"}
    assert _envelope(db, created["id"]) == {"subject": "Spring is here", "preheader": "Three new routes"}


def test_a_variant_answers_with_its_envelope_never_with_email_field_names(campaign):
    created = _create(campaign, envelope={"subject": "Spring"})
    assert "subject" not in created and "preheader" not in created
    assert created["envelope"] == {"subject": "Spring"}


def test_whitespace_is_trimmed_and_blank_is_empty_on_create(db, campaign):
    created = _create(campaign, envelope={"subject": "  Spring  ", "preheader": "   "})
    assert _envelope(db, created["id"]) == {"subject": "Spring"}


def test_whitespace_only_on_update_clears_the_envelope(db, campaign):
    created = _create(campaign, envelope={"subject": "Spring", "preheader": "Peek"})
    updated = _update(created["id"], envelope={"subject": " ", "preheader": "\t"})
    assert updated["envelope"] == {}
    assert _envelope(db, created["id"]) is None


def test_an_update_without_an_envelope_leaves_it_alone(db, campaign):
    """Renaming is not clearing: the envelope is replaced only when sent."""
    created = _create(campaign, envelope={"subject": "Spring", "preheader": "Peek"})
    updated = _update(created["id"], name="Renamed")
    assert (updated["name"], updated["envelope"]) == ("Renamed", {"subject": "Spring", "preheader": "Peek"})


def test_a_variant_created_without_one_has_no_envelope(db, campaign):
    created = _create(campaign)
    assert created["envelope"] == {} and _envelope(db, created["id"]) is None


def test_a_push_variant_has_an_empty_envelope_and_ignores_fields_it_does_not_declare(campaign):
    created = _create(campaign, channel="push", envelope={"subject": "Not a push field"})
    assert created["envelope"] == {}
    assert _update(created["id"], envelope={"subject": "Still not"})["envelope"] == {}


def test_the_audit_entry_records_the_envelope(db, campaign):
    from app.audit import service as audit
    from app.audit.db_models import AuditEventDB

    created = _create(campaign, envelope={"subject": "Spring"})
    _update(created["id"], envelope={"subject": "Summer"})
    entry = (db.query(AuditEventDB)
             .filter(AuditEventDB.action == audit.VARIANT_UPDATED, AuditEventDB.subject_id == created["id"])
             .order_by(AuditEventDB.id.desc()).first())
    assert entry.detail == {"name": "B", "envelope": {"subject": "Summer"}}


@pytest.fixture
def jinja(db, default_brand):
    """A signed-in person on the Jinja plane, whose variant forms are email's."""
    from app.auth import service as auth
    from sqlalchemy import text

    user = auth.create_user(db, email=f"env-{uuid.uuid4().hex[:6]}@example.invalid",
                            role_key="admin", brand_id=default_brand.id)
    token = auth.create_session(db, user)
    browser = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
    browser.cookies.set(auth.SESSION_COOKIE, token)
    yield browser, auth.csrf_token_for(token)
    db.rollback()
    for table in ("audit_events", "login_codes", "auth_sessions", "role_assignments"):
        column = "actor_id" if table == "audit_events" else "user_id"
        db.execute(text(f"DELETE FROM {table} WHERE {column} = :u"), {"u": user.id})
    db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
    db.commit()


def test_the_jinja_forms_subject_and_preheader_reach_the_envelope(db, campaign, jinja):
    browser, csrf = jinja
    created = browser.post(f"/ui/campaigns/{campaign.id}/variants",
                           data={"name": "J", "channel": "email", "subject": "From the form",
                                 "preheader": "", "csrf_token": csrf})
    assert created.status_code == 303, created.text
    variant = db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).one()
    assert _envelope(db, variant.id) == {"subject": "From the form"}
    edited = browser.post(f"/ui/campaigns/{campaign.id}/variants/{variant.id}/edit",
                          data={"name": "J", "subject": "Edited", "preheader": "Peek", "csrf_token": csrf})
    assert edited.status_code == 303, edited.text
    assert _envelope(db, variant.id) == {"subject": "Edited", "preheader": "Peek"}
