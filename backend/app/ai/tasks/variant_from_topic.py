"""Task: prepare a variant from a topic (task-370; ADR-141 addendum 2026-10-17).

The dev-owned scaffold. **The stack's shape is the scaffold's, not the
model's**, so the look stays the brand's: a hero bound to a record, an
editorial block whose text the model writes, two to four records in
alternating image-left and image-right blocks, and — when the model judges a
reader-chosen block fits — one block drawing from a decision slot limited to
the categories it names, showing up to three picks. Plus subject and
preheader.

**What the model may choose from** is exactly what a slot may take
(`decision.strategies.base.takeable`): published, ready for email, machine
ready, in the variant's language or none — the newest `OFFER_LIMIT`, each
with the blocks it can fill. What it was offered is kept on the run, so the
proposal is checked against that offer when read back and when built. The
topic the manager typed is sent and not kept.

**Where it lands.** Nowhere by itself: a person reviews the proposal and
builds the ticked parts into the empty variant. No held form (ADR-140
addendum 2026-10-16).
"""
import json

from sqlalchemy.orm import Session

from app.ai.tasks.base import TaskMeta, json_object

TASK_KEY = "variant_from_topic"

MAX_OUTPUT_TOKENS = 1500

#: How many of the newest takeable records the model sees (the panel says so).
OFFER_LIMIT = 60

MAX_TOPIC_CHARS = 500

#: The blocks, by role. The image blocks alternate; the slot's block continues it.
HERO, EDITORIAL, IMAGE_BLOCKS = "hero", "editorial", ("img_left", "img_right")
MIN_BLOCKS, MAX_BLOCKS = 2, 4
SLOT_PICKS = 3

DEFAULT_PROMPT = """You prepare one edition of an email newsletter about a topic, from the content records below.

The edition always has this shape:
1. a hero: one record from those marked "hero";
2. an editorial: two to four sentences you write for this edition, introducing the topic and what follows, in {language}. You may use **bold**; no links, no placeholders;
3. two to four more records, each from those marked "image block", none used twice;
4. optionally, when one block chosen per reader fits better than another fixed record: a slot, given as category names from the list below that fit the topic;
and a subject line (at most 60 characters) and a preheader (at most 90 characters), in {language}.

Choose only records listed here. For each record you choose, give one short reason.

Your house style:
- None set yet. Replace this line in Settings with your own rules.

Answer with one JSON object and nothing else, in this shape:
{"hero": {"record_id": 1, "reason": "why"}, "editorial": "text", "blocks": [{"record_id": 2, "reason": "why"}], "slot": {"categories": ["Name"], "reason": "why"}, "subject": "text", "preheader": "text"}
Leave "slot" as null when there should be none.

The topic:
{topic}

The records (newest first):
{records}

The categories:
{categories}
"""

META = TaskMeta(
    key=TASK_KEY,
    label="Variant from a topic",
    description=(
        "Proposes an empty email variant's stack from a topic: a hero, an editorial text, two to four "
        "records and optionally a slot, from content a machine may take, plus subject and preheader. "
        "A person reviews it and builds what they tick."
    ),
    default_prompt=DEFAULT_PROMPT,
    max_output_tokens=MAX_OUTPUT_TOKENS,
    held_form=False,
)


class ProposalRefused(ValueError):
    """Refused before the call. `field` set: on that request field (422); else the variant's state (409)."""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field


def content_blocks(db: Session, variant) -> list:
    """The variant's modules that are content: not its envelope, not decorative
    (the visible header and footer) — the frame's own rule for "meaningful"."""
    from app.campaigns.db_models import ModuleInstanceDB
    from app.modules.registry import envelope_module_type, get_manifest

    envelope = envelope_module_type(variant.channel)
    rows = db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant.id).all()
    return [m for m in rows if m.module_type != envelope
            and not ((manifest := get_manifest(variant.channel, m.module_type)) and manifest.decorative)]


def _needed(block: str) -> list[str]:
    from app.content.service import fields_a_record_must_fill
    from app.modules.registry import get_manifest

    return fields_a_record_must_fill(get_manifest("email", block))


