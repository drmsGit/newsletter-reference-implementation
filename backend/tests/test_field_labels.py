"""A field's label is written once, in its definition (task-271).

ADR-177 point 3 said a form label "can be built from concept and size";
nothing built it, so the React editor and the bind picker showed storage keys
(`headline_hero`). Concept and size cannot tell `image_url` from `image_alt`
anyway. The addendum of 2026-10-04: one `label` per field in
`storage/fields.json`, never declared by a manifest, reaching every surface
from there.
"""
import json
import uuid
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


def test_a_manifest_that_labels_a_field_is_not_offered():
    """One source: a label in a manifest is refused, not quietly ignored or
    preferred — the module is skipped like any manifest the registry cannot
    read, and the rest stay offered."""
    prefix = f"labeltest{uuid.uuid4().hex[:6]}"
    planted = registry.MODULES_DIR / "email" / f"{prefix}.json"
    planted.write_text(json.dumps({
        "label": "Labels its own field", "channel": "email", "cms": False, "has_template": False,
        "variables": [{"name": "text", "label": "My own word for it"}],
    }))
    try:
        registry._registry_mtime = None
        names = [m.name for m in registry.list_manifests("email")]
        assert prefix not in names
        assert "hero" in names
    finally:
        planted.unlink(missing_ok=True)
        registry._registry_mtime = None
