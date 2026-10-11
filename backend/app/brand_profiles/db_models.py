from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, JSON, String,
    UniqueConstraint, func, text,
)

from app.database import Base


class BrandProfileDB(Base):
    """One of a brand's looks — its texts, links, legal details and style
    values (ADR-194). Which fields `field_values` may hold is declared in
    `storage/brand_profile.json` (`app.brand_profiles.structure`), so the
    values are JSON rather than columns: the structure is the installation's,
    not the schema's.

    **Every brand always has exactly one default** (the partial unique index
    below; `service.ensure_default_profile` creates it). Profiles are deleted
    with their brand rather than blocking it (`auth.service.DELETED_WITH_BRAND`).
    """

    __tablename__ = "brand_profiles"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    #: One profile per language (ADR-194 point 6): its texts are in this one.
    language = Column(String(20), nullable=False, server_default="en")
    #: marketing | transactional (ADR-194 point 9). Transactional is refused by
    #: the API until its guard exists (task-355).
    kind = Column(String(20), nullable=False, server_default="marketing")
    is_default = Column(Boolean, nullable=False, server_default=text("false"))
    #: Not `values`: that is an SQL keyword.
    field_values = Column(JSON, nullable=False, server_default=text("'{}'"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    #: The version token for If-Match, like every other editable row.
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
                        nullable=False)

    __table_args__ = (
        UniqueConstraint("brand_id", "name", name="uq_brand_profiles_brand_name"),
        CheckConstraint("kind IN ('marketing','transactional')", name="ck_brand_profiles_kind"),
        Index(
            "ux_brand_profiles_one_default_per_brand",
            "brand_id",
            unique=True,
            postgresql_where=(is_default == True),  # noqa: E712
        ),
    )
