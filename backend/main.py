from fastapi import FastAPI

from app.database import Base, engine, SessionLocal
from app.content.db_models import ContentRecordDB, CategoryDB, ContentCategoryAssignmentDB, ContentVersionDB
from app.content.router import router as content_router
from app.content.service import create_demo_content_if_empty

from app.campaigns.db_models import CampaignDB, VariantDB, ModuleInstanceDB, DecisionSlotDB, DecisionResolutionDB
from app.campaigns.router import router as campaigns_router

from app.rendering.router import router as rendering_router

from app.snapshots.db_models import SnapshotDB
from app.snapshots.router import router as snapshots_router

from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.delivery.router import router as delivery_router

from app.insight.db_models import EngagementEventDB
from app.insight.router import router as insight_router

from app.decision.router import router as decision_router

from app.recipients.db_models import RecipientDB, RecipientPreferenceDB
from app.recipients.router import router as recipients_router


app = FastAPI(
    title="Newsletter Reference Architecture API",
    version="0.1.0",
)


Base.metadata.create_all(bind=engine)


with SessionLocal() as db:
    create_demo_content_if_empty(db)


app.include_router(content_router)
app.include_router(campaigns_router)
app.include_router(rendering_router)
app.include_router(snapshots_router)
app.include_router(delivery_router)
app.include_router(insight_router)
app.include_router(decision_router)
app.include_router(recipients_router)


@app.get("/")
def root():
    return {"message": "Newsletter Reference Architecture API"}