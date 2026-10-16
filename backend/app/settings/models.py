"""Shapes for the settings API (task-49 C2, task-50 B5–B8)."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SignalTuning(BaseModel):
    """Contribution base weights and decay half-lives, by contribution type."""

    weights: dict[str, float]
    half_lives: dict[str, float]


class SpendCap(BaseModel):
    warn_tokens: int
    hard_stop_tokens: int
    budget_usd: float


class Spend(BaseModel):
    usd: float
    unpriced_runs: int


class AIBudget(BaseModel):
    #: month | quarter | year | lifetime (task-345); the figures cover it.
    period: str = "month"
    #: When it began, at midnight UTC; null for lifetime.
    period_start: datetime | None = None
    cap: SpendCap
    tokens_used: int
    spend: Spend
    tokens_remaining: int
    used_pct: int
    over_warn: bool


class PromptVersion(BaseModel):
    version: int
    body: str
    is_published: bool
    created_at: datetime


class AITaskSettings(BaseModel):
    key: str
    label: str
    description: str
    # The live prompt: the published version, or the task's default if none.
    prompt_body: str
    prompt_version: int | None = None
    versions: list[PromptVersion]
    # None means the deployment default model (ADR-144 §2).
    model: str | None = None
    approval_mode: str
    held_form: bool = Field(True, description="False: no approval step; the output appears only where a person takes it")


class ChannelSetting(BaseModel):
    name: str
    # Whether this deployment has the channel switched on (ADR-160 point 8).
    # Readable only; there is no route that changes it yet.
    available: bool


class DeliveryProviderSetting(BaseModel):
    name: str
    label: str
    channels: list[str]
    # ADR-182 point 4: false means clicks count for the email and credit no
    # category — the provider stays selectable.
    click_content_attribution: bool
    # The send screen asks for a sender only where the provider uses one
    # (task-67), prefilled with the deployment's default sender.
    needs_from_address: bool = False
    default_from_address: str | None = None


class Settings(BaseModel):
    """Everything the settings screen shows. Readable with `view`."""

    signals: SignalTuning
    # The code defaults (ADR-132), so a screen can say what a blank means.
    signal_defaults: SignalTuning
    known_contribution_types: list[str]
    max_send_recipients: int
    session_absolute_hours: int = 12
    session_idle_minutes: int = 60
    channels: list[ChannelSetting]
    delivery_providers: list[DeliveryProviderSetting]
    ai_provider: str
    ai_providers: list[str]
    # Whether a key is configured — never the key (ADR-152).
    ai_key_present: bool
    ai_model: str
    ai_model_from_env: bool
    ai_budget: AIBudget
    ai_tasks: list[AITaskSettings]
    governed_models: list[str]
    # What THIS caller may change (2026-10-03), so the screen offers controls
    # only where a write would be accepted — computed by the same rules the
    # write routes apply, never by the client. People only, platform-wide.
    may_manage: bool = False
    may_configure_ai: bool = False


class SendCapUpdate(BaseModel):
    max_send_recipients: int = Field(gt=0)


class SessionLengths(BaseModel):
    """How long a sign-in lasts (task-342; ADR-151 addendum 2026-10-11): at
    most `absolute_hours` (1-72), and `idle_minutes` (5-480, never longer than
    the lifetime) without activity. A shorter value applies at once."""

    absolute_hours: int
    idle_minutes: int


class UnsubscribeOptions(BaseModel):
    """Whether the unsubscribe page offers opting out of everything from the
    company, beside the sending brand (ADR-191 point 4). Off by default."""

    offer_everything: bool


class AIBudgetPeriod(BaseModel):
    """How often the AI cap refills (task-345): month, quarter, year or lifetime.
    Periods start at midnight UTC."""

    period: str


class SpendCapUpdate(BaseModel):
    """Any of the three; an omitted field keeps its current value."""

    warn_tokens: int | None = Field(default=None, gt=0)
    hard_stop_tokens: int | None = Field(default=None, gt=0)
    budget_usd: float | None = Field(default=None, ge=0)


class ProviderUpdate(BaseModel):
    provider: str


class PromptPublish(BaseModel):
    body: str = Field(min_length=1)


class ModelChoice(BaseModel):
    # None points the task back at the deployment default.
    model: str | None = None


class ApprovalModeChoice(BaseModel):
    mode: Literal["auto_apply", "require_approval"]
