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


class BrandOverview(BaseModel):
    """The dashboard's counts (task-50, B4). `recipients` is company-wide."""

    content_active: int
    campaigns: int
    recipients: int
    snapshots: int
    deliveries: int
    events: int


class CategoryRef(BaseModel):
    id: int
    name: str
    type: str
    # The relation linking it, for deleting that link (DELETE /content/category-relations/{id}).
    relation_id: int | None = None


class CategoryContent(BaseModel):
    content_id: int
    title: str
    score: float | None = None


class CategoryRecipient(BaseModel):
    recipient_id: int
    external_id: str | None = None
    score: float


class CategoryImpact(BaseModel):
    update_count: int
    total_delta: float
    avg_delta: float


class CategoryDetail(BaseModel):
    """One category for the working brand (task-50, B20): this brand's content
    and this brand's audience; the category and its relations are shared."""

    category: CategoryRef
    parents: list[CategoryRef]
    children: list[CategoryRef]
    assigned_content: list[CategoryContent]
    top_recipients: list[CategoryRecipient]
    impact: CategoryImpact
