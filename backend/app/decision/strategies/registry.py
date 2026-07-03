import importlib
import inspect
import pkgutil
from pathlib import Path

from app.decision.strategies.base import DecisionStrategy, StrategyMeta

_EXCLUDED_MODULES = {"base", "registry"}


def _discover() -> dict[str, DecisionStrategy]:
    strategies: dict[str, DecisionStrategy] = {}
    package_dir = Path(__file__).parent

    for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
        if module_name in _EXCLUDED_MODULES:
            continue
        module = importlib.import_module(
            f"app.decision.strategies.{module_name}"
        )
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, DecisionStrategy) and obj is not DecisionStrategy:
                instance = obj()
                strategies[instance.meta.name] = instance

    return strategies


_REGISTRY: dict[str, DecisionStrategy] = _discover()


def get_strategy(name: str) -> DecisionStrategy:
    strategy = _REGISTRY.get(name)
    if strategy is None:
        raise ValueError(f"Unknown decision strategy: '{name}'")
    return strategy


def list_strategies() -> list[StrategyMeta]:
    return [s.meta for s in _REGISTRY.values()]
