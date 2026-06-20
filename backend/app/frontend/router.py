from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db

from app.content.db_models import ContentRecordDB
from app.campaigns.db_models import CampaignDB
from app.recipients.db_models import RecipientDB
from app.snapshots.db_models import SnapshotDB
from app.delivery.db_models import DeliveryExecutionDB
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