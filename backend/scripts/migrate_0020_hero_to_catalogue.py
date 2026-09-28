"""ADR-179: `hero` becomes a catalogue-bound module.

Run from `backend/`:  venv/bin/python scripts/migrate_0020_hero_to_catalogue.py [--apply]

**Python rather than SQL**, unlike every migration beside it, because the work
is not a schema change: it reads a JSON column, invents no values, and creates
rows in another table. A `.sql` file would have had to build a content record
out of `module_data ->> 'headline'` in a string, which is the kind of thing that
is right once and unreviewable afterwards.

**Three cases, and only one of them is a migration.**

1. **`module_data` with a headline.** A content record is created carrying
   `headline_hero`, and the module is bound to it. Nothing is invented: the
   title comes from the headline and the brand from module → variant →
   campaign. Any `text` is preserved by planting an `editorial` module beside
   the hero, because ADR-179 moved body copy out of the hero and losing it
   would be the migration deciding the copy did not matter.

2. **Already bound to a content record.** Left alone and **reported**. Those
   records carry the catalogue's medium-size fields and no `headline_hero`, so
   after the flip the hero renders empty — and the required-field check
   (ADR-174 point 3) reports `hero.headline_hero`. Note the order: if the
   record also has no published version, `UnpublishedContentError` is raised
   first and the required-field check hands that to the snapshot gate, so the
   send is refused for publication before it is refused for the headline. Both
   refuse; only the second names the field. Copying
   `headline_medium` across was considered and rejected: a hero headline sits
   over a background image and must be short, a medium one need not be, so the
   guess would ship a headline that does not fit and nobody would be told. A
   refused send is the louder, correcter outcome.

3. **Neither.** Nothing to do. An unbound cms module resolves to no content,
   which ADR-086 hides and the required-field check correctly ignores.

Idempotent: a hero already carrying `headline_hero` is skipped, so a re-run
after a partial apply finishes the job rather than duplicating it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.campaigns.db_models import (  # noqa: E402
    CampaignDB, ModuleInstanceDB, VariantDB,
)
# Imported for its side effect: `content_records.brand_id` points at
# `brands`, and SQLAlchemy resolves that at flush time, not at import.
# Without this the dry run passes — it never flushes — and `--apply`
# dies with NoReferencedTableError.
from app.auth import db_models as _brand_models  # noqa: E402,F401
from app.content.db_models import ContentRecordDB  # noqa: E402
from app.database import SessionLocal  # noqa: E402

APPLY = "--apply" in sys.argv


def main() -> int:
    db = SessionLocal()
    created = bound = planted = 0
    needs_a_headline: list[tuple[int, int]] = []
    try:
        heroes = (
            db.query(ModuleInstanceDB)
            .filter(ModuleInstanceDB.module_type == "hero")
            .order_by(ModuleInstanceDB.id)
            .all()
        )
        print(f"{len(heroes)} hero module instance(s)\n")

        for module in heroes:
            variant = db.query(VariantDB).filter(
                VariantDB.id == module.variant_id).first()
            campaign = db.query(CampaignDB).filter(
                CampaignDB.id == variant.campaign_id).first() if variant else None
            if campaign is None:
                print(f"  module {module.id}: orphaned, skipped")
                continue

            if module.content_record_id is not None:
                record = db.query(ContentRecordDB).filter(
                    ContentRecordDB.id == module.content_record_id).first()
                if record and not (record.content or {}).get("headline_hero"):
                    needs_a_headline.append((module.id, record.id))
                continue

            data = module.module_data or {}
            headline = (data.get("headline") or "").strip()
            if not headline:
                print(f"  module {module.id}: nothing to migrate")
                continue

            title = headline[:255]
            if APPLY:
                record = ContentRecordDB(
                    brand_id=campaign.brand_id,
                    title=title,
                    description="Migrated from a hero module's module_data (0020).",
                    content={"headline_hero": headline},
                )
                db.add(record)
                db.flush()
                module.content_record_id = record.id
                module.module_data = None
            created += 1
            bound += 1
            print(f"  module {module.id}: -> content record "
                  f"{'#' + str(record.id) if APPLY else '(dry run)'} "
                  f"title={title!r}")

            body = (data.get("text") or "").strip()
            if body:
                if APPLY:
                    used = {p for (p,) in db.query(ModuleInstanceDB.position)
                            .filter(ModuleInstanceDB.variant_id == module.variant_id)}
                    db.add(ModuleInstanceDB(
                        variant_id=module.variant_id,
                        module_type="editorial",
                        position=max(used) + 1,
                        module_data={"text": body},
                    ))
                planted += 1
                print(f"      + editorial module carrying its text "
                      f"({len(body)} chars) — hero no longer has a body")

        if needs_a_headline:
            print(f"\n  {len(needs_a_headline)} hero(es) bound to a record with "
                  "no headline_hero. NOT guessed — see this file's docstring.")
            for module_id, record_id in needs_a_headline:
                print(f"      module {module_id} -> content record {record_id}")
            print("      The send is refused until somebody writes one — by the")
            print("      publication gate first if the record is unpublished, and")
            print("      by name once it is not.")

        if APPLY:
            db.commit()
            print(f"\nAPPLIED: {created} record(s), {bound} binding(s), "
                  f"{planted} editorial module(s).")
        else:
            db.rollback()
            print(f"\nDRY RUN: would create {created}, bind {bound}, "
                  f"plant {planted}. Re-run with --apply.")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
