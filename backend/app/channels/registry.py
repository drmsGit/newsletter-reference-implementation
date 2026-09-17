"""Channels, discovered from `storage/channels/*.json`.

[[ADR-160]] point 6: **registering a channel means a channel manifest plus a
provider adapter — two files, no config step.** "The manifest *is* the channel;
the adapter *is* the vendor." There is deliberately no registry table and no
settings row for *registration* — decision strategies already auto-register
from a dropped `.py` and module manifests from `name.json`, and a third pattern
that needs registering in several places is the one that eventually gets
registered in two.

**What a channel manifest holds is deliberately almost nothing.** ADR-161
point 7 settles the split: *provider `.py` = capabilities · module manifest =
fields and limits · channel = an attribute on the variant plus which manifests
it accepts*, leaving **cardinality** as "the only genuinely channel-level
fact". So `max_modules` is the one rule here, and it is what lets composition
code stay channel-neutral: ADR-160 point 2 requires push to be "one
`ModuleInstanceDB` at position 0" **as a declared capability rather than the
composition code special-casing push**, and a number in a file is how that
promise is kept.

`max_modules: null` means unbounded — email and letter. Push declares 1.

Registration is not availability. Whether a deployment may *select* a channel
is ADR-160 point 8's settings row (`app/settings/service.py`), because a
company without a paid-social ad account still has the files on disk; deleting
them is not how anyone manages a contract they do not hold.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

CHANNELS_DIR = Path(__file__).parent.parent.parent.parent / "storage" / "channels"

#: The channel every pre-2026-09-17 variant is, and the fallback a caller gets
#: when it asks for nothing. Named rather than repeated as a string literal,
#: the same way `consent.DEFAULT_CHANNEL` is.
DEFAULT_CHANNEL = "email"


@dataclass
class ChannelManifest:
    name: str            # derived from the filename stem, as module manifests are
    label: str
    description: str
    #: None = unbounded. ADR-161 point 7's one channel-level fact.
    max_modules: int | None
    #: Which `storage/modules/<dir>/` this channel's modules live in
    #: (ADR-162 point 5). Defaults to the channel name; declared so a channel
    #: could share another's modules without a symlink.
    module_directory: str


def _load(path: Path) -> ChannelManifest:
    data = json.loads(path.read_text())
    return ChannelManifest(
        name=path.stem,
        label=data["label"],
        description=data.get("description", ""),
        max_modules=data.get("max_modules"),
        module_directory=data.get("module_directory", path.stem),
    )


def _discover() -> dict[str, ChannelManifest]:
    if not CHANNELS_DIR.exists():
        logger.warning("channels directory not found: %s", CHANNELS_DIR)
        return {}

    manifests: dict[str, ChannelManifest] = {}
    for path in sorted(CHANNELS_DIR.glob("*.json")):
        try:
            manifests[path.stem] = _load(path)
        except Exception:
            # One malformed manifest must not take the registry down with it —
            # the same tolerance `email_modules.registry` already applies, and
            # for the same reason: a typo in a channel nobody is using should
            # not stop the ones that are.
            logger.warning("Failed to load channel manifest '%s' — skipping",
                           path.name, exc_info=True)
    return manifests


def _dir_mtime() -> float:
    if not CHANNELS_DIR.exists():
        return 0.0
    return max((p.stat().st_mtime for p in CHANNELS_DIR.glob("*")), default=0.0)


_REGISTRY: dict[str, ChannelManifest] = {}
_registry_mtime: float | None = None


def _ensure_fresh() -> None:
    global _REGISTRY, _registry_mtime
    current = _dir_mtime()
    if _registry_mtime is None or current != _registry_mtime:
        _REGISTRY = _discover()
        _registry_mtime = current


def get_channel(name: str) -> ChannelManifest | None:
    _ensure_fresh()
    return _REGISTRY.get(name)


def list_channels() -> list[ChannelManifest]:
    _ensure_fresh()
    return list(_REGISTRY.values())


def is_registered(name: str) -> bool:
    """Whether a channel exists on disk at all.

    Distinct from *available* — a registered channel a deployment has not
    turned on is refused by the settings check, not by this one.
    """
    return get_channel(name) is not None


def max_modules_for(name: str) -> int | None:
    """How many modules a variant of this channel may hold. None = unbounded.

    An unregistered channel answers 1 rather than unbounded. Fail-closed: the
    caller is about to be refused anyway, and guessing "unlimited" for
    something nobody declared is the wrong direction to be wrong in.
    """
    manifest = get_channel(name)
    if manifest is None:
        return 1
    return manifest.max_modules
