from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, JSON, func

from app.database import Base


class OverrideEventDB(Base):
    __tablename__ = "override_events"

    id = Column(Integer, primary_key=True, index=True)
    override_type = Column(String(50), nullable=False)  # "content" | "segment"

    module_instance_id = Column(Integer, ForeignKey("module_instances.id"), nullable=True)
    decision_slot_id = Column(Integer, ForeignKey("decision_slots.id"), nullable=True)
    send_instance_id = Column(Integer, ForeignKey("send_instances.id"), nullable=True)

    system_content_record_id = Column(Integer, ForeignKey("content_records.id"), nullable=False)
    override_content_record_id = Column(Integer, ForeignKey("content_records.id"), nullable=False)

    overridden_by = Column(String(255), nullable=False)
    reason = Column(String(1000), nullable=True)

    # Filled retroactively after send when engagement data is available
    outcome_delta = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
