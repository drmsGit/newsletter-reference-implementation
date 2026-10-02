from datetime import datetime
from typing import Any

from pydantic import BaseModel


class EngagementEvent(BaseModel):
    id: int
    delivery_execution_id: int
    event_type: str
    provider: str | None = None
    provider_event_id: str | None = None
    event_data: dict[str, Any] | None = None
    occurred_at: datetime
    created_at: datetime


class EngagementEventCreate(BaseModel):
    delivery_execution_id: int
    event_type: str
    provider: str | None = None
    provider_event_id: str | None = None
    event_data: dict[str, Any] | None = None
    occurred_at: datetime | None = None


class PreferenceUpdateResult(BaseModel):
    event_id: int
    recipient_id: int
    content_record_id: int
    updated_categories: list[int]
    applied_deltas: dict[int, float]

class CategoryGraphNode(BaseModel):
    """One category and what this brand's figures say about it (ADR-150).

    Counts are this brand's content and resolutions; the impact figures sum
    this brand's audience (latest marketing consent opted in on any channel).
    """

    id: int
    name: str
    type: str
    selected_count: int
    content_count: int
    update_count: int
    event_count: int
    total_delta: float
    avg_delta: float
    parent_count: int
    child_count: int


class CategoryGraphEdge(BaseModel):
    source: int
    target: int
    # "relation" (a declared parent/child link) or "cooccurrence" (assigned
    # together on this brand's content and not otherwise related).
    type: str
    cooccurrence_count: int
    event_count: int
    total_delta: float
    strength: int


class CategoryGraph(BaseModel):
    """The category graph's figures for one brand — no layout. Positions,
    radius, colour and thickness are presentation and stay with the client."""

    brand_id: int
    nodes: list[CategoryGraphNode]
    edges: list[CategoryGraphEdge]
