"""Every composer write is audited, on both planes (task-252, ADR-153 point 4).

Only the two duplicates were. Each case below makes one write as a machine
over JSON and as a person through the Jinja form, then finds the entry: the
action, the subject, and the actor the plane resolves (the integration, or the
signed-in user). An override reset is the one that also answers "who reset
it", which nothing recorded before.

A module delete names the overrides it erased — the design pass's D2 kept the
erase and moved the history into this log.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.audit import service as audit
from app.audit.db_models import AuditEventDB
from app.auth import service as auth
from app.auth.permissions import CAMPAIGNS_MANAGE, OVERRIDES_MANAGE
from app.campaigns.db_models import CampaignDB, DecisionSlotDB, ModuleInstanceDB, VariantDB
from app.content.db_models import ContentRecordDB
from app.overrides.db_models import ContentOverrideDB
from main import app
from tests.machine import machine

api = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def world(db, default_brand):
    """A campaign with a variant, a record-bound module carrying an active
    override, a second module to move, and a slot."""
    campaign = CampaignDB(brand_id=default_brand.id, name=f"aud-{uuid.uuid4().hex[:6]}")
    db.add(campaign); db.flush()
    variant = VariantDB(campaign_id=campaign.id, channel="email", name="v", status="draft")
    record = ContentRecordDB(title="r", content={"headline_medium": "H"}, status="active",
                             brand_id=default_brand.id)
    db.add_all([variant, record]); db.flush()
    bound = ModuleInstanceDB(variant_id=variant.id, module_type="img_left", position=1,
                             content_record_id=record.id)
    other = ModuleInstanceDB(variant_id=variant.id, module_type="cta", position=2, module_data={})
    slot = DecisionSlotDB(variant_id=variant.id, name="s", decision_type="content_recommendation",
                          decision_strategy="top_score")
    db.add_all([bound, other, slot]); db.flush()
    override = ContentOverrideDB(module_instance_id=bound.id, field_overrides={"headline_medium": "X"},
                                 overridden_by="t", active=True)
    db.add(override); db.commit()
    world = {"campaign": campaign, "variant": variant, "record": record, "bound": bound,
             "other": other, "slot": slot, "override": override, "created_campaigns": []}
    yield world
    db.rollback()
    campaign_ids = [campaign.id, *world["created_campaigns"]]
    variant_ids = [v.id for v in db.query(VariantDB).filter(VariantDB.campaign_id.in_(campaign_ids))]
    module_ids = [m.id for m in db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id.in_(variant_ids))]
    db.query(ContentOverrideDB).filter(ContentOverrideDB.module_instance_id.in_(module_ids)).delete(
        synchronize_session=False)
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.id.in_(module_ids)).delete(synchronize_session=False)
    db.query(DecisionSlotDB).filter(DecisionSlotDB.variant_id.in_(variant_ids)).delete(
        synchronize_session=False)
    db.query(VariantDB).filter(VariantDB.id.in_(variant_ids)).delete(synchronize_session=False)
    db.query(CampaignDB).filter(CampaignDB.id.in_(campaign_ids)).delete(synchronize_session=False)
    db.query(ContentRecordDB).filter(ContentRecordDB.id == record.id).delete()
    db.commit()


@pytest.fixture
def person(db, default_brand):
    user = auth.create_user(db, email=f"aud-{uuid.uuid4().hex[:8]}@example.invalid",
                            role_key="admin", brand_id=default_brand.id)
    token = auth.create_session(db, user)
    page = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
    page.cookies.set(auth.SESSION_COOKIE, token)
    yield page, auth.csrf_token_for(token), user
    db.rollback()
    db.query(AuditEventDB).filter(AuditEventDB.actor_type == audit.ACTOR_USER,
                                  AuditEventDB.actor_id == user.id).delete()
    for table in ("login_codes", "auth_sessions", "role_assignments"):
        db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
    db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
    db.commit()


# --- each write, once per plane ---------------------------------------------
# A case returns (action, subject_id). `j` posts a Jinja form with the CSRF
# token; `h` is the machine's headers.

def _ui(w):
    return f"/ui/campaigns/{w['campaign'].id}/variants/{w['variant'].id}"


def campaign_created(w, plane, call):
    name = f"aud-new-{uuid.uuid4().hex[:6]}"
    if plane == "json":
        body = call("post", "/campaigns/", json={"name": name, "channel": "email"}).json()
        cid = body["id"]
    else:
        location = call("post", "/ui/campaigns", data={"name": name, "channel": "email"}).headers["location"]
        cid = int(location.rsplit("/", 1)[1])
    w["created_campaigns"].append(cid)
    return audit.CAMPAIGN_CREATED, cid


def variant_created(w, plane, call, db):
    before = {v.id for v in db.query(VariantDB).filter(VariantDB.campaign_id == w["campaign"].id)}
    if plane == "json":
        call("post", f"/campaigns/{w['campaign'].id}/variants", json={"name": "B", "channel": "email"})
    else:
        call("post", f"/ui/campaigns/{w['campaign'].id}/variants", data={"name": "B", "channel": "email"})
    db.expire_all()
    [new] = {v.id for v in db.query(VariantDB).filter(VariantDB.campaign_id == w["campaign"].id)} - before
    return audit.VARIANT_CREATED, new


def variant_updated(w, plane, call):
    vid = w["variant"].id
    if plane == "json":
        call("put", f"/campaigns/variants/{vid}", json={"name": "renamed", "envelope": {"subject": "S"}})
    else:
        call("post", f"{_ui(w)}/edit", data={"name": "renamed", "subject": "S"})
    return audit.VARIANT_UPDATED, vid


def module_created(w, plane, call, db):
    if plane == "json":
        call("post", f"/campaigns/variants/{w['variant'].id}/modules", json={"module_type": "editorial"})
    else:
        call("post", f"{_ui(w)}/modules", data={"module_type": "editorial"})
    db.expire_all()
    new = db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == w["variant"].id,
                                            ModuleInstanceDB.module_type == "editorial").one()
    return audit.MODULE_CREATED, new.id


def module_updated(w, plane, call):
    mid = w["other"].id
    if plane == "json":
        call("put", f"/campaigns/modules/{mid}", json={"module_type": "cta", "module_data": {"label": "Go"}})
    else:
        call("post", f"{_ui(w)}/modules/{mid}/edit", data={"module_type": "cta", "module_data_json": '{"label": "Go"}'})
    return audit.MODULE_UPDATED, mid


def module_deleted(w, plane, call):
    mid = w["bound"].id
    if plane == "json":
        call("delete", f"/campaigns/modules/{mid}")
    else:
        call("post", f"{_ui(w)}/modules/{mid}/delete")
    return audit.MODULE_DELETED, mid


def module_moved(w, plane, call):
    mid = w["other"].id
    if plane == "json":
        call("post", f"/campaigns/modules/{mid}/move?direction=up")
    else:
        call("post", f"{_ui(w)}/modules/{mid}/move", data={"direction": "up"})
    return audit.MODULE_MOVED, mid


def slot_created(w, plane, call, db):
    if plane == "json":
        call("post", f"/campaigns/variants/{w['variant'].id}/decision-slots", json={"name": "new"})
    else:
        call("post", f"{_ui(w)}/decision-slots", data={"name": "new"})
    db.expire_all()
    new = db.query(DecisionSlotDB).filter(DecisionSlotDB.variant_id == w["variant"].id,
                                          DecisionSlotDB.name == "new").one()
    return audit.DECISION_SLOT_CREATED, new.id


def slot_updated(w, plane, call):
    sid = w["slot"].id
    if plane == "json":
        call("patch", f"/campaigns/decision-slots/{sid}", json={"candidate_filter": {"category_ids": [1]}})
    else:
        call("post", f"/ui/decisions/slots/{sid}/edit", data={"decision_strategy": "top_score"})
    return audit.DECISION_SLOT_UPDATED, sid


def slot_replaced(w, plane, call):
    """PUT, the JSON plane's second slot write (the Jinja edit is the case above)."""
    sid = w["slot"].id
    call("put", f"/campaigns/decision-slots/{sid}", json={"decision_strategy": "top_score"})
    return audit.DECISION_SLOT_UPDATED, sid


