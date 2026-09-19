from datetime import datetime

from typing import Any

from pydantic import BaseModel


class AudienceGroup(BaseModel):
    id: int
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class AudienceGroupCreate(BaseModel):
    name: str
    description: str | None = None


class AudienceGroupMember(BaseModel):
    id: int
    group_id: int
    recipient_id: int
    added_at: datetime


class AudienceRuleBlock(BaseModel):
    """A single criteria rule inside a group.

    The group's audience is evaluated live from its blocks rather than stored
    as a frozen member list, so this is the authoring surface for who a group
    means — not a snapshot of who it currently contains.
    """

    id: int
    group_id: int
    kind: str
    criteria: dict[str, Any] | None = None
    label: str | None = None
    source: str
    position: int

    model_config = {"from_attributes": True}


class AudienceRuleBlockCreate(BaseModel):
    kind: str = "include"
    criteria: dict[str, Any] | None = None
    label: str | None = None


class AudienceRuleBlockUpdate(BaseModel):
    kind: str | None = None
    criteria: dict[str, Any] | None = None
    label: str | None = None


class BulkAddRequest(BaseModel):
    """Pins, added in one call.

    Named `recipient_ids` rather than `members` because these become manual
    pins in `AudienceGroupMemberDB` — the half of a group that is a list of
    people rather than a rule about them.
    """

    recipient_ids: list[int]
