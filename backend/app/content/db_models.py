from sqlalchemy import Column, Integer, String, Text

from app.database import Base


class ContentRecordDB(Base):
    __tablename__ = "content_records"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="active")