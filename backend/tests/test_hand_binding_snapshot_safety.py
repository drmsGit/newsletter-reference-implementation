"""Manual exclusions follow the approved frame (ADR-176 and ADR-183)."""
import re

from app.campaigns.db_models import ModuleInstanceDB
from app.campaigns.service import create_module_for_variant
from app.delivery.service import reconstruct_delivery
from app.snapshots.service import create_snapshot_for_variant
from tests import test_render_skip as fixtures
from tests.test_several_picks import (  # noqa: F401
    _configure, _execution, _picked, _slots, catalogue,
)

db = fixtures.db
world = fixtures.world


def test_editing_a_manual_binding_after_approval_does_not_change_slot_exclusions(
    db, world, catalogue, monkeypatch,  # noqa: F811
):
    category, (a, b, c) = catalogue([9, 7, 5])
    variant = world["variant"](slots=1)
    [slot] = _slots(db, variant)
    _configure(db, slot, [category], 2)
    create_module_for_variant(
        db, variant_id=variant.id, module_type="single_stack",
        content_record_id=a, brand_id=world["brand"].id,
    )
    snapshot = create_snapshot_for_variant(db, variant.id, brand_id=world["brand"].id)
    # The approved frame shows A by hand. Live composition now shows B.
    manual = db.query(ModuleInstanceDB).filter_by(
        variant_id=variant.id, content_record_id=a,
    ).one()
    manual.content_record_id = b
    db.commit()
    # Reuse the approved snapshot in the existing mock-send fixture.
    monkeypatch.setattr(fixtures, "create_snapshot_for_variant", lambda *args, **kwargs: snapshot)
    person = world["person"]()
    _, outcomes = world["send"](variant, [person], skip=True)
    assert outcomes[person.id] == ("sent", None)
    execution = _execution(db, person)
    assert _picked(execution) == [(b, 1), (c, 2)]
    rebuilt = reconstruct_delivery(db, execution.id, brand_id=world["brand"].id)
    assert rebuilt["hash_matches"] is True
    assert [int(i) for i in re.findall(r'data-content-id="(\d+)"', rebuilt["body"])] == [b, c, a]
