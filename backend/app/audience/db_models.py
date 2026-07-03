from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class AudienceGroupDB(Base):
    __tablename__ = "audience_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AudienceGroupMemberDB(Base):
    __tablename__ = "audience_group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("audience_groups.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("recipients.id"), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
