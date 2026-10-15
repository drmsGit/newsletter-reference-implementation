from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, func

from app.database import Base


class AssetDB(Base):
    """One image in a brand's library (ADR-197).

    **The served path is the token, not the id or the name** (point 11): a
    random component per asset, so `/media/1..9999` cannot walk anyone's
    library, and the generated `name` — predictable on purpose, so search
    works — never becomes a path. A replaced file keeps its token, so emails
    already sent show the new image (point 3).

    **Nothing is deleted** (point 4): `hidden_at` takes an image out of the
    picker; the file is served for as long as any email might show it. So a
    brand holding images cannot be deleted either (`auth.service.brand_holders`).
    """

    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False, index=True)
    #: The unguessable part of `/media/<token>`; also the file's key in the store.
    token = Column(String(64), nullable=False, unique=True)
    #: Generated from the setup file's template; searchable metadata (point 9).
    name = Column(String(255), nullable=False)
    #: What the person typed, kept so a replacement can regenerate the name.
    label = Column(String(200), nullable=False)
    product_id = Column(String(100), nullable=True)
    #: The running number in the name: per brand, per upload day.
    sequence = Column(Integer, nullable=False)
    media_type = Column(String(50), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    #: Written once at upload; a usage may override it (point 1).
    alt_text = Column(String(500), nullable=False, server_default="")
    hidden_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
                        nullable=False)

    __table_args__ = (Index("ix_assets_brand_name", "brand_id", "name"),)
