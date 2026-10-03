from datetime import datetime
from pydantic import BaseModel


class Snapshot(BaseModel):
    id: int
    variant_id: int
    recipient_id: int | None = None
    created_at: datetime
    render_context: dict | None = None