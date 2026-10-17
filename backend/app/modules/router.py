from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.modules.registry import ModuleManifest, envelope_module_type, list_manifests, get_manifest


router = APIRouter(prefix="/modules", tags=["modules"])


class ModuleVariableOut(BaseModel):
    """One field of a module, as an authoring form needs it (task-208).

    `label` is optional (a form falls back to `name`); `envelope` says the field
    belongs on the delivery envelope rather than in the body (ADR-162 point 1);
    `type`, `size`, `note` and `concept` come from `storage/fields.json`
    (ADR-177), the one home for what a field is. Only `name` and `required`
    were exposed until 2026-10-03, so no client could build a form from this.
    """

    name: str
    required: bool
    label: str | None = None
    envelope: bool = False
    type: str = "text"
    size: str | None = None
    note: str | None = None
    concept: str | None = None
    #: `content` (the record or the slot's pick) or `module` (typed in the
    #: module itself): ADR-179's 2026-10-04 addendum, task-223.
    source: str = "content"
    #: May a manager hide this field in this module (ADR-187 point 2)?
    hideable: bool = False
    #: For an `image` field, the field that holds the alt text of a web
    #: address; a form shows it with the address, not as a field of its own
    #: (ADR-197 addendum 2026-10-15, the second).
    alt: str | None = None


class ModuleManifestOut(BaseModel):
    name: str
    channel: str
    label: str
    description: str
    cms: bool
    #: Whether this is the module that carries the channel's envelope — the
    #: subject and preheader for email (ADR-162 point 1). The server's answer
    #: (`envelope_module_type`), exposed so a client never re-derives it by
    #: scanning every module's fields (ADR-177 point 8; task-221). Push has none.
    carries_envelope: bool = False
    #: Two in a row share one 50:50 row (ADR-198 point 4): the Column. The
    #: editor offers adding two at once.
    pairs: bool = False
    variables: list[ModuleVariableOut]


def _to_out(manifest: ModuleManifest) -> ModuleManifestOut:
    return ModuleManifestOut(
        name=manifest.name,
        channel=manifest.channel,
        label=manifest.label,
        description=manifest.description,
        cms=manifest.cms,
        carries_envelope=envelope_module_type(manifest.channel) == manifest.name,
        pairs=manifest.pairs,
        variables=[
            ModuleVariableOut(
                name=v.name, required=v.required, label=v.label, envelope=v.envelope,
                type=v.type, size=v.size, note=v.note, concept=v.concept, source=v.source,
                hideable=v.hideable, alt=v.alt,
            )
            for v in manifest.variables
        ],
    )


@router.get("", response_model=list[ModuleManifestOut])
def get_module_templates(channel: str):
    """Modules one channel accepts. **`channel` is required** (task-21).

    It defaulted to email "so this read-only route keeps its existing contract
    for anything already calling it" — and nothing calls it: not the React
    client, not the Jinja UI, not a test (checked 2026-10-01). What the default
    did do is answer a push screen that forgot the parameter with email modules,
    the module-picker miss in another place. `migrate_0010` added a server
    default, backfilled with it and then dropped it precisely so a forgotten
    channel fails; a route-level default put the email-by-omission back one
    layer up. A missing channel is now a 422.
    """
    return [_to_out(m) for m in list_manifests(channel)]


@router.get("/{name}", response_model=ModuleManifestOut)
def get_module_template(name: str, channel: str):
    """One module on one channel. `channel` required, for the reason above."""
    manifest = get_manifest(channel, name)
    if manifest is None:
        raise HTTPException(
            status_code=404,
            detail=f"Module template '{name}' not found on channel '{channel}'",
        )
    return _to_out(manifest)
