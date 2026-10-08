"""Module manifests, discovered per channel from `storage/modules/<channel>/`.

[[ADR-162]] point 5: **a channel directory AND a channel declaration, with a
startup assertion when they disagree.**

*Namespace*, because name collisions are real — "hero" is natural in email,
letter and social, and flat organisation just re-implements namespacing inside
filenames. *Declaration*, because a manifest read on its own should say what it
is for; location-only makes the file meaningless outside its directory, which
bites in review, in docs and in error messages. **The assertion matters more
than either**: a misfiled manifest would otherwise surface as a manager being
offered a module that cannot render.

The lookup key is therefore `(channel, name)`. A module instance stores only
the bare name in `module_type`; its channel comes from the variant it belongs
to, which is where ADR-160 point 4 put it. Nothing had to be migrated for that
— the names happen not to collide today, and the point of this file is that it
no longer matters whether they start to.
"""

import json
from functools import lru_cache
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

MODULES_DIR = Path(__file__).parent.parent.parent.parent / "storage" / "modules"


class MisfiledManifestError(Exception):
    """A manifest's declared channel contradicts the directory it sits in.

    Raised rather than logged, and at discovery rather than at render: the
    alternative is a manager being offered a module whose renderer will not
    take it. Same fail-closed idiom as an unmapped write route.
    """


class UnguardedHideableFieldError(Exception):
    """A field the manifest marks hideable can be printed while hidden.

    ADR-187 point 5: a hidden field reaches the template as empty, so every use
    of a hideable field must sit inside an `{% if %}` whose test has the field
    as a conjunct. Otherwise "hideable" would be a convention a template could
    quietly break. Not fatal, like `UndefinedFieldError`: it costs that one
    module, which `_discover` skips with a warning naming the field and line.
    """


class UndefinedFieldError(Exception):
    """A manifest names a field that `storage/fields.json` does not define.

    Raised rather than defaulted, and at discovery rather than at render: the
    alternative is a manager being offered a module whose fields nothing can
    describe. ADR-177 makes the definition file the one home for what a field
    *is*, which only works if a reference to a name it does not carry is an
    error rather than a shrug.

    **Unlike `MisfiledManifestError` this is not fatal**, and the difference is
    the one `_discover` already draws: a misfiled manifest offers a module on a
    channel that cannot render it, so it must stop everything, while an
    undefined field costs that one module. It is swallowed with a warning and
    the module is simply not offered.
    """


@dataclass
class ModuleVariable:
    name: str
    required: bool = True
    #: What to call this field in an authoring form. From `storage/fields.json`
    #: only, written once per field (ADR-177 addendum 2026-10-04, task-271):
    #: never built from concept and size, never declared by a manifest.
    label: str | None = None
    #: Whether this field belongs on the delivery **envelope** rather than in
    #: the rendered body. A subject line is the case that forces it: it is a
    #: field of an email (ADR-162 point 1) but no part of the document.
    #:
    #: **Declared rather than inferred from the module's name.** A renderer
    #: that special-cased a module called "header" would be the composition
    #: code knowing about one module, which is exactly the shape ADR-160
    #: point 2 refuses for push — the channel declares its capability, the
    #: code reads the declaration.
    envelope: bool = False

    #: From `storage/fields.json` (ADR-177). Not declared per module — a
    #: field's definition was never a property of any one module that uses it,
    #: which is the whole argument of that record.
    concept: str | None = None
    size: str | None = None
    type: str = "text"
    note: str | None = None
    #: **Declared, never derived from the directory a module sits in** —
    #: ADR-177's 2026-09-28 addendum. `content_field_groups()` is the consumer
    #: that makes this load-bearing rather than descriptive.
    channel: str | None = None
    #: Where a catalogue module takes this field from (ADR-179's 2026-10-04
    #: addendum, task-223): `content` — the record or the slot's pick — or
    #: `module`, typed in the module itself and kept in `module_data`. Declared
    #: per (module, field) in the manifest, like `required`, because where a
    #: value comes from is a property of the module that uses the field. A
    #: static module's fields are all the module's own whatever this says.
    source: str = "content"
    #: May a manager hide this field in this module (ADR-187 point 2)? Declared
    #: per (module, field) in the manifest, beside `required`, and only where
    #: the template guards every use of it (`_check_hideable_guards`). It says
    #: the field *may* be hidden; whether it is, is the module's choice in a
    #: variant.
    hideable: bool = False


