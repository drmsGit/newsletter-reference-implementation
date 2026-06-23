from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, func, JSON

from app.database import Base


class SnapshotDB(Base):
    __tablename__ = "snapshots"

    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(Integer, ForeignKey("variants.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("recipients.id"), nullable=True)
    html_storage_type = Column(String(50), nullable=False, default="file")
    html_location = Column(String(500), nullable=False)
    html_size = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    render_context = Column(JSON, nullable=True)