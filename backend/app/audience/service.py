import logging

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB, AudienceRuleBlockDB
from app.recipients.db_models import RecipientDB
from app.recipients.consent import DEFAULT_CHANNEL, MARKETING, is_consenting_filter, resolve_emails
from app.insight.signals import operational_signals_for_category

logger = logging.getLogger(__name__)

# Default minimum signal a system-suggested include block asks for. Deliberately
# low: the first suggestion should be inclusive ("anyone who's shown interest in
# this topic") and let the manager tighten it live — same broad-then-narrow
# stance as the override layer. On the operational-signal scale (declared
# interest ≈ 90, each click ≈ 5, decaying) this keeps recipients with any
# lingering positive signal for the category.
DEFAULT_SUGGESTION_MIN_SCORE = 1.0


def list_groups(db: Session, *, brand_id: int) -> list[AudienceGroupDB]:
    """Audience groups, scoped to one brand (ADR-150 point 2).

    Brand here is **ownership, not membership**: the criteria behind a group
    resolve to the same people whichever brand asks, because a recipient
    carries no brand (point 9) and consent does not carry one yet. Making
    membership differ per brand is the Phase 2 consent work.

    **The brand is required since 2026-09-19** (ADR-172 point 4). It used to
    default to every brand, which meant a forgotten argument returned the whole
    platform rather than failing. `list_all_audience_groups` is the road for
    callers that genuinely span brands.
    """
    return (
        db.query(AudienceGroupDB)
        .filter(AudienceGroupDB.brand_id == brand_id)
        .order_by(AudienceGroupDB.name.asc())
        .all()
    )


def list_all_audience_groups(db: Session) -> list[AudienceGroupDB]:
    """Every group, across every brand — the ADR-172 point 4 escape hatch.

    For callers that legitimately have no working brand. Counted by
    `test_brand_boundary.py`; no router may reach for it.
    """
    return db.query(AudienceGroupDB).order_by(AudienceGroupDB.name.asc()).all()


def group_regardless_of_brand(db: Session, group_id: int) -> AudienceGroupDB | None:
    """A group without asking which brand the caller is in.

    **Deliberately unscoped, and there is exactly one legitimate use**:
    `resolve_audience`, which gates on the group's OWN brand and therefore has
    to find the group before it knows which brand that is. Scoping it there
    would be circular, and passing the caller's brand in would be wrong — a
    manager who switched brand between building a send and firing it must not
    change whose consent was checked.

    Every other caller wants `get_group`, which takes a brand and refuses
    outside it. This one is named at length so that reaching for it is a
    decision rather than an autocomplete.
    """
    return db.query(AudienceGroupDB).filter(AudienceGroupDB.id == group_id).first()


# --- writes: one version, validated rules (task-295) ------------------------

#: "Not passed", for a partial update where None is a value (clear it).
UNSET = object()


def touch(group: AudienceGroupDB) -> None:
    """Move the group's version: any write to it, its rules or its members
    changes who the audience is, so it is one thing with one version (the
    design pass, decision 10). By hand, because a rule or member write leaves
    the group's own row clean and `onupdate` would not fire."""
    group.updated_at = func.now()


def check_version(db: Session, group: AudienceGroupDB, expected_updated_at) -> None:
    """Refuse a write based on an out-of-date read (ADR-180 point 2), the
    composer's rule: no token, no check."""
    from app.campaigns.service import refuse_stale

    refuse_stale(db, group, expected_updated_at, "audience")


class GroupInUse(Exception):
    """A group a send uses cannot be deleted (the design pass, decision 8).
    Not a ValueError, so no route mistakes it for a bad request."""

    def __init__(self, sends: list[str]):
        self.sends = sends
        named = ", ".join(sends[:5]) + (", …" if len(sends) > 5 else "")
        super().__init__(
            f"Used by {len(sends)} send{'' if len(sends) == 1 else 's'} ({named}). Sent mail must keep "
            "its audience; remove it from planned sends first."
        )


class CriteriaInvalid(ValueError):
    """A rule that does not say something meaningful, with each field's reason."""

    def __init__(self, errors: list[tuple[str, str]]):
        self.errors = errors
        super().__init__("; ".join(f"{field}: {message}" for field, message in errors))


#: What a rule can say today (ADR-188 point 2). Related data waits for task-294.
CRITERIA_FIELDS = frozenset({"language", "status", "category_id", "min_score"})


def _values(value) -> list[str]:
    """A rule's multi-value field as a list: an older rule's single string is a
    list of one, and blanks are nothing."""
    if value in (None, ""):
        return []
    values = [value] if isinstance(value, str) else list(value)
    return [v.strip() for v in values if isinstance(v, str) and v.strip()]


def normalise_criteria(criteria: dict | None) -> dict:
    """Check a rule and return it in its stored form (ADR-188 points 1-3).

    Unknown fields are refused by name rather than stored, where they would
    silently never match. Language and status are lists ("is one of").
    **Interest in a category always carries a minimum score above 0** —
    every recipient's signal is at least 0 unless they unsubscribed, so a
    category without one matches nearly everyone. A score without a category
    means nothing and is refused too. Raises `CriteriaInvalid`.
    """
    criteria = dict(criteria or {})
    errors: list[tuple[str, str]] = [
        (key, f"a rule cannot say '{key}'; it can say language, status and category interest")
        for key in sorted(set(criteria) - CRITERIA_FIELDS)
    ]
    out: dict = {}
    for key in ("language", "status"):
        raw = criteria.get(key)
        if raw not in (None, "") and not (isinstance(raw, str) or (
                isinstance(raw, list) and all(isinstance(v, str) for v in raw))):
            errors.append((key, "one or more values"))
        elif values := _values(raw):
            out[key] = values
    category, score = criteria.get("category_id"), criteria.get("min_score")
    try:
        category = None if category in (None, "") else int(category)
    except (TypeError, ValueError):
        errors.append(("category_id", "a category"))
        category = None
    try:
        score = None if score in (None, "") else float(score)
    except (TypeError, ValueError):
        errors.append(("min_score", "a number"))
        score = None
    if category is not None:
        if score is None or score <= 0:
            errors.append(("min_score", "interest in a category needs a minimum score above 0; "
                                        "without one it matches nearly everyone"))
        else:
            out.update(category_id=category, min_score=score)
    elif score is not None:
        errors.append(("category_id", "a minimum score needs a category"))
    if errors:
        raise CriteriaInvalid(errors)
    return out


