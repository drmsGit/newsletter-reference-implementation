from datetime import datetime
from pydantic import BaseModel


class Snapshot(BaseModel):
    id: int
    variant_id: int
    html: str
    created_at: datetime