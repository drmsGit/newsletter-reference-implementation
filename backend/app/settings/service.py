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


def get_max_send_recipients(db: Session) -> int:
    """Recipient cap for a single send, code default overridden by config."""
    value = get_config(db, MAX_SEND_RECIPIENTS_KEY, None)
    try:
        return int(value) if value is not None else DEFAULT_MAX_SEND_RECIPIENTS
    except (TypeError, ValueError):
        return DEFAULT_MAX_SEND_RECIPIENTS
