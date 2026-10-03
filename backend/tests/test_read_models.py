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
            rows = client.get("/campaigns/decision-slots", params={"limit": 200},
                              headers=headers).json()["items"]
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
                rows = client.get("/campaigns/decision-slots", params={"limit": 200},
                                  headers=headers).json()["items"]
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


class TestB11CampaignComposition:
    @pytest.fixture
    def composed(self, db, default_brand):
        from app.campaigns.db_models import DecisionSlotDB, ModuleInstanceDB
        from app.campaigns.service import create_campaign, create_module_for_variant
        from app.content.service import create_content, create_content_version
        from app.overrides.db_models import ContentOverrideDB

        campaign = create_campaign(db, name=f"comp-{uuid.uuid4().hex[:6]}", brand_id=default_brand.id,
                                   channel="email")
        variant = db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).one()
        record = create_content(db, title=f"comp-{uuid.uuid4().hex[:6]}", brand_id=default_brand.id,
                                content={"headline_medium": "H", "body_medium": "B"})
        create_content_version(db, content_record_id=record.id, created_by="t", brand_id=default_brand.id)
        header = create_module_for_variant(db, variant_id=variant.id, module_type="header",
                                           module_data={"subject": "S"}, brand_id=default_brand.id)
        content = create_module_for_variant(db, variant_id=variant.id, module_type="img_right",
                                            content_record_id=record.id, brand_id=default_brand.id)
        slot = DecisionSlotDB(variant_id=variant.id, name="slot", decision_type="content_recommendation",
                              decision_strategy="top_score")
        db.add(slot); db.flush()
        slotted = ModuleInstanceDB(variant_id=variant.id, module_type="single_stack", position=9,
                                   decision_slot_id=slot.id, module_data={})
        override = ContentOverrideDB(module_instance_id=content.id, field_overrides={"headline_medium": "X"},
                                     overridden_by="t", active=True)
        db.add_all([slotted, override]); db.commit()
        yield {"campaign": campaign, "header": header.id, "content": content.id, "slotted": slotted.id,
               "slot": slot.id, "override": override.id}
        db.rollback()
        db.query(ContentOverrideDB).filter(ContentOverrideDB.id == override.id).delete()
        db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant.id).delete()
        db.query(DecisionSlotDB).filter(DecisionSlotDB.id == slot.id).delete()
        db.query(VariantDB).filter(VariantDB.id == variant.id).delete()
        db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
        db.commit()

    def _get(self, campaign_id):
        with machine([VIEW]) as headers:
            return client.get(f"/campaigns/{campaign_id}/composition", headers=headers)

    def test_modules_say_what_may_be_overridden(self, composed):
        body = self._get(composed["campaign"].id).json()
        [variant] = body["variants"]
        by_id = {m["id"]: m for m in variant["modules"]}
        assert by_id[composed["content"]]["overrideable"] is True
        assert by_id[composed["content"]]["active_override"]["field_overrides"] == {"headline_medium": "X"}
        assert by_id[composed["slotted"]]["overrideable"] is False, "a slot is never overridden"

    def test_the_envelope_is_reported_apart(self, composed):
        [variant] = self._get(composed["campaign"].id).json()["variants"]
        assert [m["id"] for m in variant["envelope_modules"]] == [composed["header"]]
        assert composed["header"] not in {m["id"] for m in variant["modules"]}
        assert variant["has_envelope"] is True and "header" not in variant["accepted_module_types"]
        assert variant["module_limit"] is None and variant["can_add_module"] is True

    def test_slots_carry_their_counts(self, composed):
        [variant] = self._get(composed["campaign"].id).json()["variants"]
        assert [s["id"] for s in variant["decision_slots"]] == [composed["slot"]]

    def test_another_brands_campaign_is_not_found(self, db, foreign_brand):
        campaign = CampaignDB(brand_id=foreign_brand.id, name=f"comp-f-{uuid.uuid4().hex[:6]}")
        db.add(campaign); db.commit()
        assert self._get(campaign.id).status_code == 404

    def test_the_jinja_page_no_longer_offers_to_override_a_slot(self, db, composed):
        from sqlalchemy import text

        from app.auth import service as auth

        user = auth.create_user(db, email=f"rm-{uuid.uuid4().hex[:8]}@example.invalid", role_key="admin")
        token = auth.create_session(db, user)
        page_client = TestClient(app, raise_server_exceptions=False)
        page_client.cookies.set(auth.SESSION_COOKIE, token)
        try:
            page = page_client.get(f"/ui/campaigns/{composed['campaign'].id}")
            assert page.status_code == 200, page.text[:300]
            assert f"#{composed['content']} img_right" in page.text
            assert f"#{composed['slotted']} single_stack" not in page.text, (
                "the page offered an override the service refuses (ADR-178 point 5)"
            )
        finally:
            db.rollback()
            for table in ("auth_sessions", "role_assignments"):
                db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
            db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
            db.commit()


