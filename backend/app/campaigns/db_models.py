from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func, JSON

from app.database import Base


class CampaignDB(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
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
    name = Column(String(255), nullable=False)
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
    score = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)