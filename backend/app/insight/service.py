from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.insight.db_models import EngagementEventDB
from app.insight.models import EngagementEvent

from app.delivery.db_models import DeliveryExecutionDB
from app.content.db_models import ContentCategoryAssignmentDB
from app.recipients.db_models import RecipientPreferenceDB
from app.insight.models import EngagementEvent, PreferenceUpdateResult


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


def apply_event_to_preferences(
    db: Session,
    event_id: int,
) -> PreferenceUpdateResult:
    event = (
        db.query(EngagementEventDB)
        .filter(EngagementEventDB.id == event_id)
        .first()
    )

    if event is None:
        raise ValueError(f"EngagementEvent {event_id} not found")

    EVENT_PREFERENCE_DELTAS = {
        "click": 5.0,
    }
    base_delta = EVENT_PREFERENCE_DELTAS.get(event.event_type)

    if base_delta is None:
        raise ValueError(
            f"Event type {event.event_type} does not update preferences"
        )

    event_data = event.event_data or {}
    content_record_id = event_data.get("content_record_id")

    if content_record_id is None:
        raise ValueError("Event data must contain content_record_id")

    delivery_execution = (
        db.query(DeliveryExecutionDB)
        .filter(DeliveryExecutionDB.id == event.delivery_execution_id)
        .first()
    )

    if delivery_execution is None:
        raise ValueError(
            f"DeliveryExecution {event.delivery_execution_id} not found"
        )

    recipient_external_id = delivery_execution.recipient_id

    from app.recipients.db_models import RecipientDB

    recipient = (
        db.query(RecipientDB)
        .filter(RecipientDB.external_id == recipient_external_id)
        .first()
    )

    if recipient is None:
        raise ValueError(
            f"Recipient with external_id {recipient_external_id} not found"
        )

    assignments = (
        db.query(ContentCategoryAssignmentDB)
        .filter(ContentCategoryAssignmentDB.content_id == content_record_id)
        .all()
    )

    if not assignments:
        raise ValueError(
            f"ContentRecord {content_record_id} has no category assignments"
        )

    updated_categories: list[int] = []
    applied_deltas: dict[int, float] = {}

    for assignment in assignments:
        category_delta = base_delta * (assignment.score / 10)
        preference = (
            db.query(RecipientPreferenceDB)
            .filter(
                RecipientPreferenceDB.recipient_id == recipient.id,
                RecipientPreferenceDB.category_id == assignment.category_id,
            )
            .first()
        )

        if preference is None:
            preference = RecipientPreferenceDB(
                recipient_id=recipient.id,
                category_id=assignment.category_id,
                score=category_delta,
                source="engagement",
            )
            db.add(preference)
        else:
            preference.score = preference.score + category_delta
            preference.source = "engagement"

        updated_categories.append(assignment.category_id)
        applied_deltas[assignment.category_id] = category_delta

    db.commit()

    return PreferenceUpdateResult(
        event_id=event.id,
        recipient_id=recipient.id,
        content_record_id=content_record_id,
        updated_categories=updated_categories,
        applied_deltas=applied_deltas,
    )