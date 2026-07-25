"""Signal computation (ADR-132).

A signal is a decay-weighted aggregation over the append-only
`SignalContributionDB` log — computed on read, never stored as a running total.
This is the operational signal: it drives audience resolution and sends, over a
recency-weighted window. Historical signals / long-term learning live in the
adopter's DWH (out of scope here).

Weights and half-lives are POC defaults; a future config layer lets a deployment
retune them. Reliability-weighted per ADR-132: clicks are the reliable behavioral
signal, opens are Apple-MPP/bot noise (off by default), unsubscribe is a strong
negative, and manual/declared preferences are heavy but decay slowly so behavior
eventually wins over stale stated interest.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.recipients.db_models import SignalContributionDB

# Base weight added by one contribution *before* decay, per type.
CONTRIBUTION_WEIGHTS: dict[str, float] = {
    "manual": 40.0,       # declared on purpose — heavy
    "click": 5.0,         # reliable behavioral signal (bot-filtered upstream)
    "open": 0.0,          # Apple MPP makes opens noise — off by default
    "unsubscribe": -50.0,  # strong negative — genuine disinterest
    # "conversion": extension point — sourcing is company-specific (ADR-132),
    #   the adopter supplies the event + its weight.
}

# Operational half-life (days) per contribution type. Manual is long so a
# declared preference dominates for months, then fades if never reinforced.
HALF_LIFE_DAYS: dict[str, float] = {
    "manual": 180.0,
    "click": 45.0,
    "open": 45.0,
    "unsubscribe": 120.0,
}
DEFAULT_HALF_LIFE_DAYS = 45.0


def _decayed_weight(base_weight: float, occurred_at: datetime, contribution_type: str, now: datetime) -> float:
    half_life = HALF_LIFE_DAYS.get(contribution_type, DEFAULT_HALF_LIFE_DAYS)
    age_days = max((now - occurred_at).total_seconds() / 86400.0, 0.0)
    return base_weight * (0.5 ** (age_days / half_life))


def record_contribution(
    db: Session,
    recipient_id: int,
    category_id: int,
    contribution_type: str,
    occurred_at: datetime | None = None,
    event_id: int | None = None,
    source: str = "engagement",
    base_weight: float | None = None,
) -> SignalContributionDB:
    """Append one contribution to the log. `base_weight` defaults to the
    configured weight for the type; pass it explicitly to scale (e.g. by a
    content record's category relevance)."""
    if base_weight is None:
        base_weight = CONTRIBUTION_WEIGHTS.get(contribution_type)
        if base_weight is None:
            raise ValueError(
                f"no default weight for contribution_type '{contribution_type}'"
            )
    contribution = SignalContributionDB(
        recipient_id=recipient_id,
        category_id=category_id,
        contribution_type=contribution_type,
        base_weight=base_weight,
        occurred_at=occurred_at or datetime.now(timezone.utc),
        event_id=event_id,
        source=source,
    )
    db.add(contribution)
    db.commit()
    db.refresh(contribution)
    return contribution


def get_operational_signal(
    db: Session,
    recipient_id: int,
    category_id: int,
    now: datetime | None = None,
) -> float:
    """The current operational signal for one (recipient, category): the
    decay-weighted sum of its contributions."""
    now = now or datetime.now(timezone.utc)
    rows = (
        db.query(SignalContributionDB)
        .filter(
            SignalContributionDB.recipient_id == recipient_id,
            SignalContributionDB.category_id == category_id,
        )
        .all()
    )
    return sum(_decayed_weight(r.base_weight, r.occurred_at, r.contribution_type, now) for r in rows)


def operational_signals_for_recipient(
    db: Session,
    recipient_id: int,
    now: datetime | None = None,
) -> dict[int, float]:
    """{category_id: signal} for one recipient — for the decision strategy and
    the recipient detail view."""
    now = now or datetime.now(timezone.utc)
    rows = (
        db.query(SignalContributionDB)
        .filter(SignalContributionDB.recipient_id == recipient_id)
        .all()
    )
    signals: dict[int, float] = {}
    for r in rows:
        signals[r.category_id] = signals.get(r.category_id, 0.0) + _decayed_weight(
            r.base_weight, r.occurred_at, r.contribution_type, now
        )
    return signals


def operational_signals_for_category(
    db: Session,
    category_id: int,
    now: datetime | None = None,
) -> dict[int, float]:
    """{recipient_id: signal} for one category — for audience criteria
    resolution (find recipients whose signal for a category clears a threshold)."""
    now = now or datetime.now(timezone.utc)
    rows = (
        db.query(SignalContributionDB)
        .filter(SignalContributionDB.category_id == category_id)
        .all()
    )
    signals: dict[int, float] = {}
    for r in rows:
        signals[r.recipient_id] = signals.get(r.recipient_id, 0.0) + _decayed_weight(
            r.base_weight, r.occurred_at, r.contribution_type, now
        )
    return signals
