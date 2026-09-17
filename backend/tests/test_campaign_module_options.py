"""
Tests for the add-module type dropdown in campaign_detail.html.

The <select name="module_type"> on the add-module form must offer exactly the
module types the registry can actually render — nothing hardcoded beside the
`module_templates` loop. A hardcoded option for a type with no manifest lets a
manager create a ModuleInstanceDB that falls through to render_unknown_module
(rendering/service.py) and that overrides/service.py refuses to override:
silent at creation time, visible only in the render.

No database and no network: the template is read from disk, the one <select>
is rendered in isolation against the real registry.

Run with: pytest tests/test_campaign_module_options.py -v
"""
import re
from pathlib import Path

from jinja2 import Environment

from app.modules import registry
from app.modules.registry import list_manifests

# app/ has no __init__.py, so app.__file__ is None — anchor on a real module.
TEMPLATE_PATH = (
    Path(registry.__file__).parent.parent / "templates" / "campaign_detail.html"
)

# The add-module form's select; the edit form's is form-select-sm and is
# deliberately not matched (it carries a fallback option for orphan rows).
ADD_MODULE_SELECT = re.compile(
    r'<select name="module_type" class="form-select" required>.*?</select>',
    re.DOTALL,
)


def _rendered_option_values() -> list[str]:
    source = TEMPLATE_PATH.read_text()
    matches = ADD_MODULE_SELECT.findall(source)
    assert len(matches) == 1, f"expected one add-module select, found {len(matches)}"
    # Per variant since ADR-162 point 5 — the form now reads
    # `variant.module_templates`, which is the channel's manifests and not the
    # registry's whole contents. Email is the channel under test here.
    html = Environment(autoescape=True).from_string(matches[0]).render(
        variant={"module_templates": list_manifests("email")}
    )
    return re.findall(r'<option value="([^"]*)"', html)


def test_add_module_options_are_exactly_the_registry_manifests():
    values = _rendered_option_values()
    assert sorted(values) == sorted(m.name for m in list_manifests("email"))


def test_add_module_options_have_no_duplicates():
    values = _rendered_option_values()
    assert len(values) == len(set(values)), f"duplicate options: {values}"


def test_add_module_offers_no_type_without_a_manifest():
    known = {m.name for m in list_manifests("email")}
    unknown = [v for v in _rendered_option_values() if v not in known]
    assert unknown == [], f"options with no manifest: {unknown}"
