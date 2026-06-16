from sqlalchemy import Column, DateTime, Integer, JSON, String, func

from app.database import Base


class RecipientDB(Base):
    __tablename__ = "recipients"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(255), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False)
    language = Column(String(20), nullable=True)
    preferred_airport = Column(String(20), nullable=True)
    attributes = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )