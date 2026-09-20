from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import working_brand
from app.database import get_db
from app.campaigns.db_models import VariantDB
# Aliased: the route function below is also called `render_variant`, so
# importing the service function under its own name made the endpoint call
# itself — 994 frames deep, surfacing as a 500 rather than as the shadowing it
# was. Found by re-probing after the fix rather than by the test suite, which
# does not exercise this JSON route.
from app.rendering.service import render_variant as render_channel_artifact


class RenderedVariant(BaseModel):
    variant_id: int
    channel: str
    role: str
    #: The document, for a channel that renders one. Empty for a push, whose
    #: artifact is a field payload — the OS does the rendering (ADR-160 pt 2).
    html: str = ""
    #: The structured payload, for a channel that has one.
    fields: dict | None = None


router = APIRouter(prefix="/rendering", tags=["rendering"])


@router.get("/variants/{variant_id}", response_model=RenderedVariant)
def render_variant(
    variant_id: int,
    recipient_id: int | None = None,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    # Through the channel's renderer (ADR-162 point 4). Calling the email path
    # directly returned a 200 with a 252-character empty document for a push
    # variant — no error, because nothing failed; the email assembler simply
    # found no email manifest for a push module and rendered comments.
    artifact = render_channel_artifact(
        db=db, variant_id=variant_id, recipient_id=recipient_id,
        brand_id=brand_id,
    )
    variant = db.query(VariantDB).filter(VariantDB.id == variant_id).first()

    return RenderedVariant(
        variant_id=variant_id,
        channel=variant.channel if variant else "",
        role=artifact.role,
        html=artifact.body or "",
        fields=artifact.fields,
    )