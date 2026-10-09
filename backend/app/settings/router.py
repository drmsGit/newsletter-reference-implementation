"""The settings API (task-49 C2; ADR-150 and ADR-142 addenda, 2026-10-02).

Until now the whole settings surface was `frontend/router.py` form handlers.
Reading is `view`, as the page always was. **Every write is people only**: a
machine credential is refused even if it holds `settings.manage`, because a
machine that could change settings could raise the send cap, lift the AI spend
limit or switch an AI task to auto-apply. **Publishing a prompt and choosing a
model also need `ai.run`**: each changes what every later AI run does and
spends. **No settings change is approvable** (ADR-142's addendum): whoever holds
`settings.manage` is the authority.

The rules — what a value may be — live in `settings.service`, shared with the
Jinja page; this file only maps them to HTTP.
"""
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import require_person, require_person_with
from app.auth.permissions import AI_RUN
from app.database import get_db
from app.settings import service
from app.settings.audited import audited_settings
from app.settings.models import (
    AIBudget, AITaskSettings, ApprovalModeChoice, ChannelSetting, DeliveryProviderSetting, ModelChoice,
    PromptPublish, PromptVersion, ProviderUpdate, SendCapUpdate, Settings,
    SignalTuning, SpendCapUpdate, UnsubscribeOptions,
)

router = APIRouter(prefix="/settings", tags=["settings"])

# `settings.manage` itself comes from the policy table's `/settings` entry.
_PERSON = [Depends(require_person)]
_PERSON_WITH_AI_RUN = [Depends(require_person_with(AI_RUN))]


def _invalid(error: service.SettingsInvalid) -> HTTPException:
    return HTTPException(status_code=422, detail=str(error))


def _capabilities(request: Request, db: Session) -> tuple[bool, bool]:
    """(may_manage, may_configure_ai) for this caller, by the write routes' own
    rules: a person — never a machine credential, whatever it holds
    (`require_person`) — holding `settings.manage`, and `ai.run` as well for
    prompts and models (`require_person_with`). Both platform-wide, as the
    policy guard checks them."""
    from app.auth.dependencies import _machine_credential, auth_is_enforced, request_principal
    from app.auth.permissions import SETTINGS_MANAGE
    from app.auth.service import ALL_BRANDS, has_permission

    if _machine_credential(request) is not None:
        return False, False
    if not auth_is_enforced(request):
        return True, True
    principal = request_principal(request)
    manage = has_permission(db, principal, SETTINGS_MANAGE, brand_id=ALL_BRANDS)
    return manage, manage and has_permission(db, principal, AI_RUN, brand_id=ALL_BRANDS)


@router.get("", response_model=Settings, summary="Everything the settings screen shows")
def read_settings(request: Request, db: Session = Depends(get_db)):
    from app.ai.adapters.claude import DEFAULT_MODEL as CLAUDE_DEFAULT_MODEL
    from app.ai.adapters.factory import AVAILABLE_AI_PROVIDERS
    from app.ai.service import get_published_prompt, list_prompt_versions
    from app.ai.tasks.registry import list_tasks
    from app.channels.registry import list_channels

    may_manage, may_configure_ai = _capabilities(request, db)
    enabled = {c.name for c in service.available_channels(db)}
    tasks = []
    for meta in list_tasks():
        published = get_published_prompt(db, meta.key)
        tasks.append(AITaskSettings(
            key=meta.key, label=meta.label, description=meta.description,
            prompt_body=published.body if published else meta.default_prompt,
            prompt_version=published.version if published else None,
            versions=[
                PromptVersion(version=v.version, body=v.body,
                              is_published=v.is_published, created_at=v.created_at)
                for v in list_prompt_versions(db, meta.key)
            ],
            model=service.get_task_model(db, meta.key),
            approval_mode=service.get_task_approval_mode(db, meta.key),
        ))
    return Settings(
        signals=SignalTuning(
            weights=service.get_signal_weights(db), half_lives=service.get_half_lives(db),
        ),
        signal_defaults=SignalTuning(
            weights=dict(service.CONTRIBUTION_WEIGHTS), half_lives=dict(service.HALF_LIFE_DAYS),
        ),
        known_contribution_types=sorted(service.known_contribution_types()),
        max_send_recipients=service.get_max_send_recipients(db),
        channels=[ChannelSetting(name=c.name, available=c.name in enabled) for c in list_channels()],
        delivery_providers=_delivery_providers(),
        ai_provider=service.get_ai_provider_name(db),
        ai_providers=list(AVAILABLE_AI_PROVIDERS),
        ai_key_present=bool(os.environ.get("ANTHROPIC_API_KEY")),
        ai_model=os.environ.get("ANTHROPIC_MODEL") or CLAUDE_DEFAULT_MODEL,
        ai_model_from_env=bool(os.environ.get("ANTHROPIC_MODEL")),
        ai_budget=AIBudget(**service.ai_budget_status(db)),
        ai_tasks=tasks,
        governed_models=service.governed_models(),
        may_manage=may_manage,
        may_configure_ai=may_configure_ai,
    )


def _delivery_providers() -> list[DeliveryProviderSetting]:
    """Each provider once, with the channels it carries and whether its clicks
    can name their content (task-240)."""
    from app.channels.registry import list_channels
    from app.delivery.providers.factory import providers_for_channel

    found: dict[str, dict] = {}
    for channel in (c.name for c in list_channels()):
        for provider in providers_for_channel(channel):
            entry = found.setdefault(provider["name"], {**provider, "channels": []})
            entry["channels"].append(channel)
    return [
        DeliveryProviderSetting(
            name=p["name"], label=p["label"], channels=p["channels"],
            click_content_attribution=p["click_content_attribution"],
        )
        for p in found.values()
    ]