def offer(db: Session, variant, brand_id: int, only: list[int] | None = None) -> dict[str, list[str]]:
    """{record id: the roles it can fill} for the newest takeable records:
    "hero", "image" or both. A record filling neither is not offered. With
    `only`, those records as they stand now, however old (the build's recheck)."""
    from app.content.db_models import ContentRecordDB, ContentVersionDB
    from app.decision.strategies.base import takeable
    from app.expressions.substitute import message_language

    language = message_language(db, variant)[1]
    query = (db.query(ContentRecordDB)
             .filter(*takeable(db, brand_id=brand_id, channel="email", language=language))
             .order_by(ContentRecordDB.id.desc()))
    records = query.filter(ContentRecordDB.id.in_(only)).all() if only is not None else query.limit(OFFER_LIMIT).all()
    needs = {"hero": _needed(HERO), "image": _needed(IMAGE_BLOCKS[0])}
    offered: dict[str, list[str]] = {}
    for record in records:
        latest = (db.query(ContentVersionDB.content).filter(ContentVersionDB.content_record_id == record.id)
                  .order_by(ContentVersionDB.version_number.desc()).first())
        content = (latest[0] if latest else None) or {}
        roles = [role for role, fields in needs.items()
                 if all(isinstance(content.get(f), str) and content[f].strip() for f in fields)]
        if roles:
            offered[str(record.id)] = roles
    return offered


def _categories_of(db: Session, record_ids: list[int]) -> dict[int, list[str]]:
    from app.content.db_models import CategoryDB, ContentCategoryAssignmentDB

    names: dict[int, list[str]] = {}
    for content_id, name in (db.query(ContentCategoryAssignmentDB.content_id, CategoryDB.name)
                             .join(CategoryDB, CategoryDB.id == ContentCategoryAssignmentDB.category_id)
                             .filter(ContentCategoryAssignmentDB.content_id.in_(record_ids))
                             .order_by(CategoryDB.name)):
        names.setdefault(content_id, []).append(name)
    return names


def build_prompt(db: Session, template: str, topic: str, offered: dict[str, list[str]], language: str) -> str:
    from app.ai.tasks.content_translate import language_name
    from app.content.db_models import ContentRecordDB
    from app.content.service import list_categories

    ids = [int(i) for i in offered]
    records = {r.id: r for r in db.query(ContentRecordDB).filter(ContentRecordDB.id.in_(ids))}
    categories = _categories_of(db, ids)
    lines = []
    for record_id in ids:
        r = records[record_id]
        can = " and ".join("image block" if role == "image" else role for role in offered[str(record_id)])
        about = f" — {r.description}" if r.description else ""
        cats = ", ".join(categories.get(record_id, [])) or "none"
        lines.append(f"- id {record_id}: {r.title}{about} [categories: {cats}] (can be: {can})")
    vocabulary = "\n".join(f"- {c.name}" for c in sorted(list_categories(db), key=lambda c: c.name))
    # One by one, not str.format: the JSON example has braces of its own.
    return (template.replace("{language}", language_name(language)).replace("{topic}", topic)
            .replace("{records}", "\n".join(lines)).replace("{categories}", vocabulary or "(none)"))




def _record_id(item) -> int | None:
    if not isinstance(item, dict):
        return None
    value = item.get("record_id")
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value)
    return None


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def read_proposal(db: Session, text: str, offered: dict[str, list[str]]) -> dict:
    """The answer, kept to the offer and the shape; what is dropped is said."""
    from app.content.db_models import ContentRecordDB
    from app.content.service import list_categories

    answer = json_object(text or "") or {}
    titles = {r.id: r.title for r in db.query(ContentRecordDB).filter(
        ContentRecordDB.id.in_([int(i) for i in offered]))}
    notices: list[str] = []
    used: set[int] = set()
    not_offered, doubled = [], []

    def take(item, role: str):
        record_id = _record_id(item)
        if record_id is None:
            return None
        if str(record_id) not in offered:
            not_offered.append(str(record_id))
            return None
        if record_id in used:
            doubled.append(titles.get(record_id, str(record_id)))
            return None
        if role not in offered[str(record_id)]:
            notices.append(f"Left out: {titles.get(record_id, record_id)} cannot fill "
                           f"{'a hero' if role == 'hero' else 'an image block'}.")
            return None
        used.add(record_id)
        return {"record_id": record_id, "title": titles.get(record_id, ""), "reason": _text(item.get("reason"))}

    hero = take(answer.get("hero"), "hero")
    blocks = []
    for item in answer.get("blocks") if isinstance(answer.get("blocks"), list) else []:
        taken = take(item, "image")
        if taken and len(blocks) < MAX_BLOCKS:
            blocks.append(taken)

    slot = None
    raw_slot = answer.get("slot")
    if isinstance(raw_slot, dict) and isinstance(raw_slot.get("categories"), list):
        vocabulary = {c.name.casefold(): c for c in list_categories(db)}
        chosen, invented = [], []
        for name in raw_slot["categories"]:
            category = vocabulary.get(name.strip().casefold()) if isinstance(name, str) else None
            if category is None:
                invented.append(str(name))
            elif category.id not in [c.id for c in chosen]:
                chosen.append(category)
        if invented:
            notices.append(f"Not in the category list, so left out: {', '.join(invented)}.")
        if chosen:
            slot = {"category_ids": [c.id for c in chosen], "categories": [c.name for c in chosen],
                    "reason": _text(raw_slot.get("reason"))}

    if not_offered:
        notices.append(f"Not offered, so left out: record {', '.join(not_offered)}.")
    if doubled:
        notices.append(f"Used more than once, so left out: {', '.join(doubled)}.")
    if len(blocks) < MIN_BLOCKS and answer:
        notices.append(f"Only {len(blocks)} image block{'' if len(blocks) == 1 else 's'} came back usable; "
                       f"the shape asks for {MIN_BLOCKS} to {MAX_BLOCKS}.")
    return {"hero": hero, "editorial": _text(answer.get("editorial")), "blocks": blocks, "slot": slot,
            "subject": _text(answer.get("subject")), "preheader": _text(answer.get("preheader")),
            "notices": notices}


