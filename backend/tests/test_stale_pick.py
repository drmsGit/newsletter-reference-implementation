"""A decision that finds nothing now is honoured by the send (task-320).

When a slot's decision came up empty for a recipient — the earlier pick no
longer eligible (unready, wrong category or status) — nothing recorded that
outcome, and rendering fell back to the newest stored resolution: content the
current decision had just refused (ADR-174, ADR-179). Found by the external
review of 2026-10-09. The send now tells the renderer which slots came up
empty in this run; those render empty, so the meaningful-content floor
(ADR-086 addendum 2026-10-08) sees the real outcome. Stored resolutions — the
history — are left as they are.
"""
from app.delivery.exclusion import REASON_NOTHING_TO_SHOW, STAGE_RENDER
from tests import test_render_skip as _render_skip

# Borrowed fixtures: variants with decision slots, recipients, a fake decision
# engine that records a pick for "picks=True" people, a recording provider.
db = _render_skip.db
world = _render_skip.world


def test_a_slot_that_found_nothing_now_does_not_send_an_old_pick(world, monkeypatch):
    variant = world["variant"]("email", slots=1)
    person = world["person"](picks=True)

    _, first = world["send"](variant, [person])
    assert first[person.id][0] == "sent", "the first send must use the pick it just made"

    # The earlier pick is no longer eligible: the decision now finds nothing.
    monkeypatch.setattr("app.decision.service.execute_decision_slot", lambda *a, **k: None)
    world["delivered"].clear()
    _, second = world["send"](variant, [person])

    assert world["delivered"] == [], "the send mailed the stale pick the decision had just refused"
    assert second[person.id] == ("excluded", f"{STAGE_RENDER}: {REASON_NOTHING_TO_SHOW}")


def test_a_decision_that_raises_nothing_found_is_honoured_the_same_way(world, monkeypatch):
    variant = world["variant"]("email", slots=1)
    person = world["person"](picks=True)
    world["send"](variant, [person])

    def nothing(*a, **k):
        raise ValueError("no eligible candidate")

    monkeypatch.setattr("app.decision.service.execute_decision_slot", nothing)
    world["delivered"].clear()
    _, second = world["send"](variant, [person])
    assert world["delivered"] == []
    assert second[person.id] == ("excluded", f"{STAGE_RENDER}: {REASON_NOTHING_TO_SHOW}")
