from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.insight.db_models import EngagementEventDB
from app.insight.models import EngagementEvent, PreferenceUpdateResult

from app.delivery.db_models import DeliveryExecutionDB
from app.content.db_models import ContentCategoryAssignmentDB
from app.recipients.db_models import SignalContributionDB
from app.insight.signals import CONTRIBUTION_WEIGHTS, record_contribution

# Engagement event types that map to per-category signal contributions (they
# carry a content_record_id, whose category assignments locate the affinity).
# Unsubscribe/complaint is handled on the consent path (opt-out), not as a
# per-category signal. Conversion is a company-sourced extension (ADR-132).
_CONTENT_TIED_EVENT_TYPES = {"click", "open"}

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


def apply_event_to_signals(
    db: Session,
    event_id: int,
) -> PreferenceUpdateResult:
    """Turn a content-tied engagement event (click/open) into per-category
    signal contributions (ADR-132). Appends to the contribution log; there is
    no mutable running total — the current signal is computed on read."""
    event = (
        db.query(EngagementEventDB)
        .filter(EngagementEventDB.id == event_id)
        .first()
    )

    if event is None:
        raise ValueError(f"EngagementEvent {event_id} not found")

    if event.event_type not in _CONTENT_TIED_EVENT_TYPES:
        raise ValueError(
            f"Event type {event.event_type} does not produce a content signal"
        )

    base_weight = CONTRIBUTION_WEIGHTS[event.event_type]

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

    # delivery_execution.recipient_id is a direct FK to RecipientDB.id
    # (ADR-054), so no external_id lookup/translation is needed here.
    recipient_id = delivery_execution.recipient_id

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
        # Scale the type's base weight by how strongly the content belongs to
        # the category (the 0–10 assignment score).
        category_weight = base_weight * (assignment.score / 10)

        # Dedupe on the specific event, not "any event of this type on this
        # delivery execution" — two distinct legitimate engagements (e.g.
        # clicks on two different links in the same email) must each get their
        # own contribution. This only guards re-applying the *same* event twice.
        existing = (
            db.query(SignalContributionDB)
            .filter(
                SignalContributionDB.recipient_id == recipient_id,
                SignalContributionDB.category_id == assignment.category_id,
                SignalContributionDB.event_id == event.id,
            )
            .first()
        )
        if existing is not None:
            continue

        record_contribution(
            db=db,
            recipient_id=recipient_id,
            category_id=assignment.category_id,
            contribution_type=event.event_type,
            occurred_at=event.occurred_at,
            event_id=event.id,
            source="engagement",
            base_weight=category_weight,
        )

        updated_categories.append(assignment.category_id)
        applied_deltas[assignment.category_id] = category_weight

    return PreferenceUpdateResult(
        event_id=event.id,
        recipient_id=recipient_id,
        content_record_id=content_record_id,
        updated_categories=updated_categories,
        applied_deltas=applied_deltas,
    )