from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, func, UniqueConstraint

from app.database import Base


class ContentRecordDB(Base):
    __tablename__ = "content_records"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    content = Column(JSON, nullable=False, default=dict)
    status = Column(String(50), nullable=False, default="active")


class CategoryDB(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False, default="main")


class CategoryRelationDB(Base):
    __tablename__ = "category_relations"

    id = Column(Integer, primary_key=True, index=True)
    parent_category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    child_category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    relation_type = Column(String(50), nullable=False, default="parent_child")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    

class ContentCategoryAssignmentDB(Base):
    __tablename__ = "content_category_assignments"
    # The same TOCTOU that was closed for audience members
    # (uq_audience_group_members_group_recipient) and recipient preferences on
    # 2026-07-12. Content was missed at the time.
    __table_args__ = (
        UniqueConstraint(
            "content_id", "category_id",
            name="uq_content_category_assignments_content_category",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("content_records.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    score = Column(Integer, nullable=False, default=10)


class ContentVersionDB(Base):
    __tablename__ = "content_versions"
    # ADR-128 makes a version the audit answer to "what exact content did this
    # recipient receive?". Two rows sharing a number make
    # `resolve_renderable_content`'s ORDER BY version_number DESC ... .first()
    # pick one arbitrarily, so the audit answer becomes a coin toss — the same
    # ambiguity uq_module_instances_variant_position was added for.
    __table_args__ = (
        UniqueConstraint(
            "content_record_id", "version_number",
            name="uq_content_versions_record_version",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    content_record_id = Column(Integer, ForeignKey("content_records.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    content = Column(JSON, nullable=False)
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)