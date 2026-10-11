"""A record placed by hand outranks a slot's pick of the same record (task-220;
ADR-176 addenda of 2026-10-09 and 2026-10-11, ADR-086 addendum 2026-10-11).

Decided with the user:
  - 2026-10-09: when a slot's pick is already bound by hand in the variant,
    the slot takes its next ranked pick, not "hide the module";
  - 2026-10-11: a slot showing several passes over the hand-bound record and
    still fills up to its number from further down, wherever the hand-bound
    module sits;
  - 2026-10-11: "Don't send if no slot resolved" was the wrong reading of the
    switch. It is for a fully dynamic variant that would show no content: a
    recipient is skipped only when no content record shows at all. One
    hand-picked record is enough to send. Typed-in modules do not count.
"""
from app.campaigns.service import create_module_for_variant
from app.delivery.exclusion import REASON_NO_PICK, STAGE_RENDER
from tests import test_render_skip as fixtures
from tests.test_several_picks import _configure, _execution, _picked, _slots, catalogue  # noqa: F401

db = fixtures.db
world = fixtures.world


def _bind(db, world, variant, record_id):
    create_module_for_variant(db, variant_id=variant.id, module_type="single_stack",
                              content_record_id=record_id, brand_id=world["brand"].id)


def test_a_slot_passes_over_a_record_placed_by_hand(db, world, catalogue):  # noqa: F811
    category, (a, b, c, _d) = catalogue([9, 7, 5, 3])
    variant = world["variant"](slots=1)
    [slot] = _slots(db, variant)
    _configure(db, slot, [category], 2)
    # Placed by hand BELOW the slot: the person still wins, whatever the order.
    _bind(db, world, variant, a)
    person = world["person"]()
    _, rows = world["send"](variant, [person])
    assert rows[person.id] == ("sent", None)
    assert _picked(_execution(db, person)) == [(b, 1), (c, 2)]


def test_with_the_switch_on_one_hand_picked_record_is_enough(db, world, catalogue):  # noqa: F811
    """The slot's only candidate is the hand-bound record, so the slot shows
    nothing; the email still has content, so it goes out."""
    category, (a,) = catalogue([9])
    variant = world["variant"](slots=1)
    [slot] = _slots(db, variant)
    _configure(db, slot, [category], 1)
    _bind(db, world, variant, a)
    person = world["person"]()
    _, rows = world["send"](variant, [person], skip=True)
    assert rows[person.id] == ("sent", None)
    assert _picked(_execution(db, person)) == []


def test_with_the_switch_on_typed_in_modules_alone_are_not_content(db, world, catalogue):  # noqa: F811
    """A fully dynamic variant whose slot found nothing: its typed-in CTA does
    not make it worth sending."""
    category, _ = catalogue([])
    variant = world["variant"](static=True, slots=1)
    [slot] = _slots(db, variant)
    _configure(db, slot, [category], 1)
    person = world["person"]()
    _, rows = world["send"](variant, [person], skip=True)
    assert rows[person.id] == ("excluded", f"{STAGE_RENDER}: {REASON_NO_PICK}")


def test_the_reason_names_both_ways_content_could_have_come():
    assert "no content record" in REASON_NO_PICK and "by hand" in REASON_NO_PICK
