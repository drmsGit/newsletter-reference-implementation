from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func, text

from app.database import Base


class ExpressionEntryDB(Base):
    """One entry of a brand's expression dictionary (task-365, ADR-199).

    `name` is what a text writes ({{salutation_formal}}) and is fixed once the
    entry exists; `label` is what the picker shows. `languages` holds, per
    language, an ordered list of cases and the fallback:
    `{"de": {"cases": [{"field", "is", "value"?, "text"}], "fallback": "…"}}`.
    """

    __tablename__ = "expression_entries"
    __table_args__ = (UniqueConstraint("brand_id", "name", name="uq_expression_entries_brand_name"),)

    id = Column(Integer, primary_key=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False, index=True)
    name = Column(String(64), nullable=False)
    label = Column(String(200), nullable=False)
    # The database default as migration 0051 declares it, so the schema check agrees.
    languages = Column(JSON, nullable=False, default=dict, server_default=text("'{}'::json"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
