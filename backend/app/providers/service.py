from sqlalchemy.orm import Session

from app.delivery.db_models import DeliveryExecutionDB
from app.insight.service import create_engagement_event


def ingest_provider_event(
    db: Session,
    provider: str,
    provider_message_id: str,
    event_type: str,
    provider_event_id: str,
    event_data: dict,
):
    delivery_execution = (
        db.query(DeliveryExecutionDB)
        .filter(
            DeliveryExecutionDB.provider_message_id
            == provider_message_id
        )
        .first()
    )

    if delivery_execution is None:
        raise ValueError(
            f"No DeliveryExecution found for provider_message_id={provider_message_id}"
        )

    return create_engagement_event(
    db=db,
    delivery_execution_id=delivery_execution.id,
    event_type=event_type,
    provider=provider,
    provider_event_id=provider_event_id,
    event_data=event_data,
    occurred_at=None,
)