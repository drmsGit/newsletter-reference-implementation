from sqlalchemy.orm import Session

from app.delivery.db_models import DeliveryExecutionDB
from app.insight.service import create_engagement_event
from app.providers.db_models import ProviderEventQuarantineDB
from app.providers.models import ProviderEventIngestResult, ProviderEventQuarantine


def to_provider_event_quarantine(record: ProviderEventQuarantineDB) -> ProviderEventQuarantine:
    return ProviderEventQuarantine(
        id=record.id,
        provider=record.provider,
        provider_message_id=record.provider_message_id,
        event_type=record.event_type,
        provider_event_id=record.provider_event_id,
        event_data=record.event_data,
        reason=record.reason,
        created_at=record.created_at,
    )


def ingest_provider_event(
    db: Session,
    provider: str,
    provider_message_id: str,
    event_type: str,
    provider_event_id: str,
    event_data: dict,
) -> ProviderEventIngestResult:
    delivery_execution = (
        db.query(DeliveryExecutionDB)
        .filter(
            DeliveryExecutionDB.provider_message_id
            == provider_message_id
        )
        .first()
    )

    if delivery_execution is None:
        # ADR-129: events must not be silently discarded — quarantine for
        # later reconciliation instead of losing the payload.
        quarantine = ProviderEventQuarantineDB(
            provider=provider,
            provider_message_id=provider_message_id,
            event_type=event_type,
            provider_event_id=provider_event_id,
            event_data=event_data,
            reason=f"No DeliveryExecution found for provider_message_id={provider_message_id}",
        )
        db.add(quarantine)
        db.commit()
        db.refresh(quarantine)

        return ProviderEventIngestResult(
            status="quarantined",
            quarantine=to_provider_event_quarantine(quarantine),
        )

    engagement_event = create_engagement_event(
        db=db,
        delivery_execution_id=delivery_execution.id,
        event_type=event_type,
        provider=provider,
        provider_event_id=provider_event_id,
        event_data=event_data,
        occurred_at=None,
    )

    return ProviderEventIngestResult(status="matched", engagement_event=engagement_event)


def list_quarantined_events(db: Session) -> list[ProviderEventQuarantine]:
    records = (
        db.query(ProviderEventQuarantineDB)
        .order_by(ProviderEventQuarantineDB.created_at.desc())
        .all()
    )
    return [to_provider_event_quarantine(record) for record in records]