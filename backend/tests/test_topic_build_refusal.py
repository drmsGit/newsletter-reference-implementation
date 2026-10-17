"""A refused topic build must leave the variant unchanged (ADR-141 §5; ADR-199)."""
from app.audit.db_models import AuditEventDB
from app.campaigns.db_models import DecisionSlotDB
from tests import test_variant_from_topic as fixtures
from tests.test_api_guard import signed_in

db = fixtures.db
world = fixtures.world
model = fixtures.model


def test_invalid_editorial_refuses_before_saving_the_envelope_or_hero(db, world, model):
    variant = world["variant"]
    model["reply"] = fixtures._reply(world)
    with signed_in(db) as (client, _token, csrf):
        asked = fixtures._ask(client, csrf, variant.id)
        assert asked.status_code == 200, asked.text
        run_id = asked.json()["ai_run_id"]
        before = fixtures._stack(db, variant.id)
        before_slots = db.query(DecisionSlotDB.id).filter_by(variant_id=variant.id).all()
        before_audit = {row.id for row in db.query(AuditEventDB).all()}
        # Real field validation, without injected failures: this expression
        # is not in the brand's dictionary and cannot be saved in editorial.
        response = fixtures._build(client, csrf, variant.id, run_id,
                                   editorial="A weekend for {{unknown_topic_build_entry}}.")
        assert response.status_code == 422, response.text
    assert fixtures._stack(db, variant.id) == before, "a refused build persisted part of the proposed stack"
    assert db.query(DecisionSlotDB.id).filter_by(variant_id=variant.id).all() == before_slots
    new_entries = db.query(AuditEventDB).filter(AuditEventDB.id.notin_(before_audit)).all()
    assert not [entry for entry in new_entries if (entry.detail or {}).get("ai_run_id") == run_id]
