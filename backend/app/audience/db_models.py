from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func

from app.database import Base


class AudienceGroupDB(Base):
    __tablename__ = "audience_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    # Set when the group was seeded by "Suggest audience" from a campaign.
    # Lets "Recalculate" re-derive the suggested blocks from that campaign's
    # current content after its slots/content change. Null for hand-made groups.
    source_campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        # Case-insensitive uniqueness ("Newsletter VIPs" and "newsletter
        # vips" must not both exist) — a functional index on lower(name)
        # subsumes plain case-sensitive uniqueness, so there's no separate
        # unique=True on the column.
        Index("ux_audience_groups_name_lower", func.lower(name), unique=True),
    )


class AudienceGroupMemberDB(Base):
    __tablename__ = "audience_group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("audience_groups.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("recipients.id"), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("group_id", "recipient_id", name="uq_audience_group_members_group_recipient"),
    )


class AudienceRuleBlockDB(Base):
    """A single criteria rule inside an audience group. The group's final
    audience is evaluated live from its blocks, not stored as a frozen member
    list: (union of all `include` blocks) ∪ (manual pins in
    AudienceGroupMemberDB) − (union of all `exclude` blocks), always gated to
    consenting recipients. Include blocks combine by OR so a manager can stack
    "interested in Hiking" OR "interested in Food" and see/edit/delete each
    independently; exclude blocks subtract (e.g. a removed segment).

    `source` marks whether the block was hand-authored ("manual") or seeded by
    a system suggestion ("suggested") — kept so suggested blocks stay visibly
    editable/deletable rather than becoming an opaque list (same trust model as
    the content override layer, ADR-040/041)."""

    __tablename__ = "audience_rule_blocks"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("audience_groups.id"), nullable=False)
    # "include" (adds recipients) or "exclude" (removes them).
    kind = Column(String(20), nullable=False, default="include")
    # Human label shown on the block, e.g. "Interested in Hiking".
    label = Column(String(255), nullable=True)
    # Criteria payload, keyed the same as audience.service.find_by_criteria:
    # {"language", "status", "category_id", "min_score"}. JSON so new criteria
    # (recency windows, etc.) extend without a migration.
    criteria = Column(JSON, nullable=False, default=dict)
    # "manual" | "suggested" — provenance, for the suggested badge.
    source = Column(String(20), nullable=False, default="manual")
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
