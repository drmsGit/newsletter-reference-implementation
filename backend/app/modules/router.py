from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.modules.registry import ModuleManifest, list_manifests, get_manifest


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


class ModuleManifestOut(BaseModel):
    name: str
    channel: str
    label: str
    description: str
    cms: bool
    variables: list[ModuleVariableOut]


def _to_out(manifest: ModuleManifest) -> ModuleManifestOut:
    return ModuleManifestOut(
        name=manifest.name,
        channel=manifest.channel,
        label=manifest.label,
        description=manifest.description,
        cms=manifest.cms,
        variables=[
            ModuleVariableOut(
                name=v.name, required=v.required, label=v.label, envelope=v.envelope,
                type=v.type, size=v.size, note=v.note, concept=v.concept,
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
