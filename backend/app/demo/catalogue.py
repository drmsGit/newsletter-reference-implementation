"""The Grathaus category tree, and the catalogue read from the external
model's CSVs and the generated images (task-71).

Everything read is checked the way the importer checks it: an unknown
category, brand, language or image key is reported and skipped, never
guessed or created (ADR-080: the vocabulary is governed).
"""
import csv
import io
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

#: (name, type, parents). A sub with two parents shows as two links in the
#: category graph (approved 2026-10-17).
TREE = [
    ("Wandern", "main", []),
    ("Klettern", "main", []),
    ("Wintersport", "main", []),
    ("Radfahren", "main", []),
    ("Camping & Trekking", "main", []),
    ("Familie & Kinder", "main", []),
    ("Naturerlebnis", "main", []),
    ("Sicherheit & Wissen", "main", []),
    ("Nachhaltigkeit", "main", []),
    ("Tagestouren", "sub", ["Wandern"]),
    ("Hüttentouren", "sub", ["Wandern"]),
    ("Weitwandern", "sub", ["Wandern"]),
    ("Klettersteige", "sub", ["Wandern", "Klettern"]),
    ("Familienwandern", "sub", ["Wandern", "Familie & Kinder"]),
    ("Halle & Bouldern", "sub", ["Klettern"]),
    ("Alpinklettern", "sub", ["Klettern"]),
    ("Skitouren", "sub", ["Wintersport"]),
    ("Schneeschuh", "sub", ["Wintersport"]),
    ("Langlauf", "sub", ["Wintersport"]),
    ("Lawinenkunde", "sub", ["Wintersport", "Sicherheit & Wissen"]),
    ("Gravel & Trekking", "sub", ["Radfahren"]),
    ("Mountainbike", "sub", ["Radfahren"]),
    ("Biwak", "sub", ["Camping & Trekking"]),
    ("Tierbeobachtung", "sub", ["Naturerlebnis"]),
    ("Erste Hilfe", "sub", ["Sicherheit & Wissen"]),
    ("Reparieren & Second Hand", "sub", ["Nachhaltigkeit"]),
]

#: The image keys the prompt offers (seed_content_prompt.md).
IMAGE_KEYS = (
    "wanderweg_herbst", "huette_morgen", "gipfelkreuz_nebel", "weitwanderweg_wiese", "rucksack_packen",
    "wanderschuhe_pfad", "klettersteig_leiter", "familie_bachlauf", "kletterhalle_griffe", "boulderblock_matte",
    "alpinwand_seil", "karabiner_gurt", "skitour_aufstieg", "schneeschuh_spur", "langlauf_loipe",
    "lawinensuche_lvs", "winterhuette_licht", "gravel_feldweg", "mtb_singletrail", "radtaschen_bruecke",
    "zelt_see_abend", "biwak_sterne", "kocher_tasse", "kinder_wald", "picknick_alm", "hirsch_lichtung",
    "murmeltier_fels", "vogel_fernglas", "erstehilfe_set", "karte_kompass", "reparatur_werkbank",
    "secondhand_regal", "laden_innenraum", "vortrag_abend", "testtag_parkplatz", "fuehrung_gruppe",
    "kurs_knoten", "huettenabend_tisch", "gletscher_seilschaft", "herbstlaub_bank",
)

BRANDS = ("outdoor", "touren")
LANGUAGES = ("de", "en")
COLUMNS = ("brand", "language", "title", "description", "headline_hero", "button_label_hero", "headline_medium",
           "body_medium", "body_long", "button_label", "button_url", "image", "image_alt", "push_title",
           "push_body", "categories")
#: The record's content fields the CSV fills (the rest are the record's own or keys).
CONTENT_COLUMNS = ("headline_hero", "button_label_hero", "headline_medium", "body_medium", "body_long",
                   "button_label", "button_url", "image_alt", "push_title", "push_body")


@dataclass
class Row:
    brand: str
    language: str
    title: str
    description: str
    content: dict
    image: str | None
    image_alt: str
    scores: dict[str, int]
    source: str


@dataclass
class Read:
    rows: list[Row] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def _text(raw: str) -> str:
    """As the importer reads a chat answer: smart quotes become straight ones
    when the file has no straight ones at all."""
    if '"' not in raw and ("“" in raw or "”" in raw):
        raw = raw.replace("“", '"').replace("”", '"')
    return raw.lstrip("﻿")


def parse_scores(raw: str, where: str, problems: list[str]) -> dict[str, int]:
    known = {name for name, _type, _parents in TREE}
    scores: dict[str, int] = {}
    for part in (raw or "").split("|"):
        part = part.strip()
        if not part:
            continue
        name, _, score = part.rpartition(":") if ":" in part else (part, "", "10")
        name = name.strip()
        if name not in known:
            problems.append(f"{where}: unknown category {name!r}, skipped")
            continue
        if not score.strip().isdigit() or not 1 <= int(score) <= 10:
            problems.append(f"{where}: {name}:{score} is not a score from 1 to 10, skipped")
            continue
        scores[name] = int(score)
    return scores


