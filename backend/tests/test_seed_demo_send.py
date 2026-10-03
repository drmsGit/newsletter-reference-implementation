"""The seeded Demo send is a send the system could have made (task-242).

`conftest` seeds the suite database with `seed_demo_data.seed()` before any
test runs, so these read what the seed left. The Demo send used to be written
by hand — `sent`, with no counts and no delivery records — and the deliveries
screen then showed "sent 0/0/0" beside 32 recipients whose "as sent" was empty.
"""
from app.database import SessionLocal
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.delivery.service import reconstruct_delivery, sent_content_ids
from app.insight.db_models import EngagementEventDB


def _demo(db):
    send = db.query(SendInstanceDB).filter(SendInstanceDB.name == "Demo send").one()
    executions = db.query(DeliveryExecutionDB).filter(
        DeliveryExecutionDB.send_instance_id == send.id).all()
    return send, executions


def test_its_counts_agree_with_its_executions():
    db = SessionLocal()
    try:
        send, executions = _demo(db)
        assert send.status == "sent"
        by_status = {s: sum(1 for x in executions if x.status == s) for s in ("sent", "failed", "excluded")}
        assert (send.sent_count, send.failed_count, send.excluded_count) == (
            by_status["sent"], by_status["failed"], by_status["excluded"])
        assert send.sent_count > 0
    finally:
        db.close()


def test_every_recipient_it_reached_can_be_shown_what_they_got():
    db = SessionLocal()
    try:
        send, executions = _demo(db)
        sent = [x for x in executions if x.status == "sent"]
        assert sent and all(x.delivery_record and x.sent_at for x in sent)
        # The as-sent view rebuilds rather than refusing (ADR-183).
        rebuilt = reconstruct_delivery(db, sent[0].id, brand_id=send.brand_id)
        assert rebuilt is not None and rebuilt["modules"]
    finally:
        db.close()


def test_its_clicks_name_only_what_was_sent_and_come_after_it():
    """ADR-182 / task-240: a click credits only content the message carried.
    And the history is after the send, which is dated back for that reason."""
    db = SessionLocal()
    try:
        send, executions = _demo(db)
        by_id = {x.id: x for x in executions}
        events = db.query(EngagementEventDB).filter(
            EngagementEventDB.delivery_execution_id.in_(list(by_id))).all()
        assert len(events) > 0, "the click history is gone"
        for event in events:
            execution = by_id[event.delivery_execution_id]
            named = (event.event_data or {}).get("content_record_id")
            assert named in (sent_content_ids(db, execution) or set()), event.id
            assert event.occurred_at >= execution.sent_at, event.id
    finally:
        db.close()
