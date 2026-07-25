from sqlalchemy import Column, DateTime, JSON, String, func

from app.database import Base


class AppConfigDB(Base):
    """DB-backed runtime configuration — the parametric config layer (values and
    toggles a BI/admin person can retune without touching code). Deliberately
    NOT for structure/logic: the *shape* of things (decay model, scoring
    algorithm, plugins) stays in code; only tunable values live here (signal
    weights, decay half-lives, score bounds, and — once AI capabilities exist —
    the AI-governance guard toggles).

    Generic key → JSON value, so new settings don't need a migration. Code
    defines the defaults; a row here overrides them.
    """

    __tablename__ = "app_config"

    key = Column(String(100), primary_key=True)
    value = Column(JSON, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
