"""What a field IS is written once, in its definition (task-271, task-272).

ADR-177 point 3 said a form label "can be built from concept and size";
nothing built it, so the React editor and the bind picker showed storage keys
(`headline_hero`). Concept and size cannot tell `image_url` from `image_alt`
anyway. The addendum of 2026-10-04: one `label` per field in
`storage/fields.json`, never declared by a manifest, reaching every surface
from there. `envelope` followed (task-272): ADR-177 point 3 already called it
a property of the field, yet the header manifest repeated it and the registry
fell back to the manifest's copy.
"""
import json
import uuid

import pytest
from pathlib import Path

from fastapi.testclient import TestClient

from app.auth.permissions import VIEW
from app.modules import registry
from main import app
from tests.machine import machine

client = TestClient(app, raise_server_exceptions=False)


def _get(path, **params):
    with machine([VIEW]) as headers:
        response = client.get(path, headers=headers, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def _channels():
    return sorted(p.name for p in Path(registry.MODULES_DIR).iterdir() if p.is_dir())


def test_every_module_field_reaches_the_editor_with_a_label():
    for channel in _channels():
        for module in _get("/modules", channel=channel):
            for field in module["variables"]:
                assert field["label"] and field["label"] != field["name"], (
                    f"{channel}/{module['name']} sends {field['name']!r} without a label; "
                    "write one in storage/fields.json"
                )


def test_every_definition_carries_its_label():
    missing = [name for name, spec in registry.field_definitions().items() if not spec.get("label")]
    assert not missing, f"storage/fields.json defines these without a label: {missing}"


def test_the_label_is_the_definitions_word_for_word():
    hero = {v["name"]: v["label"] for v in _get("/modules/hero", channel="email")["variables"]}
    assert hero == {
        "headline_hero": "Hero headline",
        "button_label_hero": "Hero button text",
        "button_url": "Button link",
    }


def test_catalogue_fields_side_by_side_never_share_a_label():
    """The size is named where it tells two fields apart (addendum point 2):
    the content screen shows a record's fields from several modules at once,
    and the two image fields share a concept and have no size."""
    fields = _get("/content/fields")
    labels = [f["label"] for f in fields]
    assert all(labels), f"GET /content/fields sends a field without a label: {fields}"
    assert len(labels) == len(set(labels)), f"two catalogue fields read the same: {sorted(labels)}"
    by_name = {f["name"]: f["label"] for f in fields}
    assert by_name["image_url"] != by_name["image_alt"]


def _offered(manifest: dict) -> bool:
    """Plant a manifest, ask the registry for email's modules, clean up."""
    prefix = f"deftest{uuid.uuid4().hex[:6]}"
    planted = registry.MODULES_DIR / "email" / f"{prefix}.json"
    planted.write_text(json.dumps(manifest))
    try:
        registry._registry_mtime = None
        names = [m.name for m in registry.list_manifests("email")]
        assert "hero" in names, "one refused manifest must not take the rest down"
        return prefix in names
    finally:
        planted.unlink(missing_ok=True)
        registry._registry_mtime = None


def _module(**overrides):
    return {"label": "Planted", "channel": "email", "cms": False, "has_template": False,
            "variables": [{"name": "text"}], **overrides}


def test_a_well_formed_planted_manifest_is_offered():
    """The control: without it, every refusal below could pass because the
    planted module is never offered at all."""
    assert _offered(_module(variables=[{"name": "text", "required": False, "source": "content"}]))


@pytest.mark.parametrize("key, value", [
    # What the field IS (ADR-177 point 3): a second source, refused.
    ("label", "My own word for it"), ("envelope", True), ("type", "url"), ("note", "x"),
    # Typos of the three allowed keys, which would otherwise default unseen (task-273).
    ("requried", False), ("sorce", "module"),
])
def test_a_field_entry_carries_only_name_required_and_source(key, value):
    assert not _offered(_module(variables=[{"name": "text", key: value}]))


def test_a_module_carries_only_its_own_keys():
    """`"cms "` misspelt would otherwise make a catalogue module static."""
    manifest = _module()
    manifest["cms "] = manifest.pop("cms")
    assert not _offered(manifest)


def test_the_refusal_says_where_the_key_belongs():
    with pytest.raises(ValueError) as definition:
        registry._variable({"name": "text", "type": "url"}, Path("x.json"))
    assert "storage/fields.json" in str(definition.value)
    with pytest.raises(ValueError) as typo:
        registry._variable({"name": "text", "requried": False}, Path("x.json"))
    assert "typo" in str(typo.value)


def test_every_shipped_manifest_uses_only_allowed_keys_and_loads():
    paths = sorted(Path(registry.MODULES_DIR).glob("*/*.json"))
    for path in paths:
        data = json.loads(path.read_text())
        assert set(data) <= registry.MANIFEST_KEYS, path.name
        for entry in data.get("variables", []):
            assert set(entry) <= registry.FIELD_ENTRY_KEYS, f"{path.name}: {entry}"
    registry._registry_mtime = None
    offered = {(m.channel, m.name) for channel in _channels() for m in registry.list_manifests(channel)}
    assert offered == {(p.parent.name, p.stem) for p in paths}


def test_the_envelope_still_comes_from_the_definitions():
    """The header manifest no longer says so; the definitions do, and the
    envelope lookup still finds header for email and nothing for push."""
    header = {v.name: v.envelope for v in registry.get_manifest("email", "header").variables}
    assert header == {"subject": True, "preheader": True}
    assert registry.envelope_module_type("email") == "header"
    assert registry.envelope_module_type("push") is None