class TestB17ContentDetailAndC5:
    @pytest.fixture
    def record(self, db, default_brand):
        from app.content.db_models import CategoryDB, ContentCategoryAssignmentDB, ContentRecordDB

        rec = ContentRecordDB(title=f"cd-{uuid.uuid4().hex[:6]}", content={}, status="active",
                              brand_id=default_brand.id)
        cat = CategoryDB(name=f"cd-{uuid.uuid4().hex[:6]}", type="main")
        db.add_all([rec, cat]); db.flush()
        a = ContentCategoryAssignmentDB(content_id=rec.id, category_id=cat.id, score=7)
        db.add(a); db.commit()
        yield rec, cat, a
        db.rollback()
        db.query(ContentCategoryAssignmentDB).filter(ContentCategoryAssignmentDB.category_id == cat.id).delete()
        db.query(ContentRecordDB).filter(ContentRecordDB.id == rec.id).delete()
        db.query(CategoryDB).filter(CategoryDB.id == cat.id).delete()
        db.commit()

    def test_assignments_carry_their_id_and_score(self, record):
        rec, cat, a = record
        with machine([VIEW]) as headers:
            rows = client.get(f"/content/{rec.id}/assignments", headers=headers).json()
        assert rows == [{"assignment_id": a.id, "category_id": cat.id, "name": cat.name,
                         "type": "main", "score": 7}]

    def test_c5_an_assignment_is_removed_through_its_record(self, db, record):
        from app.auth.permissions import CONTENT_MANAGE
        from app.content.db_models import ContentCategoryAssignmentDB

        rec, _, a = record
        rec_id, a_id = rec.id, a.id  # read before the row goes
        with machine([VIEW, CONTENT_MANAGE]) as headers:
            wrong = client.delete(f"/content/{rec_id + 99999}/assignments/{a_id}", headers=headers)
            right = client.delete(f"/content/{rec_id}/assignments/{a_id}", headers=headers)
        assert wrong.status_code == 404 and right.status_code == 204
        db.expire_all()
        assert db.get(ContentCategoryAssignmentDB, a_id) is None

    def test_c5_another_brands_assignment_is_not_found(self, db, record, foreign_api):
        from app.auth.permissions import CONTENT_MANAGE
        from app.content.db_models import ContentCategoryAssignmentDB

        rec, _, a = record
        with foreign_api([VIEW, CONTENT_MANAGE]) as headers:
            response = client.delete(f"/content/{rec.id}/assignments/{a.id}", headers=headers)
        assert response.status_code == 404
        db.expire_all()
        assert db.get(ContentCategoryAssignmentDB, a.id) is not None

    def test_usage_finds_old_signals_behind_newer_ones_elsewhere(self, db, record):
        """The page used to take the newest 100 contributions platform-wide and
        filter in Python, so these older ones vanished behind 101 newer."""
        from datetime import datetime, timedelta, timezone

        from app.delivery.db_models import DeliveryExecutionDB
        from app.insight.db_models import EngagementEventDB
        from app.recipients.db_models import RecipientDB, SignalContributionDB

        rec, cat, _ = record
        execution = db.query(DeliveryExecutionDB).order_by(DeliveryExecutionDB.id).first()
        recipient = RecipientDB(external_id=f"cd-{uuid.uuid4()}", status="active")
        db.add(recipient); db.flush()
        mine = EngagementEventDB(delivery_execution_id=execution.id, event_type="click",
                                 event_data={"content_record_id": rec.id})
        other = EngagementEventDB(delivery_execution_id=execution.id, event_type="click",
                                  event_data={"content_record_id": -1})
        db.add_all([mine, other]); db.flush()
        old = datetime.now(timezone.utc) - timedelta(days=30)
        db.add(SignalContributionDB(recipient_id=recipient.id, category_id=cat.id, contribution_type="click",
                                    base_weight=5.0, event_id=mine.id, created_at=old))
        db.add_all([SignalContributionDB(recipient_id=recipient.id, category_id=cat.id,
                                         contribution_type="click", base_weight=1.0, event_id=other.id)
                    for _ in range(101)])
        db.commit()
        try:
            with machine([VIEW]) as headers:
                usage = client.get(f"/content/{rec.id}/usage", headers=headers).json()
            assert [s["base_weight"] for s in usage["signals"]] == [5.0]
        finally:
            db.rollback()
            db.query(SignalContributionDB).filter(SignalContributionDB.recipient_id == recipient.id).delete()
            db.query(EngagementEventDB).filter(EngagementEventDB.id.in_([mine.id, other.id])).delete(
                synchronize_session=False)
            db.query(RecipientDB).filter(RecipientDB.id == recipient.id).delete()
            db.commit()

    def test_another_brands_record_is_not_found(self, db, foreign_brand):
        from app.content.db_models import ContentRecordDB

        rec = ContentRecordDB(title="f", content={}, status="active", brand_id=foreign_brand.id)
        db.add(rec); db.commit()
        with machine([VIEW]) as headers:
            assert client.get(f"/content/{rec.id}/assignments", headers=headers).status_code == 404
            assert client.get(f"/content/{rec.id}/usage", headers=headers).status_code == 404

    def test_the_jinja_page_renders_from_the_services(self, db, record):
        from sqlalchemy import text

        from app.auth import service as auth

        rec, cat, _ = record
        user = auth.create_user(db, email=f"rm-{uuid.uuid4().hex[:8]}@example.invalid", role_key="viewer")
        token = auth.create_session(db, user)
        page_client = TestClient(app, raise_server_exceptions=False)
        page_client.cookies.set(auth.SESSION_COOKIE, token)
        try:
            page = page_client.get(f"/ui/content/{rec.id}")
            assert page.status_code == 200, page.text[:300]
            assert cat.name in page.text
        finally:
            db.rollback()
            for table in ("auth_sessions", "role_assignments"):
                db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
            db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
            db.commit()