def criteria_values(db: Session, *, brand_id: int) -> dict:
    """The languages and statuses a rule can choose from: the values among the
    people this brand has a consent record with — values, never people."""
    from sqlalchemy import exists

    from app.recipients.db_models import ConsentEventDB

    known = exists().where(ConsentEventDB.recipient_id == RecipientDB.id, ConsentEventDB.brand_id == brand_id)

    def distinct(column):
        return sorted(v for (v,) in db.query(column).filter(known, column.isnot(None)).distinct() if v)

    return {"languages": distinct(RecipientDB.language), "statuses": distinct(RecipientDB.status)}


#: The most a paste may hold; a bigger list belongs in the CRM as a segment
#: (ADR-123; the design pass, decision 6).
PASTE_LIMIT = 5000


class PasteTooLong(ValueError):
    pass


def parse_paste(text: str) -> list[str]:
    """The entries of a pasted list: separated by new lines, commas,
    semicolons, tabs or spaces, so a spreadsheet column pastes as it is.
    Repeats collapse; order is kept."""
    import re

    entries = list(dict.fromkeys(e for e in re.split(r"[\s,;]+", text or "") if e))
    if len(entries) > PASTE_LIMIT:
        raise PasteTooLong(f"{len(entries)} entries; a paste holds up to 5,000. A bigger list belongs in the CRM.")
    return entries


def _resolve_paste(db: Session, entries: list[str]) -> tuple[set[int], list[str]]:
    """Recipient ids for the entries — a CRM identifier, or an email address
    when the entry holds "@" — and the entries that matched nobody. Nobody is
    created: the CRM owns people (ADR-120)."""
    from app.recipients.db_models import AddressabilityDB

    ids_by_external = dict(db.query(RecipientDB.external_id, RecipientDB.id)
                           .filter(RecipientDB.external_id.in_([e for e in entries if "@" not in e])))
    emails = {e.lower() for e in entries if "@" in e}
    by_email: dict[str, set[int]] = {}
    if emails:
        email = func.lower(AddressabilityDB.value["email"].as_string())
        for address, rid in db.query(email, AddressabilityDB.recipient_id).filter(
                AddressabilityDB.channel == "email", email.in_(emails)):
            by_email.setdefault(address, set()).add(rid)
    found: set[int] = set()
    missing: list[str] = []
    for entry in entries:
        hits = by_email.get(entry.lower(), set()) if "@" in entry else (
            {ids_by_external[entry]} if entry in ids_by_external else set())
        if hits:
            found |= hits
        else:
            missing.append(entry)
    return found, missing


def paste_preview(db: Session, group: AudienceGroupDB, text: str, *, channel: str) -> dict:
    """What pasting this list would do — added, already in, not found (listed),
    not agreed to `channel` — before anything is added (decision 6)."""
    found, missing = _resolve_paste(db, parse_paste(text))
    members = get_member_recipient_ids(db, group.id, brand_id=group.brand_id)
    to_add = found - members
    agreed = {rid for (rid,) in db.query(RecipientDB.id).filter(
        RecipientDB.id.in_(to_add), is_consenting_filter(group.brand_id, channel, purpose=MARKETING))} if to_add else set()
    return {"to_add": len(to_add), "already_in": len(found & members), "not_found": missing,
            "not_agreed": len(to_add - agreed), "channel": channel}


def paste_apply(db: Session, group: AudienceGroupDB, text: str, *, reason: str | None,
                added_by: str | None, expected_updated_at=None) -> dict:
    """Add the pasted people by hand, with one reason for the paste. The list
    is read again, so what is added is what is true now."""
    check_version(db, group, expected_updated_at)
    found, missing = _resolve_paste(db, parse_paste(text))
    members = get_member_recipient_ids(db, group.id, brand_id=group.brand_id)
    reason = (reason or "").strip() or None
    for rid in sorted(found - members):
        db.add(AudienceGroupMemberDB(group_id=group.id, recipient_id=rid, reason=reason, added_by=added_by))
    if found - members:
        touch(group)
    db.commit()
    return {"added": len(found - members), "already_in": len(found & members), "not_found": len(missing)}


def get_group(db: Session, group_id: int, *, brand_id: int) -> AudienceGroupDB | None:
    """One group, selected within a brand (ADR-172 points 4-6).

    The choke point for this module: update, delete, the member functions and
    the block functions all resolve through here, so scoping it once scopes
    them. A group in another brand is not found.
    """
    return (
        db.query(AudienceGroupDB)
        .filter(AudienceGroupDB.id == group_id, AudienceGroupDB.brand_id == brand_id)
        .first()
    )


def create_group(
    db: Session, name: str, brand_id: int, description: str | None = None,
    source_campaign_id: int | None = None,
) -> AudienceGroupDB:
    """A group belongs to a brand. **It deliberately does not belong to a
    channel**, and that was considered on 2026-09-18 rather than overlooked.

    The user asked whether groups should be created per channel. They should
    not, for the reason [[ADR-160 — Channel Model and Composition]] point 7
    gives about campaign coverage: a declared channel is *stored intent*, and
    stored intent "would create a drift class where intent and reality
    disagree with nobody clearing the stale state" — a group labelled push
    whose members are mostly email-only is exactly that.

    The alternative the user proposed is the one that is built: one group,
    targeted per sending channel. `resolve_audience` takes the channel, the
    consent floor is keyed to it (ADR-163 point 1), and the addressability
    stage filters on it — so the same group resolves to different people for an
    email send and a push send, and the send form shows both numbers. Nothing
    is stored, so nothing can go stale.
    """
    group = AudienceGroupDB(
        name=name, brand_id=brand_id, description=description,
        source_campaign_id=source_campaign_id,
    )
    db.add(group)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"An audience group named '{name}' already exists")
    db.refresh(group)
    return group


def update_group(
    db: Session, group_id: int, name=UNSET, description=UNSET,
    *, brand_id: int, expected_updated_at=None,
) -> AudienceGroupDB | None:
    """Rename or re-describe a group. **Only what is passed changes** (the
    design pass, task-295): a rename leaves the description alone, and
    `description=None` clears it. States the group's version when given."""
    group = get_group(db, group_id, brand_id=brand_id)
    if not group:
        return None
    check_version(db, group, expected_updated_at)
    if name is not UNSET:
        group.name = name
    if description is not UNSET:
        group.description = description
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"An audience group named '{name}' already exists")
    db.refresh(group)
    return group


