from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.modules.registry import ModuleManifest, list_manifests, get_manifest


router = APIRouter(prefix="/email-modules", tags=["email-modules"])


class ModuleVariableOut(BaseModel):
    name: str
    required: bool


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
            ModuleVariableOut(name=v.name, required=v.required)
            for v in manifest.variables
        ],
    )


@router.get("", response_model=list[ModuleManifestOut])
def get_module_templates(channel: str = "email"):
    """Modules one channel accepts. Defaults to email so this read-only route
    keeps its existing contract for anything already calling it; every other
    caller of the registry passes the channel explicitly."""
    return [_to_out(m) for m in list_manifests(channel)]


@router.get("/{name}", response_model=ModuleManifestOut)
def get_module_template(name: str, channel: str = "email"):
    manifest = get_manifest(channel, name)
    if manifest is None:
        raise HTTPException(
            status_code=404,
            detail=f"Module template '{name}' not found on channel '{channel}'",
        )
    return _to_out(manifest)
