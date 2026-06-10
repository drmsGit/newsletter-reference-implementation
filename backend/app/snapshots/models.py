from datetime import datetime
from pydantic import BaseModel


class Snapshot(BaseModel):
    id: int
    variant_id: int
    html_storage_type: str
    html_location: str
    html_size: int
    created_at: datetime