def override_reset(w, plane, call):
    oid = w["override"].id
    if plane == "json":
        call("post", f"/overrides/{oid}/reset")
    else:
        call("post", f"/ui/campaigns/{w['campaign'].id}/overrides/{oid}/reset")
    return audit.OVERRIDE_RESET, oid


def override_created(w, plane, call, db):
    db.query(ContentOverrideDB).filter(ContentOverrideDB.id == w["override"].id).update({"active": False})
    db.commit()
    mid = w["bound"].id
    if plane == "json":
        call("post", "/overrides/", json={"module_instance_id": mid, "field_overrides": {"headline_medium": "Y"}})
    else:
        call("post", f"{_ui(w)}/overrides",
             data={"module_instance_id": mid, "field_overrides_json": '{"headline_medium": "Y"}'})
    db.expire_all()
    new = db.query(ContentOverrideDB).filter(ContentOverrideDB.module_instance_id == mid,
                                             ContentOverrideDB.active.is_(True)).one()
    return audit.OVERRIDE_CREATED, new.id


def apply_subject(w, plane, call):
    """The Jinja plane's AI-suggestion apply is a variant edit too."""
    vid = w["variant"].id
    call("post", f"{_ui(w)}/apply-subject", data={"subject": "Picked"})
    return audit.VARIANT_UPDATED, vid


