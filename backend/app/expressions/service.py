"""A brand's expression dictionary (task-365, ADR-199).

One dictionary per brand. The starters from `storage/expressions.json` are
copied in the first time the dictionary is used — read in Settings or the
Personalise picker, or a text is checked against it — and the brand owns them
from then on. An entry's name is fixed once it exists; label and cases change.
An entry still used by a text is not deleted.
"""
from datetime import datetime, timezone

from sqlalchemy import Text, cast
from sqlalchemy.orm import Session

from app.auth.db_models import BrandDB
from app.campaigns.service import refuse_stale
from app.expressions.db_models import ExpressionEntryDB
from app.expressions.rules import EntryInvalid, check_entry
from app.expressions.starters import starters


class EntryNotFound(LookupError):
    pass


class EntryConflict(ValueError):
    """The name is taken, or the entry is still used."""


def entries_of(db: Session, brand_id: int, *, start: bool = True) -> list[ExpressionEntryDB]:
    """The brand's entries by label. `start` copies the starters in on first
    use; rendering passes False, so a send never writes."""
    if start:
        _start(db, brand_id)
    return (db.query(ExpressionEntryDB).filter(ExpressionEntryDB.brand_id == brand_id)
            .order_by(ExpressionEntryDB.label, ExpressionEntryDB.id).all())


def by_name(db: Session, brand_id: int, *, start: bool = True) -> dict[str, ExpressionEntryDB]:
    return {entry.name: entry for entry in entries_of(db, brand_id, start=start)}


def _start(db: Session, brand_id: int) -> None:
    """Copy the starters in, once per brand. In a session of its own, so the
    caller's transaction is neither committed nor rolled back by it; the brand
    row is locked, so two first uses at once copy them once."""
    started = db.query(BrandDB.expressions_started_at).filter(BrandDB.id == brand_id).scalar()
    if started is not None:
        return
    from app.database import SessionLocal

    own = SessionLocal()
    try:
        brand = own.query(BrandDB).filter(BrandDB.id == brand_id).with_for_update().one_or_none()
        if brand is None or brand.expressions_started_at is not None:
            return
        taken = {name for (name,) in own.query(ExpressionEntryDB.name)
                 .filter(ExpressionEntryDB.brand_id == brand_id)}
        for name, entry in starters().items():
            if name not in taken:
                own.add(ExpressionEntryDB(brand_id=brand_id, name=name, label=entry["label"],
                                          languages=entry["languages"]))
        brand.expressions_started_at = datetime.now(timezone.utc)
        own.commit()
    finally:
        own.close()


def get_entry(db: Session, entry_id: int, brand_id: int) -> ExpressionEntryDB:
    entry = db.get(ExpressionEntryDB, entry_id)
    if entry is None or entry.brand_id != brand_id:
        raise EntryNotFound(f"Entry {entry_id} is not in this brand's dictionary.")
    return entry


def create_entry(db: Session, brand_id: int, *, name: str, label: str, languages: dict) -> ExpressionEntryDB:
    check_entry(name, label, languages)
    if name in by_name(db, brand_id):
        raise EntryConflict(f"This brand already has an entry {{{{{name}}}}}.")
    entry = ExpressionEntryDB(brand_id=brand_id, name=name, label=label.strip(), languages=languages)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def update_entry(db: Session, entry_id: int, brand_id: int, *, label: str, languages: dict,
                 expected_updated_at: datetime | None = None) -> tuple[ExpressionEntryDB, list[str]]:
    """Label and cases; the name stays (decided with the user 2026-10-16)."""
    entry = get_entry(db, entry_id, brand_id)
    refuse_stale(db, entry, expected_updated_at, "entry")
    check_entry(entry.name, label, languages, name_given=False)
    changed = [part for part, new, old in (("label", label.strip(), entry.label),
                                           ("languages", languages, entry.languages)) if new != old]
    entry.label, entry.languages = label.strip(), languages
    db.commit()
    db.refresh(entry)
    return entry, changed


def delete_entry(db: Session, entry_id: int, brand_id: int, *,
                 expected_updated_at: datetime | None = None) -> str:
    """Refused while a text uses it, naming where (decided with the user
    2026-10-16). A planned send is unaffected: its frame froze the entry."""
    entry = get_entry(db, entry_id, brand_id)
    refuse_stale(db, entry, expected_updated_at, "entry")
    places = where_used(db, brand_id, entry.name)
    if places:
        shown = "; ".join(places[:5]) + (f"; and {len(places) - 5} more" if len(places) > 5 else "")
        raise EntryConflict(f"{{{{{entry.name}}}}} is still used, so it is not deleted: {shown}.")
    name = entry.name
    db.delete(entry)
    db.commit()
    return name


def where_used(db: Session, brand_id: int, name: str) -> list[str]:
    """Every text of the brand that uses {{name}}: module fields (the envelope
    included), content records, and overrides."""
    from app.campaigns.db_models import CampaignDB, ModuleInstanceDB, VariantDB
    from app.content.db_models import ContentRecordDB
    from app.overrides.db_models import ContentOverrideDB

    pattern = r"\{\{\s*" + name + r"\s*\}\}"
    places = []
    modules = (db.query(CampaignDB.name, VariantDB.name)
               .join(VariantDB, VariantDB.campaign_id == CampaignDB.id)
               .join(ModuleInstanceDB, ModuleInstanceDB.variant_id == VariantDB.id)
               .filter(CampaignDB.brand_id == brand_id, cast(ModuleInstanceDB.module_data, Text).op("~")(pattern))
               .distinct().all())
    places += [f"campaign “{campaign}”, {variant}" for campaign, variant in modules]
    records = (db.query(ContentRecordDB.title)
               .filter(ContentRecordDB.brand_id == brand_id, cast(ContentRecordDB.content, Text).op("~")(pattern))
               .all())
    places += [f"content record “{title}”" for (title,) in records]
    overridden = (db.query(CampaignDB.name, VariantDB.name)
                  .join(VariantDB, VariantDB.campaign_id == CampaignDB.id)
                  .join(ModuleInstanceDB, ModuleInstanceDB.variant_id == VariantDB.id)
                  .join(ContentOverrideDB, ContentOverrideDB.module_instance_id == ModuleInstanceDB.id)
                  .filter(CampaignDB.brand_id == brand_id,
                          cast(ContentOverrideDB.field_overrides, Text).op("~")(pattern))
                  .distinct().all())
    places += [f"an override in campaign “{campaign}”, {variant}" for campaign, variant in overridden]
    return places


__all__ = ["EntryConflict", "EntryInvalid", "EntryNotFound", "by_name", "create_entry", "delete_entry",
           "entries_of", "get_entry", "update_entry", "where_used"]
