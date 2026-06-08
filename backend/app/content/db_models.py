from sqlalchemy import Column, Integer, String, Text, ForeignKey

from app.database import Base


class ContentRecordDB(Base):
    __tablename__ = "content_records"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="active")


class CategoryDB(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False, default="main")


class ContentCategoryAssignmentDB(Base):
    __tablename__ = "content_category_assignments"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("content_records.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    score = Column(Integer, nullable=False, default=10)