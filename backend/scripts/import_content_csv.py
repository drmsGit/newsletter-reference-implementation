"""Import seed content records from a CSV file.

Usage:
    ./venv/bin/python scripts/import_content_csv.py <file>.csv [--dry-run]

Format: see scripts/seed_content_template.csv (a working two-row example) and
scripts/seed_content_prompt.md (the generation prompt).

Behaviour:
  - Adds content records; never deletes. Existing records are left alone.
  - Skips a row whose `title` already exists, so re-running the same file is safe.
  - Matches categories BY NAME against categories already in the database.
    An unknown category name is reported and skipped, never auto-created —
    the category set is a governed taxonomy (ADR-080), not a side effect of import.
  - A score is a whole number from 1 to 10 (`Beach:7`); a bare name means 10.
    Anything else (`Beach:15`, `Beach:abc`) skips that one assignment and is
    listed at the end, never clamped or guessed (task-278).
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth.service import ensure_default_brand
from app.database import SessionLocal  # noqa: E402
from app.content.service import content_field_groups  # noqa: E402
from app.content.db_models import (  # noqa: E402
    CategoryDB,
    ContentCategoryAssignmentDB,
    ContentRecordDB,
)

# Keys copied verbatim from the CSV into ContentRecordDB.content (the JSON blob
# the email modules read). Optional ones are omitted when the cell is empty.
#
# **Derived since 2026-09-28.** This was a hand-kept copy of the email half of
# `CONTENT_FIELD_GROUPS`, and the two could disagree — a field added to the
# catalogue was silently unimportable until somebody remembered this file.
# Both now read `storage/fields.json` (ADR-177), so a new email content field
# becomes importable by existing, which is the only way a duplicate stays
# correct: by not being one.
CONTENT_KEYS = content_field_groups()["email"]
REQUIRED_COLUMNS = {"title", "headline_medium", "body_medium", "categories"}


def read_rows(path: Path) -> tuple[list[dict], list[str]]:
    """Read the CSV, tolerating the smart quotes a chat UI produces.

    Pasting the generation prompt into a web chat and saving the answer yields
    “curly” quotes instead of straight ones, which csv.reader does not recognise
    as quoting — every row then parses as one giant field. We only rewrite them
    when the file contains no straight quotes at all, so a correctly-quoted file
    that merely mentions “something” in its prose is never touched.
    """
    raw = path.read_text(encoding="utf-8-sig")
    if '"' not in raw and ("“" in raw or "”" in raw):
        raw = raw.replace("“", '"').replace("”", '"')
        print("  (normalised smart quotes → straight quotes for parsing)")
    reader = csv.DictReader(raw.splitlines())
    return list(reader), list(reader.fieldnames or [])


def parse_categories(raw: str) -> tuple[list[tuple[str, int]], list[str]]:
    """'Hiking:10|Nature:7' -> ([('Hiking', 10), ('Nature', 7)], []).

    A bare name means 10, the documented default. A score that is not a whole
    number from 1 to 10 — '15', 'abc', '0' — is **refused, not clamped or
    guessed** (ADR-080's 2026-10-04 addendum; decided with the user 2026-10-05):
    that one assignment is left out and returned in the second list, so the
    rest of the row still imports and the import says what it skipped.
    """
    from app.content.models import SCORE_MAX, SCORE_MIN

    out: list[tuple[str, int]] = []
    refused: list[str] = []
    for part in (p.strip() for p in raw.split("|")):
        if not part:
            continue
        name, _, score = part.partition(":")
        name = name.strip()
        if not name:
            continue
        if not score.strip():
            out.append((name, 10))
            continue
        try:
            value = int(score.strip())
        except ValueError:
            refused.append(part)
            continue
        if SCORE_MIN <= value <= SCORE_MAX:
            out.append((name, value))
        else:
            refused.append(part)
    return out, refused


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    if len(args) != 1:
        print(__doc__)
        return 2

    path = Path(args[0])
    if not path.is_file():
        # Seed CSVs normally sit next to this script, so accept a bare filename
        # regardless of which directory the command was run from.
        beside_script = Path(__file__).resolve().parent / path.name
        if beside_script.is_file():
            path = beside_script
        else:
            print(f"No such file: {args[0]}")
            print(f"  also looked in: {beside_script}")
            return 2

    db = SessionLocal()
    try:
        categories = {c.name.lower(): c for c in db.query(CategoryDB).all()}
        existing_titles = {t.lower() for (t,) in db.query(ContentRecordDB.title).all()}

        rows, fieldnames = read_rows(path)
        missing = REQUIRED_COLUMNS - set(fieldnames)
        if missing:
            print(f"CSV is missing required column(s): {', '.join(sorted(missing))}")
            print(f"  found columns: {', '.join(fieldnames) or '(none)'}")
            return 1

        added = skipped = 0
        unknown_categories: set[str] = set()
        refused_scores: list[str] = []

        for line_no, row in enumerate(rows, start=2):
            title = (row.get("title") or "").strip()
            if not title:
                print(f"  line {line_no}: empty title — skipped")
                skipped += 1
                continue
            if title.lower() in existing_titles:
                print(f"  line {line_no}: '{title[:50]}' already exists — skipped")
                skipped += 1
                continue

            content = {
                key: row[key].strip()
                for key in CONTENT_KEYS
                if (row.get(key) or "").strip()
            }
            record = ContentRecordDB(
                title=title[:255],
                description=((row.get("description") or "").strip() or None),
                content=content,
                status="active",
                # The CSV has no brand column and inventing one per row would
                # be guessing. Imported content lands on the default brand; a
                # multi-brand adopter reassigns it or imports per brand, which
                # is a conversation to have when somebody actually needs it
                # rather than a column added to a file format on spec.
                brand_id=ensure_default_brand(db).id,
            )
            db.add(record)
            db.flush()  # assign record.id without committing

            assigned = []
            parsed, refused = parse_categories(row.get("categories") or "")
            refused_scores += [f"line {line_no} '{title[:40]}': {part}" for part in refused]
            for name, score in parsed:
                category = categories.get(name.lower())
                if category is None:
                    unknown_categories.add(name)
                    continue
                db.add(
                    ContentCategoryAssignmentDB(
                        content_id=record.id,
                        category_id=category.id,
                        # Already 1-10: parse_categories refuses anything else
                        # rather than clamping it (task-278).
                        score=score,
                    )
                )
                assigned.append(f"{category.name}:{score}")

            existing_titles.add(title.lower())
            added += 1
            print(f"  + {title[:60]}  [{', '.join(assigned) or 'no categories'}]")

        if refused_scores:
            print("\n  ! scores outside 1-10 or not a number (that assignment skipped, nothing guessed):")
            for entry in refused_scores:
                print(f"    {entry}")

        if unknown_categories:
            print(
                "\n  ! unknown categories (skipped, not auto-created): "
                + ", ".join(sorted(unknown_categories))
            )
            print("    Known: " + ", ".join(sorted(c.name for c in categories.values())))

        if dry_run:
            db.rollback()
            print(f"\nDRY RUN — nothing written. Would add {added}, skip {skipped}.")
        else:
            db.commit()
            print(f"\nDone. Added {added}, skipped {skipped}.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