def read_csv(path: Path) -> Read:
    """One batch file: rows that pass, and what was wrong with the rest."""
    read = Read()
    reader = csv.DictReader(io.StringIO(_text(path.read_text(encoding="utf-8"))))
    missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
    if missing:
        read.problems.append(f"{path.name}: missing columns {', '.join(missing)}; file skipped")
        return read
    for number, raw in enumerate(reader, start=2):
        where = f"{path.name}:{number}"
        values = {k: (raw.get(k) or "").strip() for k in COLUMNS}
        if values["brand"] not in BRANDS:
            read.problems.append(f"{where}: unknown brand {values['brand']!r}, row skipped")
            continue
        if values["language"] not in LANGUAGES:
            read.problems.append(f"{where}: unknown language {values['language']!r}, row skipped")
            continue
        if not values["title"] or not values["headline_medium"]:
            read.problems.append(f"{where}: no title or headline, row skipped")
            continue
        image = values["image"] or None
        if image is not None and image not in IMAGE_KEYS:
            read.problems.append(f"{where}: unknown image key {image!r}, the record has no image")
            image = None
        scores = parse_scores(values["categories"], where, read.problems)
        if not scores:
            read.problems.append(f"{where}: no usable category, row skipped")
            continue
        content = {k: values[k] for k in CONTENT_COLUMNS if values[k]}
        read.rows.append(Row(brand=values["brand"], language=values["language"], title=values["title"][:255],
                             description=values["description"][:500], content=content, image=image,
                             image_alt=values["image_alt"], scores=scores, source=where))
    return read


def read_all(content_dir: Path) -> Read:
    """Every batch-*.csv, in name order. The English rows go last, so their
    originals exist when they are linked."""
    out = Read()
    # Any name ending in batch-<N>.csv (a chat download may prefix it), then English.
    for path in sorted(content_dir.glob("*batch-*.csv")) + sorted(content_dir.glob("*english*.csv")):
        one = read_csv(path)
        out.rows += one.rows
        out.problems += one.problems
    seen: set[tuple[str, str]] = set()
    unique = []
    for row in out.rows:
        if (row.brand, row.title) in seen:
            out.problems.append(f"{row.source}: the title {row.title!r} appears twice, the second is skipped")
            continue
        seen.add((row.brand, row.title))
        unique.append(row)
    out.rows = unique
    return out


def create_tree(db: Session) -> dict[str, int]:
    """The categories and their links; {name: id}."""
    from app.content.db_models import CategoryDB, CategoryRelationDB

    ids = {}
    for name, ctype, _parents in TREE:
        category = CategoryDB(name=name, type=ctype)
        db.add(category)
        db.flush()
        ids[name] = category.id
    for name, _ctype, parents in TREE:
        for parent in parents:
            db.add(CategoryRelationDB(parent_category_id=ids[parent], child_category_id=ids[name],
                                      relation_type="parent_child"))
    db.commit()
    return ids


def upload_images(db: Session, images_dir: Path, brand_ids: dict[str, int], alts: dict[str, str],
                  problems: list[str]) -> dict[tuple[str, str], int]:
    """Each image found, into each brand's library (ADR-197); {(brand, key): asset id}.
    A key without a file is reported; the records using it get no image."""
    from app.assets.service import AssetRefused, upload

    found = {}
    for key in IMAGE_KEYS:
        path = next((p for p in (images_dir / f"{key}.jpg", images_dir / f"{key}.jpeg", images_dir / f"{key}.png")
                     if p.is_file()), None)
        if path is None:
            problems.append(f"image {key}: no file in {images_dir}")
            continue
        data = path.read_bytes()
        for brand, brand_id in brand_ids.items():
            try:
                asset = upload(db, brand_id=brand_id, data=data, label=key.replace("_", " "),
                               alt_text=alts.get(key, ""))
            except AssetRefused as error:
                problems.append(f"image {key}: {error}")
                break
            found[(brand, key)] = asset.id
    return found


def create_records(db: Session, rows: list[Row], brand_ids: dict[str, int], category_ids: dict[str, int],
                   assets: dict[tuple[str, str], int]) -> dict[str, list[int]]:
    """Each row as a published record, ready for email (and push when it has
    push text) and machine ready, with its categories; an English row linked
    to the German record of the same brand and link (ADR-200). {brand: ids}."""
    from app.ai.tasks.content_translate import source_of
    from app.content.db_models import ContentCategoryAssignmentDB, ContentRecordDB
    from app.content.service import create_content_version, mark_ready

    made: dict[str, list[int]] = {b: [] for b in BRANDS}
    german_by_url: dict[tuple[str, str], ContentRecordDB] = {}
    for row in rows:
        brand_id = brand_ids[row.brand]
        content = dict(row.content)
        asset = assets.get((row.brand, row.image)) if row.image else None
        if asset is not None:
            content["image_url"] = f"asset:{asset}"
            if content.get("push_title"):
                content["push_image_url"] = f"asset:{asset}"
        if content.get("push_title") and content.get("button_url"):
            content["push_link"] = content["button_url"]
        original = german_by_url.get((row.brand, content.get("button_url", ""))) if row.language == "en" else None
        record = ContentRecordDB(brand_id=brand_id, title=row.title, description=row.description or None,
                                 content=content, status="active", machine_ready=True,
                                 language=row.language)
        if original is not None:
            record.translation_of_id = original.id
            record.translated_from = source_of(original)
        db.add(record)
        db.flush()
        for name, score in row.scores.items():
            db.add(ContentCategoryAssignmentDB(content_id=record.id, category_id=category_ids[name], score=score))
        db.commit()
        create_content_version(db, content_record_id=record.id, created_by="demo", brand_id=brand_id)
        mark_ready(db, record.id, "email", marked_by="demo", brand_id=brand_id)
        if content.get("push_title") and content.get("push_body"):
            mark_ready(db, record.id, "push", marked_by="demo", brand_id=brand_id)
        if row.language == "de" and content.get("button_url"):
            german_by_url[(row.brand, content["button_url"])] = record
        made[row.brand].append(record.id)
    return made
