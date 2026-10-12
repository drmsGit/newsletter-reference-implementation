"""Changed ranked sets cannot change a frozen send (ADR-084 and ADR-183)."""
from copy import deepcopy

import pytest

from app.decision import sets
from app.delivery.service import reconstruct_delivery
from tests.test_several_picks import (  # noqa: F401
    _configure, _execution, _picked, _slots, catalogue, db, world,
)


@pytest.mark.parametrize("exhausted", [False, True], ids=["shrink", "exhaust"])
def test_a_changed_set_drops_stale_copies_but_keeps_the_earlier_send(
    db, world, catalogue, exhausted,  # noqa: F811
):
    category, (a, b, c) = catalogue([9, 7, 5])
    variant = world["variant"](static=True, slots=1)
    [slot] = _slots(db, variant)
    _configure(db, slot, [category], 3)
    person = world["person"]()
    world["send"](variant, [person])
    first = _execution(db, person)
    first_id = first.id
    frozen_record = deepcopy(first.delivery_record)
    assert _picked(first) == [(a, 1), (b, 2), (c, 3)]
    before = reconstruct_delivery(db, first_id, brand_id=world["brand"].id)
    assert before["hash_matches"] is True

    if exhausted:
        empty_category, _ = catalogue([])
        _configure(db, slot, [empty_category], 3)
    else:
        _configure(db, slot, [category], 1)
    _, outcomes = world["send"](variant, [person])
    assert outcomes[person.id] == ("sent", None), "the static module remains sendable"
    latest = _execution(db, person)
    assert latest.id != first_id
    assert _picked(latest) == ([] if exhausted else [(a, 1)])
    if not exhausted:
        assert [r.content_record_id for r in sets.own_set(db, slot.id, None)] == [a]

    db.refresh(first)
    assert first.delivery_record == frozen_record
    after = reconstruct_delivery(db, first_id, brand_id=world["brand"].id)
    assert after["hash_matches"] is True
    assert after["body"] == before["body"]
    assert after["modules"] == before["modules"]
