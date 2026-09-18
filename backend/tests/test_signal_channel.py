"""Channel affinity — ADR-164 point 9, built 2026-09-18.

"`SignalContributionDB` gains an explicit `channel` column, and it does not
change the topic score." One append-only log read along two axes: topic
affinity sums over categories ignoring channel, because interest in hiking is
interest in hiking wherever it was clicked; channel affinity sums over channels
ignoring category, and is what lets the decision layer eventually choose a
channel per recipient.

The test worth reading is `test_a_declared_preference_has_no_channel_and_is_not
_counted_as_one`. A null here means **not applicable**, not unknown — a
manually declared preference happened on no channel at all, and bucketing it
under any channel would invent an engagement nobody had.
"""
import uuid
from datetime import datetime, timezone

import pytest

from app.auth import service as auth
from app.content.db_models import CategoryDB, ContentRecordDB
from app.content.service import create_category, create_content
from app.database import SessionLocal
from app.insight.signals import (
    channel_affinity, get_operational_signal, operational_signals_for_recipient,
    record_contribution,
)
from app.recipients.db_models import RecipientDB, SignalContributionDB
# Imported for their side effect as much as their use: `signal_contributions`
# has a foreign key to `engagement_events` and `send_instances` one to
# `audience_groups`, and SQLAlchemy cannot configure the mappers until those
# tables are registered. Without them the first query fails with a
# NoReferencedTableError that reads like a schema problem and is not one.
from app.audience.db_models import AudienceGroupDB  # noqa: F401
from app.insight.db_models import EngagementEventDB
from app.snapshots.db_models import SnapshotDB  # noqa: F401

PREFIX = "sigchan"


@pytest.fixture
def db():
    session = SessionLocal()
    auth.bootstrap(session)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module", autouse=True)
def _sweep():
    """Last line of defence, and it earned its place immediately.

    `scenario` below creates a recipient and a category before the first
    statement that can fail, so a setup error leaves both behind — pytest runs
    a fixture's teardown only if it reached its `yield`. Three failing debug
    runs of this very file leaked thirteen of each into the shared dev
    database before this existed.
    """
    yield
    session = SessionLocal()
    try:
        _purge(session)
    finally:
        session.close()


def _purge(session):
    """Everything this file can create, in foreign-key order.

    Order is the whole content of this function: a category cannot be deleted
    while a content assignment points at it, and the first version of this
    sweep tried and failed on exactly that.
    """
    from app.content.db_models import ContentCategoryAssignmentDB
    from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB

    recipient_ids = [r.id for r in session.query(RecipientDB).filter(
        RecipientDB.external_id.like(f"{PREFIX}%")).all()]
    category_ids = [c.id for c in session.query(CategoryDB).filter(
        CategoryDB.name.like(f"{PREFIX}%")).all()]
    content_ids = [r.id for r in session.query(ContentRecordDB).filter(
        ContentRecordDB.title.like(f"{PREFIX}%")).all()]
    send_ids = [s.id for s in session.query(SendInstanceDB).filter(
        SendInstanceDB.name.like(f"{PREFIX}%")).all()]
    execution_ids = [e.id for e in session.query(DeliveryExecutionDB).filter(
        DeliveryExecutionDB.send_instance_id.in_(send_ids or [-1])).all()]

    session.query(SignalContributionDB).filter(
        SignalContributionDB.recipient_id.in_(recipient_ids or [-1])).delete(synchronize_session=False)
    session.query(EngagementEventDB).filter(
        EngagementEventDB.delivery_execution_id.in_(execution_ids or [-1])).delete(synchronize_session=False)
    session.query(DeliveryExecutionDB).filter(
        DeliveryExecutionDB.id.in_(execution_ids or [-1])).delete(synchronize_session=False)
    session.query(SendInstanceDB).filter(
        SendInstanceDB.id.in_(send_ids or [-1])).delete(synchronize_session=False)
    session.query(ContentCategoryAssignmentDB).filter(
        ContentCategoryAssignmentDB.category_id.in_(category_ids or [-1])).delete(synchronize_session=False)
    session.query(ContentCategoryAssignmentDB).filter(
        ContentCategoryAssignmentDB.content_id.in_(content_ids or [-1])).delete(synchronize_session=False)
    session.query(ContentRecordDB).filter(
        ContentRecordDB.id.in_(content_ids or [-1])).delete(synchronize_session=False)
    session.query(RecipientDB).filter(
        RecipientDB.id.in_(recipient_ids or [-1])).delete(synchronize_session=False)
    session.query(CategoryDB).filter(
        CategoryDB.id.in_(category_ids or [-1])).delete(synchronize_session=False)
    session.commit()


@pytest.fixture
def scenario(db):
    """One recipient, one category, and contributions on two channels."""
    brand = auth.ensure_default_brand(db)
    category = create_category(db, name=f"{PREFIX}-{uuid.uuid4().hex[:8]}")
    recipient = RecipientDB(external_id=f"{PREFIX}-{uuid.uuid4().hex[:8]}", status="active")
    db.add(recipient); db.commit(); db.refresh(recipient)
    made = []
    now = datetime.now(timezone.utc)
    for channel, weight in (("email", 5.0), ("email", 5.0), ("push", 3.0)):
        made.append(record_contribution(
            db, recipient_id=recipient.id, category_id=category.id,
            contribution_type="click", base_weight=weight, occurred_at=now,
            source="engagement", channel=channel))
    yield recipient, category, made
    db.query(SignalContributionDB).filter(
        SignalContributionDB.recipient_id == recipient.id).delete(synchronize_session=False)
    db.query(RecipientDB).filter(RecipientDB.id == recipient.id).delete()
    db.query(CategoryDB).filter(CategoryDB.id == category.id).delete()
    db.commit()


