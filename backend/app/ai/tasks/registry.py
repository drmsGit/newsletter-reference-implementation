"""AI tasks, discovered from this package.

The last plugin family that was not drop-a-file. Four registries already follow
this exact shape — `decision/strategies`, `modules`, `channels` and
`rendering/renderers` — and a fifth pattern would be the one that eventually
gets registered in two places.

What this fixes, concretely: `app/ai/tasks/` held one task and no registry, so
the settings route imported that module by name and the template hardcoded a
card bound to singular context keys. Tasks only *looked* like a plugin family
because there was exactly one; a second needed a new `.py`, an import plus
three context keys in the router, and a duplicated card in the template.

**Discovery finds `META`, not a filename.** A module in this package that does
not declare one is not a task — `base.py` and this file are the obvious cases,
and excluding them by name would break the moment somebody adds a helper.
"""

import importlib
import inspect
import logging
import pkgutil
import sys
from pathlib import Path

from app.ai.tasks.base import TaskMeta

logger = logging.getLogger(__name__)


def _discover() -> dict[str, tuple[TaskMeta, object]]:
    tasks: dict[str, tuple[TaskMeta, object]] = {}
    package_dir = Path(__file__).parent

    for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
        full_name = f"app.ai.tasks.{module_name}"
        try:
            if full_name in sys.modules:
                module = importlib.reload(sys.modules[full_name])
            else:
                module = importlib.import_module(full_name)
        except Exception:
            # One broken task file must not take the registry down with it —
            # the same tolerance the other four registries apply, and for the
            # same reason: a typo in a task nobody is using should not stop the
            # ones that are.
            logger.warning("Failed to load AI task '%s' — skipping",
                           module_name, exc_info=True)
            continue

        meta = getattr(module, "META", None)
        if isinstance(meta, TaskMeta):
            tasks[meta.key] = (meta, module)

    return tasks


def _dir_mtime() -> float:
    package_dir = Path(__file__).parent
    return max((p.stat().st_mtime for p in package_dir.glob("*.py")), default=0.0)


_REGISTRY: dict[str, tuple[TaskMeta, object]] = {}
_registry_mtime: float | None = None


def _ensure_fresh() -> None:
    global _REGISTRY, _registry_mtime
    current = _dir_mtime()
    if _registry_mtime is None or current != _registry_mtime:
        _REGISTRY = _discover()
        _registry_mtime = current


def list_tasks() -> list[TaskMeta]:
    """Every registered task, in key order so the settings page is stable."""
    _ensure_fresh()
    return [meta for meta, _ in sorted(_REGISTRY.values(), key=lambda pair: pair[0].key)]


def get_task(key: str) -> TaskMeta | None:
    _ensure_fresh()
    entry = _REGISTRY.get(key)
    return entry[0] if entry else None


def get_task_module(key: str):
    """The module itself, for the caller that needs to *run* the task.

    Separate from `get_task` on purpose: the settings page only ever wants the
    metadata, and handing it an importable module would invite it to reach past
    the declaration into functions that differ per task.
    """
    _ensure_fresh()
    entry = _REGISTRY.get(key)
    return entry[1] if entry else None
