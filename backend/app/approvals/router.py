"""The approval inbox over JSON — [[ADR-168]]'s 2026-09-19 addendum.

**A person may approve here; a machine may not.** That is ADR-166 point 5 kept
in fact: an integration may *request* approval and may never grant it, because
one that can approve its own held request has defeated the mechanism holding
it. Until now the property was kept by there being no route at all — true of
the machine plane, and wrong for people the moment ADR-168 put them on it,
where it said the React client could not work an inbox at all. The property is
unchanged; what enforces it is a guard rather than an absence, which is also
the sharper thing to test.

**The row-level rule is not here.** `approvals.service.may_decide` answers
"may this person decide this row", because every approvable action declares its
own `approve_permission` and the policy table cannot express a permission that
depends on the row. The Jinja plane asks the same function (ADR-172 point 7).
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.approvals import service as approvals
from app.approvals.actions.registry import get_action, get_action_module
from app.approvals.models import (
    DecisionRequest, DecisionResult, DescriptionRow, PendingActionDetail,
    PendingActionRow,
)
from app.audit.service import ACTOR_USER, events_for_subject
from app.auth.dependencies import require_person, working_brand
from app.auth.service import SESSION_COOKIE, user_for_token
from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/approvals", tags=["approvals"])


def _row(row) -> PendingActionRow:
    meta = get_action(row.action_key)
    return PendingActionRow(
        id=row.id,
        action_key=row.action_key,
        label=meta.label if meta else row.action_key,
        summary=row.summary,
        # `effective_status`, never the column — see the model's note.
        status=approvals.effective_status(row),
        brand_id=row.brand_id,
        requested_by_type=row.requested_by_type,
        requested_by_id=row.requested_by_id,
        created_at=row.created_at,
        expires_at=row.expires_at,
        decided_at=row.decided_at,
    )


@router.get(
    "/",
    response_model=list[PendingActionRow],
    summary="The approval inbox for the working brand",
    description=(
        "`status` is one of `pending` (the default), `decided` or `all`. "
        "Pending excludes a request whose deadline has passed but whose stored "
        "status has not caught up: the list agrees with what approving would "
        "actually do, which is read from the timestamp."
    ),
)
def list_pending(
    status: str = approvals.PENDING,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    return [_row(row) for row in approvals.list_for_brand(db, brand_id, status=status)]


@router.get(
    "/{pending_id}",
    response_model=PendingActionDetail,
    summary="One held action, with its live description",
)
def get_pending(
    request: Request,
    pending_id: int,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    from app.approvals.db_models import PendingActionDB

    row = (
        db.query(PendingActionDB)
        .filter(PendingActionDB.id == pending_id, PendingActionDB.brand_id == brand_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="No such request in this brand.")

    meta = get_action(row.action_key)
    module = get_action_module(row.action_key)
    rows: list[DescriptionRow] = []
    blocked_reason = None
    describe_error = None
    if module is not None and hasattr(module, "describe"):
        try:
            # The row's brand, not the reader's working brand. They are equal
            # here because the row was selected by it — but `describe` is
            # answering about the request, and the request's brand is the one
            # on the row (ADR-172 point 5's resolver half).
            description = module.describe(db, row.payload or {}, brand_id=row.brand_id)
            rows = [DescriptionRow(label=k, value=str(v)) for k, v in description.rows]
            blocked_reason = description.blocked_reason
        except Exception as failure:
            # A description that raises must not hide the request: the reviewer
            # still needs to see something is waiting, and still needs to be
            # able to reject it.
            describe_error = str(failure)
            logger.warning("approval %s: describe() failed", pending_id, exc_info=True)

    user = user_for_token(db, request.cookies.get(SESSION_COOKIE))
    return PendingActionDetail(
        **_row(row).model_dump(),
        rows=rows,
        blocked_reason=blocked_reason,
        describe_error=describe_error,
        may_decide=bool(meta) and approvals.may_decide(db, user, meta, row),
    )


@router.get(
    "/{pending_id}/history",
    summary="What has happened to this request",
    description=(
        "From `audit_events`, not from the pending row. ADR-142 §4: the "
        "accountability lives in the audit trail, and dropping every pending "
        "row would leave this answer intact."
    ),
)
def get_history(
    pending_id: int,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    from app.approvals.db_models import PendingActionDB

    exists = (
        db.query(PendingActionDB.id)
        .filter(PendingActionDB.id == pending_id, PendingActionDB.brand_id == brand_id)
        .first()
    )
    if exists is None:
        raise HTTPException(status_code=404, detail="No such request in this brand.")
    return [
        {
            "action": event.action,
            "actor_type": event.actor_type,
            "actor_id": event.actor_id,
            "created_at": event.created_at,
            "detail": event.detail,
        }
        for event in events_for_subject(db, approvals.SUBJECT, pending_id)
    ]


def _decide(request: Request, db: Session, pending_id: int, brand_id: int):
    user = user_for_token(db, request.cookies.get(SESSION_COOKIE))
    row, meta, refusal = approvals.resolve_for_decision(
        db, pending_id, brand_id=brand_id, user=user,
    )
    if refusal:
        # 404 when it is not here, 403 when it is and this person may not
        # decide it. Conflating them would tell a caller to go and fix a
        # permission for a request that simply is not theirs.
        raise HTTPException(status_code=404 if row is None else 403, detail=refusal)
    return user, row, meta


@router.post(
    "/{pending_id}/approve",
    response_model=DecisionResult,
    dependencies=[Depends(require_person)],
    summary="Approve a held action, which runs it",
)
def approve(
    request: Request,
    pending_id: int,
    payload: DecisionRequest | None = None,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    """Approving is what executes it (ADR-142 §4).

    **A bearer credential is refused here** by `require_person`, whatever
    permissions it holds. That is not a permission question: the machine plane
    may request and may not grant.
    """
    user, row, _meta = _decide(request, db, pending_id, brand_id)
    payload = payload or DecisionRequest()
    choice = (
        {"index": payload.choice_index} if payload.choice_index is not None else None
    )
    result = approvals.approve(
        db, pending_id,
        approver_type=ACTOR_USER, approver_id=user.id if user else None,
        choice=choice, reason=(payload.reason or "").strip() or None,
    )
    db.refresh(row)
    return DecisionResult(
        ok=result.ok,
        message=result.message or ("Approved and executed." if result.ok else "Refused."),
        status=approvals.effective_status(row),
    )


@router.post(
    "/{pending_id}/reject",
    response_model=DecisionResult,
    dependencies=[Depends(require_person)],
    summary="Reject a held action",
)
def reject(
    request: Request,
    pending_id: int,
    payload: DecisionRequest | None = None,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    user, row, _meta = _decide(request, db, pending_id, brand_id)
    payload = payload or DecisionRequest()
    ok = approvals.reject(
        db, pending_id,
        approver_type=ACTOR_USER, approver_id=user.id if user else None,
        reason=(payload.reason or "").strip() or None,
    )
    db.refresh(row)
    return DecisionResult(
        ok=bool(ok),
        message="Rejected." if ok else "That request is no longer pending.",
        status=approvals.effective_status(row),
    )


@router.post(
    "/process-expired",
    summary="Retire every request past its deadline",
    description=(
        "The cron seam, for the same reason `/delivery/process-due` has one: a "
        "scheduler drives it on an interval and the architecture exposes the "
        "seam rather than baking in a scheduler. Bookkeeping only — approving "
        "already refuses an expired request whatever this has or has not done, "
        "so a deployment that never calls it is correct and merely untidy."
    ),
)
def process_expired(db: Session = Depends(get_db)):
    expired = approvals.expire_due_pending_actions(db)
    return {"expired": len(expired), "pending_action_ids": expired}
