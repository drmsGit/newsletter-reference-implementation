from sqlalchemy import Boolean, Column, DateTime, Index, Integer, JSON, String, UniqueConstraint, func, Float, ForeignKey

from app.database import Base


class RecipientDB(Base):
    __tablename__ = "recipients"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(255), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False)
    language = Column(String(20), nullable=True)
    attributes = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False, default="active")
    # Consent is no longer a column here. It is an append-only event per
    # (recipient, channel, purpose), latest wins — see ConsentEventDB and
    # ADR-163 point 1. A single column could not carry the source and timestamp
    # that make consent provable, could not survive an erasure in the minimised
    # form ADR-154 requires, and could not express more than one channel.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ConsentEventDB(Base):
    """Append-only consent grants and withdrawals (ADR-163 point 1).

    Latest row wins per `(recipient_id, channel, purpose)`. Events rather than a
    mutable status because a column cannot carry the *source* and *timestamp*
    that make consent provable — and ADR-154 requires proof of consent to
    survive an erasure in minimised form, which a value you overwrite cannot do.

    `source` is what distinguishes a CRM assertion from a provider suppression
    from a signup form, and it is what makes drift computable without the sync
    log storing consent values (ADR-163 addendum 2026-09-12, points 2 and 4):
    the CRM's last assertion is simply the latest row with `source = 'crm'`.
    """

    __tablename__ = "consent_events"

    id = Column(Integer, primary_key=True, index=True)
    recipient_id = Column(Integer, ForeignKey("recipients.id"), nullable=False, index=True)
    # The (channel, purpose) grid. Not an enum: a new channel or purpose must
    # cost a row, not a migration (ADR-163 point 1).
    channel = Column(String(50), nullable=False, default="email")
    purpose = Column(String(50), nullable=False, default="marketing")
    # "opted_in" | "opted_out" | "pending". Only opted_in is a grant; the
    # absence of a decision is not consent.
    status = Column(String(50), nullable=False)
    # Where this came from: crm | provider | form | import | manual.
    source = Column(String(100), nullable=False)
    note = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        # The read is always "latest row for this cell", so the index has to
        # carry the ordering as well as the lookup.
        Index(
            "ix_consent_events_cell_latest",
            "recipient_id",
            "channel",
            "purpose",
            "created_at",
        ),
    )


class AddressabilityDB(Base):
    """Every contact point a recipient has, whatever its type (ADR-163 point 2).

    Off `RecipientDB` for three reasons the record states: cardinality (one
    email, but many push tokens — phone, tablet, a reinstalled app), lifecycle
    (tokens expire and the OS reports dead ones, so a status you can mark
    invalid beats a value you overwrite), and structure (a postal address is
    street/postcode/city/country, not a string).

    `value` is JSON to hold all three shapes, matching the idiom already used by
    `ContentRecordDB.content`, `module_data` and `app_config.value`.

    Phase A note (2026-09-12): this table is created and populated from
    `recipients.email`, but that column is not dropped yet — the ~22 display
    sites that read it move in phase B. Until then this is the authoritative
    store for *resolution*, and the column is a leftover, not a second source.
    """

    __tablename__ = "recipient_addresses"

    id = Column(Integer, primary_key=True, index=True)
    recipient_id = Column(Integer, ForeignKey("recipients.id"), nullable=False, index=True)
    channel = Column(String(50), nullable=False, default="email")
    # {"email": "..."} | {"token": "...", "platform": "apns"} |
    # {"street": "...", "postcode": "...", "city": "...", "country": "..."}
    value = Column(JSON, nullable=False)
    # "active" | "expired" | "invalid" — a dead push token is marked, not deleted,
    # so the history of what was addressable when stays intact.
    status = Column(String(50), nullable=False, default="active")
    # Optional pin for pick-one channels (ADR-163 point 11). Deliberately NOT
    # required: many rows are always allowed, and flagging one is only needed
    # when recency is the wrong answer. Fan-out channels (push) ignore it.
    is_primary = Column(Boolean, nullable=False, default=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_recipient_addresses_channel", "recipient_id", "channel", "status"),
    )


class ConsentSyncLogDB(Base):
    """What happened in a *conversation with the CRM* — it ran, it failed, it
    applied N changes (ADR-163 point 4).

    It deliberately carries no consent values. It used to hold
    `crm_consent_status` and `platform_status_before`, but only because consent
    was one mutable column with no history to diff against. The CRM's assertion
    is now a `ConsentEventDB` row with `source = 'crm'`, so recording it here
    too would be the same fact in two places, free to disagree
    (ADR-163 addendum 2026-09-12, point 2).

    Drift is therefore computed from the event log, not from this table.
    """

    __tablename__ = "consent_sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    # Nullable: a sync that could not be matched to a recipient is exactly the
    # kind of run worth recording.
    recipient_id = Column(Integer, ForeignKey("recipients.id"), nullable=True, index=True)
    # Denormalized so a log row stays interpretable independent of the
    # recipient's current external_id, and so a sync that couldn't be matched
    # to a recipient can still be recorded.
    external_id = Column(String(255), nullable=True, index=True)
    # Did the run succeed, and how much did it change.
    ok = Column(Boolean, nullable=False, default=True)
    changes_applied = Column(Integer, nullable=False, default=0)
    source = Column(String(100), nullable=False, default="crm")
    note = Column(String, nullable=True)
    synced_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SignalContributionDB(Base):
    """Append-only signal-contribution log (ADR-132) — the source of truth for
    the recipient-category affinity signal. Each row is one engagement's (or one
    manual declaration's) contribution; the current signal is a decay-weighted
    sum computed over these rows at read time, never a stored running total.

    Evolves the old preference_update_logs: `base_weight` replaces the old
    `delta` (there is no running total, so `previous_score`/`new_score` are
    gone), `contribution_type` replaces `reason`, and `occurred_at` (when the
    underlying engagement happened) is what decay is measured against.
    """

    __tablename__ = "signal_contributions"

    id = Column(Integer, primary_key=True, index=True)

    recipient_id = Column(Integer, ForeignKey("recipients.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False, index=True)

    # "manual" | "click" | "open" | "unsubscribe" | "conversion" (extension).
    contribution_type = Column(String(50), nullable=False)

    # The signed weight this contribution adds *before* decay.
    base_weight = Column(Float, nullable=False)

    # When the underlying engagement occurred — decay is measured from here, not
    # from created_at (which is just when we recorded it).
    occurred_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # The engagement event this came from, if any. Nullable: manual/declared
    # contributions have no engagement event behind them.
    event_id = Column(Integer, ForeignKey("engagement_events.id"), nullable=True)

    # Provenance: "engagement", "manual", "import", ...
    source = Column(String(50), nullable=False, default="engagement")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)