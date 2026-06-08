from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.content.models import ContentRecord
from app.content.service import list_content_records


router = APIRouter(prefix="/content", tags=["content"])


@router.get("/", response_model=list[ContentRecord])
def get_content_records(db: Session = Depends(get_db)):
    return list_content_records(db)