from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import get_db

from app.content.db_models import ContentRecordDB, ContentVersionDB, CategoryDB, ContentCategoryAssignmentDB
from app.campaigns.db_models import CampaignDB, DecisionResolutionDB, VariantDB, ModuleInstanceDB, DecisionSlotDB
from app.recipients.db_models import RecipientDB, RecipientPreferenceDB, PreferenceUpdateLogDB
from app.snapshots.db_models import SnapshotDB
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.insight.db_models import EngagementEventDB

router = APIRouter(tags=["frontend"])

templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
):
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "title": "Architecture Dashboard",
            "content_count": db.query(ContentRecordDB).count(),
            "campaign_count": db.query(CampaignDB).count(),
            "recipient_count": db.query(RecipientDB).count(),
            "snapshot_count": db.query(SnapshotDB).count(),
            "delivery_count": db.query(DeliveryExecutionDB).count(),
            "event_count": db.query(EngagementEventDB).count(),
        },
    )


@router.get("/ui/recipients")
def recipients_list(
    request: Request,
    db: Session = Depends(get_db),
):
    recipients = (
        db.query(RecipientDB)
        .order_by(RecipientDB.id.asc())
        .all()
    )

    return templates.TemplateResponse(
        request,
        "recipients.html",
        {
            "title": "Recipients",
            "recipients": recipients,
        },
    )


