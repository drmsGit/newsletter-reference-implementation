"""A record's language, and translations as linked records (task-369; ADR-200).

The rules live here once, for the JSON routes: which languages a record may
have (its brand's profile languages, or none), the lock while it is linked,
making a translation, and which of its fields the original has changed since.
"""
from sqlalchemy.orm import Session

from app.content.db_models import ContentCategoryAssignmentDB, ContentRecordDB


class TranslationRefused(ValueError):
    """Refused before anything is spent, on the request field at fault."""

    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field


class TranslationExists(ValueError):
    """At most one translation per original per language (ADR-200 point 3)."""

    def __init__(self, message: str, record_id: int | None = None):
        super().__init__(message)
        self.record_id = record_id


class TranslationFailed(ValueError):
    """The model was asked and gave nothing usable; no record was made."""


def brand_languages(db: Session, brand_id: int) -> list[str]:
    """The languages a record of this brand may have: its profiles' (ADR-194 point 6)."""
    from app.brand_profiles.db_models import BrandProfileDB

    return sorted({lang for (lang,) in db.query(BrandProfileDB.language).filter(BrandProfileDB.brand_id == brand_id)})


def translations_of(db: Session, record_id: int) -> list[ContentRecordDB]:
    return (db.query(ContentRecordDB).filter(ContentRecordDB.translation_of_id == record_id)
            .order_by(ContentRecordDB.language).all())


def language_lock(db: Session, record: ContentRecordDB) -> str | None:
    """Why this record's language may not change, or None (ADR-200 point 1)."""
    if record.translation_of_id is not None:
        return "This record is a translation, so its language stays."
    if db.query(ContentRecordDB.id).filter(ContentRecordDB.translation_of_id == record.id).first():
        return "This record has translations, so its language stays. Delete them to change it."
    return None


def check_language(db: Session, record: ContentRecordDB, language: str | None) -> None:
    if language == record.language:
        return
    lock = language_lock(db, record)
    if lock:
        raise TranslationRefused("language", lock)
    if language is not None and language not in brand_languages(db, record.brand_id):
        raise TranslationRefused(
            "language", f"{language!r} is none of this brand's profile languages: "
            f"{', '.join(brand_languages(db, record.brand_id))}.")


def original_changed(db: Session, record: ContentRecordDB) -> list[str]:
    """A translation's fields whose original text changed since it was
    translated, or that the original has and the translation never took
    (ADR-200 point 5). Empty for a record that translates nothing."""
    from app.ai.tasks.content_translate import source_of

    if record.translation_of_id is None:
        return []
    original = db.get(ContentRecordDB, record.translation_of_id)
    if original is None:
        return []
    now = source_of(original)
    then = record.translated_from or {}
    return sorted(name for name in set(now) | set(then) if now.get(name) != then.get(name))


def create_translation(db: Session, original: ContentRecordDB, language: str, *,
                       actor_type: str | None, actor_id: int | None) -> tuple[ContentRecordDB, int, list[str]]:
    """Translate `original` into `language` as a new record (ADR-200 points 3-4).
    Returns (the new record, the run id, notices). Refuses before the call."""
    from app.ai.db_models import AIRunDB
    from app.ai.tasks import content_translate

    if original.translation_of_id is not None:
        raise TranslationExists("This record is a translation; translate its original instead.")
    if original.language is None:
        raise TranslationRefused("language", "Set this record's own language first.")
    if language == original.language:
        raise TranslationRefused("language", "That is this record's own language.")
    if language not in brand_languages(db, original.brand_id):
        raise TranslationRefused("language", f"{language!r} is none of this brand's profile languages.")
    existing = (db.query(ContentRecordDB).filter(ContentRecordDB.translation_of_id == original.id,
                                                 ContentRecordDB.language == language).first())
    if existing is not None:
        raise TranslationExists(f"This record already has a {language} translation: record {existing.id}.",
                                existing.id)
    source = content_translate.source_of(original)

    run = content_translate.translate(db, source=source, source_language=original.language,
                                      target_language=language, target_id=original.id,
                                      actor_type=actor_type, actor_id=actor_id)
    if not run.ok:
        raise TranslationFailed(run.message or "The translation could not be made.")
    fields, notices = content_translate.read_translation(run.text or "", source)
    if not fields:
        raise TranslationFailed("No translation could be read from the reply; nothing was created.")

    content = dict(original.content or {})
    content.update({k: v for k, v in fields.items() if k not in content_translate.RECORD_FIELDS})
    record = ContentRecordDB(
        brand_id=original.brand_id,
        title=(fields.get("title") or f"{original.title} ({language})")[:255],
        description=fields.get("description", original.description),
        content=content, status=original.status, machine_ready=False,
        language=language, translation_of_id=original.id,
        # Only what was translated counts as translated from: a field kept in
        # the original's words shows as still to translate.
        translated_from={k: v for k, v in source.items() if k in fields},
    )
    db.add(record)
    db.flush()
    for assignment in db.query(ContentCategoryAssignmentDB).filter_by(content_id=original.id):
        db.add(ContentCategoryAssignmentDB(content_id=record.id, category_id=assignment.category_id,
                                           score=assignment.score))
    # The run stays pointed at the original it read: it is not a proposal on
    # the new record, whose Translate again lists only its own runs.
    db.commit()
    db.refresh(record)
    return record, run.run_id, notices


