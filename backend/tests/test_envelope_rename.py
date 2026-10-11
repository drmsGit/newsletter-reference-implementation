"""The envelope module is called envelope; frozen frames still read as sent (task-349).

The module holding the subject and preheader was named `header`, which the
visible logo header of ADR-193 needs. Renamed (ADR-193 point 6), with one
decision taken in the final-design pass (2026-10-10): **frozen frames are left
exactly as they are.** `module_html` writes each module's type into the HTML,
so rewriting them would change every sent email's bytes and break ADR-183's
"matches what was sent". A version-1 frame's `header` is read as the envelope
instead, while still rendering under its old name.
"""
import copy

from app.modules.registry import envelope_module_type, get_manifest
from app.rendering.frame import (
    FRAME_VERSION, build_frame, is_frame, missing_required_in_frame, render_frame, what_rendered,
)
from tests import test_render_skip as _render_skip

db = _render_skip.db
world = _render_skip.world


def _new_frame(db, world):
    variant = world["variant"](static=True, slots=0)
    frame = build_frame(db, variant.id)
    [envelope] = [e for e in frame["modules"] if e["module_type"] == envelope_module_type("email")]
    envelope["variables"] = {**envelope.get("variables", {}), "preheader": "Seen in the inbox only"}
    return frame


def _as_before_the_rename(frame):
    """The same frame as it was frozen before 2026-10-10: version 1, `header`."""
    old = copy.deepcopy(frame)
    old["frame_version"] = 1
    for entry in old["modules"]:
        if entry["module_type"] == "envelope":
            entry["module_type"] = "header"
    return old


def test_the_envelope_module_is_called_envelope():
    assert envelope_module_type("email") == "envelope"
    assert get_manifest("email", "header") is None, "the name is free for ADR-193's visible header"


def test_a_new_frame_names_its_envelope_and_says_its_version(db, world):
    frame = _new_frame(db, world)
    # 3 since task-357 (brand profiles); the rename came with 2.
    assert frame["frame_version"] == FRAME_VERSION == 3
    assert "header" not in {e["module_type"] for e in frame["modules"]}


def test_a_frame_from_before_the_rename_is_still_a_frame(db, world):
    assert is_frame(_as_before_the_rename(_new_frame(db, world)))


def test_a_frame_from_before_the_rename_renders_as_it_was_sent(db, world):
    """Byte for byte, but for the module type it was frozen under."""
    frame = _new_frame(db, world)
    # Compared as version 2, the last before frames carried the legal footer
    # (task-357): the rename is what this test is about.
    new_html = render_frame(db, {**frame, "frame_version": 2})[0].body
    old_html = render_frame(db, _as_before_the_rename(frame))[0].body
    assert 'data-module-type="header"' in old_html and "Seen in the inbox only" in old_html
    assert old_html.replace('data-module-type="header"', 'data-module-type="envelope"') == new_html


def test_an_old_envelope_still_is_not_content(db, world):
    """The nothing-to-show floor (task-228) compares by name; an old frame's
    `header` must still count as the envelope, not as something to show."""
    old = _as_before_the_rename(_new_frame(db, world))
    only_envelope = {**old, "modules": [e for e in old["modules"] if e["module_type"] == "header"]}
    assert what_rendered(only_envelope, picks=[]) == (False, 0)


def test_the_required_field_check_reads_old_frames(db, world):
    frame = _new_frame(db, world)
    assert missing_required_in_frame(_as_before_the_rename(frame)) == missing_required_in_frame(frame)