@router.get("/ui/recipients/{recipient_id}")
def recipient_detail(
    recipient_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    recipient = (
        db.query(RecipientDB)
        .filter(RecipientDB.id == recipient_id)
        .first()
    )

    preferences = (
        db.query(
            RecipientPreferenceDB,
            CategoryDB.name,
        )
        .join(
            CategoryDB,
            RecipientPreferenceDB.category_id == CategoryDB.id,
        )
        .filter(
            RecipientPreferenceDB.recipient_id == recipient_id
        )
        .all()
    )

    preference_rows = [
        {
            "category_name": category_name,
            "score": pref.score,
            "source": pref.source,
        }
        for pref, category_name in preferences
    ]

    decisions = (
        db.query(
            DecisionResolutionDB,
            ContentRecordDB.title,
            ContentVersionDB.version_number,
        )
        .join(
            ContentRecordDB,
            DecisionResolutionDB.content_record_id == ContentRecordDB.id,
        )
        .outerjoin(
            ContentVersionDB,
            DecisionResolutionDB.content_version_id == ContentVersionDB.id,
        )
        .filter(
            DecisionResolutionDB.recipient_id == recipient_id
        )
        .order_by(
            DecisionResolutionDB.created_at.desc()
        )
        .limit(20)
        .all()
    )

    decision_rows = [
        {
            "id": decision.id,
            "decision_slot_id": decision.decision_slot_id,
            "content_title": content_title,
            "content_version": version_number,
            "score": decision.score,
            "reason": decision.reason,
            "created_at": decision.created_at,
        }
        for decision, content_title, version_number in decisions
    ]

    deliveries = (
        db.query(
            DeliveryExecutionDB,
            SendInstanceDB.name,
        )
        .join(
            SendInstanceDB,
            DeliveryExecutionDB.send_instance_id == SendInstanceDB.id,
        )
        .filter(
            DeliveryExecutionDB.recipient_id == recipient.external_id
        )
        .order_by(
            DeliveryExecutionDB.created_at.desc()
        )
        .limit(20)
        .all()
    )

    delivery_rows = []

    for delivery, send_instance_name in deliveries:
        delivery_events = (
            db.query(EngagementEventDB)
            .filter(
                EngagementEventDB.delivery_execution_id == delivery.id
            )
            .order_by(
                EngagementEventDB.created_at.desc()
            )
            .all()
        )

        event_rows = []

        for event in delivery_events:
            preference_updates = (
                db.query(
                    PreferenceUpdateLogDB,
                    CategoryDB.name,
                )
                .join(
                    CategoryDB,
                    PreferenceUpdateLogDB.category_id == CategoryDB.id,
                )
                .filter(
                    PreferenceUpdateLogDB.event_id == event.id
                )
                .all()
            )

            event_rows.append(
                {
                    "id": event.id,
                    "event_type": event.event_type,
                    "provider_event_id": event.provider_event_id,
                    "created_at": event.created_at,
                    "preference_updates": [
                        {
                            "category_name": category_name,
                            "previous_score": update.previous_score,
                            "delta": update.delta,
                            "new_score": update.new_score,
                            "reason": update.reason,
                        }
                        for update, category_name in preference_updates
                    ],
                }
            )

        delivery_rows.append(
            {
                "id": delivery.id,
                "send_instance_name": send_instance_name,
                "status": delivery.status,
                "provider": delivery.provider,
                "provider_message_id": delivery.provider_message_id,
                "created_at": delivery.created_at,
                "events": event_rows,
            }
        )


    return templates.TemplateResponse(
        request,
        "recipient_detail.html",
        {
            "title": f"Recipient {recipient_id}",
            "recipient": recipient,
            "preferences": preference_rows,
            "decisions": decision_rows,
            "deliveries": delivery_rows,
        },
    )


@router.get("/ui/campaigns")
def campaigns_list(
    request: Request,
    db: Session = Depends(get_db),
):
    campaigns = (
        db.query(CampaignDB)
        .order_by(CampaignDB.created_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        request,
        "campaigns.html",
        {
            "title": "Campaigns",
            "campaigns": campaigns,
        },
    )


@router.get("/ui/campaigns/{campaign_id}")
def campaign_detail(
    campaign_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    campaign = (
        db.query(CampaignDB)
        .filter(CampaignDB.id == campaign_id)
        .first()
    )

    variants = (
        db.query(VariantDB)
        .filter(VariantDB.campaign_id == campaign_id)
        .order_by(VariantDB.id.asc())
        .all()
    )

    variant_rows = []

    for variant in variants:
        modules = (
            db.query(ModuleInstanceDB)
            .filter(ModuleInstanceDB.variant_id == variant.id)
            .order_by(ModuleInstanceDB.position.asc())
            .all()
        )

        decision_slots = (
            db.query(DecisionSlotDB)
            .filter(DecisionSlotDB.variant_id == variant.id)
            .order_by(DecisionSlotDB.id.asc())
            .all()
        )
        
        decision_slot_rows = []

        for slot in decision_slots:
            resolution_count = (
                db.query(DecisionResolutionDB)
                .filter(
                    DecisionResolutionDB.decision_slot_id == slot.id
                )
                .count()
            )
            unique_content_count = (
                db.query(
                    DecisionResolutionDB.content_record_id
                )
                .filter(
                    DecisionResolutionDB.decision_slot_id == slot.id
                )
                .distinct()
                .count()
            )
            top_content = (
                db.query(
                    ContentRecordDB.title,
                    func.count(
                        DecisionResolutionDB.id
                    ).label("resolution_count"),
                )
                .join(
                    ContentRecordDB,
                    DecisionResolutionDB.content_record_id
                    == ContentRecordDB.id,
                )
                .filter(
                    DecisionResolutionDB.decision_slot_id == slot.id
                )
                .group_by(
                    ContentRecordDB.title
                )
                .order_by(
                    desc("resolution_count")
                )
                .limit(5)
                .all()
            )
            latest_resolutions = (
                db.query(
                    DecisionResolutionDB,
                    ContentRecordDB.title,
                )
                .join(
                    ContentRecordDB,
                    DecisionResolutionDB.content_record_id
                    == ContentRecordDB.id,
                )
                .filter(
                    DecisionResolutionDB.decision_slot_id == slot.id
                )
                .order_by(
                    DecisionResolutionDB.created_at.desc()
                )
                .limit(10)
                .all()
            )
            decision_slot_rows.append(
                {
                    "id": slot.id,
                    "name": slot.name,
                    "decision_type": slot.decision_type,
                    "decision_strategy": slot.decision_strategy,
                    "resolution_count": resolution_count,
                    "unique_content_count": unique_content_count,
                    "top_content": top_content,
                    "latest_resolutions": latest_resolutions,
                }
            )

        snapshots = (
            db.query(SnapshotDB)
            .filter(SnapshotDB.variant_id == variant.id)
            .order_by(SnapshotDB.created_at.desc())
            .all()
        )

        variant_rows.append(
            {
                "id": variant.id,
                "name": variant.name,
                "modules": modules,
                "decision_slots": decision_slot_rows,
                "snapshots": snapshots,
            }
        )

    return templates.TemplateResponse(
        request,
        "campaign_detail.html",
        {
            "title": f"Campaign {campaign_id}",
            "campaign": campaign,
            "variants": variant_rows,
        },
    )


@router.get("/ui/content")
def content_list(
    request: Request,
    db: Session = Depends(get_db),
):
    records = (
        db.query(ContentRecordDB)
        .order_by(ContentRecordDB.id.asc())
        .all()
    )

    return templates.TemplateResponse(
        request,
        "content.html",
        {
            "title": "Content",
            "records": records,
        },
    )


@router.get("/ui/content/{content_record_id}")
def content_detail(
    content_record_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    record = (
        db.query(ContentRecordDB)
        .filter(ContentRecordDB.id == content_record_id)
        .first()
    )

    categories = (
        db.query(
            CategoryDB.name,
            CategoryDB.type,
            ContentCategoryAssignmentDB.score,
        )
        .join(
            ContentCategoryAssignmentDB,
            ContentCategoryAssignmentDB.category_id == CategoryDB.id,
        )
        .filter(
            ContentCategoryAssignmentDB.content_id == content_record_id
        )
        .all()
    )

    category_rows = [
        {
            "name": name,
            "type": category_type,
            "score": score,
        }
        for name, category_type, score in categories
    ]

    versions = (
        db.query(ContentVersionDB)
        .filter(ContentVersionDB.content_record_id == content_record_id)
        .order_by(ContentVersionDB.version_number.desc())
        .all()
    )

    version_rows = [
        {
            "version_number": version.version_number,
            "created_by": version.created_by,
            "created_at": version.created_at,
            "headline": (
                (version.content or {}).get("headline_medium")
                or (version.content or {}).get("headline_short")
                or (version.content or {}).get("headline")
            ),
            "text": (
                (version.content or {}).get("text_medium")
                or (version.content or {}).get("text_short")
                or (version.content or {}).get("text")
            ),
        }
        for version in versions
    ]

    decision_usage = (
        db.query(DecisionResolutionDB)
        .filter(
            DecisionResolutionDB.content_record_id == content_record_id
        )
        .order_by(
            DecisionResolutionDB.created_at.desc()
        )
        .limit(20)
        .all()
    )

    signals = (
        db.query(
            PreferenceUpdateLogDB,
            CategoryDB.name,
            EngagementEventDB.event_data,
        )
        .join(
            CategoryDB,
            PreferenceUpdateLogDB.category_id == CategoryDB.id,
        )
        .join(
            EngagementEventDB,
            PreferenceUpdateLogDB.event_id == EngagementEventDB.id,
        )
        .order_by(
            PreferenceUpdateLogDB.created_at.desc()
        )
        .limit(100)
        .all()
    )

    signal_rows = []

    for update, category_name, event_data in signals:
        event_content_record_id = (event_data or {}).get("content_record_id")

        if event_content_record_id != content_record_id:
            continue

        signal_rows.append(
            {
                "recipient_id": update.recipient_id,
                "category_name": category_name,
                "previous_score": update.previous_score,
                "delta": update.delta,
                "new_score": update.new_score,
                "reason": update.reason,
                "created_at": update.created_at,
            }
        )

    return templates.TemplateResponse(
        request,
        "content_detail.html",
        {
            "title": f"Content {content_record_id}",
            "record": record,
            "categories": category_rows,
            "versions": version_rows,
            "decision_usage": decision_usage,
            "preference_signals": signal_rows,
        },
    )