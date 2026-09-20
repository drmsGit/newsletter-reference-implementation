"""Apply an AI-suggested subject line a manager chose — ADR-141 §4.

**The second action, and deliberately the least like the first.** A machine
send is one thing to say yes or no to; this is *pick one of three*, and the
spine was designed around ADR-141 §4's "accept/reject per item, **pick-one for
options**" precisely so the difference lives in the action rather than in the
inbox. N options are ONE pending action — three proposed subject lines are a
single decision, not three.

**Its subject is the AI run, not the variant**, which is what closes
`docs/backlog.md`'s "recall past AI suggestions" item without migrating
`ai_runs`: a pending action pointing at a run gives that run a decision record
— who applied which option, when, and why — while `AIRunDB` keeps being the
audit of the call. ADR-153's division exactly: domain records for *what*, and
the thing beside them for *who*.

**Approving is a different permission from requesting.** Asking costs `ai.run`,
because it spends money; applying writes the variant, which is
`campaigns.manage`. That divergence is why `approve_permission` is declared per
action rather than inferred from the route that raised the request — the first
action's two happened to coincide, and this one's do not.
"""

import logging

from sqlalchemy.orm import Session

from app.approvals.actions.base import (
    ActionDescription, ActionResult, ApprovableAction,
)
from app.ai.db_models import AIRunDB
from app.campaigns.db_models import VariantDB

logger = logging.getLogger(__name__)

META = ApprovableAction(
    key="ai.apply_subject_preheader",
    label="Use an AI-suggested subject line",
    approve_permission="campaigns.manage",
    # Shorter than a send's day. A suggestion is about copy that is being
    # written now; one from last week is answering a question nobody is still
    # asking, and the options can be regenerated for a few cents.
    default_ttl_seconds=8 * 60 * 60,
    subject_type="ai_run",
    description=(
        "An AI task proposed subject and preheader options for a variant. "
        "Approving writes the one that was picked."
    ),
)


def summarise(db: Session, run_id: int, *, brand_id: int) -> str:
    """The frozen line, naming only what this brand may see (ADR-172 point 6).

    `ai_runs` carries no brand of its own — it targets a variant, which does,
    transitively. So the variant is resolved through the scoped getter and an
    out-of-brand one falls back to the bare id rather than quoting a name the
    reader has no business seeing.
    """
    from app.campaigns.service import get_variant

    run = db.query(AIRunDB).filter(AIRunDB.id == run_id).first()
    if run is None:
        return f"Subject suggestions from run #{run_id} (no longer present)"
    variant = get_variant(db, run.target_id, brand_id=brand_id)
    label = variant.name if variant else f"variant {run.target_id}"
    return f"Subject line options for “{label}”"


def _options(db: Session, run: AIRunDB) -> list[dict]:
    from app.ai.tasks import subject_preheader

    return subject_preheader.parse_options(run.output_text or "")


def describe(db: Session, payload: dict, *, brand_id: int) -> ActionDescription:
    run_id = payload.get("ai_run_id")
    run = db.query(AIRunDB).filter(AIRunDB.id == run_id).first()
    if run is not None:
        from app.campaigns.service import get_variant

        # The run exists; whether this brand may look at it is a separate
        # question, answered by its target variant.
        if get_variant(db, run.target_id, brand_id=brand_id) is None:
            run = None
    if run is None:
        return ActionDescription(
            summary=f"AI run #{run_id} no longer exists.",
            blocked_reason=(
                "The suggestions this request refers to have been pruned, so "
                "there is nothing left to apply."
            ),
        )

    variant = db.query(VariantDB).filter(VariantDB.id == run.target_id).first()
    options = _options(db, run)

    rows = [
        ("Variant", variant.name if variant else f"#{run.target_id}"),
        ("Model", run.model or "—"),
        ("Cost", f"{run.input_tokens or 0} in / {run.output_tokens or 0} out tokens"),
    ]
    if run.prompt_id:
        # ADR-140 §5 requires the prompt-version id in the audit of every AI
        # action. Showing it here is what makes "which prompt produced this?"
        # answerable by the person deciding rather than only by a query.
        rows.append(("Prompt version", f"#{run.prompt_id}"))

    blocked_reason = None
    if variant is None:
        blocked_reason = "The variant these were written for no longer exists."
    elif not options:
        blocked_reason = (
            "No usable options could be read from the reply, so there is "
            "nothing to apply."
        )

    return ActionDescription(
        summary=summarise(db, run.id, brand_id=brand_id),
        rows=rows,
        warnings=(
            [run.message] if run.message else []
        ),
        blocked_reason=blocked_reason,
        # The options themselves, which the detail page renders as a pick-one.
        options=[
            {"label": f"{o['subject']} — {o['preheader']}".rstrip(" —"), **o}
            for o in options
        ] or None,
        link=(
            f"/ui/campaigns/{variant.campaign_id}" if variant else None
        ),
    )


def execute(
    db: Session, payload: dict, *, choice: dict | None = None, brand_id: int,
) -> ActionResult:
    """Write the chosen option onto the variant.

    **Refuses without a choice rather than defaulting to the first.** A
    pick-one with an implicit default is how "the manager approved it" becomes
    "the manager approved whatever happened to be at the top", and the whole
    point of holding three options is that somebody chose between them.
    """
    # The same writer the inline accept uses. Reaching for `update_variant`
    # here instead would write columns that no longer exist — subject and
    # preheader became module fields in ADR-162 point 1 — and the fact that
    # `update_variant` still takes those keyword arguments is exactly why this
    # is worth saying out loud rather than discovering at runtime.
    from app.campaigns.service import set_envelope_fields

    run = db.query(AIRunDB).filter(AIRunDB.id == payload.get("ai_run_id")).first()
    if run is None:
        return ActionResult(ok=False, message="those suggestions are gone")

    options = _options(db, run)
    if not options:
        return ActionResult(ok=False, message="no usable options in that reply")

    index = (choice or {}).get("index")
    if index is None:
        return ActionResult(
            ok=False,
            message="pick one of the options — approving does not choose for you",
        )
    try:
        picked = options[int(index)]
    except (ValueError, IndexError):
        return ActionResult(ok=False, message=f"option {index} is not on offer")

    variant = db.query(VariantDB).filter(VariantDB.id == run.target_id).first()
    if variant is None:
        return ActionResult(ok=False, message="that variant no longer exists")

    # **Resolved from the variant, not from the approver's session.** This runs
    # inside `approvals.approve`, which has no request — and the brand that
    # matters is the one the variant belongs to, not whichever brand the
    # approver happened to be looking at. `brand_of_variant` answers exactly
    # that question (ADR-172 point 5's resolver half).
    from app.campaigns.service import brand_of_variant

    brand_id = brand_of_variant(db, variant.id)
    if brand_id is None:
        return ActionResult(ok=False, message="that variant has no brand")

    set_envelope_fields(db, variant.id, {
        "subject": picked.get("subject", ""),
        "preheader": picked.get("preheader", ""),
    }, brand_id=brand_id)
    return ActionResult(
        ok=True,
        message=f"Applied: {picked.get('subject', '')}",
        audit_action="ai.suggestion_applied",
        audit_detail={
            "ai_run_id": run.id,
            "variant_id": variant.id,
            "option_index": int(index),
            "prompt_id": run.prompt_id,
        },
    )