NEEDS_DB = {variant_created, module_created, slot_created, override_created}
CASES = [
    campaign_created, variant_created, variant_updated, module_created, module_updated,
    module_deleted, module_moved, slot_created, slot_updated, override_reset, override_created,
]
PARAMS = ([pytest.param(c, "json", id=f"json-{c.__name__}") for c in [*CASES, slot_replaced]]
          + [pytest.param(c, "jinja", id=f"jinja-{c.__name__}") for c in [*CASES, apply_subject]])


@pytest.mark.parametrize("case,plane", PARAMS)
def test_the_write_is_audited_with_its_actor(db, world, person, case, plane):
    page, csrf, user = person

    def run(call):
        args = (world, plane, call, db) if case in NEEDS_DB else (world, plane, call)
        return case(*args)

    if plane == "json":
        with machine([CAMPAIGNS_MANAGE, OVERRIDES_MANAGE]) as headers:
            def call(method, url, **kw):
                response = getattr(api, method)(url, headers=headers, **kw)
                assert response.status_code < 300, response.text
                return response
            action, subject_id = run(call)
            entries = db.query(AuditEventDB).filter(
                AuditEventDB.action == action, AuditEventDB.subject_id == subject_id,
                AuditEventDB.actor_type == audit.ACTOR_INTEGRATION).all()
    else:
        def call(method, url, data=None, **kw):
            response = page.post(url, data={"csrf_token": csrf, **(data or {})})
            assert response.status_code == 303, response.text[:300]
            assert "error=" not in response.headers["location"], response.headers["location"]
            return response
        action, subject_id = run(call)
        entries = db.query(AuditEventDB).filter(
            AuditEventDB.action == action, AuditEventDB.subject_id == subject_id,
            AuditEventDB.actor_type == audit.ACTOR_USER, AuditEventDB.actor_id == user.id).all()
    try:
        assert len(entries) == 1, f"{action} for {subject_id}: {len(entries)} entries"
    finally:
        db.query(AuditEventDB).filter(AuditEventDB.action == action,
                                      AuditEventDB.subject_id == subject_id).delete()
        db.commit()


def test_a_module_delete_names_the_overrides_it_erased(db, world, person):
    page, csrf, user = person
    w = world
    module_id, override_id = w["bound"].id, w["override"].id  # both rows are gone after
    page.post(f"{_ui(w)}/modules/{module_id}/delete", data={"csrf_token": csrf})
    entry = db.query(AuditEventDB).filter(AuditEventDB.action == audit.MODULE_DELETED,
                                          AuditEventDB.subject_id == module_id).one()
    try:
        [removed] = entry.detail["overrides_removed"]
        assert removed["id"] == override_id
        assert removed["field_overrides"] == {"headline_medium": "X"}
    finally:
        db.delete(entry); db.commit()


def test_a_reset_records_the_fields_it_reverted_and_who_reset_them(db, world, person):
    page, csrf, user = person
    oid = world["override"].id
    page.post(f"/ui/campaigns/{world['campaign'].id}/overrides/{oid}/reset", data={"csrf_token": csrf})
    entry = db.query(AuditEventDB).filter(AuditEventDB.action == audit.OVERRIDE_RESET,
                                          AuditEventDB.subject_id == oid).one()
    try:
        assert (entry.actor_type, entry.actor_id) == (audit.ACTOR_USER, user.id)
        assert entry.detail["field_overrides"] == {"headline_medium": "X"}
    finally:
        db.delete(entry); db.commit()


def test_a_refused_write_is_not_audited(db, world):
    with machine([CAMPAIGNS_MANAGE]) as headers:
        response = api.post(f"/campaigns/variants/{world['variant'].id}/modules",
                            json={"module_type": "header"}, headers=headers)
    assert response.status_code == 400
    assert db.query(AuditEventDB).filter(
        AuditEventDB.action == audit.MODULE_CREATED,
        AuditEventDB.detail["variant_id"].as_integer() == world["variant"].id).count() == 0
