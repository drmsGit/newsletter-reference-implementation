from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, func, JSON

from app.database import Base


class SnapshotDB(Base):
    __tablename__ = "snapshots"

    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(Integer, ForeignKey("variants.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("recipients.id"), nullable=True)
    # No artifact columns: ADR-183 point 5 stopped writing snapshot files, and
    # `render_context` (the frame) is the snapshot. The three that described a
    # file were dropped by migration 0028 (task-247).
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    render_context = Column(JSON, nullable=True)