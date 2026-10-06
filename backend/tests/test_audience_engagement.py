"""Audience rules can read engagement history (task-296).

ADR-188 points 4 and 5, decided with the user on 2026-10-06: an engagement
field says what happened — received, opened or clicked — to which mailing —
a specific send, any send of a campaign, or any send on the channel — and
when — absolute or relative. "Received" means handed to the provider and not
bounced (the user, 2026-10-06): excluded and failed deliveries never count, a
bounce removes the person. "Did not" is a leave-out rule. Closes task-215.

Fixture (all agreed to email with this brand), sends S1 (campaign A) and S2
(campaign B), and a foreign brand's send:
  anna  S1 sent 5 days ago; opened and clicked it 2 days ago
  ben   S1 sent 40 days ago, then bounced
  cleo  S1 excluded
  dan   S2 sent 10 days ago; opened it
  eve   S2 failed
  gus   S1 sent 5 days ago; did nothing
  fred  the foreign brand's send, sent 3 days ago (and agreed with this brand
        too, so only the brand check keeps that send out)
  hank  a push delivery only, sent 3 days ago (agreed to email: only the
        channel check keeps it out of "any email send")
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.audience import service as audience
from app.audience.db_models import AudienceGroupDB, AudienceRuleBlockDB
from app.campaigns.db_models import CampaignDB, VariantDB
from app.database import SessionLocal
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.insight.db_models import EngagementEventDB
from app.recipients.consent import record_consent
from app.recipients.db_models import ConsentEventDB, RecipientDB
from app.snapshots.db_models import SnapshotDB

TAG = f"eng{uuid.uuid4().hex[:6]}"
NOW = datetime.now(timezone.utc)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def world(db, default_brand, foreign_brand):
    made = {"campaigns": [], "variants": [], "snapshots": [], "sends": [], "executions": [], "recipients": [],
            "groups": []}

    def send(brand_id, name, channel="email"):
        campaign = CampaignDB(brand_id=brand_id, name=f"{TAG}-{name}")
        db.add(campaign); db.flush()
        variant = VariantDB(campaign_id=campaign.id, channel=channel, name="v", status="draft")
        db.add(variant); db.flush()
        snapshot = SnapshotDB(variant_id=variant.id)
        db.add(snapshot); db.flush()
        si = SendInstanceDB(name=f"{TAG}-{name}", status="sent", brand_id=brand_id, snapshot_id=snapshot.id,
                            provider="mock")
        db.add(si); db.flush()
        made["campaigns"].append(campaign.id); made["variants"].append(variant.id)
        made["snapshots"].append(snapshot.id); made["sends"].append(si.id)
        return campaign, si

    camp_a, s1 = send(default_brand.id, "A")
    camp_b, s2 = send(default_brand.id, "B")
    _, foreign = send(foreign_brand.id, "F")
    _, push_send = send(default_brand.id, "P", channel="push")
    people = {}

    def person(name, brand_id):
        r = RecipientDB(external_id=f"{TAG}-{name}", status="active", language=f"{TAG}-de")
        db.add(r); db.flush()
        record_consent(db, r.id, "opted_in", brand_id, channel="email", source="test", note="eng", commit=False,
                       purpose="marketing")
        made["recipients"].append(r.id)
        people[name] = r
        return r

    def execution(r, si, status, days_ago=None):
        ex = DeliveryExecutionDB(send_instance_id=si.id, recipient_id=r.id, status=status, channel="email",
                                 purpose="marketing",
                                 sent_at=NOW - timedelta(days=days_ago) if days_ago is not None else None)
        db.add(ex); db.flush()
        made["executions"].append(ex.id)
        return ex

    def event(ex, kind, days_ago):
        db.add(EngagementEventDB(delivery_execution_id=ex.id, event_type=kind,
                                 occurred_at=NOW - timedelta(days=days_ago)))

    b = default_brand.id
    a_ex = execution(person("anna", b), s1, "sent", 5)
    event(a_ex, "open", 2); event(a_ex, "click", 2)
    event(execution(person("ben", b), s1, "sent", 40), "bounce", 39)
    execution(person("cleo", b), s1, "excluded")
    event(execution(person("dan", b), s2, "sent", 10), "open", 9)
    execution(person("eve", b), s2, "failed")
    execution(person("gus", b), s1, "sent", 5)
    fred = person("fred", foreign_brand.id)
    record_consent(db, fred.id, "opted_in", b, channel="email", source="test", note="eng", commit=False,
                   purpose="marketing")
    execution(fred, foreign, "sent", 3)
    hank = person("hank", b)
    push = DeliveryExecutionDB(send_instance_id=push_send.id, recipient_id=hank.id, status="sent", channel="push",
                               purpose="marketing", sent_at=NOW - timedelta(days=3))
    db.add(push); db.flush()
    made["executions"].append(push.id)
    db.commit()
    yield {"people": people, "s1": s1, "s2": s2, "foreign": foreign, "camp_a": camp_a, "camp_b": camp_b,
           "brand": b, "made": made}
    db.rollback()
    db.query(AudienceRuleBlockDB).filter(AudienceRuleBlockDB.group_id.in_(made["groups"])).delete(synchronize_session=False)
    db.query(AudienceGroupDB).filter(AudienceGroupDB.id.in_(made["groups"])).delete(synchronize_session=False)
    db.query(EngagementEventDB).filter(EngagementEventDB.delivery_execution_id.in_(made["executions"])).delete(
        synchronize_session=False)
    db.query(DeliveryExecutionDB).filter(DeliveryExecutionDB.id.in_(made["executions"])).delete(synchronize_session=False)
    db.query(SendInstanceDB).filter(SendInstanceDB.id.in_(made["sends"])).delete(synchronize_session=False)
    db.query(SnapshotDB).filter(SnapshotDB.id.in_(made["snapshots"])).delete(synchronize_session=False)
    db.query(VariantDB).filter(VariantDB.id.in_(made["variants"])).delete(synchronize_session=False)
    db.query(CampaignDB).filter(CampaignDB.id.in_(made["campaigns"])).delete(synchronize_session=False)
    db.query(ConsentEventDB).filter(ConsentEventDB.recipient_id.in_(made["recipients"])).delete(synchronize_session=False)
    db.query(RecipientDB).filter(RecipientDB.id.in_(made["recipients"])).delete(synchronize_session=False)
    db.commit()


def _who(db, world, engagement, channel="email", **more):
    criteria = audience.normalise_criteria({"engagement": engagement, **more})
    names = {r.id: n for n, r in world["people"].items()}
    return {names[r.id] for r in audience.find_by_criteria(
        db, world["brand"], channel=channel, language=criteria.get("language"),
        engagement=criteria["engagement"]) if r.id in names}


class TestWhatHappened:
    def test_received_means_sent_and_not_bounced(self, db, world):
        """Excluded and failed never count; a bounce removes the person."""
        assert _who(db, world, {"event": "received", "send_instance_id": world["s1"].id}) == {"anna", "gus"}

    def test_opened_and_clicked(self, db, world):
        assert _who(db, world, {"event": "clicked", "send_instance_id": world["s1"].id}) == {"anna"}
        assert _who(db, world, {"event": "opened"}) == {"anna", "dan"}


class TestWhichMailing:
    def test_any_send_on_the_channel_and_only_this_brands(self, db, world):
        assert _who(db, world, {"event": "received"}) == {"anna", "gus", "dan"}

    def test_any_send_of_a_campaign(self, db, world):
        assert _who(db, world, {"event": "received", "campaign_id": world["camp_b"].id}) == {"dan"}

    def test_another_brands_send_matches_nobody(self, db, world):
        assert _who(db, world, {"event": "received", "send_instance_id": world["foreign"].id}) == set()

    def test_any_send_is_on_the_resolution_channel(self, db, world):
        assert _who(db, world, {"event": "received"}, channel="push") == set()


class TestWhen:
    def test_relative(self, db, world):
        assert _who(db, world, {"event": "received", "within_days": 7}) == {"anna", "gus"}
        assert _who(db, world, {"event": "received", "more_than_days": 7}) == {"dan"}

    def test_absolute(self, db, world):
        start, end = (NOW - timedelta(days=12)).date(), (NOW - timedelta(days=8)).date()
        assert _who(db, world, {"event": "received", "from": start.isoformat(), "to": end.isoformat()}) == {"dan"}
        assert _who(db, world, {"event": "clicked", "from": (NOW - timedelta(days=3)).date().isoformat()}) == {"anna"}
        # "to" covers its whole day: a single-day period on the day S1 went out finds both.
        day = (NOW - timedelta(days=5)).date().isoformat()
        assert _who(db, world, {"event": "received", "from": day, "to": day}) == {"anna", "gus"}


def test_it_combines_with_the_other_fields(db, world):
    db.query(RecipientDB).filter_by(id=world["people"]["gus"].id).update({"language": f"{TAG}-fr"}); db.commit()
    assert _who(db, world, {"event": "received", "send_instance_id": world["s1"].id},
                language=[f"{TAG}-de"]) == {"anna"}


def test_did_not_is_a_leave_out_rule_and_the_arithmetic_follows(db, world):
    """Received S1 but did not click it: include received, leave out clicked."""
    group = AudienceGroupDB(brand_id=world["brand"], name=f"{TAG}-reminder")
    db.add(group); db.commit()
    world["made"]["groups"].append(group.id)
    s1 = world["s1"].id
    audience.add_block(db, group.id, kind="include", criteria={"engagement": {"event": "received", "send_instance_id": s1}},
                       brand_id=world["brand"])
    audience.add_block(db, group.id, kind="exclude", criteria={"engagement": {"event": "clicked", "send_instance_id": s1}},
                       brand_id=world["brand"])
    resolved = {r.id for r in audience.resolve_audience(db, group.id, "email")}
    assert resolved == {world["people"]["gus"].id}
    numbers = audience.audience_arithmetic(db, group.id, "email")
    assert (numbers["matched_rules"], numbers["removed_by_exclusion"], numbers["total"]) == (2, 1, 1)
    rows = audience.audience_memberships(db, world["people"]["anna"].id, brand_id=world["brand"], channel="email")
    assert [r["member"] for r in rows if r["group_id"] == group.id] == [False]


@pytest.mark.parametrize("engagement, field", [
    ({"event": "forwarded"}, "event"),
    ({}, "event"),
    ({"event": "received", "send_instance_id": 1, "campaign_id": 1}, "campaign_id"),
    ({"event": "received", "within_days": 7, "more_than_days": 30}, "more_than_days"),
    ({"event": "received", "within_days": 7, "from": "2026-01-01"}, "within_days"),
    ({"event": "received", "from": "2026-02-01", "to": "2026-01-01"}, "to"),
    ({"event": "received", "within_days": 0}, "within_days"),
    ({"event": "received", "from": "yesterday"}, "from"),
    ({"event": "received", "colour": "red"}, "colour"),
])
def test_an_engagement_that_does_not_say_something_meaningful_is_refused(engagement, field):
    with pytest.raises(audience.CriteriaInvalid) as refused:
        audience.normalise_criteria({"engagement": engagement})
    assert field in str(refused.value)
