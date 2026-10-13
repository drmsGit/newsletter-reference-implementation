from datetime import datetime
from pydantic import BaseModel


class Snapshot(BaseModel):
    id: int
    variant_id: int
    recipient_id: int | None = None
    created_at: datetime
    render_context: dict | None = None

class VariantFramePreview(BaseModel):
    """What a variant would send if frozen now (ADR-183 addendum 2026-10-13):
    the subject and preheader, and the email's HTML or the push's fields."""

    channel: str
    subject: str | None = None
    preheader: str | None = None
    html: str | None = None
    fields: dict | None = None
