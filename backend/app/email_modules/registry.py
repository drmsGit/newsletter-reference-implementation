import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

EMAIL_MODULES_DIR = (
    Path(__file__).parent.parent.parent.parent / "storage" / "email_modules"
)


@dataclass
class ModuleVariable:
    name: str
    required: bool = True


@dataclass
class ModuleManifest:
    name: str        # derived from filename stem
    label: str
    description: str
    cms: bool        # True = variables come from CMS/decision slot; False = from module_data
    variables: list[ModuleVariable] = field(default_factory=list)


def _load_manifest(json_path: Path) -> ModuleManifest:
    data = json.loads(json_path.read_text())
    return ModuleManifest(
        name=json_path.stem,
        label=data["label"],
        description=data.get("description", ""),
        cms=data.get("cms", False),
        variables=[
            ModuleVariable(name=v["name"], required=v.get("required", True))
            for v in data.get("variables", [])
        ],
    )


def _discover() -> dict[str, ModuleManifest]:
    if not EMAIL_MODULES_DIR.exists():
        logger.warning("email_modules directory not found: %s", EMAIL_MODULES_DIR)
        return {}

    manifests: dict[str, ModuleManifest] = {}

    for json_path in sorted(EMAIL_MODULES_DIR.glob("*.json")):
        html_path = json_path.with_suffix(".html")
        if not html_path.exists():
            logger.warning(
                "Manifest %s has no matching .html file — skipping", json_path.name
            )
            continue
        manifests[json_path.stem] = _load_manifest(json_path)

    for html_path in EMAIL_MODULES_DIR.glob("*.html"):
        if html_path.stem not in manifests:
            logger.warning(
                "%s has no matching .json manifest — skipping", html_path.name
            )

    return manifests


def _dir_mtime() -> float:
    if not EMAIL_MODULES_DIR.exists():
        return 0.0
    return max(
        (p.stat().st_mtime for p in EMAIL_MODULES_DIR.glob("*")),
        default=0.0,
    )


_REGISTRY: dict[str, ModuleManifest] = {}
_registry_mtime: float | None = None


def _ensure_fresh() -> None:
    global _REGISTRY, _registry_mtime
    current_mtime = _dir_mtime()
    if _registry_mtime is None or current_mtime != _registry_mtime:
        _REGISTRY = _discover()
        _registry_mtime = current_mtime


def get_manifest(name: str) -> ModuleManifest | None:
    _ensure_fresh()
    return _REGISTRY.get(name)


def list_manifests() -> list[ModuleManifest]:
    _ensure_fresh()
    return list(_REGISTRY.values())


def get_template_html(name: str) -> str | None:
    html_path = EMAIL_MODULES_DIR / f"{name}.html"
    if not html_path.exists():
        return None
    return html_path.read_text()
