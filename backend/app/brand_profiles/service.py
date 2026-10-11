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


def ensure_default_profile(db: Session, brand_id: int, *, commit: bool = True) -> BrandProfileDB:
    """The brand's default profile, made if it has none. Commits when it makes
    one, unless `commit` is False: then it is only flushed, inside a savepoint,
    for a caller whose transaction must stay open (a duplication).

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
    if not commit:
        try:
            with db.begin_nested():
                db.add(profile)
        except IntegrityError:
            return _default(db, brand_id)
        return profile
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


# --- reading and writing a brand's profiles (task-350) ----------------------
#
# Every function takes the working brand and finds the profile only inside it,
# so another brand's profile reads as not found rather than forbidden: its
# existence is not this caller's to learn (ADR-172).

import re
from datetime import datetime

from app.brand_profiles.structure import KINDS, MARKETING, TRANSACTIONAL, profile_structure

NAME_MAX = 200
TEXT_MAX = 2000
LANGUAGE = re.compile(r"[a-z]{2}(-[A-Z]{2})?")
_COLOUR = re.compile(r"#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?")
_SIZE = re.compile(r"\d+(\.\d+)?(px|em|rem|%)")
_URL = re.compile(r"https?://\S+")
#: A font list goes into CSS (brand.css, task-354): names, commas, quotes,
#: hyphens and dots only, so a value can never close a rule.
_FONT_FAMILY = re.compile(r"[A-Za-z0-9 ,'\"._-]+")
#: One further link parameter per line of utm_extra.
_PARAM_LINE = re.compile(r"[A-Za-z0-9_.-]+=[^\s&=]*")


class ProfileNotFound(LookupError):
    pass


class ProfileConflict(Exception):
    """A write the profile's current state refuses: a taken name, deleting the
    default. A 409 — the request was well-formed."""


class ProfileInvalid(ValueError):
    """One entry per refused part: `(location, message)`, where the location is
    `("field_values", name)` or a top-level key such as `("kind",)`."""

    def __init__(self, errors: list[tuple[tuple[str, ...], str]]):
        self.errors = errors
        super().__init__("; ".join(f"{'.'.join(loc)}: {msg}" for loc, msg in errors))


def list_profiles(db: Session, brand_id: int):
    """The brand's profiles as a query: the default first, then by name."""
    ensure_default_profile(db, brand_id)
    return db.query(BrandProfileDB).filter(BrandProfileDB.brand_id == brand_id)


LIST_ORDER = (BrandProfileDB.is_default.desc(), BrandProfileDB.name.asc(), BrandProfileDB.id.asc())


def get_profile(db: Session, profile_id: int, brand_id: int, *, lock: bool = False) -> BrandProfileDB:
    query = db.query(BrandProfileDB).filter(
        BrandProfileDB.id == profile_id, BrandProfileDB.brand_id == brand_id)
    if lock:
        query = query.with_for_update().populate_existing()  # fresh values under the lock
    profile = query.first()
    if profile is None:
        raise ProfileNotFound(f"Brand profile {profile_id} not found")
    return profile


def clean_values(values: dict) -> dict:
    """The values as stored: declared fields only, each of its type, empty ones
    dropped. Raises `ProfileInvalid` naming every refused field at once."""
    fields = {f.name: f for f in profile_structure()}
    errors, cleaned = [], {}
    for name, value in (values or {}).items():
        field = fields.get(name)
        if field is None:
            errors.append((("field_values", name), "Not a field of this installation's brand profiles."))
            continue
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        problem, value = _check(field.type, value)
        if not problem and name == "utm_extra":
            problem = _check_param_lines(value)
        if problem:
            errors.append((("field_values", name), problem))
        else:
            cleaned[name] = value
    if errors:
        raise ProfileInvalid(errors)
    return cleaned


def _check(field_type: str, value):
    """(problem or None, the value to store)."""
    if field_type == "number":
        if isinstance(value, bool):
            return "Must be a number.", value
        if isinstance(value, (int, float)):
            return None, value
        try:
            number = float(str(value).strip())
        except ValueError:
            return "Must be a number.", value
        return None, int(number) if number.is_integer() else number
    if not isinstance(value, str):
        return "Must be text.", value
    if len(value) > TEXT_MAX:
        return f"At most {TEXT_MAX} characters.", value
    value = value.strip()
    if field_type == "colour" and not _COLOUR.fullmatch(value):
        return "A colour as #rgb or #rrggbb, for example #1a5db0.", value
    if field_type == "size" and not _SIZE.fullmatch(value):
        return "A size with its unit: px, em, rem or %, for example 16px.", value
    if field_type in ("url", "image") and not _URL.fullmatch(value):
        return "A full web address starting with https:// or http://.", value
    if field_type == "font_family" and not _FONT_FAMILY.fullmatch(value):
        return "Font names separated by commas, for example Georgia, serif.", value
    return None, value


def _check_param_lines(value: str) -> str | None:
    for line in value.splitlines():
        if line.strip() and not _PARAM_LINE.fullmatch(line.strip()):
            return "One parameter per line, written as key=value, for example ref=newsletter."
    return None


def _check_header(name: str | None, language: str | None, kind: str | None) -> list:
    errors = []
    if name is not None and not (0 < len(name.strip()) <= NAME_MAX):
        errors.append((("name",), f"A name of 1 to {NAME_MAX} characters."))
    if language is not None and not LANGUAGE.fullmatch(language):
        errors.append((("language",), "A language code such as en, de or de-AT."))
    if kind is not None and kind not in KINDS:
        errors.append((("kind",), f"One of: {', '.join(KINDS)}."))
    elif kind == TRANSACTIONAL:
        # ADR-194 addendum 2026-10-11, point 7: stored, but refused until the
        # guard that lets a transactional email go without an opt-in is built.
        errors.append((("kind",), "Transactional profiles are not available yet: sending without "
                                  "an opt-in needs its own safeguard first. Use marketing."))
    return errors


def _name_taken(db: Session, brand_id: int, name: str, except_id: int | None = None) -> bool:
    query = db.query(BrandProfileDB.id).filter(
        BrandProfileDB.brand_id == brand_id, BrandProfileDB.name == name)
    if except_id is not None:
        query = query.filter(BrandProfileDB.id != except_id)
    return query.first() is not None


def _taken(name: str) -> ProfileConflict:
    return ProfileConflict(f'This brand already has a profile called "{name}".')


def create_profile(db: Session, brand_id: int, *, name: str, language: str = "en",
                   kind: str = MARKETING, field_values: dict | None = None) -> BrandProfileDB:
    errors = _check_header(name, language, kind)
    try:
        values = clean_values(field_values or {})
    except ProfileInvalid as invalid:
        errors += invalid.errors
    if errors:
        raise ProfileInvalid(errors)
    name = name.strip()
    ensure_default_profile(db, brand_id)
    if _name_taken(db, brand_id, name):
        raise _taken(name)
    profile = BrandProfileDB(brand_id=brand_id, name=name, language=language, kind=kind,
                             is_default=False, field_values=values)
    db.add(profile)
    _commit_or_taken(db, name)
    db.refresh(profile)
    return profile


def update_profile(db: Session, profile_id: int, brand_id: int, *, name: str,
                   language: str | None = None, kind: str | None = None,
                   field_values: dict | None = None,
                   expected_updated_at: datetime | None = None) -> tuple[BrandProfileDB, list[str]]:
    """Replace the name and values; language and kind only when given.
    Returns the profile and the names of what changed, in the structure's order."""
    from app.campaigns.service import refuse_stale

    errors = _check_header(name, language, kind)
    try:
        values = clean_values(field_values or {})
    except ProfileInvalid as invalid:
        errors += invalid.errors
    if errors:
        raise ProfileInvalid(errors)
    profile = get_profile(db, profile_id, brand_id)
    refuse_stale(db, profile, expected_updated_at, "brand profile")
    name = name.strip()
    if _name_taken(db, brand_id, name, except_id=profile.id):
        raise _taken(name)

    before = dict(profile.field_values or {})
    order = [f.name for f in profile_structure()]
    changed = [key for key, new in (("name", name), ("language", language), ("kind", kind))
               if new is not None and getattr(profile, key) != new]
    changed += sorted((k for k in set(before) | set(values) if before.get(k) != values.get(k)),
                      key=lambda k: (order.index(k) if k in order else len(order), k))
    profile.name = name
    if language is not None:
        profile.language = language
    if kind is not None:
        profile.kind = kind
    profile.field_values = values
    _commit_or_taken(db, name)
    db.refresh(profile)
    return profile, changed


def duplicate_profile(db: Session, profile_id: int, brand_id: int,
                      name: str | None = None) -> BrandProfileDB:
    """A copy under a free name, never the default (ADR-194 point 1)."""
    source = get_profile(db, profile_id, brand_id)
    if name is not None:
        if errors := _check_header(name, None, None):
            raise ProfileInvalid(errors)
        name = name.strip()
        if _name_taken(db, brand_id, name):
            raise _taken(name)
    else:
        name = _free_copy_name(db, brand_id, source.name)
    copy = BrandProfileDB(brand_id=brand_id, name=name, language=source.language,
                          kind=source.kind, is_default=False,
                          field_values=dict(source.field_values or {}))
    db.add(copy)
    _commit_or_taken(db, name)
    db.refresh(copy)
    return copy


def _free_copy_name(db: Session, brand_id: int, name: str) -> str:
    for n in range(1, 1000):
        suffix = " (copy)" if n == 1 else f" (copy {n})"
        candidate = name[:NAME_MAX - len(suffix)] + suffix
        if not _name_taken(db, brand_id, candidate):
            return candidate
    raise ProfileConflict("No free name for the copy; name it yourself.")


def make_default(db: Session, profile_id: int, brand_id: int) -> BrandProfileDB:
    """Move the default mark. The brand's profiles are locked so two people
    doing this at once end with one default, not a refused second commit."""
    # `populate_existing`: a row this session read before the lock keeps its
    # old values in the identity map otherwise, so a default moved meanwhile by
    # another request would look unmoved here, and the new mark would collide
    # with it at the unique index (Codex doc-14).
    profiles = (db.query(BrandProfileDB).filter(BrandProfileDB.brand_id == brand_id)
                .order_by(BrandProfileDB.id).with_for_update().populate_existing().all())
    target = next((p for p in profiles if p.id == profile_id), None)
    if target is None:
        raise ProfileNotFound(f"Brand profile {profile_id} not found")
    for profile in profiles:
        if profile.is_default and profile.id != target.id:
            profile.is_default = False
    db.flush()               # the old mark goes before the new one, for the unique index
    target.is_default = True
    db.commit()
    db.refresh(target)
    return target


def delete_profile(db: Session, profile_id: int, brand_id: int,
                   expected_updated_at: datetime | None = None) -> int:
    """Delete a profile; the variants using it fall back to the default, each
    with a notice saying so (ADR-194 point 1). Returns how many moved."""
    from app.campaigns.db_models import VariantDB
    from app.campaigns.service import refuse_stale

    profile = get_profile(db, profile_id, brand_id)
    refuse_stale(db, profile, expected_updated_at, "brand profile")
    if profile.is_default:
        raise ProfileConflict(
            "The default profile cannot be deleted. Make another profile the default first.")
    default = ensure_default_profile(db, brand_id)
    notice = (f'Its brand profile "{profile.name}" was deleted, so it now uses the default '
              f'"{default.name}".')[:255]
    moved = (db.query(VariantDB).filter(VariantDB.brand_profile_id == profile.id)
             .update({"brand_profile_id": default.id, "brand_profile_notice": notice},
                     synchronize_session=False))
    db.delete(profile)
    db.commit()
    return moved


def _commit_or_taken(db: Session, name: str) -> None:
    """The name check above is a read; two writers can both pass it. The
    unique constraint is the real guard, and this keeps it a 409."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _taken(name)


# --- a variant's profile (ADR-194 point 4) ----------------------------------

def profile_id_for_variant(db: Session, brand_id: int, profile_id: int | None, *,
                           commit: bool = True) -> int:
    """The profile a variant in this brand will use: the one asked for, which
    must be this brand's (`ProfileNotFound` otherwise), or the default."""
    if profile_id is None:
        return ensure_default_profile(db, brand_id, commit=commit).id
    return get_profile(db, profile_id, brand_id).id


def profile_of_variant(db: Session, variant, brand_id: int) -> BrandProfileDB:
    """The profile a variant uses. NULL reads as the brand's default, and so
    does a profile of another brand, which no service writes: a variant never
    shows a look its brand does not own."""
    if variant.brand_profile_id is not None:
        profile = db.get(BrandProfileDB, variant.brand_profile_id)
        if profile is not None and profile.brand_id == brand_id:
            return profile
    return ensure_default_profile(db, brand_id)
