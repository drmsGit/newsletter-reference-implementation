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
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
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
    name = Column(String(255), nullable=False)
    # `name` is an internal label (e.g. "Variant A — Beach Focus"); the actual
    # email subject line and inbox preview text are their own first-class
    # fields, per-variant so A/B versions can differ. Historically the send
    # path reused send_instance.name as the subject, conflating an internal
    # label with recipient-facing copy — these fields end that.
    subject = Column(String(255), nullable=True)
    preheader = Column(String(255), nullable=True)
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
    variant_id = Column(Integer, ForeignKey("variants.id"), nullable=False)
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
    decision_slot_id = Column(Integer, ForeignKey("decision_slots.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("recipients.id"), nullable=True)
    content_record_id = Column(Integer, ForeignKey("content_records.id"), nullable=False)
    content_version_id = Column(Integer, ForeignKey("content_versions.id"), nullable=True)
    reason = Column(String(255), nullable=True)
    score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)