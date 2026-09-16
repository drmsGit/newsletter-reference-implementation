from sqlalchemy import Column, DateTime, Index, Integer, JSON, String, func

from app.database import Base


class AuditEventDB(Base):
    """Append-only accountability log (ADR-153).

    Distinct from the domain records on purpose. The domain logs are history
    the product needs to function; this one answers **who acted, on what, and
    when** — one screen for "what has this operator done", one export for a
    company's SIEM, one place to point a reviewer or DPO. ADR-153 point 1
    accepts the resulting overlap deliberately, because none of those three
    fall out of a set of domain-specific logs however complete each is.

    **No foreign keys anywhere, and that is the design rather than laziness.**
    An accountability entry has to outlive what it references — ADR-153 point 5
    makes exactly that asymmetry deliberate: an entry attributing an action to
    an operator survives the erasure of any recipient. A foreign key would
    either block the deletion or cascade it, and both destroy the record that
    is the whole point. So actor and subject are stored as a type plus an id,
    resolved on read and allowed to dangle.

    **Nothing here is ever updated.** There is no status, no `updated_at`, and
    no code path that writes an existing row twice. An audit entry that can be
    edited is not evidence.

    Scope of this first slice (2026-09-16): the events ADR-153 point 2 says
    have no home at all — sign-in, role grants and removals, user
    deactivation — plus duplication, which is what prompted building it. Point
    4's exports and bulk reads, and point 6's aggregated authentication
    failures, are NOT in this slice and are not silently assumed to be.
    """

    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)

    # ADR-153 point 3: the actor may be a system or an integration, not only a
    # person. Modelled that way from the start because retrofitting it when
    # Mode B lands means revisiting every write path a second time. Today only
    # "user" is ever written; "integration" arrives with ADR-166.
    actor_type = Column(String(50), nullable=False)
    # Nullable for one case only: an action taken with access control switched
    # off, where there is genuinely no actor. Recording "unknown" honestly is
    # better than attributing it to somebody.
    actor_id = Column(Integer, nullable=True, index=True)

    # A dotted verb — "user.role_granted", "campaign.duplicated". Not an enum:
    # a new event must cost a constant, not a migration, which is the same
    # reasoning ADR-163 gives for channel and purpose.
    action = Column(String(100), nullable=False, index=True)

    # What was acted on. Type plus id, no FK — see the class docstring.
    subject_type = Column(String(50), nullable=True)
    subject_id = Column(Integer, nullable=True)

    # The brand the action happened in, where it had one. Nullable because
    # several of this slice's events genuinely have none: a sign-in is not an
    # act within a brand, and neither is deactivating a user (ADR-150's
    # addendum makes users.manage platform-level).
    brand_id = Column(Integer, nullable=True, index=True)

    # Anything the action needs that is not a subject — the old and new role on
    # a grant, the source record on a duplication. ADR-153 point 5 binds what
    # may go in here: internal identifiers, never contact details. An entry
    # records recipient 45, not anna@example.com.
    detail = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    __table_args__ = (
        # "What has this operator done", newest first — the screen ADR-153
        # point 1 exists to make possible.
        Index("ix_audit_events_actor_recent", "actor_type", "actor_id", "created_at"),
        # "What happened to this thing" — the read duplication needs to answer
        # "was this already copied, and to what".
        Index("ix_audit_events_subject", "subject_type", "subject_id", "created_at"),
    )
