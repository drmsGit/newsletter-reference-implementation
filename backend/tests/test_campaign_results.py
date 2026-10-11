"""A campaign's results section (task-58, which absorbs task-360; ADR-196).

Decided with the user 2026-10-11, one question at a time:
  - the one KPI view is a collapsible section on the campaign page, one row
    per variant and a campaign line; nothing for sends that have not gone out;
  - per variant: recipients, sent, delivered (email), failed, excluded by
    stage, bounced, complaints, total clicks, unique clickers, click rate and
    unsubscribes, summed over the variant's sends;
  - the campaign line is the totals; every click rate is unique clickers over
    sent, so email and push compare like for like;
  - opens are not shown (task-353); per-content figures are the catalogue's;
  - an unsubscribe records the delivery it came through, so it can be counted
    per send; earlier ones cannot, and the section says so;
  - computed on read, nothing stored; no export is built.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.auth.permissions import SENDS_PLAN
from app.campaigns import results
from app.campaigns.db_models import CampaignDB, VariantDB
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.insight.db_models import EngagementEventDB
from app.providers.adapters.resend import NormalizedEvent
from app.providers.service import process_provider_webhook_event
from app.recipients.consent import record_consent
from app.recipients.db_models import ConsentEventDB
from app.settings import service as settings
from app.snapshots.db_models import SnapshotDB
from main import app
from tests import test_render_skip as _render_skip
from tests.machine import machine
from tests.test_api_guard import signed_in

api = TestClient(app, raise_server_exceptions=False)
db = _render_skip.db
world = _render_skip.world
UTC = timezone.utc


@pytest.fixture
def campaign(db, world):
    """A campaign of the default brand with an email and a push variant, and
    helpers to give them sends, executions and events. Nothing is fired."""
    brand = world["brand"]
    row = CampaignDB(name=f"results-{uuid.uuid4().hex[:6]}", status="draft", brand_id=brand.id)
    db.add(row)
    db.flush()
    world["made"]["campaigns"].append(row.id)
    email = VariantDB(campaign_id=row.id, channel="email", name="Main", status="draft")
    push = VariantDB(campaign_id=row.id, channel="push", name="Push", status="draft")
    db.add_all([email, push])
    db.commit()
    executions: list[int] = []

    def send(variant, rows, *, status="sent", created_at=None):
        """`rows` is a list of (execution status, exclusion reason)."""
        snapshot = SnapshotDB(variant_id=variant.id)
        db.add(snapshot)
        db.flush()
        world["made"]["snapshots"].append(snapshot.id)
        made = SendInstanceDB(snapshot_id=snapshot.id, brand_id=brand.id, name="results", status=status,
                              provider="mock")
        if created_at is not None:
            made.created_at = created_at
        db.add(made)
        db.flush()
        world["made"]["sends"].append(made.id)
        out = []
        for execution_status, reason in rows:
            person = world["person"](variant.channel)
            execution = DeliveryExecutionDB(send_instance_id=made.id, recipient_id=person.id,
                                            status=execution_status, exclusion_reason=reason, provider="mock",
                                            channel=variant.channel, purpose="marketing")
            db.add(execution)
            db.flush()
            executions.append(execution.id)
            out.append(execution)
        db.commit()
        return out

    def event(execution, event_type, times=1):
        for _ in range(times):
            db.add(EngagementEventDB(delivery_execution_id=execution.id, event_type=event_type, provider="mock",
                                     provider_event_id=uuid.uuid4().hex))
        db.commit()

    yield {"campaign": row, "email": email, "push": push, "send": send, "event": event, "brand": brand}
    db.rollback()
    db.query(EngagementEventDB).filter(EngagementEventDB.delivery_execution_id.in_(executions)).delete(
        synchronize_session=False)
    db.commit()


def _results(db, campaign_id, brand_id):
    db.expire_all()
    return results.campaign_results(db, campaign_id, brand_id=brand_id)


def _figures(the_results, name):
    return next(v for v in the_results["variants"] if v["name"] == name)


# --- what is counted -----------------------------------------------------------------

def test_a_campaign_that_has_sent_nothing_has_no_results(db, campaign):
    campaign["send"](campaign["email"], [("created", None)], status="draft")
    campaign["send"](campaign["push"], [("created", None)], status="scheduled")
    shown = _results(db, campaign["campaign"].id, campaign["brand"].id)
    assert shown["variants"] == [] and shown["campaign"] is None


def test_a_variant_adds_up_every_send_that_went_out(db, campaign):
    email, event = campaign["email"], campaign["event"]
    first = campaign["send"](email, [("sent", None)] * 4 + [("failed", None), ("uncertain", None),
                                    ("excluded", "consent: opted out"), ("excluded", "render: nothing to send")])
    second = campaign["send"](email, [("sent", None)] * 2)
    campaign["send"](email, [("created", None)] * 5, status="draft")   # not gone out: not counted
    for execution in first[:3]:
        event(execution, "delivered")
    event(first[3], "bounce")
    event(first[2], "complaint")
    event(first[0], "click", times=3)
    event(first[1], "click")
    event(second[0], "click")
    event(second[0], "open")   # opens are not a figure (task-353)

    shown = _figures(_results(db, campaign["campaign"].id, campaign["brand"].id), "Main")
    assert shown["channel"] == "email"
    assert (shown["recipients"], shown["sent"], shown["failed"], shown["excluded"]) == (10, 6, 2, 2)
    assert shown["excluded_by_stage"] == {"consent": 1, "render": 1}
    assert (shown["delivered"], shown["bounced"], shown["complaints"]) == (3, 1, 1)
    assert (shown["clicks_total"], shown["unique_clickers"]) == (5, 3)
    assert shown["click_rate"] == pytest.approx(3 / 6)
    assert "opens" not in shown


def test_every_send_status_that_went_out_counts(db, campaign):
    for status in ("sending", "sent", "partial_failed", "failed", "no_recipients"):
        campaign["send"](campaign["email"], [("sent", None)], status=status)
    assert _figures(_results(db, campaign["campaign"].id, campaign["brand"].id), "Main")["sent"] == 5


def test_push_has_no_delivered_figure(db, campaign):
    campaign["send"](campaign["push"], [("sent", None)] * 2)
    shown = _figures(_results(db, campaign["campaign"].id, campaign["brand"].id), "Push")
    assert shown["delivered"] is None and shown["sent"] == 2


def test_only_variants_that_sent_are_listed(db, campaign):
    campaign["send"](campaign["email"], [("sent", None)])
    shown = _results(db, campaign["campaign"].id, campaign["brand"].id)
    assert [v["name"] for v in shown["variants"]] == ["Main"]


def test_the_campaign_line_is_the_totals_and_its_rate_is_pooled(db, campaign):
    """3 of 6 clicked on email, 0 of 2 on push: 3 of 8, not the mean 0.25."""
    email = campaign["send"](campaign["email"], [("sent", None)] * 6)
    campaign["send"](campaign["push"], [("sent", None)] * 2 + [("excluded", "consent: none")])
    for execution in email[:3]:
        campaign["event"](execution, "click", times=2)
    campaign["event"](email[0], "delivered")
    line = _results(db, campaign["campaign"].id, campaign["brand"].id)["campaign"]
    assert (line["recipients"], line["sent"], line["excluded"]) == (9, 8, 1)
    assert line["excluded_by_stage"] == {"consent": 1}
    assert (line["clicks_total"], line["unique_clickers"]) == (6, 3)
    assert line["click_rate"] == pytest.approx(3 / 8)
    assert line["delivered"] == 1, "delivered is the email variants' total"


def test_no_rate_when_nothing_was_sent(db, campaign):
    campaign["send"](campaign["email"], [("failed", None)], status="failed")
    shown = _results(db, campaign["campaign"].id, campaign["brand"].id)
    assert _figures(shown, "Main")["click_rate"] is None and shown["campaign"]["click_rate"] is None


def test_a_campaign_line_of_push_only_has_no_delivered(db, campaign):
    campaign["send"](campaign["push"], [("sent", None)])
    assert _results(db, campaign["campaign"].id, campaign["brand"].id)["campaign"]["delivered"] is None


# --- unsubscribes ---------------------------------------------------------------------

def test_unsubscribes_are_the_deliveries_they_came_through(db, campaign):
    executions = campaign["send"](campaign["email"], [("sent", None)] * 3)
    brand = campaign["brand"]
    # One person opted out of everything: many rows, one delivery.
    for channel in ("email", "push"):
        record_consent(db, executions[0].recipient_id, "opted_out", brand.id, source="unsubscribe", channel=channel,
                       purpose="marketing", delivery_execution_id=executions[0].id)
    record_consent(db, executions[1].recipient_id, "opted_out", brand.id, source="unsubscribe",
                   purpose="marketing", delivery_execution_id=executions[1].id)
    # A provider suppression linked to a delivery is a bounce or complaint, not an unsubscribe.
    record_consent(db, executions[2].recipient_id, "opted_out", brand.id, source="provider",
                   purpose="marketing", delivery_execution_id=executions[2].id)
    # An unsubscribe with no delivery cannot be placed.
    record_consent(db, executions[2].recipient_id, "opted_out", brand.id, source="unsubscribe", purpose="marketing")
    shown = _results(db, campaign["campaign"].id, brand.id)
    assert _figures(shown, "Main")["unsubscribes"] == 2
    assert shown["campaign"]["unsubscribes"] == 2


def test_sends_before_the_attribution_are_flagged(db, campaign, monkeypatch):
    since = datetime.now(UTC) - timedelta(hours=1)
    monkeypatch.setattr(results, "UNSUBSCRIBES_COUNTED_SINCE", since)
    campaign["send"](campaign["email"], [("sent", None)])
    assert _results(db, campaign["campaign"].id, campaign["brand"].id)["unsubscribes_partial"] is False
    campaign["send"](campaign["push"], [("sent", None)], created_at=since - timedelta(minutes=1))
    shown = _results(db, campaign["campaign"].id, campaign["brand"].id)
    assert shown["unsubscribes_partial"] is True
    assert shown["unsubscribes_counted_since"] == since


@pytest.fixture
def sent(db, world):
    """One marketing email sent to one consenting person, through the real send."""
    variant = world["variant"]("email", static=True, slots=0)
    person = world["person"]("email")
    world["send"](variant, [person])
    db.expire_all()
    execution = (db.query(DeliveryExecutionDB).filter_by(recipient_id=person.id)
                 .order_by(DeliveryExecutionDB.id.desc()).first())
    return execution, person


def _linked(db, execution_id, source):
    db.expire_all()
    return (db.query(ConsentEventDB).filter(ConsentEventDB.delivery_execution_id == execution_id,
                                            ConsentEventDB.source == source).all())


def test_the_unsubscribe_link_records_its_delivery(db, sent):
    execution, _ = sent
    api.post(f"/unsubscribe/{execution.unsubscribe_token}", data={"scope": "brand"})
    assert len(_linked(db, execution.id, "unsubscribe")) == 1


def test_an_everything_opt_out_links_every_row_to_its_delivery(db, sent):
    execution, person = sent
    before = settings.get_unsubscribe_offer_everything(db)
    settings.set_unsubscribe_offer_everything(db, True)
    try:
        api.post(f"/unsubscribe/{execution.unsubscribe_token}", data={"scope": "everything"})
    finally:
        settings.set_unsubscribe_offer_everything(db, before)
    rows = (db.query(ConsentEventDB).filter(ConsentEventDB.recipient_id == person.id,
                                            ConsentEventDB.source == "unsubscribe").all())
    assert len(rows) > 1 and {r.delivery_execution_id for r in rows} == {execution.id}


def test_a_provider_suppression_records_its_delivery(db, world):
    from app.snapshots.service import create_snapshot_for_variant

    brand = world["brand"]
    person = world["person"]()
    variant = world["variant"](static=True, slots=0)
    snapshot = create_snapshot_for_variant(db, variant.id, brand_id=brand.id)
    world["made"]["snapshots"].append(snapshot.id)
    send = SendInstanceDB(snapshot_id=snapshot.id, brand_id=brand.id, name="task-58", status="sent", provider="mock")
    db.add(send)
    db.flush()
    world["made"]["sends"].append(send.id)
    message_id = f"msg-{uuid.uuid4().hex}"
    execution = DeliveryExecutionDB(send_instance_id=send.id, recipient_id=person.id, status="sent", provider="mock",
                                    channel="email", purpose="marketing", provider_message_id=message_id)
    db.add(execution)
    db.commit()
    try:
        process_provider_webhook_event(db, NormalizedEvent(
            provider="resend", provider_message_id=message_id, event_type="complaint",
            provider_event_id=f"{message_id}:complaint", event_data={}, suppresses_consent=True))
        db.commit()
        assert len(_linked(db, execution.id, "provider")) == 1
    finally:
        db.rollback()
        db.query(EngagementEventDB).filter(EngagementEventDB.delivery_execution_id == execution.id).delete()
        db.commit()


# --- through the API --------------------------------------------------------------------

def test_the_route_answers_for_the_working_brand(db, campaign):
    campaign["send"](campaign["email"], [("sent", None)] * 2)
    with signed_in(db) as (cookied, _token, _csrf):
        response = cookied.get(f"/campaigns/{campaign['campaign'].id}/results")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["variants"][0]["sent"] == 2 and body["campaign"]["sent"] == 2


def test_another_brands_campaign_is_not_found(db, campaign, foreign_brand):
    campaign["campaign"].brand_id = foreign_brand.id
    db.commit()
    try:
        with signed_in(db) as (cookied, _token, _csrf):
            response = cookied.get(f"/campaigns/{campaign['campaign'].id}/results")
        assert response.status_code == 404
    finally:
        campaign["campaign"].brand_id = campaign["brand"].id
        db.commit()


def test_an_integration_cannot_read_results(db, campaign):
    """Reporting stays behind `view`, which integrations never hold."""
    with machine([SENDS_PLAN]) as headers:
        response = api.get(f"/campaigns/{campaign['campaign'].id}/results", headers=headers)
    assert response.status_code == 403


def test_the_date_is_after_the_migration():
    assert results.UNSUBSCRIBES_COUNTED_SINCE.tzinfo is not None
    assert results.UNSUBSCRIBES_COUNTED_SINCE >= datetime(2026, 10, 11, tzinfo=UTC)
