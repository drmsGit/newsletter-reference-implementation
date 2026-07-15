from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, UniqueConstraint, func, Float, ForeignKey

from app.database import Base


class RecipientDB(Base):
    __tablename__ = "recipients"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(255), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False)
    language = Column(String(20), nullable=True)
    attributes = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False, default="active")
    # Marketing consent, sourced from the CRM (ADR-126 explicitly permits
    # "communication preferences" on the Recipient Projection). This is NOT a
    # system-of-record for consent — the CRM owns it; this is a synced copy
    # used to gate audience resolution before any decisioning/rendering runs.
    # Only "opted_in" is treated as consenting; "pending"/"opted_out" are not.
    consent_status = Column(String(50), nullable=False, default="pending", server_default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ConsentSyncLogDB(Base):
    """Append-only log of CRM→platform consent syncs, so drift between what
    the CRM asserted and what the platform currently stores is detectable
    rather than silent (some providers ignore opt-outs on API sends, so this
    platform can be the only place positioned to notice a divergence)."""

    __tablename__ = "consent_sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    recipient_id = Column(Integer, ForeignKey("recipients.id"), nullable=False, index=True)
    # Denormalized so a log row stays interpretable independent of the
    # recipient's current external_id, and so a sync that couldn't be matched
    # to a recipient can still be recorded.
    external_id = Column(String(255), nullable=False, index=True)
    # What the CRM asserted in this sync.
    crm_consent_status = Column(String(50), nullable=False)
    # The platform's consent_status immediately before this sync applied.
    platform_status_before = Column(String(50), nullable=False)
    # Whether the asserted value was actually applied to the recipient row.
    applied = Column(Boolean, nullable=False, default=True)
    source = Column(String(100), nullable=False, default="crm")
    note = Column(String, nullable=True)
    synced_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RecipientPreferenceDB(Base):
    __tablename__ = "recipient_preferences"

    id = Column(Integer, primary_key=True, index=True)

    recipient_id = Column(
        Integer,
        ForeignKey("recipients.id"),
        nullable=False,
    )

    category_id = Column(
        Integer,
        ForeignKey("categories.id"),
        nullable=False,
    )

    score = Column(Float, nullable=False)

    source = Column(
        String(50),
        nullable=False,
        default="manual",
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("recipient_id", "category_id", name="uq_recipient_preferences_recipient_category"),
    )


class PreferenceUpdateLogDB(Base):
    __tablename__ = "preference_update_logs"

    id = Column(Integer, primary_key=True)

    recipient_id = Column(
        Integer,
        ForeignKey("recipients.id"),
        nullable=False,
    )

    category_id = Column(
        Integer,
        ForeignKey("categories.id"),
        nullable=False,
    )

    event_id = Column(
        Integer,
        ForeignKey("engagement_events.id"),
        nullable=False,
    )

    previous_score = Column(
        Float,
        nullable=False,
    )

    delta = Column(
        Float,
        nullable=False,
    )

    new_score = Column(
        Float,
        nullable=False,
    )

    reason = Column(
        String,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )