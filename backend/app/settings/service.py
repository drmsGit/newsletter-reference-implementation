"""Runtime config layer (parametric settings).

Code holds the defaults; an `app_config` row overrides them. Typed accessors
merge the two so callers always get a complete config. Only *values* live here
— the decay model, scoring logic, and plugins stay in code (a different decay
*model* is a code/plugin change, not a setting).
"""
from sqlalchemy.orm import Session

from app.ai.adapters.factory import AVAILABLE_AI_PROVIDERS, DEFAULT_AI_PROVIDER
from app.settings.db_models import AppConfigDB
from app.insight.signals import CONTRIBUTION_WEIGHTS, HALF_LIFE_DAYS

# Config keys.
SIGNAL_WEIGHTS = "signal_weights"
HALF_LIFE_DAYS_KEY = "half_life_days"
MAX_SEND_RECIPIENTS_KEY = "max_send_recipients"
AI_SPEND_CAP_KEY = "ai_spend_cap"
AI_PROVIDER_KEY = "ai_provider"
CHANNEL_AVAILABILITY_KEY = "channel_availability"

# AI token budget (ADR-144 §5). Two numbers, not one: warn first, then hard stop.
# The buffer between them is the point — it is what lets the hard stop be a
# *pre-call* gate, refusing to start a task that would not fit rather than
# cutting one off mid-run. Configurable because the company sets its own limit.
DEFAULT_AI_WARN_TOKENS = 80_000
DEFAULT_AI_HARD_STOP_TOKENS = 100_000

# What the company actually topped up, in USD. Purely a reference point for the
# money readout — the *cap* is and stays the token pair above. A currency figure
# cannot be the gate: what a token costs depends on the input/output mix of a
# run that hasn't happened yet, so a dollar limit could only ever be enforced
# after the fact. 0 means "not stated", and the readout simply omits it.
DEFAULT_AI_BUDGET_USD = 0.0

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


def get_ai_provider_name(db: Session) -> str:
    """Which model the AI layer calls — mock unless a deployment opts in.

    A setting rather than an env var because ADR-140 makes model enablement a
    governed, visible choice: a manager should be able to see that real calls
    are switched on, and switch them off again, without a redeploy. The key
    itself stays in the environment (see the Claude adapter) — the same split
    as sends, where the provider is chosen in the UI and RESEND_API_KEY is not.

    An unrecognised stored value falls back to the safe default instead of
    breaking every run; the form is what refuses to write one.
    """
    name = get_config(db, AI_PROVIDER_KEY, None)
    if isinstance(name, str) and name in AVAILABLE_AI_PROVIDERS:
        return name
    return DEFAULT_AI_PROVIDER


def get_ai_spend_cap(db: Session) -> dict:
    """AI token cap: warn threshold and hard stop, code defaults overridden by config.

    Also carries `budget_usd` — the company's stated top-up, reported next to
    the token figures but never enforced (see DEFAULT_AI_BUDGET_USD).
    """
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

    merged["budget_usd"] = DEFAULT_AI_BUDGET_USD
    try:
        budget = float(overrides["budget_usd"])
        if budget > 0:
            merged["budget_usd"] = budget
    except (KeyError, TypeError, ValueError):
        pass

    return merged


def get_max_send_recipients(db: Session) -> int:
    """Recipient cap for a single send, code default overridden by config."""
    value = get_config(db, MAX_SEND_RECIPIENTS_KEY, None)
    try:
        return int(value) if value is not None else DEFAULT_MAX_SEND_RECIPIENTS
    except (TypeError, ValueError):
        return DEFAULT_MAX_SEND_RECIPIENTS


# --- channel availability (ADR-160 point 8) --------------------------------
# **Registration is a file; availability is a row.** A deployment not licensed
# for a channel — no paid-social ad account, no letter-shop contract — still
# has the manifest and provider files on disk, because deleting them is not how
# anyone manages a contract they do not hold. Code and manifests describe what
# the platform *can* do; this describes what *this deployment* has turned on,
# the same idiom already trusted for the AI kill switch and the governed model
# list.
#
# Stored as {channel name: bool}, and **absent means on**. That direction is
# ADR-160 point 6's criterion applied honestly: *time-to-first-output beats
# completeness* — a channel whose two files someone just dropped in should work
# without a second configuration step, and a company that lacks the contract
# turns it off. Default-off would mean every adopter debugging an empty dropdown
# on day one.


def channel_availability(db: Session) -> dict[str, bool]:
    """The stored overrides only — not the answer. Use `available_channels`."""
    stored = get_config(db, CHANNEL_AVAILABILITY_KEY, None)
    return stored if isinstance(stored, dict) else {}


def available_channels(db: Session):
    """Registered channels this deployment may select, in manifest order."""
    from app.channels.registry import list_channels

    overrides = channel_availability(db)
    return [c for c in list_channels() if overrides.get(c.name, True)]


def channel_available(db: Session, name: str) -> bool:
    """Whether a variant may be created on this channel.

    Two gates, and both matter: the channel must exist on disk at all, and this
    deployment must not have switched it off. An unregistered name answers
    False rather than raising — the caller refuses it, which is ADR-160 point
    8's "refused server-side if requested directly".
    """
    from app.channels.registry import is_registered

    return is_registered(name) and channel_availability(db).get(name, True)


def set_channel_available(db: Session, name: str, enabled: bool) -> dict[str, bool]:
    overrides = channel_availability(db)
    overrides[name] = bool(enabled)
    set_config(db, CHANNEL_AVAILABILITY_KEY, overrides)
    return overrides