def delete_group(db: Session, group_id: int, *, brand_id: int, expected_updated_at=None) -> bool:
    """Delete a group nobody sends to (the design pass, decision 8). A group
    a send uses — planned or sent — is refused with `GroupInUse`, naming the
    sends: sent mail must keep the record of who it was for, and a planned send
    would lose its audience. Today's alternative was the database refusing at
    commit and an unhandled 500."""
    from app.delivery.db_models import SendInstanceDB

    group = get_group(db, group_id, brand_id=brand_id)
    if not group:
        return False
    check_version(db, group, expected_updated_at)
    used_by = [name for (name,) in db.query(SendInstanceDB.name)
               .filter(SendInstanceDB.audience_group_id == group_id).order_by(SendInstanceDB.id.asc())]
    if used_by:
        raise GroupInUse(used_by)
    # Clear both children first — members and rule blocks both FK to the group,
    # so either left behind blocks the delete.
    db.query(AudienceGroupMemberDB).filter(AudienceGroupMemberDB.group_id == group_id).delete()
    db.query(AudienceRuleBlockDB).filter(AudienceRuleBlockDB.group_id == group_id).delete()
    db.delete(group)
    db.commit()
    return True


def page_members(db: Session, group_id: int, params, *, brand_id: int):
    """One ADR-185 page of a group's pinned members, most recently added first."""
    from app.audience.models import AudienceGroupMember
    from app.pagination import page_of_query

    query = (
        db.query(AudienceGroupMemberDB)
        .join(AudienceGroupDB, AudienceGroupDB.id == AudienceGroupMemberDB.group_id)
        .filter(AudienceGroupMemberDB.group_id == group_id, AudienceGroupDB.brand_id == brand_id)
    )
    return page_of_query(query, params, AudienceGroupMemberDB.added_at.desc(),
                         AudienceGroupMemberDB.id.desc(), convert=lambda m: AudienceGroupMember.model_validate(m, from_attributes=True))

def list_members(
    db: Session, group_id: int, *, brand_id: int
) -> list[AudienceGroupMemberDB]:
    """Pinned members, joined to the owning group (ADR-172 point 5).

    The membership row carries no brand and needs none — it hangs off the
    group, which has one.
    """
    return (
        db.query(AudienceGroupMemberDB)
        .join(AudienceGroupDB, AudienceGroupDB.id == AudienceGroupMemberDB.group_id)
        .filter(
            AudienceGroupMemberDB.group_id == group_id,
            AudienceGroupDB.brand_id == brand_id,
        )
        .all()
    )


def add_member(
    db: Session, group_id: int, recipient_id: int, *, brand_id: int,
    reason: str | None = None, added_by: str | None = None, expected_updated_at=None,
) -> AudienceGroupMemberDB | None:
    """Add one person by hand, with an optional reason and who added them
    (task-295, closing task-217). Someone already in is returned as they are."""
    result = pin(db, group_id, recipient_id, brand_id=brand_id, reason=reason, added_by=added_by,
                 expected_updated_at=expected_updated_at)
    return result[0] if result else None


def pin(
    db: Session, group_id: int, recipient_id: int, *, brand_id: int,
    reason: str | None = None, added_by: str | None = None, expected_updated_at=None,
) -> tuple[AudienceGroupMemberDB, bool] | None:
    """`add_member`, saying whether the person was newly added — for the
    audit entry, which records an addition, not a repeat."""
    # The group is resolved within the brand before a pin is written, so a
    # recipient cannot be pinned into another brand's list.
    group = get_group(db, group_id, brand_id=brand_id)
    if group is None:
        return None
    check_version(db, group, expected_updated_at)

    existing = (
        db.query(AudienceGroupMemberDB)
        .filter(
            AudienceGroupMemberDB.group_id == group_id,
            AudienceGroupMemberDB.recipient_id == recipient_id,
        )
        .first()
    )
    if existing:
        return existing, False
    member = AudienceGroupMemberDB(group_id=group_id, recipient_id=recipient_id,
                                   reason=(reason or "").strip() or None, added_by=added_by)
    db.add(member)
    touch(group)
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
        ), False
    db.refresh(member)
    return member, True


def remove_member(
    db: Session, group_id: int, recipient_id: int, *, brand_id: int, expected_updated_at=None,
) -> bool:
    group = get_group(db, group_id, brand_id=brand_id)
    if group is None:
        return False
    check_version(db, group, expected_updated_at)
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
    touch(group)
    db.commit()
    return True


def get_member_recipient_ids(db: Session, group_id: int, *, brand_id: int) -> set[int]:
    rows = (
        db.query(AudienceGroupMemberDB.recipient_id)
        .join(AudienceGroupDB, AudienceGroupDB.id == AudienceGroupMemberDB.group_id)
        .filter(
            AudienceGroupMemberDB.group_id == group_id,
            AudienceGroupDB.brand_id == brand_id,
        )
        .all()
    )
    return {r.recipient_id for r in rows}


