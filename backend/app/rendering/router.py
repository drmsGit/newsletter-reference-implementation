from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
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
from app.rendering.service import module_states
from app.rendering.service import render_variant as render_channel_artifact


class ModuleState(BaseModel):
    """What one module is doing in this render (task-227). See
    `rendering.service.module_states` for what each field means."""

    module_id: int
    position: int
    module_type: str
    kind: Literal["record", "slot", "typed", "unbound", "unknown"]
    slot_state: Literal["resolved", "not_run", "finds_nothing"] | None = None
    generic_pick: bool = False
    unpublished_changes: bool = False
    missing_required: list[str] = []


class RenderedVariant(BaseModel):
    variant_id: int
    channel: str
    role: str
    #: The document, for a channel that renders one. Empty for a push, whose
    #: artifact is a field payload — the OS does the rendering (ADR-160 pt 2).
    #:
    #: Named `artifact_body` rather than `html` because rendering does not
    #: always produce HTML — ADR-162 point 3 renamed the snapshot columns
    #: `html_*` → `artifact_*` for exactly this reason and missed this model.
    artifact_body: str = ""
    #: The structured payload, for a channel that has one.
    fields: dict | None = None
    #: Each module's state, for the composer's preview (task-227): an HTML
    #: comment in the artifact is not something a client should parse.
    modules: list[ModuleState] = []


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
    try:
        artifact = render_channel_artifact(
            db=db, variant_id=variant_id, recipient_id=recipient_id,
            brand_id=brand_id,
        )
    except ValueError as error:
        # A variant outside the brand, or none at all, is not found. It
        # answered 500 until 2026-10-04 (task-227).
        raise HTTPException(status_code=404, detail=str(error))
    variant = db.query(VariantDB).filter(VariantDB.id == variant_id).first()

    return RenderedVariant(
        variant_id=variant_id,
        channel=variant.channel if variant else "",
        role=artifact.role,
        artifact_body=artifact.body or "",
        fields=artifact.fields,
        modules=module_states(db, variant_id, recipient_id, brand_id=brand_id),
    )