class TestB23B24Deliveries:
    """Against the seed's "Demo send": 32 executions with clicks and the
    contributions those clicks produced."""

    @pytest.fixture
    def demo(self, db):
        from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
        from app.insight.db_models import EngagementEventDB

        send = db.query(SendInstanceDB).filter(SendInstanceDB.name == "Demo send").one()
        clicked = (db.query(DeliveryExecutionDB).join(
            EngagementEventDB, EngagementEventDB.delivery_execution_id == DeliveryExecutionDB.id)
            .filter(DeliveryExecutionDB.send_instance_id == send.id).first())
        return send, clicked

    def test_the_list_says_what_each_send_sent_with_live_counts(self, demo):
        send, _ = demo
        with machine([VIEW]) as headers:
            rows = client.get("/delivery/send-instances", params={"limit": 200}, headers=headers).json()["items"]
        row = next(r for r in rows if r["id"] == send.id)
        assert row["campaign_name"] == "Demo Campaign 1" and row["variant_name"]
        assert row["execution_count"] == 32 and row["event_count"] > 0

    def test_executions_say_who_and_why(self, demo):
        send, _ = demo
        with machine([VIEW]) as headers:
            rows = client.get(f"/delivery/send-instances/{send.id}/executions",
                              params={"limit": 200}, headers=headers).json()["items"]
        assert all(r["recipient_external_id"].startswith("demo-") for r in rows)

    def test_the_trace_carries_what_each_click_taught(self, demo):
        _, clicked = demo
        with machine([VIEW]) as headers:
            body = client.get(f"/delivery/executions/{clicked.id}/trace", headers=headers).json()
        assert body["events"], "the seeded click events are missing"
        assert any(c["category_name"] for e in body["events"] for c in e["contributions"])

    def test_another_brand_cannot_trace_this_execution(self, demo, foreign_api):
        _, clicked = demo
        with foreign_api([VIEW]) as headers:
            response = client.get(f"/delivery/executions/{clicked.id}/trace", headers=headers)
        assert response.status_code == 404

    def test_the_detail_names_its_audience(self, db, default_brand):
        from app.audience.db_models import AudienceGroupDB
        from app.delivery.db_models import SendInstanceDB
        from app.snapshots.db_models import SnapshotDB

        group = AudienceGroupDB(brand_id=default_brand.id, name=f"rm-{uuid.uuid4().hex[:6]}")
        db.add(group); db.flush()
        snapshot_id = db.query(SnapshotDB.id).order_by(SnapshotDB.id).first()[0]
        send = SendInstanceDB(snapshot_id=snapshot_id, brand_id=default_brand.id, name="rm",
                              status="draft", provider="mock", audience_group_id=group.id)
        db.add(send); db.commit()
        try:
            with machine([VIEW]) as headers:
                body = client.get(f"/delivery/send-instances/{send.id}", headers=headers).json()
            assert body["audience_group_name"] == group.name
        finally:
            db.query(SendInstanceDB).filter(SendInstanceDB.id == send.id).delete()
            db.query(AudienceGroupDB).filter(AudienceGroupDB.id == group.id).delete()
            db.commit()

    def test_the_jinja_detail_still_shows_the_trace(self, db, demo):
        from sqlalchemy import text

        from app.auth import service as auth

        send, clicked = demo
        user = auth.create_user(db, email=f"rm-{uuid.uuid4().hex[:8]}@example.invalid", role_key="viewer")
        token = auth.create_session(db, user)
        page_client = TestClient(app, raise_server_exceptions=False)
        page_client.cookies.set(auth.SESSION_COOKIE, token)
        try:
            page = page_client.get(f"/ui/deliveries/send-instances/{send.id}")
            assert page.status_code == 200, page.text[:300]
            assert "click" in page.text
        finally:
            db.rollback()
            for table in ("auth_sessions", "role_assignments"):
                db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
            db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
            db.commit()


