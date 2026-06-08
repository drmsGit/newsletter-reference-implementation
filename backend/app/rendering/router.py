from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.rendering.service import render_variant_html


class RenderedVariant(BaseModel):
    variant_id: int
    html: str


router = APIRouter(prefix="/rendering", tags=["rendering"])


@router.get("/variants/{variant_id}", response_model=RenderedVariant)
def render_variant(
    variant_id: int,
    db: Session = Depends(get_db),
):
    html = render_variant_html(
        db=db,
        variant_id=variant_id,
    )

    return RenderedVariant(
        variant_id=variant_id,
        html=html,
    )