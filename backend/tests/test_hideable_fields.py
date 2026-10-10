"""A module manifest declares which fields may be hidden, and its template
guarantees it (task-289).

ADR-187 points 2, 5 and 8, decided with the user 2026-10-05: each field is an
element; `"hideable": true` on a manifest entry says a manager may hide it in
this module. A hidden field reaches the template as empty, so every use of a
hideable field must sit inside an `{% if %}` whose test has the field as a
conjunct — the field itself, or an `and` chain holding it. Checked when the
modules load, by Jinja's parser, not a text search; a violation costs only
that module, as an undefined field does.
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.modules import registry
from app.modules.registry import UnguardedHideableFieldError, get_manifest, list_manifests
from main import app
from tests.machine import machine
from app.auth.permissions import VIEW

api = TestClient(app, raise_server_exceptions=False)


def _module(tmp_path, template: str | None, fields: list[dict], *, name="probe", has_template=True):
    """Write a manifest (and template) into tmp_path/email/ and return the json path."""
    folder = tmp_path / "email"
    folder.mkdir(exist_ok=True)
    manifest = {"label": "Probe", "channel": "email", "cms": True, "variables": fields}
    if not has_template:
        manifest["has_template"] = False
    path = folder / f"{name}.json"
    path.write_text(json.dumps(manifest))
    if template is not None:
        (folder / f"{name}.html").write_text(template)
    return path


BODY = [{"name": "body_medium", "required": False, "hideable": True}]


class TestTheAttribute:
    def test_it_is_read_and_defaults_to_false(self, tmp_path):
        path = _module(tmp_path, "{% if body_medium %}{{ body_medium }}{% endif %}{{ image_url }}",
                       BODY + [{"name": "image_url", "required": False}])
        manifest = registry._load_manifest(path, "email")
        assert {v.name: v.hideable for v in manifest.variables} == {"body_medium": True, "image_url": False}

    def test_it_must_be_true_or_false(self, tmp_path):
        path = _module(tmp_path, "{% if body_medium %}{{ body_medium }}{% endif %}",
                       [{"name": "body_medium", "hideable": "yes"}])
        with pytest.raises(ValueError, match="hideable"):
            registry._load_manifest(path, "email")


class TestTheTemplateRule:
    @pytest.mark.parametrize("why, template", [
        ("printed with no guard", "<p>{{ body_medium }}</p>"),
        ("printed inside its guard and outside it too",
         "{% if body_medium %}<p>{{ body_medium }}</p>{% endif %}<span>{{ body_medium }}</span>"),
        ("guarded by another field", "{% if image_url %}<p>{{ body_medium }}</p>{% endif %}"),
        ("in an `or`, which still prints it with the field hidden",
         "{% if body_medium or image_url %}<p>{{ body_medium }}</p>{% endif %}"),
        ("in the else branch of its own guard",
         "{% if body_medium %}<p>{{ body_medium }}</p>{% else %}<i>{{ body_medium }}</i>{% endif %}"),
        ("in an elif branch of its own guard, which runs when it is empty",
         "{% if body_medium %}<p>{{ body_medium }}</p>{% elif image_url %}<i>{{ body_medium }}</i>{% endif %}"),
        ("passed through a filter, unguarded", "<p>{{ body_medium | upper }}</p>"),
    ])
    def test_a_use_outside_a_guard_that_holds_the_field_is_refused(self, tmp_path, why, template):
        path = _module(tmp_path, template, BODY + [{"name": "image_url", "required": False}])
        with pytest.raises(UnguardedHideableFieldError, match="body_medium") as refused:
            registry._load_manifest(path, "email")
        assert "probe" in str(refused.value), why

    @pytest.mark.parametrize("template", [
        "{% if body_medium %}<p>{{ body_medium }}</p>{% endif %}",
        "{% if body_medium and image_url %}<p>{{ body_medium }}</p>{% endif %}",
        "{% if image_url and body_medium %}{% if image_url %}<p>{{ body_medium }}</p>{% endif %}{% endif %}",
        "{% if image_url %}x{% elif body_medium %}<p>{{ body_medium }}</p>{% endif %}",
    ])
    def test_a_guard_holding_the_field_as_a_conjunct_passes(self, tmp_path, template):
        path = _module(tmp_path, template, BODY + [{"name": "image_url", "required": False}])
        assert registry._load_manifest(path, "email").name == "probe"

    def test_the_button_guard_may_keep_its_link(self, tmp_path):
        """What is hidden is the label; the link is not hideable (ADR-187 point 5)."""
        path = _module(
            tmp_path,
            '{% if button_label and button_url %}<a href="{{ button_url }}">{{ button_label }}</a>{% endif %}'
            '<img src="x" alt="{{ button_url }}">',
            [{"name": "button_label", "required": False, "hideable": True},
             {"name": "button_url", "required": False}])
        assert registry._load_manifest(path, "email").name == "probe"

    def test_a_module_with_no_template_cannot_declare_a_hideable_field(self, tmp_path):
        path = _module(tmp_path, None, BODY, has_template=False)
        with pytest.raises(UnguardedHideableFieldError, match="no template"):
            registry._load_manifest(path, "email")

    def test_a_violation_costs_only_that_module(self, tmp_path, monkeypatch):
        _module(tmp_path, "<p>{{ body_medium }}</p>", BODY, name="broken")
        _module(tmp_path, "{% if body_medium %}<p>{{ body_medium }}</p>{% endif %}", BODY, name="sound")
        monkeypatch.setattr(registry, "MODULES_DIR", tmp_path)
        assert set(registry._discover()) == {("email", "sound")}


class TestTheStandardSet:
    """ADR-187 point 8."""

    @pytest.mark.parametrize("module, hideable", [
        ("img_left", {"image_url", "headline_medium", "body_medium", "button_label"}),
        ("img_right", {"image_url", "headline_medium", "body_medium", "button_label"}),
        ("single_stack", {"image_url", "headline_medium", "body_medium", "button_label"}),
        ("hero", {"headline_hero", "button_label_hero"}),
        ("cta", set()), ("editorial", set()), ("envelope", set()),
    ])
    def test_the_agreed_fields_are_hideable(self, module, hideable):
        manifest = get_manifest("email", module)
        assert manifest is not None, f"{module} did not load"
        assert {v.name for v in manifest.variables if v.hideable} == hideable

    def test_push_has_none_for_now(self):
        assert [v.name for m in list_manifests("push") for v in m.variables if v.hideable] == []

    def test_the_manifest_endpoint_reports_it(self):
        with machine([VIEW]) as headers:
            modules = api.get("/modules", params={"channel": "email"}, headers=headers).json()
        img_left = next(m for m in modules if m["name"] == "img_left")
        assert {v["name"]: v["hideable"] for v in img_left["variables"]}["body_medium"] is True
        assert {v["name"]: v["hideable"] for v in img_left["variables"]}["button_url"] is False