def test_event_trace_answers_only_for_the_brand_asked(db, default_brand, foreign_brand):
    """B10 will call `event_trace` without the route's check in front of it."""
    from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
    from app.insight.db_models import EngagementEventDB
    from app.insight.service import event_trace

    send = db.query(SendInstanceDB).filter(SendInstanceDB.name == "Demo send").one()
    clicked = (db.query(DeliveryExecutionDB).join(
        EngagementEventDB, EngagementEventDB.delivery_execution_id == DeliveryExecutionDB.id)
        .filter(DeliveryExecutionDB.send_instance_id == send.id).first())
    assert event_trace(db, [clicked.id], brand_id=default_brand.id).get(clicked.id)
    assert event_trace(db, [clicked.id], brand_id=foreign_brand.id) == {}


class TestC11C12C13AudienceCriteria:
    @pytest.fixture
    def group(self, db, default_brand):
        from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB
        from app.recipients.consent import record_consent
        from app.recipients.db_models import AddressabilityDB, ConsentEventDB, RecipientDB

        lang = f"lc-{uuid.uuid4().hex[:5]}"
        people = {}
        for name, channel in (("email", "email"), ("push", "push"), ("member", "email")):
            r = RecipientDB(external_id=f"crit-{uuid.uuid4()}", status="active", language=lang)
            db.add(r); db.flush()
            record_consent(db, r.id, "opted_in", default_brand.id, channel=channel,
                           purpose="marketing", source="test", commit=False)
            db.add(AddressabilityDB(recipient_id=r.id, channel=channel, status="active", is_primary=True,
                                    value={"email": f"{uuid.uuid4().hex[:6]}@example.invalid"}
                                    if channel == "email" else {"token": "tok-1", "platform": "apns"}))
            people[name] = r
        g = AudienceGroupDB(brand_id=default_brand.id, name=f"crit-{uuid.uuid4().hex[:6]}")
        db.add(g); db.flush()
        db.add(AudienceGroupMemberDB(group_id=g.id, recipient_id=people["member"].id))
        db.commit()
        yield g, people, lang
        db.rollback()
        ids = [p.id for p in people.values()]
        db.query(AudienceGroupMemberDB).filter(AudienceGroupMemberDB.group_id == g.id).delete()
        db.query(AudienceGroupDB).filter(AudienceGroupDB.id == g.id).delete()
        db.query(ConsentEventDB).filter(ConsentEventDB.recipient_id.in_(ids)).delete(synchronize_session=False)
        db.query(AddressabilityDB).filter(AddressabilityDB.recipient_id.in_(ids)).delete(synchronize_session=False)
        db.query(RecipientDB).filter(RecipientDB.id.in_(ids)).delete(synchronize_session=False)
        db.commit()

    def _preview(self, group_id, channel, lang, headers):
        return client.get(f"/api/audience-groups/{group_id}/criteria-preview",
                          params={"channel": channel, "language": lang}, headers=headers)

    def test_c11_the_preview_is_per_channel_and_skips_members(self, group):
        g, people, lang = group
        with machine([VIEW]) as headers:
            email = self._preview(g.id, "email", lang, headers).json()
            push = self._preview(g.id, "push", lang, headers).json()
        assert [s["recipient_id"] for s in email["sample"]] == [people["email"].id]
        assert email["sample"][0]["address"].endswith("@example.invalid")
        assert [s["recipient_id"] for s in push["sample"]] == [people["push"].id]
        assert push["sample"][0]["address"] == "tok-1"

    def test_c12_bulk_add_pins_the_matches_and_needs_manage(self, db, group):
        from app.auth.permissions import AUDIENCES_MANAGE, AUDIENCES_PIN

        g, people, lang = group
        body = {"channel": "email", "language": lang}
        with machine([VIEW, AUDIENCES_PIN]) as headers:
            refused = client.post(f"/api/audience-groups/{g.id}/bulk-add", json=body, headers=headers)
        with machine([VIEW, AUDIENCES_MANAGE]) as headers:
            added = client.post(f"/api/audience-groups/{g.id}/bulk-add", json=body, headers=headers)
            after = self._preview(g.id, "email", lang, headers).json()
        assert refused.status_code == 403, "a pin-only grant could bulk-add by rule"
        assert added.json() == {"matched": 1, "added": 1}
        assert after["count"] == 0, "the added recipient is now a member"

    def test_c11_c12_another_brands_group_is_not_found(self, db, foreign_brand):
        from app.audience.db_models import AudienceGroupDB
        from app.auth.permissions import AUDIENCES_MANAGE

        g = AudienceGroupDB(brand_id=foreign_brand.id, name=f"crit-f-{uuid.uuid4().hex[:6]}")
        db.add(g); db.commit()
        with machine([VIEW, AUDIENCES_MANAGE]) as headers:
            preview = self._preview(g.id, "email", None, headers)
            add = client.post(f"/api/audience-groups/{g.id}/bulk-add", json={"channel": "email"},
                              headers=headers)
        assert preview.status_code == 404 and add.status_code == 404

    def test_c13_a_suggested_audience_is_built_only_in_the_brand(self, db, default_brand, foreign_brand):
        from app.audience.db_models import AudienceGroupDB, AudienceRuleBlockDB
        from app.auth.permissions import AUDIENCES_MANAGE

        own = CampaignDB(brand_id=default_brand.id, name=f"sugg-{uuid.uuid4().hex[:6]}")
        foreign = CampaignDB(brand_id=foreign_brand.id, name=f"sugg-f-{uuid.uuid4().hex[:6]}")
        db.add_all([own, foreign]); db.commit()
        created = None
        try:
            with machine([VIEW, AUDIENCES_MANAGE]) as headers:
                ok = client.post("/api/audience-groups/suggested", json={"campaign_id": own.id}, headers=headers)
                refused = client.post("/api/audience-groups/suggested", json={"campaign_id": foreign.id},
                                      headers=headers)
            assert refused.status_code == 404
            assert ok.status_code in (201, 409), ok.text  # 409: the campaign has no content to suggest from
            if ok.status_code == 201:
                created = ok.json()["id"]
        finally:
            if created:
                db.query(AudienceRuleBlockDB).filter(AudienceRuleBlockDB.group_id == created).delete()
                db.query(AudienceGroupDB).filter(AudienceGroupDB.id == created).delete()
            db.query(CampaignDB).filter(CampaignDB.id == own.id).delete()
            db.commit()


