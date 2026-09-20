"""Running an AI task and deciding what happens to its output.

**This is the step between a task and a screen**, and it lived inside one Jinja
route until 2026-09-20 (inventory B15). Three things happen here and none of
them belongs to a presentation layer:

1. **The envelope guard.** A channel with no envelope module is refused
   *before* the model is called. The button is hidden in the template, but a
   hand-crafted POST never sees a template — and this task spends tokens
   against the budget (ADR-144 §5) to write copy that has nowhere to be
   stored, since `set_envelope_fields` writes only into the module a channel
   declares. A guard that exists only where the button is drawn is not a
   spend guard.
2. **The approval mode.** ADR-141 §4's per-task setting: inline by default,
   because ADR-140's Context rejects routing every AI action through approval
   — it "buries managers in approvals" — and a manager who asked for subject
   lines is looking at the page. A company that wants a second pair of eyes
   turns it on, and only then does the suggestion become a held request.
3. **The duplicate.** One open request per subject is a partial unique index,
   so asking twice is an ordinary thing a user does, not an error.

The caller decides how to render the outcome. It does not decide any of the
above, which is the point: a JSON client that skipped the envelope guard would
spend tokens on a request that cannot succeed.
"""
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

#: What happened, for a caller to render.
#:
#: `refused` and `nothing_to_work_from` are deliberately distinct even though
#: both mean "no tokens were spent". The first is "this channel has no subject
#: line"; the second is "there is no content to write one from". They are
#: different things for the person to fix.
Outcome = Literal["refused", "nothing_to_work_from", "inline", "held", "duplicate"]


@dataclass
class SuggestionResult:
    outcome: Outcome
    message: str | None = None
    #: The persisted run, for the inline case. The run id is what a caller
    #: reads the options back with — the options are not returned here,
    #: because the run row is the record and a second copy would be a second
    #: source of truth.
    run_id: int | None = None
    #: The held request, for the approval case.
    pending_action_id: int | None = None


def suggest_subject_for_variant(
    db: Session,
    variant_id: int,
    *,
    brand_id: int,
    requested_by_type: str,
    requested_by_id: int | None,
) -> SuggestionResult:
    """Suggest subject/preheader copy, honouring both guards and the mode.

    `brand_id` is required and the variant is resolved through the scoped
    getter: the Jinja route read `VariantDB` by bare id, so this was also a
    small brand gap — one that ADR-172 would otherwise have missed, because it
    lived in a router rather than a service.
    """
    from app.ai.tasks import subject_preheader as subject_task
    from app.approvals import service as approvals
    from app.approvals.actions import ai_subject_apply
    from app.campaigns.service import get_variant
    from app.modules.registry import envelope_module_type
    from app.settings.service import REQUIRE_APPROVAL, get_task_approval_mode

    variant = get_variant(db, variant_id, brand_id=brand_id)
    if variant is None or envelope_module_type(variant.channel) is None:
        return SuggestionResult(
            outcome="refused",
            message=(
                "That channel has no subject line, so there is nothing to "
                "suggest."
            ),
        )

    try:
        _options, run = subject_task.suggest(db, variant_id)
    except subject_task.NothingToWorkFrom as refusal:
        # Refused before the call, so no tokens were spent and no run row was
        # written. The person is told what to fix rather than being handed the
        # model's (correct, and paid-for) version of the same sentence.
        return SuggestionResult(outcome="nothing_to_work_from", message=str(refusal))

    if run is None:
        return SuggestionResult(
            outcome="refused", message="That variant no longer exists.",
        )

    if get_task_approval_mode(db, subject_task.TASK_KEY) != REQUIRE_APPROVAL:
        return SuggestionResult(outcome="inline", run_id=run.run_id)

    try:
        held = approvals.request_approval(
            db, ai_subject_apply.META.key,
            payload={"ai_run_id": run.run_id},
            summary=ai_subject_apply.summarise(db, run.run_id, brand_id=brand_id),
            requested_by_type=requested_by_type,
            requested_by_id=requested_by_id,
            brand_id=brand_id,
            subject_id=run.run_id,
        )
    except approvals.DuplicateRequest:
        return SuggestionResult(
            outcome="duplicate",
            message=(
                "A suggestion for this variant is already waiting for approval."
            ),
            run_id=run.run_id,
        )
    return SuggestionResult(
        outcome="held", run_id=run.run_id, pending_action_id=held.id,
    )
