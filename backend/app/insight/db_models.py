from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint, func

from app.database import Base


class EngagementEventDB(Base):
    __tablename__ = "engagement_events"

    id = Column(Integer, primary_key=True, index=True)
    # Indexed 2026-09-29 (task-11, migration 0023). Every event of one
    # delivery is looked up by this column, and without the index that is a
    # scan over every engagement event ever recorded — one of the fastest-
    # growing tables. At 100,000 events: 2.235 ms / 738 buffers → 0.005 ms / 4.
    delivery_execution_id = Column(
        Integer,
        ForeignKey("delivery_executions.id"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(100), nullable=False)
    provider = Column(String(100), nullable=True)
    provider_event_id = Column(String(255), nullable=True)
    event_data = Column(JSON, nullable=True)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        # NULLs don't collide in Postgres, so this only guards rows that
        # actually came from a provider (both fields set) — safety net
        # behind the application-level duplicate check in ingest_provider_event.
        UniqueConstraint("provider", "provider_event_id", name="uq_engagement_events_provider_event"),
    )