def find_by_criteria(
    db: Session,
    brand_id: int,
    *,
    channel: str,
    language: str | None = None,
    status: str | None = None,
    preference_category_id: int | None = None,
    min_preference_score: float | None = None,
    exclude_ids: set[int] | None = None,
    not_agreed: bool = False,
    only_ids: set[int] | None = None,
) -> list[RecipientDB]:
    # Consent gate: audiences are resolved only from consenting recipients.
    # Filtering here — at audience-resolution time, before any decisioning or
    # rendering runs — is deliberate (F1 in docs/backlog.md): it keeps
    # non-consenting recipients out of the processing scope entirely, both for
    # GDPR reasons (running the decision engine over their data is itself
    # "processing") and cost reasons (no paid AI/token spend on people who will
    # never receive anything).
    #
    # Reads the latest (recipient, email, marketing) consent event (ADR-163
    # point 1). Fail-closed in both directions: "pending" and "opted_out" are
    # excluded, and so is a recipient with no consent event at all, since the
    # absence of a decision is not a grant.
    # Consent is to a SENDER (ADR-163 addendum 2026-09-15), so the gate has
    # to ask "consenting to WHOM". Before brand_id was threaded here, every
    # brand's audience resolved against every brand's consent — the authoring
    # side was scoped and the send side was not.
    # **On THIS channel.** `is_consenting_filter` defaults to email, and this
    # call used the default until 2026-09-29 — so a push rule block asked
    # whether these people had consented to *email*, and a push-only recipient
    # matched by an include block resolved into nothing. Same class of failure
    # as `resolve_audience`'s own channel default (ADR-176 addendum
    # 2026-09-27), one layer further in, which is why `channel` is required
    # here too rather than defaulted for convenience.
    #
    # `not_agreed=True` turns the gate around, **for a count and nothing else**
    # (task-213, the user 2026-10-06): the people the same criteria match who
    # have NOT agreed to this channel, among those this brand has any consent
    # record with — a recipient is not a brand's, so without that condition
    # the count would include another brand's contacts. Only
    # `audience_arithmetic` asks, and it keeps the length, never the rows.
    if not_agreed:
        from sqlalchemy import exists

        from app.recipients.consent import CONSENTING_STATUS, consenting_status_expr
        from app.recipients.db_models import ConsentEventDB

        q = db.query(RecipientDB).filter(
            func.coalesce(consenting_status_expr(brand_id, channel, purpose=MARKETING), "") != CONSENTING_STATUS,
            exists().where(ConsentEventDB.recipient_id == RecipientDB.id, ConsentEventDB.brand_id == brand_id),
        )
    else:
        q = db.query(RecipientDB).filter(is_consenting_filter(brand_id, channel, purpose=MARKETING))

    # "Is one of" (ADR-188 point 1): a rule may name several values. A single
    # string is an older rule's form and means a list of one.
    if languages := _values(language):
        q = q.filter(RecipientDB.language.in_(languages))
    if statuses := _values(status):
        q = q.filter(RecipientDB.status.in_(statuses))
    if exclude_ids:
        q = q.filter(RecipientDB.id.notin_(exclude_ids))
    if only_ids is not None:
        # One person checked against a rule (task-214), the same definition of
        # the rule as every audience, without resolving the whole segment.
        q = q.filter(RecipientDB.id.in_(only_ids))

    # Ordered by id since the address is no longer a column (ADR-163 point 2).
    # This also makes deduplication deterministic: two recipients sharing an
    # address have no order between them under an email sort, so which one
    # survived was previously whatever the database happened to return. Now it
    # is the earliest-created, always.
    records = q.order_by(RecipientDB.id.asc()).all()

    # Preference criterion: keep recipients whose *operational signal* for the
    # category clears the threshold (ADR-132, decay-on-read). Computed rather
    # than SQL-joined against a stored score, since there is no stored score.
    if preference_category_id is not None:
        min_score = min_preference_score if min_preference_score is not None else 0.0
        signals = operational_signals_for_category(db, preference_category_id)
        records = [r for r in records if signals.get(r.id, 0.0) >= min_score]

    # **No addressability filter and no deduplication here** (task-233,
    # 2026-09-29). Both moved to stage 1 of the ADR-163 point 7 exclusion
    # stack, where that record's 2026-09-12 addendum point 3 put them and
    # where the channel is already handled correctly.
    #
    # They were wrong in this function in two directions at once. An *exclude*
    # block's criteria resolve through here, and dropping somebody from an
    # exclusion puts them back in the audience — so an unaddressable recipient
    # could be pinned in and no exclude block could remove them. And an
    # *include* block asking about a non-email channel resolved against email
    # addressability, so a push-only recipient could not be included at all.
    #
    # The trade, stated because it is real: a resolved audience now counts
    # people the send will drop at stage 1. That is the honest split —
    # membership answers "who did the manager mean", addressability answers
    # "who can be reached", and the second is recorded per recipient with a
    # reason (point 8) instead of vanishing into a log line here.
    return records


def bulk_add_members(
    db: Session, group_id: int, recipient_ids: list[int], *, brand_id: int
) -> int:
    group = get_group(db, group_id, brand_id=brand_id)
    if group is None:
        return 0
    existing = get_member_recipient_ids(db, group_id, brand_id=brand_id)
    added = 0
    for rid in recipient_ids:
        if rid not in existing:
            db.add(AudienceGroupMemberDB(group_id=group_id, recipient_id=rid))
            added += 1
    if not added:
        return added
    touch(group)

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


# ---------------------------------------------------------------------------
# Rule blocks — live, editable criteria that make up a group's audience
# ---------------------------------------------------------------------------

def _recipients_for_criteria(
    db: Session, criteria: dict, brand_id: int, channel: str, *, not_agreed: bool = False,
    only_ids: set[int] | None = None,
) -> list[RecipientDB]:
    """Resolve one block's criteria to consenting recipients. Thin adapter over
    find_by_criteria so blocks and the older bulk-add path share one definition
    of what a criterion means.

    `channel` is required for the reason `find_by_criteria` states: consent is
    keyed `(recipient, brand, channel, purpose)`, so which people a criterion
    matches depends on it."""
    criteria = criteria or {}
    cat = criteria.get("category_id")
    return find_by_criteria(
        db,
        brand_id,
        channel=channel,
        language=criteria.get("language") or None,
        status=criteria.get("status") or None,
        preference_category_id=int(cat) if cat not in (None, "") else None,
        min_preference_score=criteria.get("min_score"),
        not_agreed=not_agreed,
        only_ids=only_ids,
    )


def count_for_criteria(
    db: Session, criteria: dict, brand_id: int, channel: str
) -> int:
    """How many people a criterion matches on one channel.

    There is no channel-less count (ADR-176 point 5), which is why this takes
    one rather than defaulting."""
    return len(_recipients_for_criteria(db, criteria, brand_id, channel))


def list_blocks(
    db: Session, group_id: int, *, brand_id: int
) -> list[AudienceRuleBlockDB]:
    return (
        db.query(AudienceRuleBlockDB)
        .join(AudienceGroupDB, AudienceGroupDB.id == AudienceRuleBlockDB.group_id)
        .filter(
            AudienceRuleBlockDB.group_id == group_id,
            AudienceGroupDB.brand_id == brand_id,
        )
        .order_by(AudienceRuleBlockDB.kind.asc(), AudienceRuleBlockDB.position.asc(), AudienceRuleBlockDB.id.asc())
        .all()
    )


def get_block(db: Session, block_id: int, *, brand_id: int) -> AudienceRuleBlockDB | None:
    """One rule block, via `block -> group -> brand` (ADR-172 point 5)."""
    return (
        db.query(AudienceRuleBlockDB)
        .join(AudienceGroupDB, AudienceGroupDB.id == AudienceRuleBlockDB.group_id)
        .filter(AudienceRuleBlockDB.id == block_id, AudienceGroupDB.brand_id == brand_id)
        .first()
    )


