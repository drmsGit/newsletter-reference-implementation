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
