"""Ranked column picks retain attribution and frozen fidelity (ADRs 084, 183, 198)."""
import re
from html import unescape
from urllib.parse import urlsplit

from app.campaigns.db_models import ModuleInstanceDB
from app.decision.service import execute_decision_slot
from app.delivery.service import reconstruct_delivery
from app.rendering.tracking import content_id_from_url
from tests.test_block_set import _sections
from tests.test_several_picks import (  # noqa: F401
    _configure, _execution, _picked, _slots, catalogue, db, world,
)


def test_three_picks_from_one_column_slot_pair_and_rebuild_after_later_edits(
    db, world, catalogue,  # noqa: F811
):
    category, (a, b, c) = catalogue([9, 7, 5])
    variant = world["variant"](slots=1)
    [slot] = _slots(db, variant)
    module = db.query(ModuleInstanceDB).filter_by(
        variant_id=variant.id, decision_slot_id=slot.id,
    ).one()
    module.module_type = "column"
    _configure(db, slot, [category], 3)
    person = world["person"]()
    _, outcomes = world["send"](variant, [person])
    assert outcomes[person.id] == ("sent", None)
    execution = _execution(db, person)
    assert _picked(execution) == [(a, 1), (b, 2), (c, 3)]
    before = reconstruct_delivery(db, execution.id, brand_id=world["brand"].id)
    assert before["hash_matches"] is True
    assert _sections(before["body"]) == 2, "a pair and a lone column"
    links = {}
    for href in re.findall(r'<a [^>]*href="([^"]+)"', before["body"]):
        url = unescape(href)
        if urlsplit(url).path in ("/9", "/7", "/5"):
            links[urlsplit(url).path] = content_id_from_url(url)
    assert links == {"/9": a, "/7": b, "/5": c}
    assert [m["content_record_id"] for m in before["modules"] if m["kind"] == "slot"] == [a, b, c]

    # Today's layout and current ranked set change; the sent record must not.
    module.hidden_fields = ["headline_medium"]
    _configure(db, slot, [category], 1)
    execute_decision_slot(db, slot.id, recipient_id=person.id)
    after = reconstruct_delivery(db, execution.id, brand_id=world["brand"].id)
    assert after["hash_matches"] is True
    assert after["body"] == before["body"]
    assert after["modules"] == before["modules"]
