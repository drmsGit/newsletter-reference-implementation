from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db

from app.content.db_models import ContentRecordDB, ContentVersionDB, CategoryDB
from app.campaigns.db_models import CampaignDB, DecisionResolutionDB
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