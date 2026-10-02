"""Where are my campaigns — the monitoring read model (task-216).

Manager Workflow interview Q5.4 split monitoring from deliveries: monitoring is
campaign-level and answers *where are my campaigns*, including ones that have
sent nothing; deliveries is send-level. Nothing stored answers it —
`CampaignDB.status` is set at creation and never moves — so it is derived from
variants, their snapshots and their sends.

The definition of "in flight" was decided 2026-10-02: **approved but not
finished** — any variant with a snapshot not yet sent, or a send that is
planned, scheduled or sending.

Runs against the shared dev database like the rest of the suite; every row
created here wears PREFIX and is removed in `finally`.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.auth import service as auth
from app.auth.db_models import BrandDB
from app.campaigns import monitoring
from app.campaigns.db_models import CampaignDB, VariantDB
from app.database import SessionLocal
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.recipients.db_models import RecipientDB  # noqa: F401 — mapper registration
from app.snapshots.db_models import SnapshotDB
from app.snapshots.service import INLINE_LOCATION

PREFIX = "montest"


@pytest.fixture
def db():
    session = SessionLocal()
    auth.bootstrap(session)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def build(db):
    """`build(variants=[...])` makes one campaign; each variant is a list of
    what happened to it: "snapshot", or a send status ("draft", "scheduled",
    "sending", "sent", "partial_failed", …) which implies its own snapshot."""
    made: list[int] = []
    brand = auth.ensure_default_brand(db)

    def make(variants, brand_id=None):
        campaign = CampaignDB(name=f"{PREFIX}-{uuid.uuid4().hex[:8]}", status="draft",
                              brand_id=brand_id or brand.id)
        db.add(campaign)
        db.flush()
        made.append(campaign.id)
        for index, history in enumerate(variants):
            variant = VariantDB(campaign_id=campaign.id, channel="email",
                                name=f"V{index}", status="draft")
            db.add(variant)
            db.flush()
            for event in history:
                snapshot = SnapshotDB(variant_id=variant.id, artifact_storage_type="inline",
                                      artifact_location=INLINE_LOCATION, artifact_size=0)
                db.add(snapshot)
                db.flush()
                if event == "snapshot":
                    continue
                send = SendInstanceDB(
                    brand_id=campaign.brand_id, snapshot_id=snapshot.id, name="s",
                    status=event,
                    scheduled_at=(datetime.now(timezone.utc) + timedelta(days=1)
                                  if event == "scheduled" else None),
                )
                db.add(send)
                db.flush()
        db.commit()
        return campaign

    yield make

    db.rollback()
    for campaign_id in made:
        variant_ids = [v.id for v in db.query(VariantDB).filter(VariantDB.campaign_id == campaign_id)]
        snapshot_ids = [s.id for s in db.query(SnapshotDB).filter(SnapshotDB.variant_id.in_(variant_ids))]
        send_ids = [s.id for s in db.query(SendInstanceDB).filter(SendInstanceDB.snapshot_id.in_(snapshot_ids))]
        db.query(DeliveryExecutionDB).filter(DeliveryExecutionDB.send_instance_id.in_(send_ids)).delete(
            synchronize_session=False)
        db.query(SendInstanceDB).filter(SendInstanceDB.id.in_(send_ids)).delete(synchronize_session=False)
        db.query(SnapshotDB).filter(SnapshotDB.id.in_(snapshot_ids)).delete(synchronize_session=False)
        db.query(VariantDB).filter(VariantDB.id.in_(variant_ids)).delete(synchronize_session=False)
        db.query(CampaignDB).filter(CampaignDB.id == campaign_id).delete(synchronize_session=False)
    db.commit()


@pytest.fixture
def other_brand(db):
    """A second brand. Requested BEFORE `build` in a test's arguments, so pytest
    tears it down AFTER `build` has removed the campaign graph that points at
    it. Cleanup never re-assigns rows to another brand: on a shared dev
    database that would move whatever matched into a real brand."""
    brand = BrandDB(key=f"{PREFIX}-{uuid.uuid4().hex[:8]}", name="Monitoring other")
    db.add(brand)
    db.commit()
    yield brand
    db.rollback()
    db.query(BrandDB).filter(BrandDB.id == brand.id).delete()
    db.commit()


def _row(db, campaign, brand_id=None):
    rows = monitoring.campaign_monitoring(db, brand_id=brand_id or campaign.brand_id)
    return next((r for r in rows if r["id"] == campaign.id), None)


class TestTheCampaignState:
    def test_nothing_snapshotted_is_in_preparation(self, db, build):
        row = _row(db, build([[]]))
        assert row["state"] == "in_preparation"
        assert [v["stage"] for v in row["variants"]] == ["composing"]

    @pytest.mark.parametrize("history, stage", [
        (["snapshot"], "snapshotted"),
        (["draft"], "planned"),
        (["scheduled"], "scheduled"),
        (["sending"], "sending"),
    ])
    def test_approved_but_not_finished_is_in_flight(self, db, build, history, stage):
        row = _row(db, build([history]))
        assert row["state"] == "in_flight", history
        assert row["variants"][0]["stage"] == stage

    def test_a_scheduled_send_says_when(self, db, build):
        row = _row(db, build([["scheduled"]]))
        assert row["next_scheduled_at"] is not None

    def test_only_finished_sends_is_sent(self, db, build):
        row = _row(db, build([["sent"]]))
        assert row["state"] == "sent" and row["has_failures"] is False
        assert row["variants"][0]["stage"] == "sent"

    def test_a_partly_failed_send_is_sent_and_flagged(self, db, build):
        row = _row(db, build([["partial_failed"]]))
        assert row["state"] == "sent" and row["has_failures"] is True
        assert row["variants"][0]["has_failures"] is True

    def test_a_new_snapshot_after_a_send_is_in_flight_again(self, db, build):
        """The weekly case: last week's send finished, this week's snapshot is
        waiting. The variant's furthest-along fact is the waiting one."""
        row = _row(db, build([["sent", "snapshot"]]))
        assert row["state"] == "in_flight"
        assert row["variants"][0]["stage"] == "snapshotted"

    def test_one_variant_in_flight_puts_the_campaign_in_flight(self, db, build):
        row = _row(db, build([["sent"], ["snapshot"], []]))
        assert row["state"] == "in_flight"
        assert [v["stage"] for v in row["variants"]] == ["sent", "snapshotted", "composing"]


