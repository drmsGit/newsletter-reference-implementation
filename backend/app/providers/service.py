import logging

from sqlalchemy.orm import Session

from app.delivery.db_models import DeliveryExecutionDB
from app.insight.db_models import EngagementEventDB
from app.insight.service import create_engagement_event, to_engagement_event
from app.providers.db_models import ProviderEventQuarantineDB
from app.providers.models import ProviderEventIngestResult, ProviderEventQuarantine

logger = logging.getLogger(__name__)


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

    # A webhook delivered twice must not create a second EngagementEventDB
    # row unconditionally — distinct from the later Insight-layer dedup
    # (which governs whether a *scoring* update applies to an already-stored
    # event), this is about not double-recording the raw event itself.
    existing = (
        db.query(EngagementEventDB)
        .filter(
            EngagementEventDB.provider == provider,
            EngagementEventDB.provider_event_id == provider_event_id,
        )
        .first()
    )
    if existing is not None:
        return ProviderEventIngestResult(status="duplicate", engagement_event=to_engagement_event(existing))

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

def _primary_content_id_for_delivery(db: Session, delivery_execution: DeliveryExecutionDB) -> int | None:
    """The content a recipient actually received in a delivery, for attributing
    an open/click to per-category affinity. Prefers the recipient's *resolved
    decision content* (their personalized pick, ADR-083); falls back to the
    variant's first fixed-content module. Resend clicks report a URL, not our
    content id, so we attribute to what was shown rather than parsing the link —
    mapping specific links to content ids (tracking params) is a later refinement."""
    from app.delivery.db_models import SendInstanceDB
    from app.snapshots.db_models import SnapshotDB
    from app.campaigns.db_models import ModuleInstanceDB, DecisionSlotDB, DecisionResolutionDB

    send_instance = db.query(SendInstanceDB).filter(SendInstanceDB.id == delivery_execution.send_instance_id).first()
    if send_instance is None:
        return None
    snapshot = db.query(SnapshotDB).filter(SnapshotDB.id == send_instance.snapshot_id).first()
    if snapshot is None:
        return None
    variant_id = snapshot.variant_id

    slot_ids = [s.id for s in db.query(DecisionSlotDB.id).filter(DecisionSlotDB.variant_id == variant_id).all()]
    if slot_ids:
        resolution = (
            db.query(DecisionResolutionDB)
            .filter(
                DecisionResolutionDB.decision_slot_id.in_(slot_ids),
                DecisionResolutionDB.recipient_id == delivery_execution.recipient_id,
            )
            .order_by(DecisionResolutionDB.created_at.desc())
            .first()
        )
        if resolution is not None:
            return resolution.content_record_id

    module = (
        db.query(ModuleInstanceDB)
        .filter(ModuleInstanceDB.variant_id == variant_id, ModuleInstanceDB.content_record_id.isnot(None))
        .order_by(ModuleInstanceDB.position.asc())
        .first()
    )
    return module.content_record_id if module is not None else None


def process_provider_webhook_event(db: Session, normalized) -> ProviderEventIngestResult:
    """End-to-end handling of one normalized webhook event: correlate → record
    (dedup/quarantine via ingest_provider_event) → and, for a content-tied
    click/open, turn it into per-category signal contributions immediately so a
    recipient's score updates live. `normalized` is a NormalizedEvent from a
    provider adapter (e.g. app.providers.adapters.resend.parse_webhook)."""
    from app.insight.service import apply_event_to_signals

    event_data = dict(normalized.event_data or {})

    # Attach the content the recipient received so the signal layer can locate
    # the affinity — only meaningful for content-tied events.
    if normalized.event_type in ("click", "open"):
        delivery_execution = (
            db.query(DeliveryExecutionDB)
            .filter(DeliveryExecutionDB.provider_message_id == normalized.provider_message_id)
            .first()
        )
        if delivery_execution is not None:
            content_id = _primary_content_id_for_delivery(db, delivery_execution)
            if content_id is not None:
                event_data["content_record_id"] = content_id

    result = ingest_provider_event(
        db=db,
        provider=normalized.provider,
        provider_message_id=normalized.provider_message_id,
        event_type=normalized.event_type,
        provider_event_id=normalized.provider_event_id,
        event_data=event_data,
    )

    if (
        result.status == "matched"
        and normalized.event_type in ("click", "open")
        and result.engagement_event is not None
    ):
        try:
            apply_event_to_signals(db, result.engagement_event.id)
        except ValueError as error:
            # e.g. open weight 0, or content has no category assignments — the
            # raw event is still recorded, it just moved no signal.
            logger.info("event %s recorded but produced no signal: %s", result.engagement_event.id, error)

    return result