@dataclass
class ModuleManifest:
    name: str        # derived from filename stem
    channel: str     # the directory it was found in, verified against its own declaration
    label: str
    description: str
    cms: bool        # True = variables come from CMS/decision slot; False = from module_data
    #: Whether a `name.html` counterpart is required. Push declares False:
    #: ADR-160 point 2 — "a push renderer fills fields and has no layout job",
    #: because the receiving OS does all the rendering. A **module-level** fact,
    #: not a channel-level one, which keeps ADR-161 point 7's split intact:
    #: module manifest = fields and limits; channel = cardinality.
    has_template: bool = True
    variables: list[ModuleVariable] = field(default_factory=list)


FIELDS_PATH = MODULES_DIR.parent / "fields.json"


@lru_cache(maxsize=1)
def field_definitions() -> dict[str, dict]:
    """`storage/fields.json`, or `{}` when it is absent.

    Absent is tolerated and an undefined *reference* is not: a repository
    without the file yet still starts, while a manifest naming a field the file
    does not carry is refused. That asymmetry is deliberate — the first is a
    state this migration passes through, the second is a mistake.
    """
    if not FIELDS_PATH.exists():
        logger.warning("field definitions not found: %s", FIELDS_PATH)
        return {}
    return json.loads(FIELDS_PATH.read_text()).get("fields", {})


def _source(declared: dict, json_path: Path) -> str:
    source = declared.get("source", "content")
    if source not in ("content", "module"):
        raise ValueError(
            f"{json_path} declares source {source!r} for {declared['name']!r}; "
            "a field comes from the content or is typed in the module."
        )
    return source


#: The keys a field entry in a manifest may carry, and nothing else (task-273):
#: which field, whether this module requires it (ADR-177 point 4), and where a
#: catalogue module takes it from (ADR-179's 2026-10-04 addendum). Anything
#: else is refused rather than ignored, because an ignored key fails quietly
#: and the wrong way: `"requried": false` leaves the field required.
FIELD_ENTRY_KEYS = frozenset({"name", "required", "source", "hideable"})

#: What a field IS: written once in `storage/fields.json`, never in a manifest
#: (ADR-177 point 3; its 2026-10-04 addendum for `label`, task-272 for
#: `envelope`). Named apart from a typo only so the refusal can say where the
#: key belongs.
DEFINITION_ATTRIBUTES = frozenset({"label", "envelope", "concept", "size", "type", "note", "channel"})

#: The keys a module manifest may carry (task-273, the user's call to include
#: the top level). `"cms "` misspelt would otherwise turn a catalogue module
#: into a static one without a word.
MANIFEST_KEYS = frozenset({"label", "channel", "description", "cms", "has_template", "variables"})


def _refuse_unknown(keys, allowed: frozenset, where: str, json_path: Path) -> None:
    unknown = sorted(set(keys) - allowed)
    if not unknown:
        return
    reasons = [
        f"{key!r} (what the field is: it belongs in storage/fields.json)"
        if key in DEFINITION_ATTRIBUTES and where != "the module" else f"{key!r} (unknown — a typo?)"
        for key in unknown
    ]
    raise ValueError(
        f"{json_path} declares {', '.join(reasons)} on {where}; allowed there: "
        f"{', '.join(sorted(allowed))}."
    )


def _variable(declared: dict, json_path: Path) -> ModuleVariable:
    """One manifest entry plus its definition.

    The manifest supplies `name`, `required` and `source`; everything else
    comes from `fields.json`. Any other key on the entry is refused rather than
    ignored or used as a fallback (task-273): a definition attribute repeated
    here is a second source, the condition ADR-177 exists to end, and anything
    else is a typo that would otherwise fall back to a default unseen.
    """
    name = declared["name"]
    _refuse_unknown(declared, FIELD_ENTRY_KEYS, f"the field {name!r}", json_path)
    defs = field_definitions()
    if defs and name not in defs:
        raise UndefinedFieldError(
            f"{json_path} declares a field {name!r} that storage/fields.json "
            "does not define. Add the definition, or correct the name — a "
            "field with no definition cannot be labelled, grouped, typed or "
            "assigned to a channel."
        )
    spec = defs.get(name, {})
    return ModuleVariable(
        name=name,
        required=declared.get("required", True),
        label=spec.get("label"),
        envelope=bool(spec.get("envelope", False)),
        concept=spec.get("concept"),
        size=spec.get("size"),
        type=spec.get("type", "text"),
        note=spec.get("note"),
        channel=spec.get("channel"),
        source=_source(declared, json_path),
        hideable=_hideable(declared, json_path),
    )


