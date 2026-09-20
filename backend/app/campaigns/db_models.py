from sqlalchemy import CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func, JSON

from app.database import Base


class CampaignDB(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    # ADR-150 point 2. A campaign is composed for one brand and sent as it.
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class VariantDB(Base):
    __tablename__ = "variants"

    id = Column(Integer, primary_key=True, index=True)
    # Indexed: every variant lookup filters on it, and Postgres does not
    # index a foreign key for you. Measured 2026-09-20 at 60,004 variants —
    # 1.335 ms and 617 buffers unindexed, 0.016 ms and 3 with (migration 0018).
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)
    # ADR-160 point 4: **channel is an attribute on the variant.** Not on the
    # campaign — a campaign ("Hiking") carries email, push and paid-social
    # variants, and a channel-plan level between the two was considered and
    # rejected, because "the campaign is the topic; the channel is a delivery
    # preference, not a structural division of the work".
    #
    # Point 5: **fixed at creation.** Switching an email variant to push would
    # invalidate its modules, its content-readiness and its renderer at once,
    # so changing channel means creating a new variant. Nothing updates this.
    #
    # **No server default, deliberately.** A default would let a caller that
    # forgets to pass a channel produce a silent email variant, which is
    # harmless only while email is the only channel — exactly the shape of
    # fail-open that stops being harmless the moment it matters. The migration
    # uses a default to backfill and then drops it.
    channel = Column(String(50), nullable=False, index=True)
    # An internal label ("Variant A — Beach Focus"), never recipient-facing.
    # The send path once reused `send_instance.name` as the subject line,
    # conflating an internal label with copy a person reads; subject and
    # preheader became first-class fields to end that, and they still are —
    # they are simply not columns here.
    name = Column(String(255), nullable=False)
    # **No `subject` / `preheader`.** ADR-162 point 1: "The variant holds no
    # channel fields at all." They are fields of an *email*, so they live in
    # the composition — a `header` module whose manifest declares them, at
    # position 0 (migration 0011 expand, 0012 contract).
    #
    # Nothing on this row is channel-shaped now, which is what lets one table
    # carry an email variant and a push variant without either describing the
    # other. A push variant used to hold two NULL columns naming a thing it is
    # not.
    status = Column(String(50), nullable=False, default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ModuleInstanceDB(Base):
    __tablename__ = "module_instances"

    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(Integer, ForeignKey("variants.id"), nullable=False)
    module_type = Column(String(100), nullable=False)
    position = Column(Integer, nullable=False)
    content_record_id = Column(Integer, ForeignKey("content_records.id"), nullable=True)
    module_data = Column(JSON, nullable=True)
    decision_slot_id = Column(Integer, ForeignKey("decision_slots.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("variant_id", "position", name="uq_module_instances_variant_position"),
        # Mutual exclusivity, not "exactly one required" — non-CMS static
        # modules (e.g. a module_data-only cta/hero) legitimately leave both
        # null. What must never happen is BOTH set at once, since rendering
        # then silently prefers content_record_id and ignores the decision
        # slot with no error (rendering/service.py resolve_content_for_module).
        CheckConstraint(
            "content_record_id IS NULL OR decision_slot_id IS NULL",
            name="ck_module_instances_content_or_decision_slot",
        ),
    )


class DecisionSlotDB(Base):
    __tablename__ = "decision_slots"

    id = Column(Integer, primary_key=True, index=True)
    # Indexed for the same reason as `variants.campaign_id`: 1.554 ms -> 0.014 ms.
    variant_id = Column(Integer, ForeignKey("variants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    decision_type = Column(String(100), nullable=False, default="content_recommendation")
    decision_strategy = Column(String(100), nullable=False, default="top_score")
    candidate_filter = Column(JSON, nullable=True)
    strategy_config = Column(JSON, nullable=True)
    max_results = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DecisionResolutionDB(Base):
    __tablename__ = "decision_resolutions"

    id = Column(Integer, primary_key=True, index=True)
    # **The one that matters most.** This table grows at one row per recipient
    # per slot — the fastest-growing table in the schema — and an unindexed
    # lookup scans all of it to return the handful it wants. Measured at
    # 96,040 rows: 3.45 ms and 801 buffers, against 0.080 ms and 12 with.
    decision_slot_id = Column(Integer, ForeignKey("decision_slots.id"), nullable=False, index=True)
    recipient_id = Column(Integer, ForeignKey("recipients.id"), nullable=True)
    content_record_id = Column(Integer, ForeignKey("content_records.id"), nullable=False)
    content_version_id = Column(Integer, ForeignKey("content_versions.id"), nullable=True)
    reason = Column(String(255), nullable=True)
    score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)