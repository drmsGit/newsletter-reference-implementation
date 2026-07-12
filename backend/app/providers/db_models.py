from sqlalchemy import Column, DateTime, Integer, JSON, String, func

from app.database import Base


class ProviderEventQuarantineDB(Base):
    """
    Dead-letter storage for inbound provider events that couldn't be correlated
    to a DeliveryExecutionDB (ADR-129: events must not be silently discarded).
    """

    __tablename__ = "provider_event_quarantine"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(100), nullable=False)
    provider_message_id = Column(String(255), nullable=False)
    event_type = Column(String(100), nullable=False)
    provider_event_id = Column(String(255), nullable=False)
    event_data = Column(JSON, nullable=True)
    reason = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
