from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func

from app.database import Base


class AudienceGroupDB(Base):
    __tablename__ = "audience_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
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