class TestTheList:
    def test_in_flight_comes_first(self, db, build):
        # Created in reverse of the expected order, so "newest first" alone
        # would put sent first: only the state ordering can pass this.
        flying = build([["scheduled"]])
        preparing = build([[]])
        sent = build([["sent"]])
        ours = {sent.id, preparing.id, flying.id}
        order = [r["id"] for r in monitoring.campaign_monitoring(db, brand_id=sent.brand_id)
                 if r["id"] in ours]
        assert order == [flying.id, preparing.id, sent.id]

    def test_another_brands_campaign_is_absent(self, db, other_brand, build):
        theirs = build([["scheduled"]], brand_id=other_brand.id)
        default_id = auth.ensure_default_brand(db).id
        assert _row(db, theirs, brand_id=default_id) is None
        assert _row(db, theirs, brand_id=other_brand.id) is not None


class TestOverJson:
    def test_a_viewer_can_read_it(self, db, build):
        from fastapi.testclient import TestClient

        from app.auth.db_models import RoleAssignmentDB, RoleDB, SessionDB, UserDB
        from app.auth.permissions import VIEWER
        from main import app

        campaign = build([["scheduled"]])
        user = UserDB(email=f"mon-{uuid.uuid4().hex[:10]}@example.invalid", is_active=True)
        db.add(user)
        db.commit()
        role = db.query(RoleDB).filter(RoleDB.key == VIEWER).one()
        db.add(RoleAssignmentDB(user_id=user.id, role_id=role.id, brand_id=campaign.brand_id))
        db.commit()
        try:
            token = auth.create_session(db, user)
            auth.set_session_brand(db, token, campaign.brand_id)
            client = TestClient(app, raise_server_exceptions=False)
            client.cookies.set(auth.SESSION_COOKIE, token)
            response = client.get("/campaigns/monitoring")
            assert response.status_code == 200, response.text
            row = next(r for r in response.json() if r["id"] == campaign.id)
            assert row["state"] == "in_flight"
            assert row["variants"][0]["stage"] == "scheduled"
        finally:
            db.query(SessionDB).filter(SessionDB.user_id == user.id).delete()
            db.query(RoleAssignmentDB).filter(RoleAssignmentDB.user_id == user.id).delete()
            db.query(UserDB).filter(UserDB.id == user.id).delete()
            db.commit()
