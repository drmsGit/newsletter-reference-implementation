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


def _brand_of_execution(db: Session, delivery_execution) -> int:
    """The sending brand behind one delivery execution.

    One join rather than a denormalised column: unlike channel and purpose,
    which the execution carries because a webhook must resolve them after the
    send instance may have been pruned, brand is needed only while the parent
    row still exists — this path starts by finding that execution, so the send
    instance is reachable by definition. Revisit if executions outlive their
    send instances.
    """
    from app.delivery.db_models import SendInstanceDB

    brand_id = (
        db.query(SendInstanceDB.brand_id)
        .filter(SendInstanceDB.id == delivery_execution.send_instance_id)
        .scalar()
    )
    if brand_id is None:
        raise ValueError(
            f"Delivery execution {delivery_execution.id} has no send instance, so "
            "the brand to scope this opt-out to is unknown. Refusing rather than "
            "suppressing on a guessed brand."
        )
    return brand_id


def ingest_provider_event(
    db: Session,
    provider: str,
    provider_message_id: str,
    event_type: str,
    provider_event_id: str,
    event_data: dict,
    *,
    commit: bool = True,
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
        commit=commit,
    )

    return ProviderEventIngestResult(status="matched", engagement_event=engagement_event)


def page_quarantined_events(db: Session, params):
    """One ADR-185 page of quarantined provider events, newest first."""
    from app.pagination import page_of_query

    return page_of_query(db.query(ProviderEventQuarantineDB), params,
                         ProviderEventQuarantineDB.created_at.desc(),
                         ProviderEventQuarantineDB.id.desc(),
                         convert=to_provider_event_quarantine)

def process_provider_webhook_event(db: Session, normalized) -> ProviderEventIngestResult:
    """End-to-end handling of one normalized webhook event: correlate → record
    (dedup/quarantine via ingest_provider_event) → and, for a content-tied
    click/open, turn it into per-category signal contributions immediately so a
    recipient's score updates live. `normalized` is a NormalizedEvent from a
    provider adapter (e.g. app.providers.adapters.resend.parse_webhook)."""
    # **The content is the event's to name, never ours to guess** (ADR-182,
    # task-45). Until 2026-10-02 a "primary" record — the latest personalized
    # pick, else the first content-bound module — was attached to every click
    # and open, so in a multi-content mail a click on the fourth item credited
    # the first. Now a click credits a category only when the provider's event
    # carries `content_record_id` (a tracked link, ADR-102); otherwise it is
    # recorded — it happened, and counts for the email — and credits nothing.
    event_data = dict(normalized.event_data or {})

    # **Only content this recipient was sent** (task-240). A link names its
    # content, but a URL is text: a stale, forwarded or edited link could name
    # anything. The delivery record says what the message carried (ADR-183), so
    # a named id outside it — or a send with no record to ask — credits nothing.
    named = event_data.get("content_record_id")
    if named is not None and normalized.event_type in ("click", "open"):
        from app.delivery.service import sent_content_ids

        execution = (
            db.query(DeliveryExecutionDB)
            .filter(DeliveryExecutionDB.provider_message_id == normalized.provider_message_id)
            .first()
        )
        sent = sent_content_ids(db, execution) if execution is not None else None
        if sent is None or named not in sent:
            logger.info(
                "event for message %s names content %s, which it did not carry — recorded, not credited",
                normalized.provider_message_id, named,
            )
            event_data.pop("content_record_id")

    # **The event and its mandatory effects commit together, or not at all**
    # (task-319). The event used to be committed first: when an effect then
    # failed, the provider's retry of the same event was answered "duplicate"
    # and a complaint's opt-out never landed (ADR-106 makes it mandatory). Now
    # a failure rolls everything back and the retry starts from the beginning;
    # a completed event retried is still a duplicate, and changes nothing.
    try:
        result = _record_with_effects(db, normalized, event_data)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


def _record_with_effects(db: Session, normalized, event_data: dict) -> ProviderEventIngestResult:
    """Record the event and apply its effects without committing — the caller
    commits all of it at once (task-319)."""
    from app.insight.service import apply_event_to_signals

    result = ingest_provider_event(
        db=db,
        provider=normalized.provider,
        provider_message_id=normalized.provider_message_id,
        event_type=normalized.event_type,
        provider_event_id=normalized.provider_event_id,
        event_data=event_data,
        commit=False,
    )

    if (
        result.status == "matched"
        and normalized.event_type in ("click", "open")
        and result.engagement_event is not None
        # Only an event that names its content can locate an affinity.
        and event_data.get("content_record_id") is not None
    ):
        try:
            apply_event_to_signals(db, result.engagement_event.id, commit=False)
        except ValueError as error:
            # e.g. open weight 0, or content has no category assignments — the
            # raw event is still recorded, it just moved no signal.
            logger.info("event %s recorded but produced no signal: %s", result.engagement_event.id, error)

    # Delivery-feedback suppression: a hard bounce / spam complaint opts the
    # recipient out so they're excluded from every future audience + send. Only
    # acts on a matched event (we know who it was); the recorded event is the
    # audit of why. ADR-106 (bounce/complaint feedback is mandatory).
    if result.status == "matched" and normalized.suppresses_consent:
        from app.recipients.service import suppress_recipient

        delivery_execution = (
            db.query(DeliveryExecutionDB)
            .filter(DeliveryExecutionDB.provider_message_id == normalized.provider_message_id)
            .first()
        )
        if delivery_execution is not None:
            # Scope the opt-out to the channel and purpose this message actually
            # went out on. Both are denormalized onto the execution at plan time
            # (ADR-163 addendum 2026-09-12, point 1) precisely so this path has
            # them without joining back to the variant — a bounce on email says
            # nothing about whether the person still wants push.
            # The brand comes from the send instance this execution belongs
            # to (ADR-163 addendum 2026-09-15). An opt-out lands on the brand
            # that actually mailed the person — a bounce from brand A says
            # nothing about whether they still want brand B, the same reasoning
            # that already scopes this to channel and purpose.
            changed = suppress_recipient(
                db,
                delivery_execution.recipient_id,
                _brand_of_execution(db, delivery_execution),
                reason=normalized.event_type,
                channel=delivery_execution.channel,
                purpose=delivery_execution.purpose,
                commit=False,
            )
            if changed:
                logger.info(
                    "recipient %s opted out of %s/%s via %s feedback",
                    delivery_execution.recipient_id,
                    delivery_execution.channel,
                    delivery_execution.purpose,
                    normalized.event_type,
                )

    return result
