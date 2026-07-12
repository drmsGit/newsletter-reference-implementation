import importlib
import inspect
import logging
import pkgutil
import sys
from pathlib import Path

from app.decision.strategies.base import DecisionStrategy, StrategyMeta

logger = logging.getLogger(__name__)

_EXCLUDED_MODULES = {"base", "registry"}


def _discover() -> dict[str, DecisionStrategy]:
    strategies: dict[str, DecisionStrategy] = {}
    package_dir = Path(__file__).parent

    for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
        if module_name in _EXCLUDED_MODULES:
            continue
        full_name = f"app.decision.strategies.{module_name}"
        try:
            # Reload (not just import) so code edits are picked up, not just
            # the first-ever import — import_module alone is a no-op for a
            # module already in sys.modules.
            if full_name in sys.modules:
                module = importlib.reload(sys.modules[full_name])
            else:
                module = importlib.import_module(full_name)
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, DecisionStrategy) and obj is not DecisionStrategy:
                    instance = obj()
                    strategies[instance.meta.name] = instance
        except Exception:
            # One broken strategy file must not take down the whole
            # registry (and the app, since this used to run at import
            # time) — log which file and keep going.
            logger.warning(
                "Failed to load decision strategy module '%s' — skipping",
                module_name,
                exc_info=True,
            )

    return strategies


def _dir_mtime() -> float:
    package_dir = Path(__file__).parent
    return max(
        (
            p.stat().st_mtime
            for p in package_dir.glob("*.py")
            if p.stem not in _EXCLUDED_MODULES
        ),
        default=0.0,
    )


_REGISTRY: dict[str, DecisionStrategy] = {}
_registry_mtime: float | None = None


def _ensure_fresh() -> None:
    global _REGISTRY, _registry_mtime
    current_mtime = _dir_mtime()
    if _registry_mtime is None or current_mtime != _registry_mtime:
        _REGISTRY = _discover()
        _registry_mtime = current_mtime


def get_strategy(name: str) -> DecisionStrategy:
    _ensure_fresh()
    strategy = _REGISTRY.get(name)
    if strategy is None:
        raise ValueError(f"Unknown decision strategy: '{name}'")
    return strategy


def list_strategies() -> list[StrategyMeta]:
    _ensure_fresh()
    return [s.meta for s in _REGISTRY.values()]