def add_block(
    db: Session,
    group_id: int,
    kind: str = "include",
    criteria: dict | None = None,
    label: str | None = None,
    source: str = "manual",
    *,
    brand_id: int,
    expected_updated_at=None,
) -> AudienceRuleBlockDB:
    if kind not in ("include", "exclude"):
        raise ValueError("kind must be 'include' or 'exclude'")
    group = get_group(db, group_id, brand_id=brand_id)
    if group is None:
        raise ValueError(f"Audience group {group_id} not found")
    check_version(db, group, expected_updated_at)
    criteria = normalise_criteria(criteria)
    next_pos = (
        db.query(AudienceRuleBlockDB)
        .filter(AudienceRuleBlockDB.group_id == group_id)
        .count()
    )
    block = AudienceRuleBlockDB(
        group_id=group_id,
        kind=kind,
        criteria=criteria or {},
        label=label,
        source=source,
        position=next_pos,
    )
    db.add(block)
    touch(group)
    db.commit()
    db.refresh(block)
    return block


def update_block(
    db: Session,
    block_id: int,
    kind: str | None = None,
    criteria: dict | None = None,
    label=UNSET,
    *,
    brand_id: int,
    expected_updated_at=None,
) -> AudienceRuleBlockDB | None:
    """Change a rule. `label=None` clears the label; leaving it out keeps it."""
    block = get_block(db, block_id, brand_id=brand_id)
    if not block:
        return None
    group = db.get(AudienceGroupDB, block.group_id)
    check_version(db, group, expected_updated_at)
    if kind is not None:
        if kind not in ("include", "exclude"):
            raise ValueError("kind must be 'include' or 'exclude'")
        block.kind = kind
    if criteria is not None:
        block.criteria = normalise_criteria(criteria)
    if label is not UNSET:
        block.label = label
    touch(group)
    db.commit()
    db.refresh(block)
    return block


def delete_block(db: Session, block_id: int, *, brand_id: int, expected_updated_at=None) -> bool:
    block = get_block(db, block_id, brand_id=brand_id)
    if not block:
        return False
    group = db.get(AudienceGroupDB, block.group_id)
    check_version(db, group, expected_updated_at)
    db.delete(block)
    touch(group)
    db.commit()
    return True


def list_groups_with_counts(
    db: Session, *, brand_id: int, channel: str | None, q: str | None = None,
) -> list[dict]:
    """The brand's groups, each with its pinned count and — **only when the
    caller names a channel** — its live resolved count for that channel (task-50, B26).

    ADR-176 point 5: a resolved count is meaningless without a channel, so
    there is no channel-less number to return; with `channel=None` the count is
    `None`, never an email figure in disguise (the defect task-116 recorded
    about the Jinja list). The count is the same consent-gated
    `resolve_audience` a send uses, not the pin count, because a rule-only
    group has no pins and real recipients.

    **Still one `resolve_audience` per group** — the N+1 the migration
    inventory flagged, moved here rather than solved. A set-based resolver
    belongs with task-213, which reshapes what `resolve_audience` returns.
    """
    groups = list_groups(db, brand_id=brand_id)
    # Narrowed by name BEFORE counting: resolving a group for its count is the
    # expensive part (task-213), and a group the search excludes needs none.
    needle = (q or "").strip().lower()
    if needle:
        groups = [g for g in groups if needle in (g.name or "").lower()]
    pinned = dict(
        db.query(AudienceGroupMemberDB.group_id, func.count(AudienceGroupMemberDB.id))
        .filter(AudienceGroupMemberDB.group_id.in_([g.id for g in groups]))
        .group_by(AudienceGroupMemberDB.group_id)
        .all()
    ) if groups else {}
    return [
        {
            "group": group,
            "pinned_count": pinned.get(group.id, 0),
            "recipient_count": (
                len(resolve_audience(db, group.id, channel=channel))
                if channel is not None else None
            ),
            "count_channel": channel,
        }
        for group in groups
    ]


def preview_group(
    db: Session, group: AudienceGroupDB, *, channel: str, sample_size: int = 20,
    q: str | None = None,
) -> dict:
    """What sending to this group on `channel` would reach (task-50, B27).

    **The send's own answer, not a second implementation of it.** ADR-163's
    rider requires the preview to run the same addressability stage the send
    does, "or a displayed count over-reports what will actually send"; so the
    resolved audience goes through `run_exclusion_stack`, and the people it
    drops are counted by stage rather than hidden — someone who matches the
    rules and cannot be reached is a fact a manager can act on.

    Each rule block carries its own count against the **group's** brand, so a
    manager sees each include/exclude's impact before sending. There is no
    channel-less version of any of these numbers (ADR-176 point 5).
    """
    from app.content.db_models import CategoryDB
    from app.delivery.exclusion import run_exclusion_stack

    category_names = dict(db.query(CategoryDB.id, CategoryDB.name).all())
    blocks = []
    for block in list_blocks(db, group.id, brand_id=group.brand_id):
        criteria = block.criteria or {}
        blocks.append({
            "id": block.id,
            "kind": block.kind,
            "label": block.label,
            "source": block.source,
            "criteria": criteria,
            "category_name": category_names.get(criteria.get("category_id")),
            "count": count_for_criteria(db, criteria, group.brand_id, channel),
        })

    # One computation for the audience and how it was arrived at (task-213).
    resolved, arithmetic = _resolve(db, group.id, channel, with_arithmetic=True)
    gate = run_exclusion_stack(db, {r.id for r in resolved}, group.brand_id, channel=channel, purpose=MARKETING)
    reachable = [r for r in resolved if r.id in gate.eligible]
    from app.recipients import search

    matching = [r for r in reachable
                if search.matches(q, r.external_id, gate.addresses.get(r.id))]
    dropped_by_stage: dict[str, int] = {}
    for exclusion in gate.exclusions:
        dropped_by_stage[exclusion.stage] = dropped_by_stage.get(exclusion.stage, 0) + 1
    return {
        "channel": channel,
        "blocks": blocks,
        "arithmetic": arithmetic,
        "resolved_count": len(resolved),
        "reachable_count": len(reachable),
        "unreachable_count": len(resolved) - len(reachable),
        "dropped_by_stage": dropped_by_stage,
        # The sample is the first `sample_size` reachable recipients matching
        # the search, and `sample_matching` how many match in all — the counts
        # above describe the segment, never the search (2026-10-03).
        "sample": [
            {"recipient": r, "address": gate.addresses.get(r.id)}
            for r in matching[:sample_size]
        ],
        "sample_matching": len(matching),
    }