@router.put(
    "/signals", response_model=SignalTuning, dependencies=_PERSON,
    summary="Replace the signal weights and half-lives",
    description=(
        "Replaces the overrides: a contribution type not named returns to its code "
        "default. Unknown types and a half-life of 0 or less are refused (422)."
    ),
)
def put_signals(payload: SignalTuning, request: Request, db: Session = Depends(get_db)):
    try:
        with audited_settings(request, db, "signals",
                              [service.SIGNAL_WEIGHTS, service.HALF_LIFE_DAYS_KEY]):
            service.save_signal_tuning(db, payload.weights, payload.half_lives)
    except service.SettingsInvalid as error:
        raise _invalid(error)
    return SignalTuning(weights=service.get_signal_weights(db),
                        half_lives=service.get_half_lives(db))


@router.put("/send-cap", response_model=SendCapUpdate, dependencies=_PERSON,
            summary="The most recipients one send may reach")
def put_send_cap(payload: SendCapUpdate, request: Request, db: Session = Depends(get_db)):
    with audited_settings(request, db, "send_cap", [service.MAX_SEND_RECIPIENTS_KEY]):
        service.save_max_send_recipients(db, payload.max_send_recipients)
    return SendCapUpdate(max_send_recipients=service.get_max_send_recipients(db))


@router.get("/unsubscribe", response_model=UnsubscribeOptions, summary="What the unsubscribe page offers")
def get_unsubscribe_options(db: Session = Depends(get_db)):
    return UnsubscribeOptions(offer_everything=service.get_unsubscribe_offer_everything(db))


@router.put("/unsubscribe", response_model=UnsubscribeOptions, dependencies=_PERSON,
            summary="Offer 'everything from the company' on the unsubscribe page")
def put_unsubscribe_options(payload: UnsubscribeOptions, request: Request, db: Session = Depends(get_db)):
    with audited_settings(request, db, "unsubscribe", [service.UNSUBSCRIBE_OFFER_EVERYTHING_KEY]):
        service.set_unsubscribe_offer_everything(db, payload.offer_everything)
    return UnsubscribeOptions(offer_everything=service.get_unsubscribe_offer_everything(db))


@router.put(
    "/ai/spend-cap", response_model=AIBudget, dependencies=_PERSON,
    summary="The AI token cap and the stated budget",
    description="Omitted fields keep their value. A warning above the hard stop is refused.",
)
def put_spend_cap(payload: SpendCapUpdate, request: Request, db: Session = Depends(get_db)):
    try:
        with audited_settings(request, db, "ai_spend_cap", [service.AI_SPEND_CAP_KEY]):
            service.save_ai_spend_cap(db, **payload.model_dump())
    except service.SettingsInvalid as error:
        raise _invalid(error)
    return AIBudget(**service.ai_budget_status(db))


@router.put("/ai/provider", response_model=ProviderUpdate, dependencies=_PERSON,
            summary="Which AI provider runs the tasks (a governed list)")
def put_provider(payload: ProviderUpdate, request: Request, db: Session = Depends(get_db)):
    try:
        with audited_settings(request, db, "ai_provider", [service.AI_PROVIDER_KEY]):
            service.save_ai_provider(db, payload.provider)
    except service.SettingsInvalid as error:
        raise _invalid(error)
    return ProviderUpdate(provider=service.get_ai_provider_name(db))


@router.put("/ai/tasks/{task_key}/approval", response_model=ApprovalModeChoice,
            dependencies=_PERSON, summary="Apply this task's output directly, or hold it")
def put_approval_mode(
    task_key: str, payload: ApprovalModeChoice, request: Request, db: Session = Depends(get_db),
):
    try:
        with audited_settings(request, db, "ai_task_approval", [service.AI_TASK_APPROVAL_KEY]):
            service.choose_task_approval_mode(db, task_key, payload.mode)
    except service.SettingsInvalid as error:
        raise HTTPException(status_code=404, detail=str(error))
    return ApprovalModeChoice(mode=service.get_task_approval_mode(db, task_key))


@router.post(
    "/ai/tasks/{task_key}/prompt", response_model=PromptVersion, status_code=201,
    dependencies=_PERSON_WITH_AI_RUN,
    summary="Publish a new prompt version (needs settings.manage and ai.run)",
    description="A new immutable version becomes the live one; no version is ever edited (ADR-140 §3).",
)
def post_prompt(
    task_key: str, payload: PromptPublish, request: Request, db: Session = Depends(get_db),
):
    try:
        service.require_known_task(task_key)
    except service.SettingsInvalid as error:
        raise HTTPException(status_code=404, detail=str(error))
    try:
        with audited_settings(request, db, "ai_task_prompt", []) as note:
            row = service.publish_task_prompt(db, task_key, payload.body)
            note.update(task=task_key, version=row.version)
    except service.SettingsInvalid as error:
        raise _invalid(error)
    return PromptVersion(version=row.version, body=row.body,
                         is_published=row.is_published, created_at=row.created_at)


@router.put(
    "/ai/tasks/{task_key}/model", response_model=ModelChoice,
    dependencies=_PERSON_WITH_AI_RUN,
    summary="Point a task at a governed model, or null for the default (needs ai.run too)",
)
def put_model(
    task_key: str, payload: ModelChoice, request: Request, db: Session = Depends(get_db),
):
    try:
        service.require_known_task(task_key)
    except service.SettingsInvalid as error:
        raise HTTPException(status_code=404, detail=str(error))
    try:
        with audited_settings(request, db, "ai_task_model", [service.AI_TASK_MODELS_KEY]):
            service.choose_task_model(db, task_key, payload.model)
    except service.SettingsInvalid as error:
        raise _invalid(error)
    return ModelChoice(model=service.get_task_model(db, task_key))