def test_bulk_add_is_priced_as_audiences_manage():
    """ADR-166 point 2: adding by rule reshapes the audience; pin is for one person."""
    from app.auth.permissions import AUDIENCES_MANAGE
    from app.auth.policy import required_permission

    assert required_permission("POST", "/api/audience-groups/{group_id}/bulk-add") == AUDIENCES_MANAGE


def _page_client(db, role_key="viewer"):
    from app.auth import service as auth

    user = auth.create_user(db, email=f"rm-{uuid.uuid4().hex[:8]}@example.invalid", role_key=role_key)
    token = auth.create_session(db, user)
    page = TestClient(app, raise_server_exceptions=False)
    page.cookies.set(auth.SESSION_COOKIE, token)
    return page, user


def _drop_user(db, user):
    from sqlalchemy import text

    db.rollback()
    for table in ("auth_sessions", "role_assignments"):
        db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
    db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
    db.commit()


def test_b4_the_overview_counts_this_brand(db, default_brand, foreign_brand):
    from app.content.db_models import ContentRecordDB

    with machine([VIEW]) as headers:
        before = client.get("/insight/overview", headers=headers).json()
    db.add(ContentRecordDB(title="f", content={}, status="active", brand_id=foreign_brand.id))
    db.add(ContentRecordDB(title="o", content={}, status="active", brand_id=default_brand.id))
    db.commit()
    try:
        with machine([VIEW]) as headers:
            after = client.get("/insight/overview", headers=headers).json()
        assert after["content_active"] == before["content_active"] + 1, "another brand's content was counted"
    finally:
        db.query(ContentRecordDB).filter(ContentRecordDB.title == "o",
                                         ContentRecordDB.brand_id == default_brand.id).delete()
        db.commit()


