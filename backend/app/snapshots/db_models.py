from sqlalchemy import Column, DateTime, Integer, Text, ForeignKey, func

from app.database import Base


class SnapshotDB(Base):
    __tablename__ = "snapshots"

    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(Integer, ForeignKey("variants.id"), nullable=False)
    html = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)