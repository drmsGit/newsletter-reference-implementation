"""A brand profile's fields are declared per installation (task-350, ADR-194).

The structure is not fixed in code: one company declares two font sizes,
another four, in `storage/brand_profile.json`, changed in a regular deployment.
A fixed core is always there because the platform relies on it — the legal
details every email carries and the unsubscribe wording. The file may relabel
or regroup a core field, never change its type or make it optional.
"""
import json

import pytest

from app.brand_profiles import structure


@pytest.fixture
def setup_file(tmp_path, monkeypatch):
    path = tmp_path / "brand_profile.json"
    monkeypatch.setattr(structure, "PROFILE_PATH", path)
    structure._loaded_mtime = None          # read afresh from the new path

    def write(fields: dict):
        path.write_text(json.dumps({"_comment": ["test"], "fields": fields}))
        structure._loaded_mtime = None
        return path

    return write


CORE = ["legal_company_name", "legal_address", "imprint_url", "privacy_url", "unsubscribe_text"]


def test_the_core_is_there_without_a_file(setup_file):
    names = [f.name for f in structure.profile_structure()]
    assert names == CORE


def test_what_is_required_depends_on_the_kind(setup_file):
    legal = ["legal_company_name", "legal_address", "imprint_url", "privacy_url"]
    assert structure.required_fields("transactional") == legal
    assert structure.required_fields("marketing") == legal + ["unsubscribe_text"]


def test_the_file_adds_fields_in_its_own_order(setup_file):
    setup_file({
        "colour_primary": {"type": "colour", "label": "Primary colour", "group": "Look"},
        "hotline": {"type": "text", "label": "Service hotline", "required": True},
    })
    fields = {f.name: f for f in structure.profile_structure()}
    assert list(fields)[len(CORE):] == ["colour_primary", "hotline"]
    assert fields["colour_primary"].type == "colour" and fields["colour_primary"].group == "Look"
    assert "hotline" in structure.required_fields("transactional")


def test_the_file_may_relabel_a_core_field(setup_file):
    setup_file({"imprint_url": {"label": "Impressum", "group": "Rechtliches"}})
    imprint = next(f for f in structure.profile_structure() if f.name == "imprint_url")
    assert (imprint.label, imprint.group, imprint.type) == ("Impressum", "Rechtliches", "url")


@pytest.mark.parametrize("fields, says", [
    ({"imprint_url": {"type": "text"}}, "core"),                       # a core field's type is fixed
    ({"legal_address": {"required": False}}, "core"),                  # and so is its requiredness
    ({"Primary Colour": {"type": "colour", "label": "x"}}, "name"),    # names are safe identifiers
    ({"glow": {"type": "neon", "label": "x"}}, "type"),                # only known types
    ({"glow": {"type": "colour", "label": "x", "colur": 1}}, "colur"),  # unknown keys are refused, not ignored
    ({"glow": {"type": "colour"}}, "label"),                           # a free field needs a label
])
def test_a_bad_file_is_refused_at_startup(setup_file, fields, says):
    setup_file(fields)
    with pytest.raises(ValueError, match=says):
        structure.assert_structure_loads()


def test_a_malformed_file_is_refused(setup_file):
    path = setup_file({})
    path.write_text("{ not json")
    structure._loaded_mtime = None
    with pytest.raises(ValueError):
        structure.assert_structure_loads()
