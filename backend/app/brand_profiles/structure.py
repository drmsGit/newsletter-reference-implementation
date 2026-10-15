"""Which fields a brand profile has (ADR-194 point 2; task-350).

The structure is the installation's, not the code's: `storage/brand_profile.json`
declares the fields — one company two font sizes, another four — and IT changes
it in a regular deployment. A **fixed core** is always present because the
platform relies on it: the legal details every email carries and the
unsubscribe wording (ADR-194's 2026-10-11 addendum names them). The file may
relabel or regroup a core field; it may never change a core field's type or
make it optional, because then a send would go out without what the law needs.

Loaded like the module manifests (`app/modules/registry.py`): read again when
the file changes, unknown keys refused rather than ignored, and checked at
startup so a bad file fails the deploy, not the first send.
"""
import json
import re
from dataclasses import dataclass, replace
from pathlib import Path

PROFILE_PATH = Path(__file__).parent.parent.parent.parent / "storage" / "brand_profile.json"

MARKETING = "marketing"
TRANSACTIONAL = "transactional"
KINDS = (MARKETING, TRANSACTIONAL)

#: ADR-194 point 2.
#: `links` (task-351, ADR-194's fourth addendum of 2026-10-11): a list of links,
#: one per line, "Label | https://address".
FIELD_TYPES = frozenset({"colour", "font_family", "size", "image", "text", "url", "number", "links"})
#: `alt` (ADR-194 addendum 2026-10-15): on an `image` field, the field that
#: holds its alt text, which inherits the library image's alt when empty.
FIELD_KEYS = frozenset({"type", "label", "required", "group", "multiline", "alt"})
#: Safe to refer to from brand.css and templates (task-354).
NAME = re.compile(r"[a-z][a-z0-9_]*")


@dataclass(frozen=True)
class ProfileField:
    name: str
    type: str
    label: str
    required: bool = False
    group: str = "General"
    multiline: bool = False
    alt: str | None = None
    core: bool = False
    #: Required only on a marketing profile: the unsubscribe wording (ADR-191).
    marketing_only: bool = False


#: The core, in the order an editor shows it.
CORE_FIELDS: tuple[ProfileField, ...] = (
    ProfileField("legal_company_name", "text", "Legal company name", True, "Legal details", core=True),
    ProfileField("legal_address", "text", "Address", True, "Legal details", multiline=True, core=True),
    ProfileField("imprint_url", "url", "Imprint link", True, "Legal details", core=True),
    ProfileField("privacy_url", "url", "Privacy link", True, "Legal details", core=True),
    ProfileField("unsubscribe_text", "text", "Unsubscribe wording", True, "Unsubscribe", core=True,
                 marketing_only=True),
    # Link tags (ADR-194 addendum 2026-10-11 (third)): core because the
    # platform reads them by name, optional because tagging is the company's
    # choice. No tags at all while utm_source is empty.
    ProfileField("utm_source", "text", "UTM source", False, "Link tracking", core=True),
    ProfileField("utm_medium", "text", "UTM medium", False, "Link tracking", core=True),
    ProfileField("utm_extra", "text", "Further link parameters", False, "Link tracking",
                 multiline=True, core=True),
)
_CORE = {f.name: f for f in CORE_FIELDS}

_loaded: tuple[ProfileField, ...] = CORE_FIELDS
_loaded_mtime: float | None = None


def _mtime() -> float:
    return PROFILE_PATH.stat().st_mtime if PROFILE_PATH.exists() else 0.0


def _read() -> tuple[ProfileField, ...]:
    if not PROFILE_PATH.exists():
        return CORE_FIELDS
    try:
        document = json.loads(PROFILE_PATH.read_text())
    except json.JSONDecodeError as error:
        raise ValueError(f"{PROFILE_PATH} is not valid JSON: {error}") from error
    declared = document.get("fields") or {}
    if not isinstance(declared, dict):
        raise ValueError(f"{PROFILE_PATH}: 'fields' must be an object of field name to definition.")

    fields = list(CORE_FIELDS)
    for name, spec in declared.items():
        if not isinstance(spec, dict):
            raise ValueError(f"{PROFILE_PATH}: field {name!r} must be an object.")
        unknown = sorted(set(spec) - FIELD_KEYS)
        if unknown:
            raise ValueError(f"{PROFILE_PATH} declares {', '.join(map(repr, unknown))} on field {name!r} "
                             f"(unknown — a typo?); allowed: {', '.join(sorted(FIELD_KEYS))}.")
        if name in _CORE:
            core = _CORE[name]
            if spec.get("type", core.type) != core.type or spec.get("required", True) is not True:
                raise ValueError(f"{PROFILE_PATH}: {name!r} is a core field; its type and requiredness "
                                 "are fixed. Only label and group may change.")
            index = next(i for i, f in enumerate(fields) if f.name == name)
            fields[index] = replace(core, label=spec.get("label", core.label), group=spec.get("group", core.group))
            continue
        if not NAME.fullmatch(name):
            raise ValueError(f"{PROFILE_PATH}: field name {name!r} must match [a-z][a-z0-9_]* "
                             "(it is referred to by name from brand.css and templates).")
        if spec.get("type") not in FIELD_TYPES:
            raise ValueError(f"{PROFILE_PATH}: field {name!r} has type {spec.get('type')!r}; "
                             f"known types: {', '.join(sorted(FIELD_TYPES))}.")
        if not spec.get("label"):
            raise ValueError(f"{PROFILE_PATH}: field {name!r} needs a label.")
        fields.append(ProfileField(
            name=name, type=spec["type"], label=spec["label"], required=bool(spec.get("required", False)),
            group=spec.get("group", "General"), multiline=bool(spec.get("multiline", False)),
            alt=spec.get("alt") if spec["type"] == "image" else None,
        ))
    return tuple(fields)


def profile_structure() -> tuple[ProfileField, ...]:
    """Every field a profile has, core first, then the file's in its order."""
    global _loaded, _loaded_mtime
    current = _mtime()
    if _loaded_mtime is None or current != _loaded_mtime:
        _loaded = _read()
        _loaded_mtime = current
    return _loaded


def required_fields(kind: str) -> list[str]:
    """What must be filled before an email using a profile of this kind may go
    out (ADR-194 addendum 2026-10-11): the legal core always, the unsubscribe
    wording on marketing, and whatever the file marks required."""
    return [f.name for f in profile_structure()
            if f.required and (not f.marketing_only or kind == MARKETING)]


def missing_fields(kind: str, values: dict | None) -> list[str]:
    """Required fields this profile leaves empty."""
    values = values or {}
    return [name for name in required_fields(kind) if not str(values.get(name) or "").strip()]


def assert_structure_loads() -> None:
    """Read the setup file at startup, so a bad one fails the deploy."""
    global _loaded_mtime
    _loaded_mtime = None
    profile_structure()