def resolve_audience(
    db: Session, group_id: int, channel: str
) -> list[RecipientDB]:
    """The group's live audience:
        ((∪ include blocks) ∪ (manual member pins)) − (∪ exclude blocks)
    then re-gated to consenting recipients.

    **`channel` has no default, deliberately — the same reasoning
    `VariantDB.channel` states for the same hazard.** Consent is keyed
    `(recipient, brand, channel, purpose)`, so the channel decides who is in
    the audience at all, not merely how they are reached. A default let a
    caller that forgot to pass one silently consent-gate on email — harmless
    only while email is the only channel, which is exactly the shape of
    fail-open that stops being harmless the moment it matters. It was the
    recorded cause of a push send resolving to nobody. Surfaced by the Manager
    Workflow design interview and closed 2026-09-27.

    **Precedence (ADR-176 point 1, implemented 2026-09-29): an exclude block
    removes a hand-pinned recipient.** Pins join the rule-driven set *before*
    the subtraction rather than being unioned back in after it, so an exclusion
    reaches them. The governing principle is the ADR's title — a negative
    decision outranks a positive one — because wrongly including costs more
    than wrongly omitting: a person who should not have received a mail and did
    cannot be un-sent.

    **This reverses the rule that stood here from 2026-07-26**, which read *"a
    manual pin is always included — exclude blocks never remove a hand-pinned
    recipient"*. That rule lived in this docstring, four documentation pages
    and a template heading and in no ADR, which is why reversing it needed a
    record rather than another docstring. Do not restore it from any document
    that still carries it; ADR-176 is the authority.

    **The consent and suppression floor is untouched and stays absolute.** It
    was never a precedence question between two people's intentions — it is a
    legal gate. A non-consenting recipient is dropped even if pinned, and hard
    suppression (bounces/opt-outs) belongs on that floor rather than in a
    regular exclude block, so it stays hard against pins too.

    **The cost, accepted rather than overlooked:** there is now no way to say
    *yes, really, this person*. A recipient an exclusion segment catches by
    accident, who asked for exactly this mail, is answerable only by editing
    the rule — which changes the audience for everybody.

    **The consent floor is per channel**, and the caller must say which.
    Consent is keyed `(recipient, brand, channel, purpose)` (ADR-163 point 1),
    so gating a push send on email consent asks the wrong question twice over:
    it would admit people who accepted email and never accepted notifications,
    and refuse people who did the reverse. It defaulted to email while email
    was the only channel, which made a push send unplannable — the audience
    resolved to nobody and the planner reported "0 consenting recipients".
    The send path passes the variant's channel; a screen previewing a group
    with no variant in hand asks, because there is no channel-less count."""
    return _resolve(db, group_id, channel)[0]


def audience_arithmetic(db: Session, group_id: int, channel: str) -> dict | None:
    """How the audience on `channel` was arrived at (task-213; Manager Workflow
    interview Q4.3): the working, not just the total. The terms add up —

        matched_rules − not_agreed + added_by_hand − removed_by_exclusion
        − dropped_by_consent = total

    - `matched_rules`: people the include blocks match, among those this brand
      has a consent record with;
    - `not_agreed`: of them, those not agreed to this channel — **counted,
      never listed** (the user, 2026-10-06);
    - `added_by_hand`: pins the rules did not already include;
    - `removed_by_exclusion`: removed by an exclude block, and
      `removed_hand_added` how many of those were hand-added — an add an
      exclusion overrode (ADR-176 point 1), which a bare count would hide;
    - `dropped_by_consent`: hand-added people not agreed to this channel;
    - `total`: the audience `resolve_audience` returns, as of now — a send
      resolves it again when it goes out.

    Per channel, always (ADR-176 point 5). None when the group does not exist.
    Computed by the same `_resolve` as the audience itself, so the number and
    the people cannot disagree.
    """
    return _resolve(db, group_id, channel, with_arithmetic=True)[1]


def audience_memberships(db: Session, recipient_id: int, *, brand_id: int, channel: str) -> list[dict]:
    """Which of this brand's audience groups one person is in on `channel`,
    and why (task-214; Manager Workflow interview Q4.5, "why did Anna get
    this").

    Worked out on request, for this one person, as of now — the user's
    decision, 2026-10-06. Rule-based membership is never stored (only
    hand-adds are rows), and storing it would make derived audience data
    authoritative ([[ADR-093]]); so each group's rules are checked against
    this person alone, with the same definitions `_resolve` uses. `member`
    is exactly whether a send resolving the group now would include them.

    Lists only the groups that touch the person — a rule matches (whether or
    not they agreed to the channel) or they were added by hand — in name
    order. Each carries its reasons, in this order: the include rules that
    match (`rule`), `pinned`, the exclude rules that remove them
    (`excluded`), and `not_agreed` when they have not agreed to the channel.
    Per channel, always (ADR-176 point 5).
    """
    only = {recipient_id}
    agreed = db.query(RecipientDB.id).filter(
        RecipientDB.id == recipient_id, is_consenting_filter(brand_id, channel, purpose=MARKETING),
    ).first() is not None
    rows = []
    for group in (db.query(AudienceGroupDB).filter(AudienceGroupDB.brand_id == brand_id)
                  .order_by(AudienceGroupDB.name.asc(), AudienceGroupDB.id.asc())):
        blocks = list_blocks(db, group.id, brand_id=brand_id)
        reasons, matched_agreed, excluded = [], False, False
        for block in blocks:
            if block.kind == "exclude":
                continue
            hit = bool(_recipients_for_criteria(db, block.criteria, brand_id, channel, only_ids=only))
            if not hit:
                hit = bool(_recipients_for_criteria(
                    db, block.criteria, brand_id, channel, not_agreed=True, only_ids=only))
            else:
                matched_agreed = True
            if hit:
                reasons.append({"kind": "rule", "label": block.label or f"Rule {block.id}"})
        pinned = recipient_id in get_member_recipient_ids(db, group.id, brand_id=brand_id)
        if not reasons and not pinned:
            continue
        if pinned:
            reasons.append({"kind": "pinned", "label": None})
        for block in blocks:
            if block.kind == "exclude" and _recipients_for_criteria(db, block.criteria, brand_id, channel, only_ids=only):
                excluded = True
                reasons.append({"kind": "excluded", "label": block.label or f"Rule {block.id}"})
        if not agreed:
            reasons.append({"kind": "not_agreed", "label": channel})
        rows.append({
            "group_id": group.id, "group_name": group.name,
            # ADR-176 point 1's order, for one person: (rules ∪ pins) − exclusions, then consent.
            "member": (matched_agreed or pinned) and not excluded and agreed,
            "reasons": reasons,
        })
    return rows


