from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from app.database import Base


class SendInstanceDB(Base):
    __tablename__ = "send_instances"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="draft")
    provider = Column(String(100), nullable=True)
    # The audience this send targets. Recorded so we know who a send went to
    # (its executions are materialized from the group at prepare time) and can
    # show it on the delivery page. Nullable for legacy/ad-hoc send instances.
    audience_group_id = Column(Integer, ForeignKey("audience_groups.id"), nullable=True)
    # Verified sender for a real (Resend) send, e.g. "News <news@domain.com>".
    # Null = the provider adapter falls back to its RESEND_FROM env default.
    from_address = Column(String(255), nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DeliveryExecutionDB(Base):
    __tablename__ = "delivery_executions"

    id = Column(Integer, primary_key=True, index=True)
    send_instance_id = Column(Integer, ForeignKey("send_instances.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("recipients.id"), nullable=False)
    status = Column(String(50), nullable=False, default="created")
    provider = Column(String(100), nullable=True)
    provider_message_id = Column(String(255), nullable=True, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )