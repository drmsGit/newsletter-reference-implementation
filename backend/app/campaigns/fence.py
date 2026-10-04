"""The advisory fence on a variant (ADR-180, task-254).

"Blocked by X, last updated HH:MM — unblock." Every composer write sets the
fence to whoever made it; it lapses 30 minutes after the last edit; a person
may clear any fence, a machine only its own (user decision 2026-10-04,
ADR-180 addendum). For a person it is a social signal and never stops an
edit (point 1). For a machine it is binding: a machine's write across
another actor's active fence is refused, server-side, by actor type rather
than by a grantable permission (points 3 and 4).

Written from the routes, beside the audit entry, because the route is where
the actor is known — the same reason the audit log is (ADR-153's addendum).
The label is the readable name, as `content_overrides.overridden_by` is
(`auth.service.actor_label`); `audit_events` keeps the id-based record.
"""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.campaigns.db_models import DecisionSlotDB, ModuleInstanceDB, VariantDB

#: How long a fence holds after the last edit (user decision, 2026-10-04).
FENCE_LAPSE = timedelta(minutes=30)

USER = "user"
INTEGRATION = "integration"


def _principal(request):
    """The caller on either plane: the JSON guard's resolved principal (a
    person or a machine), or the signed-in person of the Jinja plane, whose
    middleware sets `current_user` and no principal."""
    return getattr(request.state, "principal", None) or getattr(request.state, "current_user", None)


def _actor(principal) -> tuple[str | None, int | None, str]:
    from app.auth.db_models import IntegrationDB, UserDB
    from app.auth.service import actor_label

    if isinstance(principal, IntegrationDB):
        return INTEGRATION, principal.id, actor_label(principal)
    if isinstance(principal, UserDB):
        return USER, principal.id, actor_label(principal)
    if isinstance(principal, dict) and principal.get("id") is not None:
        # The Jinja plane's `current_user`: plain data made for templates
        # (`auth.service.current_user_summary`). Labelled as `actor_label`
        # labels a person, by email.
        return USER, principal["id"], principal["email"]
    return None, None, actor_label(principal)


def variant_of(
    db: Session,
    *,
    variant_id: int | None = None,
    module_id: int | None = None,
    slot_id: int | None = None,
    override_id: int | None = None,
) -> int | None:
    """The variant a composer write touches, from whichever id the route has."""
    if variant_id is not None:
        return variant_id
    if override_id is not None:
        from app.overrides.db_models import ContentOverrideDB

        module_id = db.query(ContentOverrideDB.module_instance_id).filter(
            ContentOverrideDB.id == override_id).scalar()
    if module_id is not None:
        return db.query(ModuleInstanceDB.variant_id).filter(ModuleInstanceDB.id == module_id).scalar()
    if slot_id is not None:
        return db.query(DecisionSlotDB.variant_id).filter(DecisionSlotDB.id == slot_id).scalar()
    return None


def is_active(variant: VariantDB, now: datetime | None = None) -> bool:
    if variant.fenced_at is None:
        return False
    return (now or datetime.now(timezone.utc)) - variant.fenced_at < FENCE_LAPSE


def view(variant: VariantDB) -> dict | None:
    """The fence as the editor shows it, lapsed or not: a lapsed fence is still
    "last edited by X at HH:MM", it just no longer holds anyone off."""
    if variant.fenced_at is None:
        return None
    return {
        "by": variant.fenced_by_label, "by_type": variant.fenced_by_type,
        "at": variant.fenced_at, "active": is_active(variant),
    }


def _held_by_other(variant: VariantDB, actor_type: str | None, actor_id: int | None) -> bool:
    return is_active(variant) and (variant.fenced_by_type, variant.fenced_by_id) != (actor_type, actor_id)


def guard(db: Session, request, **ids) -> None:
    """Refuse a machine's write across another actor's active fence (point 3).

    Called before the write. A person is never stopped (point 1); an id that
    resolves to nothing — or to another brand's variant — is left to the
    service to answer as not found, so a 423 never tells a caller that a
    variant exists in a brand it cannot see (ADR-172 point 6).
    """
    from app.auth.dependencies import working_brand
    from app.campaigns.service import get_variant

    actor_type, actor_id, _label = _actor(_principal(request))
    if actor_type != INTEGRATION:
        return
    variant_id = variant_of(db, **ids)
    variant = (
        get_variant(db, variant_id, brand_id=working_brand(request))
        if variant_id is not None else None
    )
    if variant is not None and _held_by_other(variant, actor_type, actor_id):
        raise HTTPException(status_code=423, detail=(
            f"{variant.fenced_by_label} is working on this variant (last edit "
            f"{variant.fenced_at.isoformat()}). A machine waits until the fence lapses "
            f"{int(FENCE_LAPSE.total_seconds() // 60)} minutes after the last edit, or "
            "until a person unblocks it."
        ))


def touch(db: Session, request, **ids) -> None:
    """Set the fence to whoever just wrote (every composer write, both planes).

    A Core UPDATE that writes `updated_at` back to itself: the variant's
    version token must not move when one of its modules is edited, or the
    editor's next subject save would be refused as stale against the
    person's own work (task-110).
    """
    variant_id = variant_of(db, **ids)
    if variant_id is None:
        return
    actor_type, actor_id, label = _actor(_principal(request))
    db.execute(
        update(VariantDB)
        .where(VariantDB.id == variant_id)
        .values(fenced_by_type=actor_type, fenced_by_id=actor_id, fenced_by_label=label,
                fenced_at=func.now(), updated_at=VariantDB.updated_at)
    )
    db.commit()


def clear(db: Session, request, variant: VariantDB) -> None:
    """Unblock: a person may clear any fence; a machine only one it holds
    (ADR-180 point 3). Leaves `updated_at` alone, as `touch` does."""
    actor_type, actor_id, _label = _actor(_principal(request))
    if actor_type == INTEGRATION and _held_by_other(variant, actor_type, actor_id):
        raise HTTPException(status_code=423, detail="A machine never clears a fence it did not set.")
    db.execute(
        update(VariantDB)
        .where(VariantDB.id == variant.id)
        .values(fenced_by_type=None, fenced_by_id=None, fenced_by_label=None, fenced_at=None,
                updated_at=VariantDB.updated_at)
    )
    db.commit()
