"""Rich text renders what the editor's hint promises (task-392 item 6).

The hint under every rich-text field says "**bold**, *italic*,
[link](https://…), and a line starting with - for a bullet". Until
2026-10-17 the renderer knew bold, links and line breaks only, so italics and
bullets reached the email as the characters typed. Escaping still comes first
(ADR-190's one Markup use; ADR-199 substitutes after it).
"""
from app.modules.registry import ModuleManifest, ModuleVariable
from app.rendering.service import render_rich_text, strip_rich_text

LIST = '<ul style="margin:0;padding-left:1.2em">'


def test_italic():
    assert str(render_rich_text("a *quiet* word")) == "a <em>quiet</em> word"


def test_bold_stays_bold_and_both_can_meet():
    assert str(render_rich_text("**loud** and *quiet*")) == "<strong>loud</strong> and <em>quiet</em>"


def test_a_lone_or_spaced_asterisk_is_left_as_typed():
    assert str(render_rich_text("5 * 3 * 2 = 30")) == "5 * 3 * 2 = 30"
    assert str(render_rich_text("a * b")) == "a * b"


def test_lines_starting_with_a_dash_are_one_list():
    assert str(render_rich_text("Pack:\n- a map\n- a **compass**\nThen go.")) == (
        f"Pack:{LIST}<li>a map</li><li>a <strong>compass</strong></li></ul>Then go."
    )


def test_two_lists_apart_and_a_dash_inside_a_line():
    out = str(render_rich_text("- one\nbetween - not a bullet\n- two"))
    assert out == f"{LIST}<li>one</li></ul>between - not a bullet{LIST}<li>two</li></ul>"


def test_a_dash_without_a_space_is_not_a_bullet():
    assert str(render_rich_text("-5 degrees\nline")) == "-5 degrees<br>line"


def test_plain_lines_still_break():
    assert str(render_rich_text("one\ntwo")) == "one<br>two"


def test_a_list_item_is_escaped_like_any_text():
    out = str(render_rich_text("- <script>x</script> [map](https://example.test/m)"))
    assert "<script>" not in out
    assert '<li>&lt;script&gt;x&lt;/script&gt; <a href="https://example.test/m">map</a></li>' in out


def test_push_has_no_document_so_italics_are_stripped_and_dashes_stay():
    manifest = ModuleManifest(name="p", channel="push", label="", description="", cms=True,
                              variables=[ModuleVariable(name="push_body", type="richtext")])
    out = strip_rich_text({"push_body": "a *quiet* and **loud** word\n- one"}, manifest)
    assert out["push_body"] == "a quiet and loud word\n- one"
