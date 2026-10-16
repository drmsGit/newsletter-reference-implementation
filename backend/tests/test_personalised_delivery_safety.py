"""Per-recipient merge values and partial exclusion (task-365; ADR-199/183)."""
from app.content.db_models import ContentVersionDB
from app.delivery.db_models import DeliveryExecutionDB
from app.delivery.exclusion import REASON_PERSONAL_MISSING, STAGE_RENDER
from app.delivery.service import reconstruct_delivery
from tests.test_personalised_rendering import db, setup, world  # noqa: F401


def test_one_send_keeps_each_recipients_values_separate(db, world, setup):  # noqa: F811
    anna = setup["person"]("female", "Anna", "Müller", picks=True)
    ben = setup["person"]("male", "Ben", "Weber", picks=True)
    expected = {person.id: {name: setup["says"](name, person)
                            for name in ("salutation_formal", "salutation_informal")}
                for person in (anna, ben)}
    send, rows = world["send"](setup["variant"], [anna, ben])
    assert rows == {anna.id: ("sent", None), ben.id: ("sent", None)}
    assert len(world["delivered"]) == 2
    executions = db.query(DeliveryExecutionDB).filter_by(send_instance_id=send.id).all()
    assert len(executions) == 2
    for execution in executions:
        values = expected[execution.recipient_id]
        assert execution.delivery_record["personal"] == values
        rebuilt = reconstruct_delivery(db, execution.id, brand_id=setup["brand"].id)
        assert rebuilt["hash_matches"] is True
        assert rebuilt["envelope"]["subject"] == values["salutation_formal"] + " news"
        assert values["salutation_informal"] + " go" in rebuilt["body"]
        other_id = ben.id if execution.recipient_id == anna.id else anna.id
        assert expected[other_id]["salutation_informal"] not in rebuilt["body"]


def test_a_missing_pick_language_excludes_only_its_recipient(db, world, setup):  # noqa: F811
    bad = setup["person"]("female", "Anna", "Müller", picks=True)
    healthy = setup["person"]("male", "Ben", "Weber", picks=False)
    version = db.query(ContentVersionDB).filter_by(content_record_id=world["made"]["records"][0]).order_by(
        ContentVersionDB.version_number.desc()).first()
    original = version.content
    version.content = {**original, "headline_medium": "{{unavailable_in_this_language}}"}
    db.commit()
    try:
        send, rows = world["send"](setup["variant"], [bad, healthy])
    finally:
        version.content = original
        db.commit()
    assert rows[bad.id] == ("excluded", f"{STAGE_RENDER}: {REASON_PERSONAL_MISSING}: "
                            "{{unavailable_in_this_language}}")
    assert rows[healthy.id] == ("sent", None)
    assert len(world["delivered"]) == 1
    executions = db.query(DeliveryExecutionDB).filter_by(send_instance_id=send.id).all()
    sent = next(row for row in executions if row.recipient_id == healthy.id)
    refused = next(row for row in executions if row.recipient_id == bad.id)
    assert refused.delivery_record is None and refused.artifact_hash is None
    rebuilt = reconstruct_delivery(db, sent.id, brand_id=setup["brand"].id)
    assert rebuilt["hash_matches"] is True
    assert "unavailable_in_this_language" not in rebuilt["body"]
    assert sent.delivery_record["personal"]["salutation_informal"] == setup["says"]("salutation_informal", healthy)
