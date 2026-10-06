"""A module's hidden fields: stored, set by a person, honoured everywhere
(task-290).

ADR-187, decided with the user 2026-10-05/06: the manager's choice is a list
of hidden field names on the module in the variant; a person sets it through
its own route, an integration never does (in either direction); it survives
re-binding, copies with the variant, and a type change keeps only what the new
type still marks hideable. A hidden field reaches the template as empty and
the value stays where it is. "Required" means "required when shown": the send
check, the editor's module states and slot candidacy skip a hidden field. The
frame records the list; a frame without it means nothing hidden.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.audit import service as audit
from app.audit.db_models import AuditEventDB
from app.auth import service as auth
from app.auth.permissions import CAMPAIGNS_MANAGE
from app.campaigns import duplication
from app.campaigns.db_models import (
    CampaignDB, DecisionResolutionDB, DecisionSlotDB, ModuleInstanceDB, VariantDB,
)
from app.campaigns.service import slot_candidate_count
from app.content.db_models import (
    CategoryDB, ContentCategoryAssignmentDB, ContentChannelReadinessDB, ContentRecordDB, ContentVersionDB,
)
from app.rendering import frame as frames
from app.rendering.service import missing_required_fields, module_states, render_variant_html
from main import app
from tests.machine import machine

TAG = f"hid{uuid.uuid4().hex[:6]}"
LISBON = {"headline_medium": "Lisbon in spring", "body_medium": "Three days by the river.",
          "button_label": "Read more", "button_url": "https://example.com/lisbon"}


@pytest.fixture
def world(db, default_brand):
    """An email variant with one Image Left module bound to a published record,
    and a second published record to re-bind to."""
    b = default_brand.id
    campaign = CampaignDB(brand_id=b, name=f"{TAG}-campaign")
    db.add(campaign); db.flush()
    variant = VariantDB(campaign_id=campaign.id, channel="email", name="A", status="draft")
    records = [ContentRecordDB(title=f"{TAG} {i}", content=dict(LISBON), status="active", brand_id=b,
                               machine_ready=True) for i in range(2)]
    db.add_all([variant, *records]); db.flush()
    for record in records:
        db.add(ContentVersionDB(content_record_id=record.id, version_number=1, content=dict(LISBON),
                                created_by="test"))
    module = ModuleInstanceDB(variant_id=variant.id, module_type="img_left", position=1,
                              content_record_id=records[0].id)
    db.add(module); db.commit()
    made = {"campaigns": [campaign.id], "records": [r.id for r in records], "slots": [], "categories": []}
    yield {"variant": variant, "module": module, "records": records, "campaign": campaign,
           "brand": b, "made": made}
    db.rollback()
    variants = [v for (v,) in db.query(VariantDB.id).filter(VariantDB.campaign_id.in_(made["campaigns"]))]
    modules = [m for (m,) in db.query(ModuleInstanceDB.id).filter(ModuleInstanceDB.variant_id.in_(variants))]
    db.query(AuditEventDB).filter(AuditEventDB.subject_type == "module",
                                  AuditEventDB.subject_id.in_(modules)).delete(synchronize_session=False)
    db.query(DecisionResolutionDB).filter(DecisionResolutionDB.decision_slot_id.in_(made["slots"])).delete(
        synchronize_session=False)
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id.in_(variants)).delete(synchronize_session=False)
    db.query(DecisionSlotDB).filter(DecisionSlotDB.variant_id.in_(variants)).delete(synchronize_session=False)
    db.query(VariantDB).filter(VariantDB.id.in_(variants)).delete(synchronize_session=False)
    db.query(CampaignDB).filter(CampaignDB.id.in_(made["campaigns"])).delete(synchronize_session=False)
    for model, column in ((ContentChannelReadinessDB, ContentChannelReadinessDB.content_id),
                          (ContentCategoryAssignmentDB, ContentCategoryAssignmentDB.content_id),
                          (ContentVersionDB, ContentVersionDB.content_record_id),
                          (ContentRecordDB, ContentRecordDB.id)):
        db.query(model).filter(column.in_(made["records"])).delete(synchronize_session=False)
    db.query(CategoryDB).filter(CategoryDB.id.in_(made["categories"])).delete(synchronize_session=False)
    db.commit()


@pytest.fixture
def person(db, default_brand):
    """A signed-in person on the JSON plane, as the React client is."""
    user = auth.create_user(db, email=f"{TAG}-{uuid.uuid4().hex[:6]}@example.invalid",
                            role_key="admin", brand_id=default_brand.id)
    token = auth.create_session(db, user)
    client = TestClient(app, raise_server_exceptions=False)
    client.cookies.set(auth.SESSION_COOKIE, token)
    yield client, {"X-CSRF-Token": auth.csrf_token_for(token)}
    db.rollback()
    db.execute(text("DELETE FROM audit_events WHERE actor_id = :u AND actor_type = 'user'"), {"u": user.id})
    for table in ("login_codes", "auth_sessions", "role_assignments"):
        db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
    db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
    db.commit()


def _hide(client, csrf, module, fields, token=None):
    headers = {**csrf, "If-Match": token or module.updated_at.isoformat()}
    return client.put(f"/campaigns/modules/{module.id}/hidden-fields", json={"hidden_fields": fields},
                      headers=headers)


def _stored(db, module_id):
    db.expire_all()
    return db.get(ModuleInstanceDB, module_id).hidden_fields


class TestAPersonHides:
    def test_it_stores_the_list_moves_the_version_and_is_audited(self, db, world, person):
        client, csrf = person
        module = world["module"]
        response = _hide(client, csrf, module, ["body_medium"])
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["hidden_fields"] == ["body_medium"]
        assert body["updated_at"] != module.updated_at.isoformat()
        assert _stored(db, module.id) == ["body_medium"]
        [entry] = db.query(AuditEventDB).filter(AuditEventDB.action == audit.MODULE_FIELDS_HIDDEN,
                                                AuditEventDB.subject_id == module.id).all()
        assert (entry.detail["from"], entry.detail["to"]) == ([], ["body_medium"])

    def test_showing_again_is_an_empty_list(self, db, world, person):
        client, csrf = person
        token = _hide(client, csrf, world["module"], ["body_medium"]).json()["updated_at"]
        assert _hide(client, csrf, world["module"], [], token).json()["hidden_fields"] == []

    def test_a_stale_version_is_refused(self, db, world, person):
        client, csrf = person
        response = _hide(client, csrf, world["module"], ["body_medium"], "2020-01-01T00:00:00+00:00")
        assert response.status_code == 409
        assert _stored(db, world["module"].id) == []

    @pytest.mark.parametrize("field", ["button_url", "image_alt", "no_such_field"])
    def test_a_field_the_module_does_not_mark_hideable_is_refused_by_name(self, db, world, person, field):
        client, csrf = person
        response = _hide(client, csrf, world["module"], ["body_medium", field])
        assert response.status_code == 422
        assert field in response.text
        assert _stored(db, world["module"].id) == []

    def test_another_brands_module_is_not_found(self, world, foreign_api):
        with foreign_api([CAMPAIGNS_MANAGE]) as headers:
            response = TestClient(app, raise_server_exceptions=False).put(
                f"/campaigns/modules/{world['module'].id}/hidden-fields",
                json={"hidden_fields": []}, headers=headers)
        assert response.status_code == 404


class TestAMachine:
    def test_it_may_neither_hide_nor_show(self, db, world):
        api = TestClient(app, raise_server_exceptions=False)
        with machine([CAMPAIGNS_MANAGE]) as headers:
            assert api.put(f"/campaigns/modules/{world['module'].id}/hidden-fields",
                           json={"hidden_fields": ["body_medium"]}, headers=headers).status_code == 403
        db.query(ModuleInstanceDB).filter_by(id=world["module"].id).update({"hidden_fields": ["body_medium"]})
        db.commit()
        with machine([CAMPAIGNS_MANAGE]) as headers:
            assert api.put(f"/campaigns/modules/{world['module'].id}/hidden-fields",
                           json={"hidden_fields": []}, headers=headers).status_code == 403
        assert _stored(db, world["module"].id) == ["body_medium"]


class TestItIsALayoutChoice:
    def _set(self, db, module, fields):
        db.query(ModuleInstanceDB).filter_by(id=module.id).update({"hidden_fields": fields})
        db.commit()

    def test_re_binding_the_record_keeps_it(self, db, world, person):
        client, csrf = person
        self._set(db, world["module"], ["body_medium"])
        db.expire_all()
        module = db.get(ModuleInstanceDB, world["module"].id)
        response = client.put(f"/campaigns/modules/{module.id}", headers={**csrf, "If-Match": module.updated_at.isoformat()},
                              json={"module_type": "img_left", "content_record_id": world["records"][1].id})
        assert response.status_code == 200, response.text
        assert response.json()["hidden_fields"] == ["body_medium"]

    @pytest.mark.parametrize("new_type, kept", [("img_right", ["body_medium", "button_label"]), ("cta", [])])
    def test_a_type_change_keeps_only_what_the_new_type_marks_hideable(self, db, world, person, new_type, kept):
        client, csrf = person
        self._set(db, world["module"], ["body_medium", "button_label"])
        db.expire_all()
        module = db.get(ModuleInstanceDB, world["module"].id)
        body = {"module_type": new_type}
        if new_type == "cta":
            body["module_data"] = {"label": "Go", "url": "https://example.com"}
        else:
            body["content_record_id"] = world["records"][0].id
        response = client.put(f"/campaigns/modules/{module.id}", json=body,
                              headers={**csrf, "If-Match": module.updated_at.isoformat()})
        assert response.status_code == 200, response.text
        assert _stored(db, module.id) == kept

    def test_duplicating_the_variant_copies_it(self, db, world):
        self._set(db, world["module"], ["body_medium"])
        report = duplication.duplicate_variant(db, variant_id=world["variant"].id, brand_id=world["brand"],
                                               principal=None, enforced=False)
        [copy] = db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == report.variant_id).all()
        assert copy.hidden_fields == ["body_medium"]

    def test_the_composition_says_what_is_hidden(self, db, world, person):
        client, _ = person
        self._set(db, world["module"], ["body_medium"])
        composed = client.get(f"/campaigns/{world['campaign'].id}/composition").json()
        [module] = composed["variants"][0]["modules"]
        assert module["hidden_fields"] == ["body_medium"]


class TestRendering:
    def _set(self, db, module, fields):
        db.query(ModuleInstanceDB).filter_by(id=module.id).update({"hidden_fields": fields})
        db.commit()

    def test_a_hidden_field_is_left_out_and_its_value_kept(self, db, world):
        self._set(db, world["module"], ["body_medium"])
        html = render_variant_html(db, world["variant"].id, mode="preview")
        assert "Lisbon in spring" in html and "Read more" in html
        assert "Three days by the river." not in html
        db.expire_all()
        assert db.get(ContentRecordDB, world["records"][0].id).content["body_medium"] == "Three days by the river."

    def test_a_hidden_required_field_is_not_missing(self, db, world):
        db.query(ContentRecordDB).filter_by(id=world["records"][0].id).update(
            {"content": {**LISBON, "headline_medium": ""}})
        db.commit()
        assert [f for _, _, f in missing_required_fields(db, world["variant"].id, mode="preview")] == ["headline_medium"]
        self._set(db, world["module"], ["headline_medium"])
        assert missing_required_fields(db, world["variant"].id, mode="preview") == []
        [state] = module_states(db, world["variant"].id, brand_id=world["brand"])
        assert state["missing_required"] == []

    def test_the_frame_records_the_list_and_freezes_only_shown_values(self, db, world):
        self._set(db, world["module"], ["body_medium", "headline_medium"])
        frame = frames.build_frame(db, world["variant"].id)
        [entry] = frame["modules"]
        assert entry["hidden_fields"] == ["body_medium", "headline_medium"]
        assert "body_medium" not in entry["variables"] and "headline_medium" not in entry["variables"]
        assert frames.missing_required_in_frame(frame) == [], "a hidden required field is not missing"
        artifact, _ = frames.render_frame(db, frame)
        assert "Read more" in artifact.body and "Three days" not in artifact.body and "Lisbon in spring" not in artifact.body

    def test_a_frame_frozen_before_this_renders_as_it_did(self, db, world):
        frame = frames.build_frame(db, world["variant"].id)
        del frame["modules"][0]["hidden_fields"]
        artifact, _ = frames.render_frame(db, frame)
        assert "Three days by the river." in artifact.body
        assert frames.missing_required_in_frame(frame) == []


class TestASlotModule:
    @pytest.fixture
    def slot(self, db, world):
        """The module filled by a slot over a category of our own, and a
        published, marked record in it whose headline is empty."""
        category = CategoryDB(name=f"{TAG}-cat", type="main")
        db.add(category); db.flush()
        world["made"]["categories"].append(category.id)
        slot = DecisionSlotDB(variant_id=world["variant"].id, name="s", decision_strategy="top_score",
                              candidate_filter={"category_ids": [category.id]}, max_results=1)
        db.add(slot); db.flush()
        world["made"]["slots"].append(slot.id)
        headless = ContentRecordDB(title=f"{TAG} headless", content={**LISBON, "headline_medium": ""},
                                   status="active", brand_id=world["brand"], machine_ready=True)
        db.add(headless); db.flush()
        world["made"]["records"].append(headless.id)
        db.add_all([
            ContentVersionDB(content_record_id=headless.id, version_number=1,
                             content={**LISBON, "headline_medium": ""}, created_by="test"),
            ContentCategoryAssignmentDB(content_id=headless.id, category_id=category.id, score=7),
            ContentChannelReadinessDB(content_id=headless.id, channel="email", marked_by="test"),
        ])
        db.query(ModuleInstanceDB).filter_by(id=world["module"].id).update(
            {"content_record_id": None, "decision_slot_id": slot.id})
        db.commit()
        return slot, headless

    def test_a_record_need_not_fill_a_field_the_slots_module_hides(self, db, world, slot):
        slot_row, _ = slot
        assert slot_candidate_count(db, slot_row.id, brand_id=world["brand"])["candidate_count"] == 0
        db.query(ModuleInstanceDB).filter_by(id=world["module"].id).update({"hidden_fields": ["headline_medium"]})
        db.commit()
        assert slot_candidate_count(db, slot_row.id, brand_id=world["brand"])["candidate_count"] == 1

    def test_the_pick_made_at_send_leaves_the_hidden_field_out(self, db, world, slot):
        slot_row, headless = slot
        db.query(ModuleInstanceDB).filter_by(id=world["module"].id).update({"hidden_fields": ["body_medium"]})
        db.add(DecisionResolutionDB(decision_slot_id=slot_row.id, recipient_id=None,
                                    content_record_id=headless.id, reason="r", score=1))
        db.commit()
        frame = frames.build_frame(db, world["variant"].id)
        [entry] = frame["modules"]
        assert entry["hidden_fields"] == ["body_medium"]
        artifact, picks = frames.render_frame(db, frame)
        assert "body_medium" not in picks[0]["variables"]
        assert "Three days by the river." not in artifact.body and "Read more" in artifact.body

    def test_a_recorded_pick_is_held_to_the_list_when_replayed(self, db, world, slot):
        """Reconstruction re-uses the picks a delivery stored; one stored with
        the field in it is still laid out without it."""
        slot_row, headless = slot
        db.query(ModuleInstanceDB).filter_by(id=world["module"].id).update({"hidden_fields": ["body_medium"]})
        db.commit()
        frame = frames.build_frame(db, world["variant"].id)
        recorded = [{"module_id": world["module"].id, "decision_resolution_id": None,
                     "content_record_id": headless.id, "content_version_id": None,
                     "variables": {**LISBON, "headline_medium": "Kept"}}]
        artifact, _ = frames.render_frame(db, frame, picks=recorded)
        assert "Kept" in artifact.body and "Three days by the river." not in artifact.body