def _hideable(declared: dict, json_path: Path) -> bool:
    value = declared.get("hideable", False)
    if not isinstance(value, bool):
        raise ValueError(
            f"{json_path} declares hideable {value!r} for {declared['name']!r}; "
            "it is true or false."
        )
    return value


def _conjuncts(test) -> set[str]:
    """The field names an `{% if %}` test cannot be true without: the name
    itself, or every name in an `and` chain. `or`, `not` and comparisons give
    none, because each can be true with the field empty."""
    from jinja2 import nodes

    if isinstance(test, nodes.Name):
        return {test.name}
    if isinstance(test, nodes.And):
        return _conjuncts(test.left) | _conjuncts(test.right)
    return set()


def _check_hideable_guards(manifest: "ModuleManifest", template_path: Path) -> None:
    """Refuse a template that could print a hideable field while it is hidden
    (ADR-187 point 5). Reads the template's structure with Jinja's parser, not
    its text: a text search passes a field printed once inside its guard and
    once outside it."""
    hideable = {v.name for v in manifest.variables if v.hideable}
    if not hideable:
        return
    if not manifest.has_template:
        raise UnguardedHideableFieldError(
            f"{manifest.channel}/{manifest.name} marks {', '.join(sorted(hideable))} hideable but has "
            "no template: hiding a field is a layout choice, and this module has no layout."
        )
    from jinja2 import Environment, nodes

    source = template_path.read_text()
    unguarded: list[tuple[str, int]] = []

    def walk(node, guarded: frozenset) -> None:
        if isinstance(node, nodes.If):
            # The test may read the field; what it guards is its body.
            for child in node.body:
                walk(child, guarded | _conjuncts(node.test))
            for branch in node.elif_:
                walk(branch, guarded)
            for child in node.else_:
                walk(child, guarded)
            return
        if isinstance(node, nodes.Name) and node.name in hideable and node.name not in guarded:
            unguarded.append((node.name, node.lineno))
        for child in node.iter_child_nodes():
            walk(child, guarded)

    # Parsed for its syntax tree only, never rendered, so autoescaping has nothing to
    # protect here; the environment that renders sets it (app/rendering/service.py).
    walk(Environment().parse(source), frozenset())  # noqa: S701
    if unguarded:
        where = "; ".join(f"{name} on line {line}" for name, line in unguarded)
        raise UnguardedHideableFieldError(
            f"{manifest.channel}/{manifest.name}: a hideable field is printed outside an "
            f"{{% if %}} that holds it ({where}) in {template_path.name}. Wrap each use in "
            "{% if field %} or {% if field and … %} — a hidden field reaches the template "
            "empty, and `or` would still print it (ADR-187 point 5)."
        )


def _load_manifest(json_path: Path, channel: str) -> ModuleManifest:
    data = json.loads(json_path.read_text())

    declared = data.get("channel")
    if declared is not None and declared != channel:
        raise MisfiledManifestError(
            f"{json_path} declares channel {declared!r} but sits in "
            f"storage/modules/{channel}/. One of the two is wrong, and a "
            f"misfiled manifest shows up as a module offered to a renderer "
            f"that cannot take it."
        )
    _refuse_unknown(data, MANIFEST_KEYS, "the module", json_path)

    manifest = ModuleManifest(
        name=json_path.stem,
        channel=channel,
        label=data["label"],
        description=data.get("description", ""),
        cms=data.get("cms", False),
        has_template=data.get("has_template", True),
        variables=[
            _variable(v, json_path) for v in data.get("variables", [])
        ],
    )
    template = json_path.with_suffix(".html")
    if not manifest.has_template or template.exists():
        _check_hideable_guards(manifest, template)
    return manifest


