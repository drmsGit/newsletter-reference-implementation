from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.insight.db_models import EngagementEventDB
from app.insight.models import EngagementEvent, PreferenceUpdateResult

from app.delivery.db_models import DeliveryExecutionDB
from app.content.db_models import ContentCategoryAssignmentDB
from app.recipients.db_models import SignalContributionDB
from app.insight.signals import record_contribution

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


def page_events_for_delivery_execution(db: Session, delivery_execution_id: int, params, *, brand_id: int):
    """One ADR-185 page of an execution's engagement events, newest first.

    **Brand-scoped through the execution's send** (ADR-172 point 5). The route
    passed a brand that `list_events_for_delivery_execution` never accepted,
    so it raised TypeError on every call until 2026-10-03 — and, had it run,
    would have answered for any brand's execution.
    """
    from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
    from app.pagination import page_of_query

    query = (
        db.query(EngagementEventDB)
        .join(DeliveryExecutionDB, DeliveryExecutionDB.id == EngagementEventDB.delivery_execution_id)
        .join(SendInstanceDB, SendInstanceDB.id == DeliveryExecutionDB.send_instance_id)
        .filter(EngagementEventDB.delivery_execution_id == delivery_execution_id,
                SendInstanceDB.brand_id == brand_id)
    )
    return page_of_query(query, params, EngagementEventDB.occurred_at.desc(),
                         EngagementEventDB.id.desc(), convert=to_engagement_event)

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

    # Read the *configured* weight, not the module-level defaults, so the
    # Settings editor's override actually reaches computed signals
    # (ADR-132 §3: weights are tunable). Lazy import mirrors
    # `signals._configured_half_lives` — settings.service imports the weight
    # defaults from app.insight.signals, so keep it off the module-load path.
    from app.settings.service import get_signal_weights

    base_weight = get_signal_weights(db).get(event.event_type)
    if base_weight is None:
        raise ValueError(
            f"no configured weight for contribution_type '{event.event_type}'"
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
            # The execution carries the real channel since ADR-160 point 4 was
            # built; before that it defaulted to email for every send, so
            # copying it then would have recorded a fact nobody had.
            channel=delivery_execution.channel,
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

def event_trace(db: Session, execution_ids: list[int], *, brand_id: int) -> dict[int, list[dict]]:
    """For each execution in this brand, its engagement events newest first,
    each with the signal contributions it produced (task-50, B24; B10 reuses it).

    Two queries for any number of executions — the Jinja delivery page did one
    per execution and one per event. An execution of another brand's send is
    simply absent from the result.
    """
    from app.content.db_models import CategoryDB
    from app.delivery.db_models import SendInstanceDB

    if not execution_ids:
        return {}
    events = (
        db.query(EngagementEventDB)
        .join(DeliveryExecutionDB, DeliveryExecutionDB.id == EngagementEventDB.delivery_execution_id)
        .join(SendInstanceDB, SendInstanceDB.id == DeliveryExecutionDB.send_instance_id)
        .filter(EngagementEventDB.delivery_execution_id.in_(execution_ids),
                SendInstanceDB.brand_id == brand_id)
        .order_by(EngagementEventDB.occurred_at.desc(), EngagementEventDB.id.desc())
        .all()
    )
    contributions: dict[int, list[dict]] = {}
    if events:
        for c, name in (
            db.query(SignalContributionDB, CategoryDB.name)
            .join(CategoryDB, CategoryDB.id == SignalContributionDB.category_id)
            .filter(SignalContributionDB.event_id.in_([e.id for e in events]))
            .all()
        ):
            contributions.setdefault(c.event_id, []).append({
                "category_id": c.category_id, "category_name": name,
                "base_weight": c.base_weight, "contribution_type": c.contribution_type,
            })
    trace: dict[int, list[dict]] = {}
    for e in events:
        trace.setdefault(e.delivery_execution_id, []).append({
            "id": e.id, "event_type": e.event_type, "occurred_at": e.occurred_at,
            "event_data": e.event_data, "contributions": contributions.get(e.id, []),
            "provider": e.provider, "provider_event_id": e.provider_event_id,
            "created_at": e.created_at,
        })
    return trace


def brand_overview(db: Session, *, brand_id: int) -> dict:
    """The dashboard's counts for one brand (task-50, B4). Recipients are the
    exception and are company-wide by design: a recipient carries no brand
    (ADR-150 point 9)."""
    from app.campaigns.db_models import CampaignDB, VariantDB
    from app.content.db_models import ContentRecordDB
    from app.delivery.db_models import SendInstanceDB
    from app.recipients.db_models import RecipientDB
    from app.snapshots.db_models import SnapshotDB

    return {
        "content_active": db.query(ContentRecordDB).filter(
            ContentRecordDB.status == "active", ContentRecordDB.brand_id == brand_id).count(),
        "campaigns": db.query(CampaignDB).filter(CampaignDB.brand_id == brand_id).count(),
        "recipients": db.query(RecipientDB).count(),
        "snapshots": (
            db.query(SnapshotDB)
            .join(VariantDB, VariantDB.id == SnapshotDB.variant_id)
            .join(CampaignDB, CampaignDB.id == VariantDB.campaign_id)
            .filter(CampaignDB.brand_id == brand_id).count()
        ),
        "deliveries": (
            db.query(DeliveryExecutionDB)
            .join(SendInstanceDB, SendInstanceDB.id == DeliveryExecutionDB.send_instance_id)
            .filter(SendInstanceDB.brand_id == brand_id).count()
        ),
        "events": (
            db.query(EngagementEventDB)
            .join(DeliveryExecutionDB, DeliveryExecutionDB.id == EngagementEventDB.delivery_execution_id)
            .join(SendInstanceDB, SendInstanceDB.id == DeliveryExecutionDB.send_instance_id)
            .filter(SendInstanceDB.brand_id == brand_id).count()
        ),
    }