class TestB10RecipientActivity:
    @pytest.fixture
    def person(self, db, default_brand, foreign_brand):
        """One recipient with a delivery and a decision in each brand."""
        from app.campaigns.db_models import DecisionResolutionDB, DecisionSlotDB
        from app.content.db_models import ContentRecordDB
        from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
        from app.recipients.consent import record_consent
        from app.recipients.db_models import ConsentEventDB, RecipientDB
        from app.snapshots.db_models import SnapshotDB

        r = RecipientDB(external_id=f"act-{uuid.uuid4()}", status="active")
        db.add(r); db.flush()
        made = {"sends": [], "slots": [], "content": []}
        for brand, tag in ((default_brand, "OWN"), (foreign_brand, "FOREIGN")):
            variant = _variant(db, brand)
            snapshot = SnapshotDB(variant_id=variant.id,
                                  render_context={})
            content = ContentRecordDB(title=f"{tag}-content-{uuid.uuid4().hex[:4]}", content={},
                                      status="active", brand_id=brand.id)
            slot = DecisionSlotDB(variant_id=variant.id, name="s", decision_type="content_recommendation",
                                  decision_strategy="top_score")
            db.add_all([snapshot, content, slot]); db.flush()
            send = SendInstanceDB(snapshot_id=snapshot.id, brand_id=brand.id, status="sent",
                                  provider="mock", name=f"{tag}-send-{uuid.uuid4().hex[:4]}")
            db.add(send); db.flush()
            db.add(DeliveryExecutionDB(send_instance_id=send.id, recipient_id=r.id, status="sent",
                                       provider="mock", channel="email", purpose="marketing"))
            db.add(DecisionResolutionDB(decision_slot_id=slot.id, recipient_id=r.id,
                                        content_record_id=content.id))
            record_consent(db, r.id, "opted_in", brand.id, channel="email", purpose="marketing",
                           source="test", commit=False)
            made["sends"].append(send); made["slots"].append(slot); made["content"].append(content)
            made.setdefault("snapshots", []).append(snapshot.id)
        db.commit()
        yield r, made
        db.rollback()
        ids = [s.id for s in made["sends"]]
        db.query(DeliveryExecutionDB).filter(DeliveryExecutionDB.send_instance_id.in_(ids)).delete(
            synchronize_session=False)
        db.query(DecisionResolutionDB).filter(DecisionResolutionDB.recipient_id == r.id).delete()
        db.query(SendInstanceDB).filter(SendInstanceDB.id.in_(ids)).delete(synchronize_session=False)
        db.query(DecisionSlotDB).filter(DecisionSlotDB.id.in_([s.id for s in made["slots"]])).delete(
            synchronize_session=False)
        db.query(SnapshotDB).filter(SnapshotDB.id.in_(made["snapshots"])).delete(synchronize_session=False)
        db.query(ContentRecordDB).filter(ContentRecordDB.id.in_([c.id for c in made["content"]])).delete(
            synchronize_session=False)
        db.query(ConsentEventDB).filter(ConsentEventDB.recipient_id == r.id).delete()
        db.query(RecipientDB).filter(RecipientDB.id == r.id).delete()
        db.commit()

    def test_only_this_brands_decisions_and_deliveries(self, person):
        r, made = person
        with machine([VIEW]) as headers:
            body = client.get(f"/recipients/{r.id}/activity", headers=headers).json()
        assert [d["send_instance_name"] for d in body["deliveries"]] == [made["sends"][0].name]
        assert [d["content_title"] for d in body["decisions"]] == [made["content"][0].title]

    def test_consent_history_spans_brands_and_says_which(self, person, default_brand, foreign_brand):
        r, _ = person
        with machine([VIEW]) as headers:
            body = client.get(f"/recipients/{r.id}/activity", headers=headers).json()
        assert {e["brand_id"] for e in body["consent_history"]} == {default_brand.id, foreign_brand.id}
        assert all(e["brand_name"] for e in body["consent_history"])

    def test_the_jinja_page_no_longer_shows_another_brands_sends(self, db, person):
        r, made = person
        page, user = _page_client(db)
        try:
            html = page.get(f"/ui/recipients/{r.id}").text
            assert made["sends"][0].name in html
            assert made["sends"][1].name not in html, "another brand's send name on the recipient page"
            assert made["content"][1].title not in html, "another brand's content title on the page"
        finally:
            _drop_user(db, user)


