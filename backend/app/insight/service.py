from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.insight.db_models import EngagementEventDB
from app.insight.models import EngagementEvent


def to_engagement_event(record: EngagementEventDB) -> EngagementEvent:
    return EngagementEvent(
        id=record.id,
        delivery_execution_id=record.delivery_execution_id,
        event_type=record.event_type,
        provider=record.provider,
        provider_event_id=record.provider_event_id,
        event_data=record.event_data,
        occurred_at=record.occurred_at,
        created_at=record.created_at,
    )


def create_engagement_event(
    db: Session,
    delivery_execution_id: int,
    event_type: str,
    provider: str | None = None,
    provider_event_id: str | None = None,
    event_data: dict | None = None,
    occurred_at: datetime | None = None,
) -> EngagementEvent:
    event = EngagementEventDB(
        delivery_execution_id=delivery_execution_id,
        event_type=event_type,
        provider=provider,
        provider_event_id=provider_event_id,
        event_data=event_data,
        occurred_at=occurred_at or datetime.now(timezone.utc),
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return to_engagement_event(event)


def list_events_for_delivery_execution(
    db: Session,
    delivery_execution_id: int,
) -> list[EngagementEvent]:
    records = (
        db.query(EngagementEventDB)
        .filter(EngagementEventDB.delivery_execution_id == delivery_execution_id)
        .order_by(EngagementEventDB.occurred_at.desc())
        .all()
    )

    return [to_engagement_event(record) for record in records]