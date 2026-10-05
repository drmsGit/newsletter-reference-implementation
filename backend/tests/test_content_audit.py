"""Every content write is audited, on both planes (task-275, ADR-153 point 4).

Only edits, publishing and duplicating were. Create, status, delete and the
category assignments — which feed slot ranking and every interest profile
(ADR-080) — wrote nothing. Each case below makes one write as a machine over
JSON and as a person through the Jinja form, then finds the entry: the action,
the record, and the actor the plane resolves. The detail tests pin what an
entry has to say to be worth having.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.audit import service as audit
from app.audit.db_models import AuditEventDB
from app.auth import service as auth
from app.auth.permissions import CONTENT_MANAGE
from app.campaigns.db_models import CampaignDB, ModuleInstanceDB, VariantDB
from app.content.db_models import (
    CategoryDB, ContentCategoryAssignmentDB, ContentRecordDB, ContentVersionDB,
)
from main import app
from tests.machine import machine

api = TestClient(app, raise_server_exceptions=False)
TAG = f"caud{uuid.uuid4().hex[:6]}"


@pytest.fixture
def world(db, default_brand):
    """A record with one category assigned and a version, a module bound to
    it, and a second category free to assign."""
    record = ContentRecordDB(title=f"{TAG} record", content={"headline_medium": "H"},
                             status="active", brand_id=default_brand.id)
    assigned, free = CategoryDB(name=f"{TAG} assigned"), CategoryDB(name=f"{TAG} free")
    campaign = CampaignDB(brand_id=default_brand.id, name=f"{TAG} campaign")
    db.add_all([record, assigned, free, campaign]); db.flush()
    variant = VariantDB(campaign_id=campaign.id, channel="email", name="v", status="draft")
    db.add(variant); db.flush()
    module = ModuleInstanceDB(variant_id=variant.id, module_type="img_left", position=1,
                              content_record_id=record.id)
    assignment = ContentCategoryAssignmentDB(content_id=record.id, category_id=assigned.id, score=7)
    db.add_all([module, assignment,
                ContentVersionDB(content_record_id=record.id, version_number=1, content={})])
    db.commit()
    w = {"record_id": record.id, "assignment_id": assignment.id, "module_id": module.id,
         "free_id": free.id, "assigned_id": assigned.id, "created": []}
    # Ids now: a case may delete the record, and its expired instance cannot
    # be read afterwards.
    record_id, variant_id, campaign_id = record.id, variant.id, campaign.id
    category_ids = [assigned.id, free.id]
    yield w
    db.rollback()
    ids = [record_id, *w["created"]]
    db.query(AuditEventDB).filter(AuditEventDB.subject_type == "content",
                                  AuditEventDB.subject_id.in_(ids)).delete(synchronize_session=False)
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant_id).delete()
    db.query(VariantDB).filter(VariantDB.id == variant_id).delete()
    db.query(CampaignDB).filter(CampaignDB.id == campaign_id).delete()
    db.query(ContentCategoryAssignmentDB).filter(ContentCategoryAssignmentDB.content_id.in_(ids)).delete(
        synchronize_session=False)
    db.query(ContentVersionDB).filter(ContentVersionDB.content_record_id.in_(ids)).delete(
        synchronize_session=False)
    db.query(ContentRecordDB).filter(ContentRecordDB.id.in_(ids)).delete(synchronize_session=False)
    db.query(CategoryDB).filter(CategoryDB.id.in_(category_ids)).delete(synchronize_session=False)
    db.commit()


@pytest.fixture
def person(db, default_brand):
    user = auth.create_user(db, email=f"{TAG}-{uuid.uuid4().hex[:6]}@example.invalid",
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
# A case makes the write through `call` and returns (action, record id).

def created(w, plane, call):
    title = f"{TAG} new {uuid.uuid4().hex[:4]}"
    if plane == "json":
        rid = call("post", "/content/", json={"title": title, "content": {}}).json()["id"]
    else:
        location = call("post", "/ui/content", data={"title": title, "headline_medium": "H"}).headers["location"]
        rid = int(location.rsplit("/", 1)[1])
    w["created"].append(rid)
    return audit.CONTENT_CREATED, rid


def status_changed(w, plane, call):
    rid = w["record_id"]
    if plane == "json":
        call("put", f"/content/{rid}/status", json={"status": "inactive"})
    else:
        call("post", f"/ui/content/{rid}/set-status", data={"status": "inactive"})
    return audit.CONTENT_STATUS_CHANGED, rid


def deleted(w, plane, call):
    rid = w["record_id"]
    if plane == "json":
        call("delete", f"/content/{rid}?force=true")
    else:
        call("post", f"/ui/content/{rid}/delete", data={"force": "true"})
    return audit.CONTENT_DELETED, rid


def category_assigned(w, plane, call):
    rid = w["record_id"]
    if plane == "json":
        call("post", f"/content/{rid}/categories", json={"category_id": w["free_id"], "score": 4})
    else:
        call("post", f"/ui/content/{rid}/assign-category", data={"category_id": w["free_id"], "score": 4})
    return audit.CONTENT_CATEGORY_ASSIGNED, rid


def category_unassigned(w, plane, call):
    rid, aid = w["record_id"], w["assignment_id"]
    if plane == "json":
        call("delete", f"/content/{rid}/assignments/{aid}")
    else:
        call("post", f"/ui/content/{rid}/categories/{aid}/delete")
    return audit.CONTENT_CATEGORY_UNASSIGNED, rid


CASES = [created, status_changed, deleted, category_assigned, category_unassigned]


def _entries(db, action, subject_id, actor_type, actor_id=None):
    query = db.query(AuditEventDB).filter(
        AuditEventDB.action == action, AuditEventDB.subject_type == "content",
        AuditEventDB.subject_id == subject_id, AuditEventDB.actor_type == actor_type)
    if actor_id is not None:
        query = query.filter(AuditEventDB.actor_id == actor_id)
    return query.all()


def _json_call(headers):
    def call(method, url, **kw):
        response = getattr(api, method)(url, headers=headers, **kw)
        assert response.status_code < 300, response.text
        return response
    return call


def _jinja_call(page, csrf):
    def call(method, url, data=None):
        response = page.post(url, data={"csrf_token": csrf, **(data or {})})
        assert response.status_code == 303, response.text[:300]
        assert "error=" not in response.headers["location"], response.headers["location"]
        return response
    return call


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.__name__)
@pytest.mark.parametrize("plane", ["json", "jinja"])
def test_the_write_is_audited_with_its_actor(db, world, person, case, plane):
    page, csrf, user = person
    if plane == "json":
        with machine([CONTENT_MANAGE]) as headers:
            action, rid = case(world, plane, _json_call(headers))
            entries = _entries(db, action, rid, audit.ACTOR_INTEGRATION)
    else:
        action, rid = case(world, plane, _jinja_call(page, csrf))
        entries = _entries(db, action, rid, audit.ACTOR_USER, user.id)
    assert len(entries) == 1, f"{action} for content {rid}: {len(entries)} entries"


# --- what an entry says ------------------------------------------------------

def test_a_forced_delete_names_what_it_took_with_it(db, world, person):
    page, csrf, _ = person
    w = world
    _jinja_call(page, csrf)("post", f"/ui/content/{w['record_id']}/delete", data={"force": "true"})
    [entry] = db.query(AuditEventDB).filter(AuditEventDB.action == audit.CONTENT_DELETED,
                                            AuditEventDB.subject_id == w["record_id"]).all()
    assert entry.detail == {
        "title": f"{TAG} record", "category_assignments": 1, "versions": 1,
        "modules_unbound": [w["module_id"]], "forced": True,
    }


def test_a_status_change_says_from_and_to_and_a_repeat_says_nothing(db, world):
    rid = world["record_id"]
    with machine([CONTENT_MANAGE]) as headers:
        call = _json_call(headers)
        call("put", f"/content/{rid}/status", json={"status": "inactive"})
        call("put", f"/content/{rid}/status", json={"status": "inactive"})
        entries = _entries(db, audit.CONTENT_STATUS_CHANGED, rid, audit.ACTOR_INTEGRATION)
    assert [(e.detail["from"], e.detail["to"]) for e in entries] == [("active", "inactive")]


def test_an_unassign_records_the_category_and_the_score_it_had(db, world):
    w = world
    with machine([CONTENT_MANAGE]) as headers:
        _json_call(headers)("delete", f"/content/{w['record_id']}/assignments/{w['assignment_id']}")
        [entry] = _entries(db, audit.CONTENT_CATEGORY_UNASSIGNED, w["record_id"], audit.ACTOR_INTEGRATION)
    assert entry.detail == {"category_id": w["assigned_id"], "category": f"{TAG} assigned", "score": 7}


@pytest.mark.parametrize("plane", ["json", "jinja"])
def test_an_edit_records_only_the_fields_it_changed(db, world, person, plane):
    """The API listed every key sent, unchanged ones too; the Jinja form listed
    every key on the record. Both record what changed (task-275)."""
    page, csrf, user = person
    rid = world["record_id"]
    if plane == "json":
        with machine([CONTENT_MANAGE]) as headers:
            _json_call(headers)("patch", f"/content/{rid}", json={
                "content": {"headline_medium": "H", "body_medium": "New body"}, "groups": ["email"]})
            [entry] = _entries(db, audit.CONTENT_UPDATED, rid, audit.ACTOR_INTEGRATION)
    else:
        _jinja_call(page, csrf)("post", f"/ui/content/{rid}/edit", data={
            "title": f"{TAG} record", "headline_medium": "H", "body_medium": "New body"})
        [entry] = _entries(db, audit.CONTENT_UPDATED, rid, audit.ACTOR_USER, user.id)
    assert entry.detail["fields"] == ["body_medium"]