def _discover() -> dict[tuple[str, str], ModuleManifest]:
    if not MODULES_DIR.exists():
        logger.warning("modules directory not found: %s", MODULES_DIR)
        return {}

    manifests: dict[tuple[str, str], ModuleManifest] = {}

    for channel_dir in sorted(p for p in MODULES_DIR.iterdir() if p.is_dir()):
        channel = channel_dir.name
        for json_path in sorted(channel_dir.glob("*.json")):
            try:
                manifest = _load_manifest(json_path, channel)
            except MisfiledManifestError:
                # Not swallowed like a malformed file is. A typo in a manifest
                # costs that one module; a manifest in the wrong directory
                # silently offers it on a channel that cannot render it.
                raise
            except Exception:
                logger.warning(
                    "Failed to load manifest '%s' — skipping", json_path.name,
                    exc_info=True,
                )
                continue

            if manifest.has_template and not json_path.with_suffix(".html").exists():
                logger.warning(
                    "Manifest %s has no matching .html file — skipping. Declare "
                    '"has_template": false if this module renders without one.',
                    json_path.name,
                )
                continue

            manifests[(channel, json_path.stem)] = manifest

        for html_path in channel_dir.glob("*.html"):
            if (channel, html_path.stem) not in manifests:
                logger.warning("%s has no matching .json manifest — skipping", html_path.name)

    return manifests


def _dir_mtime() -> float:
    if not MODULES_DIR.exists():
        return 0.0
    return max((p.stat().st_mtime for p in MODULES_DIR.rglob("*")), default=0.0)


_REGISTRY: dict[tuple[str, str], ModuleManifest] = {}
_registry_mtime: float | None = None


def _ensure_fresh() -> None:
    global _REGISTRY, _registry_mtime
    current_mtime = _dir_mtime()
    if _registry_mtime is None or current_mtime != _registry_mtime:
        _REGISTRY = _discover()
        _registry_mtime = current_mtime


def get_manifest(channel: str, name: str) -> ModuleManifest | None:
    """One module, on one channel.

    **Channel is required and not defaulted.** Defaulting it to email would
    make every caller that has not thought about channel silently resolve an
    email module, which is precisely the collision this namespacing exists to
    make impossible.
    """
    _ensure_fresh()
    return _REGISTRY.get((channel, name))


def list_manifests(channel: str) -> list[ModuleManifest]:
    """Every module this channel accepts — what the composer may offer.

    ADR-161 point 7: a channel is "an attribute on the variant plus **which
    manifests it accepts**". This is that second half, and it is why a manager
    composing an email is never offered a push module.
    """
    _ensure_fresh()
    return [m for (c, _), m in _REGISTRY.items() if c == channel]


def required_when_shown(manifest: ModuleManifest, hidden=()) -> list[str]:
    """The fields this module requires, less those hidden in it: ADR-187
    point 6, "required" means "required when shown". The one definition every
    required check reads — the send check, the editor's module states, slot
    candidacy — so they cannot drift apart."""
    hidden = set(hidden or ())
    return [v.name for v in manifest.variables if v.required and v.name not in hidden]


def hideable_fields(manifest: ModuleManifest) -> list[str]:
    """The fields a manager may hide in this module, in manifest order."""
    return [v.name for v in manifest.variables if v.hideable]


def get_template_html(channel: str, name: str) -> str | None:
    manifest = get_manifest(channel, name)
    if manifest is None or not manifest.has_template:
        return None
    html_path = MODULES_DIR / channel / f"{name}.html"
    return html_path.read_text() if html_path.exists() else None


def assert_manifests_load() -> None:
    """Force discovery so a misfiled manifest fails at startup, not at render.

    Called from application startup. Without it the first failure would be
    whichever request happened to touch the registry first, which is the same
    class of late surprise the assertion exists to remove.
    """
    _ensure_fresh()


def envelope_module_type(channel: str) -> str | None:
    """Which of this channel's modules carries its envelope fields.

    Found by reading the manifests for a variable declaring `envelope`, not by
    looking for a module called "header" — the same reason the renderer does
    not special-case it. A channel whose envelope copy lives in a module named
    something else works without this function changing.

    Returns None when the channel has no envelope fields at all, which is push:
    a notification's title is body, not envelope, because the OS renders the
    whole thing.
    """
    for manifest in list_manifests(channel):
        if any(var.envelope for var in manifest.variables):
            return manifest.name
    return None
