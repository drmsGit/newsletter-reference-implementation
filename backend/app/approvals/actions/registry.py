"""Approvable actions, discovered from this package.

The sixth plugin family to follow this shape — decision strategies, modules,
channels, renderers and AI tasks came first — and it is copied rather than
improved on purpose. A registry that is almost like the other five is the one
somebody eventually registers in two places.

**Discovery finds `META`, not a filename.** `base.py` and this file declare
none and are therefore not actions; excluding them by name would break the
moment somebody adds a helper module here.
"""

import importlib
import logging
import pkgutil
import sys
from pathlib import Path

from app.approvals.actions.base import ApprovableAction

logger = logging.getLogger(__name__)


def _discover() -> dict[str, tuple[ApprovableAction, object]]:
    actions: dict[str, tuple[ApprovableAction, object]] = {}
    package_dir = Path(__file__).parent

    for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
        full_name = f"app.approvals.actions.{module_name}"
        try:
            if full_name in sys.modules:
                module = importlib.reload(sys.modules[full_name])
            else:
                module = importlib.import_module(full_name)
        except Exception:
            # One broken action file must not take the registry down with it —
            # the same tolerance the other five apply. A held send whose module
            # fails to import simply cannot be approved, which is the safe
            # direction: the action does not run.
            logger.warning("Failed to load approvable action '%s' — skipping",
                           module_name, exc_info=True)
            continue

        meta = getattr(module, "META", None)
        if isinstance(meta, ApprovableAction):
            if not callable(getattr(module, "execute", None)):
                # An action that cannot run is worse than one that does not
                # exist: it would accept requests, fill the inbox, and refuse
                # at the moment somebody approves it.
                logger.warning(
                    "approvable action '%s' declares META but no execute() — skipping",
                    meta.key,
                )
                continue
            actions[meta.key] = (meta, module)

    return actions


def _dir_mtime() -> float:
    package_dir = Path(__file__).parent
    return max((p.stat().st_mtime for p in package_dir.glob("*.py")), default=0.0)


_REGISTRY: dict[str, tuple[ApprovableAction, object]] = {}
_registry_mtime: float | None = None


def _ensure_fresh() -> None:
    global _REGISTRY, _registry_mtime
    current = _dir_mtime()
    if _registry_mtime is None or current != _registry_mtime:
        _REGISTRY = _discover()
        _registry_mtime = current


def list_actions() -> list[ApprovableAction]:
    """Every registered action, in key order so any listing is stable."""
    _ensure_fresh()
    return [meta for meta, _ in sorted(_REGISTRY.values(), key=lambda pair: pair[0].key)]


def get_action(key: str) -> ApprovableAction | None:
    _ensure_fresh()
    entry = _REGISTRY.get(key)
    return entry[0] if entry else None


def get_action_module(key: str):
    """The module itself, for the caller that needs to `describe` or `execute`.

    Separate from `get_action` for the reason `get_task_module` is separate: the
    inbox listing only ever wants the declaration, and handing it an importable
    module invites it to reach past the contract into functions that differ per
    action.
    """
    _ensure_fresh()
    entry = _REGISTRY.get(key)
    return entry[1] if entry else None
