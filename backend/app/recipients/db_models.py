from sqlalchemy import Column, DateTime, Integer, JSON, String, func, Float, ForeignKey

from app.database import Base


class RecipientDB(Base):
    __tablename__ = "recipients"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(255), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False)
    language = Column(String(20), nullable=True)
    attributes = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class RecipientPreferenceDB(Base):
    __tablename__ = "recipient_preferences"

    id = Column(Integer, primary_key=True, index=True)

    recipient_id = Column(
        Integer,
        ForeignKey("recipients.id"),
        nullable=False,
    )

    category_id = Column(
        Integer,
        ForeignKey("categories.id"),
        nullable=False,
    )

    score = Column(Float, nullable=False)

    source = Column(
        String(50),
        nullable=False,
        default="manual",
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class PreferenceUpdateLogDB(Base):
    __tablename__ = "preference_update_logs"

    id = Column(Integer, primary_key=True)

    recipient_id = Column(
        Integer,
        ForeignKey("recipients.id"),
        nullable=False,
    )

    category_id = Column(
        Integer,
        ForeignKey("categories.id"),
        nullable=False,
    )

    event_id = Column(
        Integer,
        ForeignKey("engagement_events.id"),
        nullable=False,
    )

    previous_score = Column(
        Float,
        nullable=False,
    )

    delta = Column(
        Float,
        nullable=False,
    )

    new_score = Column(
        Float,
        nullable=False,
    )

    reason = Column(
        String,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )