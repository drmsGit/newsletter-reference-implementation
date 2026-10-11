"""Brand profiles: the default every brand has, and what a profile lacks.

ADR-194 and its 2026-10-11 addendum (task-350's final-design pass).
"""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.brand_profiles.db_models import BrandProfileDB
from app.brand_profiles.structure import missing_fields

DEFAULT_PROFILE_NAME = "Default"
#: What a new default profile starts with. English, because profiles are one
#: language each and the platform's own texts are English today. The legal
#: details are deliberately left empty: they are the company's to state, and a
#: placeholder would be sent as if it were true.
DEFAULT_VALUES = {"unsubscribe_text": "Unsubscribe"}


def ensure_default_profile(db: Session, brand_id: int) -> BrandProfileDB:
    """The brand's default profile, made if it has none. Commits when it makes one.

    Two callers racing here both try to insert; the partial unique index lets
    one through, and the other reads the winner's row.
    """
    profile = _default(db, brand_id)
    if profile is not None:
        return profile
    profile = BrandProfileDB(
        brand_id=brand_id, name=DEFAULT_PROFILE_NAME, language="en", kind="marketing",
        is_default=True, field_values=dict(DEFAULT_VALUES),
    )
    db.add(profile)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        winner = _default(db, brand_id)
        if winner is None:
            raise
        return winner
    db.refresh(profile)
    return profile


#: Read as "the default, whatever it takes": callers that only want to know.
default_profile = ensure_default_profile


def _default(db: Session, brand_id: int) -> BrandProfileDB | None:
    return (
        db.query(BrandProfileDB)
        .filter(BrandProfileDB.brand_id == brand_id, BrandProfileDB.is_default.is_(True))
        .first()
    )


def missing(profile: BrandProfileDB) -> list[str]:
    """The fields this profile must still fill before an email may use it."""
    return missing_fields(profile.kind, profile.field_values or {})
