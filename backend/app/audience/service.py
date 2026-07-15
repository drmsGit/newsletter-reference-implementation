from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB
from app.recipients.db_models import RecipientDB, RecipientPreferenceDB
from app.recipients.service import CONSENTING_STATUS


def list_groups(db: Session) -> list[AudienceGroupDB]:
    return db.query(AudienceGroupDB).order_by(AudienceGroupDB.name.asc()).all()


def get_group(db: Session, group_id: int) -> AudienceGroupDB | None:
    return db.query(AudienceGroupDB).filter(AudienceGroupDB.id == group_id).first()


def create_group(db: Session, name: str, description: str | None = None) -> AudienceGroupDB:
    group = AudienceGroupDB(name=name, description=description)
    db.add(group)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"An audience group named '{name}' already exists")
    db.refresh(group)
    return group


def update_group(
    db: Session, group_id: int, name: str, description: str | None = None
) -> AudienceGroupDB | None:
    group = get_group(db, group_id)
    if not group:
        return None
    group.name = name
    group.description = description
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"An audience group named '{name}' already exists")
    db.refresh(group)
    return group


def delete_group(db: Session, group_id: int) -> bool:
    group = get_group(db, group_id)
    if not group:
        return False
    db.query(AudienceGroupMemberDB).filter(AudienceGroupMemberDB.group_id == group_id).delete()
    db.delete(group)
    db.commit()
    return True


def list_members(db: Session, group_id: int) -> list[AudienceGroupMemberDB]:
    return (
        db.query(AudienceGroupMemberDB)
        .filter(AudienceGroupMemberDB.group_id == group_id)
        .all()
    )


def add_member(db: Session, group_id: int, recipient_id: int) -> AudienceGroupMemberDB | None:
    existing = (
        db.query(AudienceGroupMemberDB)
        .filter(
            AudienceGroupMemberDB.group_id == group_id,
            AudienceGroupMemberDB.recipient_id == recipient_id,
        )
        .first()
    )
    if existing:
        return existing
    member = AudienceGroupMemberDB(group_id=group_id, recipient_id=recipient_id)
    db.add(member)
    try:
        db.commit()
    except IntegrityError:
        # A concurrent call won the TOCTOU race between the check above and
        # this insert — the unique constraint caught it; treat it the same
        # as "already a member" rather than surfacing a raw 500.
        db.rollback()
        return (
            db.query(AudienceGroupMemberDB)
            .filter(
                AudienceGroupMemberDB.group_id == group_id,
                AudienceGroupMemberDB.recipient_id == recipient_id,
            )
            .first()
        )
    db.refresh(member)
    return member


def remove_member(db: Session, group_id: int, recipient_id: int) -> bool:
    member = (
        db.query(AudienceGroupMemberDB)
        .filter(
            AudienceGroupMemberDB.group_id == group_id,
            AudienceGroupMemberDB.recipient_id == recipient_id,
        )
        .first()
    )
    if not member:
        return False
    db.delete(member)
    db.commit()
    return True


def get_member_recipient_ids(db: Session, group_id: int) -> set[int]:
    rows = (
        db.query(AudienceGroupMemberDB.recipient_id)
        .filter(AudienceGroupMemberDB.group_id == group_id)
        .all()
    )
    return {r.recipient_id for r in rows}


def find_by_criteria(
    db: Session,
    *,
    language: str | None = None,
    status: str | None = None,
    preference_category_id: int | None = None,
    min_preference_score: float | None = None,
    exclude_ids: set[int] | None = None,
) -> list[RecipientDB]:
    # Consent gate: audiences are resolved only from consenting recipients.
    # Filtering here — at audience-resolution time, before any decisioning or
    # rendering runs — is deliberate (F1 in docs/backlog.md): it keeps
    # non-consenting recipients out of the processing scope entirely, both for
    # GDPR reasons (running the decision engine over their data is itself
    # "processing") and cost reasons (no paid AI/token spend on people who will
    # never receive anything). "pending" and "opted_out" are both excluded.
    q = db.query(RecipientDB).filter(RecipientDB.consent_status == CONSENTING_STATUS)

    if language:
        q = q.filter(RecipientDB.language == language)
    if status:
        q = q.filter(RecipientDB.status == status)
    if preference_category_id is not None:
        min_score = min_preference_score if min_preference_score is not None else 0.0
        q = (
            q.join(RecipientPreferenceDB, RecipientDB.id == RecipientPreferenceDB.recipient_id)
            .filter(RecipientPreferenceDB.category_id == preference_category_id)
            .filter(RecipientPreferenceDB.score >= min_score)
        )
    if exclude_ids:
        q = q.filter(RecipientDB.id.notin_(exclude_ids))

    records = q.order_by(RecipientDB.email.asc()).all()

    # RecipientDB.email has no unique constraint (a hard-unique decision is
    # deferred) — dedupe by email here so a bad import with duplicate-email
    # rows doesn't inflate or double-count a segment preview.
    seen_emails: set[str] = set()
    deduplicated: list[RecipientDB] = []
    for record in records:
        if record.email in seen_emails:
            continue
        seen_emails.add(record.email)
        deduplicated.append(record)

    return deduplicated


def bulk_add_members(db: Session, group_id: int, recipient_ids: list[int]) -> int:
    existing = get_member_recipient_ids(db, group_id)
    added = 0
    for rid in recipient_ids:
        if rid not in existing:
            db.add(AudienceGroupMemberDB(group_id=group_id, recipient_id=rid))
            added += 1
    if not added:
        return added

    try:
        db.commit()
    except IntegrityError:
        # A concurrent call added one of these rows between the check above
        # and this commit. Fall back to committing one at a time so a
        # single conflicting row doesn't lose the rest of a legitimate
        # batch — each conflicting insert is skipped, not fatal.
        db.rollback()
        added = 0
        for rid in recipient_ids:
            if rid in existing:
                continue
            db.add(AudienceGroupMemberDB(group_id=group_id, recipient_id=rid))
            try:
                db.commit()
                added += 1
            except IntegrityError:
                db.rollback()

    return added
