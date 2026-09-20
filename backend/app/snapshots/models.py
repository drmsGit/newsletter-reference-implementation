from datetime import datetime
from pydantic import BaseModel


class Snapshot(BaseModel):
    id: int
    variant_id: int
    recipient_id: int | None = None
    artifact_storage_type: str
    artifact_location: str
    artifact_size: int
    created_at: datetime
    render_context: dict | None = None