def check(db: Session, variant) -> None:
    if variant.channel != "email":
        raise ProposalRefused("A variant is prepared from a topic for email only.")
    if content_blocks(db, variant):
        raise ProposalRefused("This variant already has content blocks; it is prepared from a topic only while empty.")


def propose(db: Session, variant, topic: str, *, brand_id: int, actor_type=None, actor_id=None):
    """Refuse before the call, or run it. The offer is kept on the run; the topic is not."""
    from app.ai.db_models import AIRunDB
    from app.ai.service import get_published_prompt, run_task
    from app.expressions.substitute import message_language

    if not topic.strip():
        raise ProposalRefused("Name the topic.", "topic")
    if len(topic) > MAX_TOPIC_CHARS:
        raise ProposalRefused(f"The topic is {len(topic)} characters; at most {MAX_TOPIC_CHARS}.", "topic")
    check(db, variant)
    offered = offer(db, variant, brand_id)
    if not any("hero" in roles for roles in offered.values()) or \
            sum("image" in roles for roles in offered.values()) < MIN_BLOCKS:
        raise ProposalRefused(
            "There is not enough content a machine may take to prepare an edition: it needs a record "
            f"that can fill a hero and {MIN_BLOCKS} for image blocks — published, ready for email and "
            "machine ready, in this variant's language or none.")
    prompt_row = get_published_prompt(db, TASK_KEY)
    template = prompt_row.body if prompt_row else DEFAULT_PROMPT
    run = run_task(
        db, task_key=TASK_KEY,
        rendered_prompt=build_prompt(db, template, topic.strip(), offered, message_language(db, variant)[1]),
        max_output_tokens=MAX_OUTPUT_TOKENS, target_type="variant", target_id=variant.id,
        actor_type=actor_type, actor_id=actor_id,
    )
    if run.run_id is not None:
        db.query(AIRunDB).filter(AIRunDB.id == run.run_id).update({"input_snapshot": {"offered": offered}})
        db.commit()
    return run


def proposals_for_variant(db: Session, variant) -> list[dict]:
    from app.ai.db_models import AIPromptDB, AIRunDB

    from app.ai.service import RUNNING

    # A running run is no result yet (ADR-144 addendum 2026-10-17).
    runs = (db.query(AIRunDB).filter(AIRunDB.task_key == TASK_KEY, AIRunDB.target_type == "variant",
                                     AIRunDB.target_id == variant.id, AIRunDB.status != RUNNING)
            .order_by(AIRunDB.created_at.desc(), AIRunDB.id.desc()).limit(25).all())
    versions = {p.id: p.version for p in db.query(AIPromptDB).filter(
        AIPromptDB.id.in_({r.prompt_id for r in runs if r.prompt_id}))}
    result = []
    for run in runs:
        offered = (run.input_snapshot or {}).get("offered", {})
        proposal = read_proposal(db, run.output_text or "", offered) if run.status == "ok" else \
            {"hero": None, "editorial": "", "blocks": [], "slot": None, "subject": "", "preheader": "", "notices": []}
        result.append({
            "run_id": run.id, "status": run.status, "created_at": run.created_at, "provider": run.provider,
            "model": run.model, "prompt_version": versions.get(run.prompt_id),
            "input_tokens": run.input_tokens or 0, "output_tokens": run.output_tokens or 0,
            "offered": len(offered), **proposal,
            "notices": ([run.message] if run.status == "ok" and run.message else []) + proposal["notices"],
            "reply": (run.output_text or "").strip(), "message": run.message,
        })
    return result
