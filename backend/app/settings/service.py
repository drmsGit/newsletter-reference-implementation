"""Runtime config layer (parametric settings).

Code holds the defaults; an `app_config` row overrides them. Typed accessors
merge the two so callers always get a complete config. Only *values* live here
— the decay model, scoring logic, and plugins stay in code (a different decay
*model* is a code/plugin change, not a setting).
"""
from sqlalchemy.orm import Session

from app.settings.db_models import AppConfigDB
from app.insight.signals import CONTRIBUTION_WEIGHTS, HALF_LIFE_DAYS

# Config keys.
SIGNAL_WEIGHTS = "signal_weights"
HALF_LIFE_DAYS_KEY = "half_life_days"
MAX_SEND_RECIPIENTS_KEY = "max_send_recipients"
AI_SPEND_CAP_KEY = "ai_spend_cap"

# AI token budget (ADR-144 §5). Two numbers, not one: warn first, then hard stop.
# The buffer between them is the point — it is what lets the hard stop be a
# *pre-call* gate, refusing to start a task that would not fit rather than
# cutting one off mid-run. Configurable because the company sets its own limit.
DEFAULT_AI_WARN_TOKENS = 80_000
DEFAULT_AI_HARD_STOP_TOKENS = 100_000

# Safety cap on how many recipients one send may target — a guardrail against an
# accidental mass blast. Lives in settings (retunable) here in the POC; in a real
# deployment this belongs in ops/dev config. Generous default so it never blocks
# normal use, only catches obvious mistakes.
DEFAULT_MAX_SEND_RECIPIENTS = 1000


def get_config(db: Session, key: str, default=None):
    row = db.query(AppConfigDB).filter(AppConfigDB.key == key).first()
    return row.value if row is not None else default


def set_config(db: Session, key: str, value) -> AppConfigDB:
    row = db.query(AppConfigDB).filter(AppConfigDB.key == key).first()
    if row is None:
        row = AppConfigDB(key=key, value=value)
        db.add(row)
    else:
        row.value = value
    db.commit()
    db.refresh(row)
    return row


def get_signal_weights(db: Session) -> dict[str, float]:
    """Contribution base weights, code defaults overridden by any config row."""
    overrides = get_config(db, SIGNAL_WEIGHTS, {}) or {}
    return {**CONTRIBUTION_WEIGHTS, **{k: float(v) for k, v in overrides.items()}}


def get_half_lives(db: Session) -> dict[str, float]:
    """Decay half-lives (days), code defaults overridden by any config row."""
    overrides = get_config(db, HALF_LIFE_DAYS_KEY, {}) or {}
    return {**HALF_LIFE_DAYS, **{k: float(v) for k, v in overrides.items()}}


def get_ai_spend_cap(db: Session) -> dict[str, int]:
    """AI token cap: warn threshold and hard stop, code defaults overridden by config."""
    overrides = get_config(db, AI_SPEND_CAP_KEY, {}) or {}
    defaults = {
        "warn_tokens": DEFAULT_AI_WARN_TOKENS,
        "hard_stop_tokens": DEFAULT_AI_HARD_STOP_TOKENS,
    }
    merged = {**defaults}
    for key in defaults:
        try:
            value = int(overrides[key])
            if value > 0:
                merged[key] = value
        except (KeyError, TypeError, ValueError):
            pass
    # A warn threshold above the hard stop would never fire; clamp rather than
    # silently keeping a setting that cannot do its job.
    if merged["warn_tokens"] > merged["hard_stop_tokens"]:
        merged["warn_tokens"] = merged["hard_stop_tokens"]
    return merged


def get_max_send_recipients(db: Session) -> int:
    """Recipient cap for a single send, code default overridden by config."""
    value = get_config(db, MAX_SEND_RECIPIENTS_KEY, None)
    try:
        return int(value) if value is not None else DEFAULT_MAX_SEND_RECIPIENTS
    except (TypeError, ValueError):
        return DEFAULT_MAX_SEND_RECIPIENTS
