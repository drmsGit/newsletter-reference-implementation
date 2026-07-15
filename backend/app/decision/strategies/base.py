from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.campaigns.db_models import DecisionSlotDB


@dataclass
class StrategyResult:
    content_record_id: int
    content_version_id: int | None
    score: float
    reason: str


@dataclass
class ConfigField:
    """One declared key a strategy expects in its candidate_filter or
    strategy_config. Mirrors the `variables` manifest email module templates
    declare — it lets the UI/API lock a decision slot's config *structure* to
    the chosen strategy (only values editable, not which keys exist)."""

    name: str
    type: str  # "int" | "number" | "str" | "list[int]"
    required: bool = False
    default: Any = None
    description: str = ""


@dataclass
class StrategyMeta:
    name: str
    label: str
    description: str
    requires_recipient: bool = False
    # Declared shapes for the two JSON config columns on a decision slot.
    # Empty list = "this strategy takes no keys here" (anything supplied is
    # rejected). Enforced by normalize_slot_config at slot create/update.
    candidate_filter_fields: list[ConfigField] = field(default_factory=list)
    config_fields: list[ConfigField] = field(default_factory=list)


def _check_type(section: str, spec: "ConfigField", value: Any) -> None:
    ok = True
    if spec.type == "int":
        ok = isinstance(value, int) and not isinstance(value, bool)
    elif spec.type == "number":
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
    elif spec.type == "str":
        ok = isinstance(value, str)
    elif spec.type == "list[int]":
        ok = isinstance(value, list) and all(
            isinstance(v, int) and not isinstance(v, bool) for v in value
        )
    if not ok:
        raise ValueError(
            f"{section} key '{spec.name}' must be of type {spec.type}, got "
            f"{type(value).__name__}"
        )


def _normalize_section(
    section: str, fields: list["ConfigField"], incoming: dict | None
) -> dict | None:
    incoming = incoming or {}
    declared = {f.name: f for f in fields}

    unknown = set(incoming) - set(declared)
    if unknown:
        allowed = sorted(declared) or "(none — this strategy takes no keys here)"
        raise ValueError(
            f"{section} has key(s) not declared by this strategy: "
            f"{sorted(unknown)}. Allowed: {allowed}"
        )

    result: dict[str, Any] = {}
    for name, spec in declared.items():
        if name in incoming:
            _check_type(section, spec, incoming[name])
            result[name] = incoming[name]
        elif spec.required:
            raise ValueError(
                f"{section} is missing required key '{name}' for this strategy"
            )
        elif spec.default is not None:
            # copy so a shared default (e.g. a list) can't be mutated in place
            result[name] = list(spec.default) if isinstance(spec.default, list) else spec.default

    return result or None


def normalize_slot_config(
    meta: StrategyMeta,
    candidate_filter: dict | None,
    strategy_config: dict | None,
) -> tuple[dict | None, dict | None]:
    """Validate a decision slot's candidate_filter/strategy_config against the
    chosen strategy's declared shape and return normalized copies (unknown
    keys rejected, defaults filled, types checked). Raises ValueError on any
    violation so it surfaces as a clean 400/error banner rather than crashing
    later at resolution time."""
    return (
        _normalize_section("candidate_filter", meta.candidate_filter_fields, candidate_filter),
        _normalize_section("strategy_config", meta.config_fields, strategy_config),
    )


class DecisionStrategy(ABC):

    @property
    @abstractmethod
    def meta(self) -> StrategyMeta:
        pass

    @abstractmethod
    def execute(
        self,
        db: Session,
        slot: DecisionSlotDB,
        recipient_id: int | None = None,
    ) -> StrategyResult | None:
        """
        Return a StrategyResult when content is found, or None when no
        suitable content exists. Never raise for a missing-content case —
        the caller handles graceful degradation (ADR-086).
        """
        pass
