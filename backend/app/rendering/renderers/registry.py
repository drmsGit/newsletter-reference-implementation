"""Channel renderers, discovered from this package — ADR-162 point 4.

Same shape as `decision/strategies/registry.py`, deliberately: a reference
architecture that uses three different plugin patterns teaches three things
nobody asked to learn.
"""

import importlib
import inspect
import logging
import pkgutil
import sys
from pathlib import Path

from app.rendering.renderers.base import ChannelRenderer

logger = logging.getLogger(__name__)

_EXCLUDED_MODULES = {"base", "registry"}


def _discover() -> dict[str, ChannelRenderer]:
    renderers: dict[str, ChannelRenderer] = {}
    package_dir = Path(__file__).parent

    for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
        if module_name in _EXCLUDED_MODULES:
            continue
        full_name = f"app.rendering.renderers.{module_name}"
        try:
            if full_name in sys.modules:
                module = importlib.reload(sys.modules[full_name])
            else:
                module = importlib.import_module(full_name)
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, ChannelRenderer) and obj is not ChannelRenderer:
                    instance = obj()
                    if instance.channel:
                        renderers[instance.channel] = instance
        except Exception:
            logger.warning(
                "Failed to load channel renderer '%s' — skipping",
                module_name, exc_info=True,
            )

    return renderers


def _dir_mtime() -> float:
    package_dir = Path(__file__).parent
    return max(
        (p.stat().st_mtime for p in package_dir.glob("*.py")
         if p.stem not in _EXCLUDED_MODULES),
        default=0.0,
    )


_REGISTRY: dict[str, ChannelRenderer] = {}
_registry_mtime: float | None = None


def _ensure_fresh() -> None:
    global _REGISTRY, _registry_mtime
    current_mtime = _dir_mtime()
    if _registry_mtime is None or current_mtime != _registry_mtime:
        _REGISTRY = _discover()
        _registry_mtime = current_mtime


def get_renderer(channel: str) -> ChannelRenderer | None:
    _ensure_fresh()
    return _REGISTRY.get(channel)


def list_renderers() -> list[ChannelRenderer]:
    _ensure_fresh()
    return list(_REGISTRY.values())