class TestB20CategoryDetailAndC10:
    @pytest.fixture
    def category(self, db, default_brand, foreign_brand):
        from app.content.db_models import CategoryDB, CategoryRelationDB, ContentCategoryAssignmentDB, ContentRecordDB
        from app.recipients.consent import record_consent
        from app.recipients.db_models import ConsentEventDB, RecipientDB, SignalContributionDB

        cat = CategoryDB(name=f"cat-{uuid.uuid4().hex[:6]}", type="main")
        other = CategoryDB(name=f"cat-p-{uuid.uuid4().hex[:6]}", type="main")
        db.add_all([cat, other]); db.flush()
        relation = CategoryRelationDB(parent_category_id=other.id, child_category_id=cat.id,
                                      relation_type="parent_child")
        own = ContentRecordDB(title=f"OWN-{uuid.uuid4().hex[:4]}", content={}, status="active", brand_id=default_brand.id)
        theirs = ContentRecordDB(title=f"FOREIGN-{uuid.uuid4().hex[:4]}", content={}, status="active",
                                 brand_id=foreign_brand.id)
        db.add_all([relation, own, theirs]); db.flush()
        for rec in (own, theirs):
            db.add(ContentCategoryAssignmentDB(content_id=rec.id, category_id=cat.id, score=5))
        people = []
        for brand, weight in ((default_brand, 10.0), (foreign_brand, 99.0)):
            p = RecipientDB(external_id=f"cat-{uuid.uuid4()}", status="active")
            db.add(p); db.flush()
            record_consent(db, p.id, "opted_in", brand.id, channel="email", purpose="marketing",
                           source="test", commit=False)
            db.add(SignalContributionDB(recipient_id=p.id, category_id=cat.id, contribution_type="manual",
                                        base_weight=weight))
            people.append(p)
        db.commit()
        yield cat, relation, own, theirs, people
        db.rollback()
        ids = [p.id for p in people]
        db.query(SignalContributionDB).filter(SignalContributionDB.category_id == cat.id).delete()
        db.query(ConsentEventDB).filter(ConsentEventDB.recipient_id.in_(ids)).delete(synchronize_session=False)
        db.query(RecipientDB).filter(RecipientDB.id.in_(ids)).delete(synchronize_session=False)
        db.query(ContentCategoryAssignmentDB).filter(ContentCategoryAssignmentDB.category_id == cat.id).delete()
        db.query(ContentRecordDB).filter(ContentRecordDB.id.in_([own.id, theirs.id])).delete(
            synchronize_session=False)
        db.query(CategoryRelationDB).filter(CategoryRelationDB.child_category_id == cat.id).delete()
        db.query(CategoryDB).filter(CategoryDB.id.in_([cat.id, other.id])).delete(synchronize_session=False)
        db.commit()

    def test_only_this_brands_content_and_audience(self, category):
        cat, relation, own, _, people = category
        with machine([VIEW]) as headers:
            body = client.get(f"/insight/categories/{cat.id}", headers=headers).json()
        assert [c["content_id"] for c in body["assigned_content"]] == [own.id]
        assert [r["recipient_id"] for r in body["top_recipients"]] == [people[0].id]
        assert body["impact"]["total_delta"] == 10.0, "another brand's audience was summed"
        assert body["parents"][0]["relation_id"] == relation.id

    def test_c10_a_relation_is_deleted_once(self, db, category):
        from app.auth.permissions import CONTENT_MANAGE

        _, relation, _, _, _ = category
        rid = relation.id
        with machine([VIEW, CONTENT_MANAGE]) as headers:
            first = client.delete(f"/content/category-relations/{rid}", headers=headers)
            second = client.delete(f"/content/category-relations/{rid}", headers=headers)
        assert (first.status_code, second.status_code) == (204, 404)

    def test_the_jinja_page_shows_only_this_brands_content(self, db, category):
        cat, _, own, theirs, _ = category
        page, user = _page_client(db)
        try:
            html = page.get(f"/ui/categories/{cat.id}").text
            assert own.title in html and theirs.title not in html
        finally:
            _drop_user(db, user)