def _resolve(db: Session, group_id: int, channel: str, *, with_arithmetic: bool = False):
    """`(audience, arithmetic or None)` — the one computation behind
    `resolve_audience` and `audience_arithmetic`."""
    # The brand comes from the GROUP, never from the caller's working context.
    # A group belongs to exactly one brand (ADR-150 point 2), so resolving it
    # gates on that brand's consent — and a manager who switched brand between
    # building a send and firing it cannot change whose consent was checked.
    # Same reasoning as `brand_for_snapshot` on the delivery side.
    group = group_regardless_of_brand(db, group_id)
    if group is None:
        return [], None
    brand_id = group.brand_id

    # The group's brand, not the caller's — so the blocks read here are the
    # ones that belong to the group being resolved.
    blocks = list_blocks(db, group_id, brand_id=brand_id)

    include_ids: set[int] = set()
    exclude_ids: set[int] = set()
    not_agreed_ids: set[int] = set()
    for block in blocks:
        ids = {r.id for r in _recipients_for_criteria(db, block.criteria, brand_id, channel)}
        if block.kind == "exclude":
            exclude_ids |= ids
        else:
            include_ids |= ids
            if with_arithmetic:
                # Counted only: the rows go no further than `len` below.
                not_agreed_ids |= {r.id for r in _recipients_for_criteria(
                    db, block.criteria, brand_id, channel, not_agreed=True)}

    # Pins join the rule-driven set and the excludes subtract from both
    # (ADR-176 point 1). The parenthesisation IS the decision — moving the
    # union outside the subtraction restores the 2026-07-26 rule that a pin
    # always survives, which is the failure that sends mail to somebody a
    # manager excluded on purpose.
    pins = get_member_recipient_ids(db, group_id, brand_id=brand_id)
    final_ids = (include_ids | pins) - exclude_ids

    records = (
        db.query(RecipientDB)
        .filter(
            RecipientDB.id.in_(final_ids),
            # Consent floor, for THIS brand AND this channel.
            is_consenting_filter(brand_id, channel, purpose=MARKETING),
        )
        .order_by(RecipientDB.id.asc())
        .all()
    ) if final_ids else []
    if not with_arithmetic:
        return records, None
    return records, {
        "matched_rules": len(include_ids | not_agreed_ids),
        "not_agreed": len(not_agreed_ids),
        "added_by_hand": len(pins - include_ids),
        "removed_by_exclusion": len((include_ids | pins) & exclude_ids),
        "removed_hand_added": len(pins & exclude_ids),
        "dropped_by_consent": len(final_ids) - len(records),
        "total": len(records),
    }


# ---------------------------------------------------------------------------
# System-suggested audience — content/category driven (use case 1)
# ---------------------------------------------------------------------------

def _brand_of_campaign(db: Session, campaign_id: int) -> int:
    """The brand a campaign belongs to, for gating its suggested audience.

    A suggestion counts how many people a block would reach, and that count is
    only meaningful against the consent of the brand the campaign will send as.
    Counting against every brand's consent would advertise reach the send
    cannot deliver.
    """
    from app.campaigns.db_models import CampaignDB

    brand_id = (
        db.query(CampaignDB.brand_id).filter(CampaignDB.id == campaign_id).scalar()
    )
    if brand_id is None:
        raise ValueError(
            f"Campaign {campaign_id} has no brand, so the consent to gate its "
            "suggested audience on is unknown. Refusing rather than guessing."
        )
    return brand_id


def campaign_category_scores(db: Session, campaign_id: int) -> list[dict]:
    """Category weights across **every variant** of the campaign, whatever its
    channel — decided 2026-09-18 after the user asked whether suggestion should
    check channels.

    Kept channel-blind because [[ADR-160 — Channel Model and Composition]]
    point 7 makes the campaign the *topic* and the channel a delivery
    preference: a push variant of a hiking campaign is still about hiking, so
    the audience it suggests is a hiking audience. The per-channel truth is
    delivered where it changes a decision — the resolved count on the send
    form, which differs per channel from the same group.

    **The accepted cost:** a campaign whose push content is narrower than its
    email content suggests a broader audience than that push needs. The manager
    edits the blocks, which the suggestion is explicitly a proposal for rather
    than a locked list.
    """
    """Rank the categories a campaign's content is about, so a suggestion can
    target recipients interested in those topics. Content reaches a category two
    ways: a module bound directly to a content record, and a decision slot whose
    picks were resolved to content records (ADR-083 personalization). Both are
    summed by category via the content↔category assignment scores."""
    from app.campaigns.db_models import VariantDB, ModuleInstanceDB, DecisionSlotDB, DecisionResolutionDB
    from app.content.db_models import ContentCategoryAssignmentDB, CategoryDB

    variant_ids = [v.id for v in db.query(VariantDB.id).filter(VariantDB.campaign_id == campaign_id).all()]
    if not variant_ids:
        return []

    content_ids: set[int] = set()
    # Direct module → content record.
    for (crid,) in (
        db.query(ModuleInstanceDB.content_record_id)
        .filter(ModuleInstanceDB.variant_id.in_(variant_ids), ModuleInstanceDB.content_record_id.isnot(None))
        .all()
    ):
        content_ids.add(crid)
    # Decision slot → resolved picks.
    slot_ids = [s.id for s in db.query(DecisionSlotDB.id).filter(DecisionSlotDB.variant_id.in_(variant_ids)).all()]
    if slot_ids:
        for (crid,) in (
            db.query(DecisionResolutionDB.content_record_id)
            .filter(DecisionResolutionDB.decision_slot_id.in_(slot_ids))
            .distinct()
            .all()
        ):
            content_ids.add(crid)

    if not content_ids:
        return []

    scores: dict[int, int] = {}
    for assignment in (
        db.query(ContentCategoryAssignmentDB)
        .filter(ContentCategoryAssignmentDB.content_id.in_(content_ids))
        .all()
    ):
        scores[assignment.category_id] = scores.get(assignment.category_id, 0) + (assignment.score or 0)

    if not scores:
        return []

    names = {c.id: c.name for c in db.query(CategoryDB).filter(CategoryDB.id.in_(scores.keys())).all()}
    ranked = [
        {"category_id": cid, "category_name": names.get(cid, f"Category {cid}"), "content_score": total}
        for cid, total in scores.items()
    ]
    ranked.sort(key=lambda r: r["content_score"], reverse=True)
    return ranked


