"""Running an AI task: prompt lookup → spend gate → adapter → audit.

The order matters and is the ADR, not a preference:

  ADR-144 §5 enforces the spend cap as a **pre-call gate**. A task's worst case
  is knowable before spending anything (count_input_tokens + the task's own
  output ceiling), so a run that would not fit under the remaining cap is
  refused *before it starts*. A stop therefore always lands between runs, never
  mid-run, and nothing is ever spent on work that cannot finish.

  ADR-140 §3 requires every action to be audited with the published
  prompt-version id. Blocked attempts are audited too — refusing to spend is an
  event worth being able to explain later.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.ai.adapters.base import TokenCountUnavailable
from app.ai.adapters.factory import get_ai_provider
from app.ai.db_models import AIPromptDB, AIRunDB
from app.ai.pricing import cost_usd, is_billable
from app.settings.service import get_ai_provider_name, get_ai_spend_cap


@dataclass
class TaskRun:
    """What a task run produced, whether or not a model was actually called."""

    ok: bool
    text: str | None = None
    run_id: int | None = None
    message: str | None = None
    # Populated even when blocked, so the UI can explain *why* it was refused.
    input_tokens: int = 0
    output_tokens: int = 0


def get_published_prompt(db: Session, task_key: str) -> AIPromptDB | None:
    return (
        db.query(AIPromptDB)
        .filter(AIPromptDB.task_key == task_key, AIPromptDB.is_published.is_(True))
        .order_by(AIPromptDB.version.desc())
        .first()
    )


def list_prompt_versions(db: Session, task_key: str) -> list[AIPromptDB]:
    return (
        db.query(AIPromptDB)
        .filter(AIPromptDB.task_key == task_key)
        .order_by(AIPromptDB.version.desc())
        .all()
    )


def publish_prompt(db: Session, task_key: str, body: str) -> AIPromptDB:
    """Save a new prompt version and make it the live one.

    Never mutates an existing row: an audit entry that references version 3 must
    keep resolving to the text version 3 actually had (ADR-140 §3).
    """
    latest = (
        db.query(AIPromptDB)
        .filter(AIPromptDB.task_key == task_key)
        .order_by(AIPromptDB.version.desc())
        .first()
    )
    next_version = (latest.version + 1) if latest else 1

    db.query(AIPromptDB).filter(
        AIPromptDB.task_key == task_key,
        AIPromptDB.is_published.is_(True),
    ).update({"is_published": False})

    row = AIPromptDB(
        task_key=task_key,
        version=next_version,
        body=body,
        is_published=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def tokens_used(db: Session) -> int:
    """Billable tokens spent so far — the ledger the cap is measured against.

    Free adapters are excluded. The cap exists to bound *spend*, and mock runs
    cost nothing, so counting them would let development and demo traffic
    consume a budget only the real model draws on — which is not a rounding
    error: after the first day of building, most rows in this table were mock.
    """
    rows = db.query(
        AIRunDB.provider, AIRunDB.input_tokens, AIRunDB.output_tokens
    ).all()
    return sum(
        (r.input_tokens or 0) + (r.output_tokens or 0)
        for r in rows
        if is_billable(r.provider)
    )


def spend_to_date(db: Session) -> dict:
    """What the billable runs actually cost, in USD.

    Reported next to the token ledger rather than replacing it: tokens are what
    the cap enforces, money is what the manager budgeted. `unpriced_runs` is
    surfaced rather than folded in — a model with no published price here would
    otherwise quietly understate the total.
    """
    rows = db.query(
        AIRunDB.provider, AIRunDB.model,
        AIRunDB.input_tokens, AIRunDB.output_tokens,
    ).all()

    total, unpriced = 0.0, 0
    for row in rows:
        input_tokens, output_tokens = row.input_tokens or 0, row.output_tokens or 0
        # A refused run spent nothing and has no model to price. It is not an
        # unpriced run, it is a run that never happened.
        if not is_billable(row.provider) or not (input_tokens or output_tokens):
            continue
        cost = cost_usd(row.model, input_tokens, output_tokens)
        if cost is None:
            unpriced += 1
            continue
        total += cost

    return {"usd": total, "unpriced_runs": unpriced}


def _record(db: Session, **kwargs) -> AIRunDB:
    row = AIRunDB(**kwargs)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def run_task(
    db: Session,
    task_key: str,
    rendered_prompt: str,
    max_output_tokens: int,
    system: str | None = None,
    provider_name: str | None = None,
    model: str | None = None,
    target_type: str | None = None,
    target_id: int | None = None,
) -> TaskRun:
    """Execute one AI task, enforcing the cap before spending anything."""

    provider_name = provider_name or get_ai_provider_name(db)
    # Which model THIS task runs on (ADR-144 §2). None means the deployment
    # default, so a task nobody has configured behaves exactly as before.
    # Resolved here rather than at the call site so every caller of a task
    # inherits the choice without knowing it exists.
    from app.settings.service import get_task_model

    model = model or get_task_model(db, task_key)
    prompt_row = get_published_prompt(db, task_key)

    if prompt_row is None:
        run = _record(
            db, task_key=task_key, provider=provider_name, status="blocked",
            target_type=target_type, target_id=target_id,
            message="No published prompt for this task — publish one in Settings.",
        )
        return TaskRun(ok=False, run_id=run.id, message=run.message)

    provider = get_ai_provider(provider_name, model=model)

    # --- the pre-call gate (ADR-144 §5) ---------------------------------
    cap = get_ai_spend_cap(db)
    try:
        input_tokens = provider.count_input_tokens(rendered_prompt, system)
    except TokenCountUnavailable as error:
        # No verified input count means no verified worst case, and a gate built
        # on an unverified number is not a gate. Refusing is the conservative
        # branch and it is also the honest one — nothing was spent finding out.
        run = _record(
            db, task_key=task_key, prompt_id=prompt_row.id, provider=provider_name,
            status="blocked", target_type=target_type, target_id=target_id,
            message=(
                f"Refused before running: the cost of this run could not be "
                f"verified up front ({error}). Nothing was spent."
            ),
        )
        return TaskRun(ok=False, run_id=run.id, message=run.message)

    worst_case = input_tokens + max_output_tokens
    used = tokens_used(db)
    # Clamped: once the cap is already exceeded the shortfall is not meaningful,
    # and "-677 remaining" reads as a bug rather than a limit.
    remaining = max(0, cap["hard_stop_tokens"] - used)

    if worst_case > remaining:
        run = _record(
            db, task_key=task_key, prompt_id=prompt_row.id, provider=provider_name,
            status="blocked", target_type=target_type, target_id=target_id,
            message=(
                f"Refused before running: worst case {worst_case} tokens exceeds the "
                f"{remaining} remaining under the {cap['hard_stop_tokens']} cap. "
                f"Nothing was spent."
            ),
        )
        return TaskRun(ok=False, run_id=run.id, message=run.message)

    result = provider.generate(rendered_prompt, max_output_tokens, system)

    if not result.success:
        run = _record(
            db, task_key=task_key, prompt_id=prompt_row.id, provider=provider_name,
            model=result.model, status="error", target_type=target_type,
            target_id=target_id, message=result.message,
        )
        return TaskRun(ok=False, run_id=run.id, message=result.message)

    usage = result.usage
    run = _record(
        db, task_key=task_key, prompt_id=prompt_row.id, provider=provider_name,
        model=result.model, status="ok",
        input_tokens=usage.input_tokens if usage else 0,
        output_tokens=usage.output_tokens if usage else 0,
        target_type=target_type, target_id=target_id,
        output_text=result.text,
        # A truncated result is still returned to the caller (ADR-144: showing a
        # partial is not the same as committing it), but the audit says so.
        message=("output hit its ceiling and is truncated"
                 if result.stop_reason == "max_tokens" else None),
    )
    return TaskRun(
        ok=True,
        text=result.text,
        run_id=run.id,
        message=run.message,
        input_tokens=run.input_tokens,
        output_tokens=run.output_tokens,
    )


def runs_for_target(
    db: Session, target_type: str, target_id: int, limit: int = 25,
) -> list[AIRunDB]:
    """Every run this task made against one thing, newest first.

    **The data was always here; only the surface was missing.** A manager who
    asked for subject lines, picked one, and left the page could not reach the
    other two again — even though `output_text`, the prompt version and the
    token cost were all persisted at the time (`docs/backlog.md`, "recall past
    AI suggestions"). ADR-140 §3 requires these runs to be recorded, and they
    were; the only way to read them was SQL, so an audit trail existed without
    being usable by the person it is meant to serve.

    Bounded, because this is a review surface rather than an export. ADR-132's
    posture applies: the operational system keeps a working window and the
    adopter's warehouse keeps history.
    """
    return (
        db.query(AIRunDB)
        .filter(
            AIRunDB.target_type == target_type,
            AIRunDB.target_id == target_id,
        )
        .order_by(AIRunDB.created_at.desc(), AIRunDB.id.desc())
        .limit(limit)
        .all()
    )


def runs_for_brand(db: Session, brand_id: int, limit: int = 50) -> list[AIRunDB]:
    """Recent variant-targeted runs in one brand, newest first.

    Joined through variant → campaign because `ai_runs` carries no brand of its
    own, and deliberately not given one: a run is audited against the thing it
    acted on, and duplicating the brand onto it would be a second place for the
    answer to drift from (the argument ADR-164 point 9 had to answer the other
    way for signal contributions, where the join was five tables deep and the
    row could outlive it — here it is two and cannot).
    """
    from app.campaigns.db_models import CampaignDB, VariantDB

    return (
        db.query(AIRunDB)
        .join(VariantDB, VariantDB.id == AIRunDB.target_id)
        .join(CampaignDB, CampaignDB.id == VariantDB.campaign_id)
        .filter(AIRunDB.target_type == "variant", CampaignDB.brand_id == brand_id)
        .order_by(AIRunDB.created_at.desc(), AIRunDB.id.desc())
        .limit(limit)
        .all()
    )
