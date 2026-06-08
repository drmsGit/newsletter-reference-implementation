from fastapi import FastAPI

from app.database import Base, engine, SessionLocal
from app.content.db_models import ContentRecordDB
from app.content.router import router as content_router
from app.content.service import create_demo_content_if_empty

from app.campaigns.db_models import CampaignDB, VariantDB, ModuleInstanceDB, DecisionSlotDB
from app.campaigns.router import router as campaigns_router


app = FastAPI(
    title="Newsletter Reference Architecture API",
    version="0.1.0",
)


Base.metadata.create_all(bind=engine)


with SessionLocal() as db:
    create_demo_content_if_empty(db)


app.include_router(content_router)
app.include_router(campaigns_router)


@app.get("/")
def root():
    return {"message": "Newsletter Reference Architecture API"}