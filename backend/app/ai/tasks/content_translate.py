"""Task: translate a content record into another language (task-369; ADR-200).

The dev-owned scaffold: what the task reads, the shape of its answer, where
it lands. The prompt is the manager's, in Settings (ADR-140 §4).

**What it reads.** The record's own text — title, description, and every text
and rich-text field it has filled, image descriptions included — never
recipient data (ADR-144 point 4). Links and images are not sent to be
translated; they are copied unchanged. What it read is kept on the run
(`input_snapshot`), so taking a field later records which original text it
was translated from (ADR-200 point 5).

**What it must keep.** Every `{{...}}` placeholder (ADR-199) and every link's
address. A field whose answer changed either keeps the original's text, and
the manager is told: a translated link that points elsewhere, or a
placeholder that became another, would be a silent change of meaning.

**Where it lands.** A first translation is written into a new record that
starts unpublished, not ready and not machine ready; a later one is a
proposal on that record, taken with ticks. No held form (ADR-140 addenda
2026-10-16 and 2026-10-17).
"""
import json
import re

from sqlalchemy.orm import Session

from app.ai.tasks.base import TaskMeta, json_object

TASK_KEY = "content_translate"

# A whole record's text, translated: room for a long body in both its forms.
MAX_OUTPUT_TOKENS = 4000

#: Fields of the record itself, translated alongside its content fields.
RECORD_FIELDS = {"title": "Title", "description": "Description"}

#: What the prompt calls a language; a code it does not know is named as is.
LANGUAGE_NAMES = {
    "de": "German", "en": "English", "fr": "French", "nl": "Dutch", "es": "Spanish", "it": "Italian",
    "pt": "Portuguese", "pl": "Polish", "da": "Danish", "sv": "Swedish", "fi": "Finnish", "cs": "Czech",
}

DEFAULT_PROMPT = """You translate one content record of a newsletter from {source_language} into {target_language}.

Translate the meaning and the tone, not word for word. Keep it as short as the
original: headlines and button texts have little room.

Keep exactly as written:
- every placeholder in double curly braces, such as {{salutation_informal}};
- every link's address, the part in round brackets after [link text];
- the **bold** markers.

Your house style:
- None set yet. Replace this line in Settings with your own rules.

Answer with one JSON object with exactly the same keys as below and the
translated texts as values, and nothing else.

The fields:
{fields}
"""

META = TaskMeta(
    key=TASK_KEY,
    label="Content translation",
    description=(
        "Translates a content record into another of the brand's languages: a new record "
        "linked to the original, unpublished until a person publishes it. When the original "
        "changes, a fresh translation is proposed field by field."
    ),
    default_prompt=DEFAULT_PROMPT,
    max_output_tokens=MAX_OUTPUT_TOKENS,
    held_form=False,
)

_PLACEHOLDER = re.compile(r"\{\{\s*[^{}]+?\s*\}\}")
_LINK_TARGET = re.compile(r"\[[^\]]*\]\(([^)]*)\)")


def language_name(code: str | None) -> str:
    return LANGUAGE_NAMES.get(code or "", code or "its own language")


def translated_field_names() -> list[str]:
    """The record's fields the model translates: every text and rich-text
    field of every channel, image descriptions included. Links and images are
    not text to translate."""
    from app.content.service import catalogue_fields

    return [f["name"] for f in catalogue_fields() if f.get("type") in ("text", "richtext")]


def field_labels() -> dict[str, dict]:
    from app.content.service import catalogue_fields

    labels = {name: {"label": label, "channel": None} for name, label in RECORD_FIELDS.items()}
    for f in catalogue_fields():
        labels[f["name"]] = {"label": f.get("label") or f["name"], "channel": f.get("channel")}
    return labels


def source_of(record) -> dict[str, str]:
    """What is translated of a record: its filled title, description and text fields."""
    source: dict[str, str] = {}
    for name in RECORD_FIELDS:
        value = getattr(record, name, None)
        if isinstance(value, str) and value.strip():
            source[name] = value
    content = record.content or {}
    for name in translated_field_names():
        value = content.get(name)
        if isinstance(value, str) and value.strip():
            source[name] = value
    return source


def build_prompt(template: str, source: dict[str, str], source_language: str, target_language: str) -> str:
    # One by one, not str.format: the placeholders in the text have braces too.
    return (template.replace("{source_language}", language_name(source_language))
            .replace("{target_language}", language_name(target_language))
            .replace("{fields}", json.dumps(source, ensure_ascii=False, indent=1)))




def _kept(original: str, translated: str) -> bool:
    """The same placeholders and the same link addresses, in any order."""
    return (sorted(_PLACEHOLDER.findall(original)) == sorted(_PLACEHOLDER.findall(translated))
            and sorted(_LINK_TARGET.findall(original)) == sorted(_LINK_TARGET.findall(translated)))


def read_translation(text: str, source: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    """The translated fields the answer gives for `source`, and what the
    manager must be told. Only keys that were sent are kept; a field whose
    placeholders or link addresses changed is left out, so it keeps the
    original's words."""
    answer = json_object(text or "") or {}
    fields: dict[str, str] = {}
    changed, missing = [], []
    for name, original in source.items():
        value = answer.get(name)
        if not isinstance(value, str) or not value.strip():
            missing.append(name)
        elif not _kept(original, value):
            changed.append(name)
        else:
            fields[name] = value.strip()
    notices = []
    if changed:
        notices.append("Kept in the original language, as a placeholder or link changed in the translation: "
                       f"{', '.join(changed)}.")
    if missing and fields:
        notices.append(f"Not translated: {', '.join(missing)}.")
    return fields, notices


def translate(db: Session, *, source: dict[str, str], source_language: str, target_language: str,
              target_id: int, actor_type: str | None = None, actor_id: int | None = None):
    """One model call. The run is pointed at `target_id` (the original for a
    first translation, the translation for a later one) and keeps `source`."""
    from app.ai.db_models import AIRunDB
    from app.ai.service import get_published_prompt, run_task

    prompt_row = get_published_prompt(db, TASK_KEY)
    template = prompt_row.body if prompt_row else DEFAULT_PROMPT
    run = run_task(
        db, task_key=TASK_KEY,
        rendered_prompt=build_prompt(template, source, source_language, target_language),
        max_output_tokens=MAX_OUTPUT_TOKENS, target_type="content", target_id=target_id,
        actor_type=actor_type, actor_id=actor_id,
    )
    if run.run_id is not None:
        db.query(AIRunDB).filter(AIRunDB.id == run.run_id).update({"input_snapshot": source})
        db.commit()
    return run