def retranslate(db: Session, record: ContentRecordDB, *, actor_type: str | None, actor_id: int | None):
    """A fresh translation of the original, proposed on its translation (point 5)."""
    from app.ai.tasks import content_translate

    original = db.get(ContentRecordDB, record.translation_of_id) if record.translation_of_id else None
    if original is None:
        raise TranslationRefused("record", "This record translates no original.")
    return content_translate.translate(db, source=content_translate.source_of(original),
                                       source_language=original.language, target_language=record.language,
                                       target_id=record.id, actor_type=actor_type, actor_id=actor_id)


def retranslations(db: Session, record: ContentRecordDB) -> list[dict]:
    """Every fresh translation proposed on this record, newest first, in the
    content draft's shape (the same panel takes it): each field with what the
    record holds now."""
    from app.ai.db_models import AIPromptDB, AIRunDB
    from app.ai.tasks import content_translate

    labels = content_translate.field_labels()
    runs = (db.query(AIRunDB).filter(AIRunDB.task_key == content_translate.TASK_KEY,
                                     AIRunDB.target_type == "content", AIRunDB.target_id == record.id,
                                     AIRunDB.input_snapshot.isnot(None))
            .order_by(AIRunDB.created_at.desc(), AIRunDB.id.desc()).limit(25).all())
    versions = {p.id: p.version for p in db.query(AIPromptDB).filter(
        AIPromptDB.id.in_({r.prompt_id for r in runs if r.prompt_id}))}
    result = []
    for run in runs:
        fields, notices = content_translate.read_translation(run.output_text or "", run.input_snapshot or {}) \
            if run.status == "ok" else ({}, [])
        result.append({
            "run_id": run.id, "status": run.status, "created_at": run.created_at, "provider": run.provider,
            "model": run.model, "prompt_version": versions.get(run.prompt_id),
            "input_tokens": run.input_tokens or 0, "output_tokens": run.output_tokens or 0,
            "fields": [{"name": name, "text": value, "label": labels.get(name, {}).get("label", name),
                        "channel": labels.get(name, {}).get("channel"), "current": _current(record, name)}
                       for name, value in fields.items()],
            "categories": [], "notices": ([run.message] if run.status == "ok" and run.message else []) + notices,
            "reply": (run.output_text or "").strip(), "message": run.message,
        })
    return result


def _current(record: ContentRecordDB, name: str) -> str:
    from app.ai.tasks.content_translate import RECORD_FIELDS

    value = getattr(record, name, None) if name in RECORD_FIELDS else (record.content or {}).get(name)
    return value if isinstance(value, str) else ""


def record_taken(db: Session, record: ContentRecordDB, run_id: int | None, taken: list[str]) -> None:
    """A person took these fields from a translation run on this record: each
    is now translated from the original text that run read (point 5)."""
    from app.ai.db_models import AIRunDB
    from app.ai.tasks.content_translate import TASK_KEY

    if run_id is None or record.translation_of_id is None:
        return
    run = db.get(AIRunDB, run_id)
    if run is None or (run.task_key, run.target_type, run.target_id) != (TASK_KEY, "content", record.id):
        return
    snapshot = run.input_snapshot or {}
    marked = dict(record.translated_from or {})
    for name in taken:
        if name in snapshot:
            marked[name] = snapshot[name]
    # Before the PATCH answers, which re-reads the row: the version it hands
    # back is the one stored after this, so the next save is not refused.
    db.query(ContentRecordDB).filter(ContentRecordDB.id == record.id).update({"translated_from": marked})
    db.commit()