def test_the_topic_score_is_unchanged_by_the_new_axis(db, scenario):
    """**The claim in the ADR's own title for point 9.** Channel affinity is a
    second reading of the same log, not a second weighting of it — if adding
    the column moved a topic score, every decision strategy reading it would
    quietly shift."""
    recipient, category, made = scenario
    at = datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc)
    topic = get_operational_signal(db, recipient.id, category.id, now=at)
    total = sum(channel_affinity(db, recipient.id, now=at).values())
    assert topic == pytest.approx(total), (
        "the two axes read different totals from one log — they must be the "
        "same contributions summed differently, not different data"
    )


def test_channel_affinity_sums_over_channels(db, scenario):
    recipient, _category, _made = scenario
    affinity = channel_affinity(db, recipient.id)
    assert set(affinity) == {"email", "push"}
    assert affinity["email"] > affinity["push"], (
        "two email clicks at weight 5 must outweigh one push tap at weight 3"
    )


def test_a_declared_preference_has_no_channel_and_is_not_counted_as_one(db, scenario):
    """**A null is "not applicable", not "unknown".** ADR-164 rejected deriving
    channel from `event_id` partly because a declared preference would answer
    *unknowable*; storing the absence explicitly is what makes it answerable.

    Excluded from channel affinity rather than bucketed: a declared preference
    is a real signal about a topic and no signal at all about a channel.
    """
    recipient, category, _made = scenario
    # **A fixed `now` for both reads.** Decay is computed continuously, so two
    # calls microseconds apart differ in the eighth decimal — comparing them
    # without pinning the clock measures the clock, not the change under test.
    at = datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc)
    before = channel_affinity(db, recipient.id, now=at)

    record_contribution(
        db, recipient_id=recipient.id, category_id=category.id,
        contribution_type="manual", base_weight=90.0, source="declared")

    after = channel_affinity(db, recipient.id, now=at)
    assert after == before, (
        "a declared preference changed a channel score — it happened on no "
        "channel, so counting it as one invents an engagement"
    )
    # ...but it very much counts towards the topic.
    assert get_operational_signal(db, recipient.id, category.id, now=at) > sum(before.values())


def test_the_engagement_path_records_the_executions_channel(db):
    """The column is only worth having if the write path fills it. The
    execution carries the real channel since ADR-160 point 4 was built."""
    from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
    from app.insight.service import apply_event_to_signals
    from app.content.service import assign_category_to_content

    brand = auth.ensure_default_brand(db)
    category = create_category(db, name=f"{PREFIX}-{uuid.uuid4().hex[:8]}")
    record = create_content(db, title=f"{PREFIX}-{uuid.uuid4().hex[:8]}",
                            brand_id=brand.id, content={"headline_medium": "x"})
    assign_category_to_content(db, content_id=record.id, category_id=category.id, score=10)
    recipient = RecipientDB(external_id=f"{PREFIX}-{uuid.uuid4().hex[:8]}", status="active")
    db.add(recipient); db.commit(); db.refresh(recipient)

    snapshot_id = db.query(SendInstanceDB.snapshot_id).limit(1).scalar()
    send = SendInstanceDB(snapshot_id=snapshot_id, brand_id=brand.id,
                          name=f"{PREFIX}-{uuid.uuid4().hex[:6]}", status="sent",
                          provider="mock")
    db.add(send); db.flush()
    execution = DeliveryExecutionDB(send_instance_id=send.id, recipient_id=recipient.id,
                                    status="sent", provider="mock", channel="push")
    db.add(execution); db.commit(); db.refresh(execution)
    # The content record travels in the event's data, not on the execution —
    # `apply_event_to_signals` reads it from there.
    event = EngagementEventDB(delivery_execution_id=execution.id, event_type="click",
                              provider="mock",
                              event_data={"content_record_id": record.id})
    db.add(event); db.commit(); db.refresh(event)

    try:
        apply_event_to_signals(db, event.id)
        rows = db.query(SignalContributionDB).filter(
            SignalContributionDB.event_id == event.id).all()
        assert rows, "the engagement produced no contribution"
        assert {r.channel for r in rows} == {"push"}, (
            f"the contribution recorded channel {[r.channel for r in rows]} — it "
            "must carry the channel the execution actually went out on"
        )
    finally:
        db.query(SignalContributionDB).filter(
            SignalContributionDB.recipient_id == recipient.id).delete(synchronize_session=False)
        db.query(EngagementEventDB).filter(EngagementEventDB.id == event.id).delete()
        db.query(DeliveryExecutionDB).filter(DeliveryExecutionDB.id == execution.id).delete()
        db.query(SendInstanceDB).filter(SendInstanceDB.id == send.id).delete()
        db.query(RecipientDB).filter(RecipientDB.id == recipient.id).delete()
        from app.content.db_models import ContentCategoryAssignmentDB
        db.query(ContentCategoryAssignmentDB).filter(
            ContentCategoryAssignmentDB.content_id == record.id).delete(synchronize_session=False)
        db.query(ContentRecordDB).filter(ContentRecordDB.id == record.id).delete()
        db.query(CategoryDB).filter(CategoryDB.id == category.id).delete()
        db.commit()