def suggest_include_blocks_for_campaign(db: Session, campaign_id: int, max_categories: int = 5) -> list[dict]:
    """Proposed (not yet persisted) include blocks for a campaign: one per top
    category its content covers, each with a default min-score.

    **Channel-blind, and that is right rather than an omission.**
    `campaign_category_scores` reads every variant whatever its channel,
    because a push variant of a hiking campaign is still about hiking. A
    suggestion is a topic proposal, and the topic does not change per channel.

    **It carried a `count` per suggestion until 2026-09-29 and no caller ever
    read it.** The docstring said it was there "so the manager sees the impact
    before accepting", which is a real requirement and was never wired to a
    screen — both callers here take `criteria` and `label` and discard the
    rest. It was removed with the channel work rather than threaded through,
    because a count is exactly the thing ADR-176 point 5 forbids being
    channel-less: whoever builds the screen asks `count_for_criteria` with the
    channel in hand, which is one call and cannot be wrong by default."""
    suggestions = []
    for row in campaign_category_scores(db, campaign_id)[:max_categories]:
        criteria = {"category_id": row["category_id"], "min_score": DEFAULT_SUGGESTION_MIN_SCORE}
        suggestions.append({
            "label": f"Interested in {row['category_name']}",
            "criteria": criteria,
            "content_score": row["content_score"],
        })
    return suggestions


def create_suggested_group_for_campaign(
    db: Session, campaign_id: int, campaign_name: str, *, brand_id: int,
) -> AudienceGroupDB:
    """Materialize a new group seeded with the campaign's suggested include
    blocks. Blocks are marked source='suggested' so the UI can badge them as the
    system's proposal — fully editable/deletable, never a locked list."""
    # The group belongs to the campaign's brand, not to whoever clicked. Same
    # rule as everywhere else a brand is needed: derive it, never read it off
    # the viewer's context.
    # **And it must be the caller's brand** (task-241, ADR-172). The policy
    # checked `audiences.manage` in the working brand only, so without this a
    # manager of brand A built a group in brand B from B's categories. Another
    # brand's campaign answers as absent.
    if _brand_of_campaign(db, campaign_id) != brand_id:
        raise ValueError(f"Campaign {campaign_id} not found")

    base_name = f"{campaign_name} — suggested audience"
    name = base_name
    suffix = 2
    # Scoped to the brand, because the constraint is (brand_id, lower(name)).
    # Querying every brand would enforce a stricter rule than the database and
    # push brand B's group to "(2)" because brand A happens to own the name —
    # the wrong direction entirely for a per-brand scope.
    while (
        db.query(AudienceGroupDB)
        .filter(
            AudienceGroupDB.brand_id == brand_id,
            func.lower(AudienceGroupDB.name) == name.lower(),
        )
        .first()
    ):
        name = f"{base_name} ({suffix})"
        suffix += 1
        # `audience_groups.name` is String(255) and a long campaign name plus a
        # suffix can exceed it, which would fail as a database error rather
        # than as the collision it actually is.
        if len(name) > 255:
            name = f"{base_name[:240].rstrip()} ({suffix})"

    group = create_group(
        db,
        name,
        brand_id,
        description=f"System-suggested from campaign #{campaign_id} content categories.",
        source_campaign_id=campaign_id,
    )
    for suggestion in suggest_include_blocks_for_campaign(db, campaign_id):
        add_block(
            db,
            group_id=group.id,
            kind="include",
            criteria=suggestion["criteria"],
            label=suggestion["label"],
            source="suggested",
            brand_id=brand_id,
        )
    return group


def recalculate_suggested_blocks(
    db: Session, group_id: int, *, brand_id: int
) -> AudienceGroupDB | None:
    """Re-derive a group's suggested include blocks from its source campaign's
    *current* content — for after a manager adjusts slots/content. Applies only
    the delta so nothing else is disturbed:
      • categories the campaign no longer covers → their suggested block removed
      • categories newly covered → a fresh suggested block added
      • a surviving category's suggested block is left untouched, preserving any
        threshold the manager already tuned on it
    Manual blocks and manual member pins are never touched. Returns None if the
    group has no source campaign to recalculate against."""
    group = get_group(db, group_id, brand_id=brand_id)
    if not group or not group.source_campaign_id:
        return None

    desired = suggest_include_blocks_for_campaign(db, group.source_campaign_id)
    desired_by_cat = {s["criteria"]["category_id"]: s for s in desired}

    existing_suggested = [
        b for b in list_blocks(db, group_id, brand_id=brand_id)
        if b.source == "suggested"
    ]
    existing_cats = {(b.criteria or {}).get("category_id") for b in existing_suggested}

    # Remove suggested blocks whose category dropped out of the campaign.
    removed = 0
    for block in existing_suggested:
        if (block.criteria or {}).get("category_id") not in desired_by_cat:
            db.delete(block)
            removed += 1
    if removed:
        touch(group)
        db.commit()

    # Add suggested blocks for newly-covered categories.
    added = 0
    for cat_id, suggestion in desired_by_cat.items():
        if cat_id not in existing_cats:
            add_block(
                db,
                group_id=group_id,
                kind="include",
                criteria=suggestion["criteria"],
                label=suggestion["label"],
                source="suggested",
                brand_id=brand_id,
            )
            added += 1

    return group


# --- criteria: who a rule would add, and adding them (task-50, C11/C12) --------

def criteria_matches(
    db: Session, group_id: int, *, brand_id: int, channel: str, criteria: dict,
) -> list[RecipientDB] | None:
    """Who these ad-hoc criteria would ADD to the group: consenting on
    `channel` for the group's brand, and not already a member. None when the
    group is not in this brand — the Jinja route called `.brand_id` on a
    missing group and answered 500.

    `channel` is required for the reason every count here takes one (ADR-176
    point 5); the Jinja preview was hard-coded to email.
    """
    group = get_group(db, group_id, brand_id=brand_id)
    if group is None:
        return None
    return find_by_criteria(
        db, group.brand_id, channel=channel,
        language=criteria.get("language") or None,
        status=criteria.get("status") or None,
        preference_category_id=criteria.get("category_id"),
        min_preference_score=criteria.get("min_score"),
        exclude_ids=get_member_recipient_ids(db, group_id, brand_id=brand_id),
    )


def bulk_add_by_criteria(
    db: Session, group_id: int, *, brand_id: int, channel: str, criteria: dict,
) -> dict | None:
    """Pin everyone `criteria_matches` returns. `{matched, added}`, or None
    when the group is not in this brand. Guarded by `audiences.manage`, not
    `audiences.pin` (decided 2026-10-02): adding everyone a rule matches
    reshapes the audience, which the narrow pin grant does not cover."""
    matches = criteria_matches(db, group_id, brand_id=brand_id, channel=channel, criteria=criteria)
    if matches is None:
        return None
    added = bulk_add_members(db, group_id, [r.id for r in matches], brand_id=brand_id)
    return {"matched": len(matches), "added": added}
