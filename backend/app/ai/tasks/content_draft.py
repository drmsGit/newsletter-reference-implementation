"""Task: draft a content record's text fields from a pasted source, and
propose its categories (task-368; ADR-141 addendum 2026-10-16).

The dev-owned scaffold, as `subject_preheader` is: what the task reads, the
shape of its answer, and where that lands. The prompt is the manager's, in
Settings (ADR-140 §4); `DEFAULT_PROMPT` is only where a deployment starts.

**What it reads.** The source a person pasted (never fetched from an address,
never stored: it goes to the model and nowhere else), the text fields of the
channels they ticked, read from the field definitions with their labels and
notes (ADR-177), and the names of the existing categories (ADR-080).

**Where it lands.** Nowhere by itself. The run belongs to the record; the
proposal is read back on the record's page, where a person takes the fields
and categories they want through the ordinary writes. So the task has no held
form (ADR-140 addendum 2026-10-16): there is nothing for an approver to hold.
"""
import json
import re

from sqlalchemy.orm import Session

from app.ai.tasks.base import TaskMeta, json_object

TASK_KEY = "content_draft"

# Every text field of two channels plus a few categories with reasons. The
# ceiling makes the worst case computable before the call (ADR-144 §5).
MAX_OUTPUT_TOKENS = 2000

#: The source cap, said on the box, so one paste cannot consume the budget.
MAX_SOURCE_CHARS = 12000

#: Field types the model writes. Links and images are never drafted: the model
#: cannot see an image or know the right address.
DRAFTED_TYPES = ("text", "richtext")

DEFAULT_PROMPT = """You draft the text of one content record for a newsletter from the source below.

Write in the language the source is written in. Use only what the source says;
do not invent facts, prices, dates or addresses. Do not write links, and do not
use placeholders such as {{first_name}}.

Fill these fields. Each line gives the field name, what it is, and guidance:
{fields}

Then choose the categories this record belongs to, from this list only, each
with a score from 1 (barely belongs) to 10 (squarely belongs) and one short
reason:
{categories}

Your house style:
- None set yet. Replace this line in Settings with your own rules.

Answer with one JSON object and nothing else, in this shape:
{"fields": {"field_name": "text"}, "categories": [{"name": "Category name", "score": 7, "reason": "why"}]}

The source:
{source}
"""

META = TaskMeta(
    key=TASK_KEY,
    label="Content draft",
    description=(
        "Drafts a content record's text fields from a source a manager pastes, and "
        "proposes categories from the existing ones with a score and a reason. A "
        "person takes what they want on the record's page; nothing is saved by itself."
    ),
    default_prompt=DEFAULT_PROMPT,
    max_output_tokens=MAX_OUTPUT_TOKENS,
    held_form=False,
)

_LINK = re.compile(r"\[([^\]]+)\]\((?:[^)]*)\)")


class DraftInvalid(ValueError):
    """Refused before the call, on the request field at fault."""

    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field


def drafted_fields(channels: list[str]) -> list[dict]:
    """The record's text fields of these channels, never links, images or
    image descriptions (an `alt` field describes an image the model cannot see)."""
    from app.content.service import catalogue_fields

    fields = catalogue_fields()
    alts = {f["alt"] for f in fields if f.get("alt")}
    return [f for f in fields if f.get("channel") in channels and f.get("type") in DRAFTED_TYPES
            and f["name"] not in alts]


def check_request(source: str, channels: list[str]) -> list[dict]:
    """The fields to draft, or DraftInvalid. Nothing is spent on a refusal."""
    if not source.strip():
        raise DraftInvalid("source", "Paste the text to draft from.")
    if len(source) > MAX_SOURCE_CHARS:
        raise DraftInvalid("source", f"The source is {len(source)} characters; at most {MAX_SOURCE_CHARS}.")
    if not channels:
        raise DraftInvalid("channels", "Tick at least one channel to draft for.")
    fields = drafted_fields(channels)
    if not fields:
        raise DraftInvalid("channels", f"{', '.join(channels)} has no text fields to draft.")
    return fields


def build_prompt(db: Session, template: str, source: str, channels: list[str]) -> str:
    from app.content.service import list_categories

    lines = []
    for f in drafted_fields(channels):
        guidance = f" ({f['note']})" if f.get("note") else ""
        lines.append(f"- {f['name']}: {f.get('label') or f['name']}{guidance}")
    categories = "\n".join(f"- {c.name}" for c in sorted(list_categories(db), key=lambda c: c.name)) \
        or "(there are no categories yet)"
    # Replaced one by one rather than with str.format: the JSON example in the
    # prompt has braces of its own.
    return (template.replace("{fields}", "\n".join(lines)).replace("{categories}", categories)
            .replace("{source}", source))




def read_proposal(db: Session, text: str, channels: list[str] | None = None) -> dict:
    """The answer, kept to what was asked: text fields and the existing
    categories with a score of 1 to 10. What is dropped is said, so a manager
    knows the proposal is partial. Tolerant on purpose: a reply that drifts
    degrades to less, never to an error.

    `channels` None is every channel: a run does not record which were ticked
    (the request is not kept), so a read-back keeps any text field of the
    record and the person ticks what they take."""
    from app.content.service import catalogue_fields, list_categories

    answer = json_object(text or "") or {}
    if channels is None:
        channels = sorted({f.get("channel") for f in catalogue_fields() if f.get("channel")})
    wanted = {f["name"]: f for f in drafted_fields(channels)}
    notices: list[str] = []

    fields, unasked = [], []
    raw_fields = answer.get("fields") if isinstance(answer.get("fields"), dict) else {}
    for name, value in raw_fields.items():
        if name not in wanted:
            unasked.append(name)
        elif isinstance(value, str) and value.strip():
            fields.append({"name": name, "text": _LINK.sub(r"\1", value).strip()})
    if unasked:
        notices.append(f"Left out, as not a text field of the ticked channels: {', '.join(sorted(unasked))}.")

    vocabulary = {c.name.casefold(): c for c in list_categories(db)}
    categories, invented, out_of_range = [], [], []
    raw_categories = answer.get("categories") if isinstance(answer.get("categories"), list) else []
    for item in raw_categories:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        category = vocabulary.get(item["name"].strip().casefold())
        if category is None:
            invented.append(item["name"].strip())
            continue
        score = item.get("score")
        if not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 10:
            out_of_range.append(category.name)
            continue
        if any(c["category_id"] == category.id for c in categories):
            continue
        reason = item.get("reason") if isinstance(item.get("reason"), str) else ""
        categories.append({"category_id": category.id, "name": category.name, "score": score,
                           "reason": reason.strip()})
    if invented:
        notices.append(f"Not in the category list, so left out: {', '.join(invented)}.")
    if out_of_range:
        notices.append(f"Left out, as the score was not a whole number from 1 to 10: {', '.join(out_of_range)}.")
    return {"fields": fields, "categories": categories, "notices": notices}


def draft(db: Session, record_id: int, source: str, channels: list[str], *,
          actor_type: str | None = None, actor_id: int | None = None):
    """Run the task for one record. Check the request with `check_request`
    first: this spends."""
    from app.ai.service import get_published_prompt, run_task

    prompt_row = get_published_prompt(db, TASK_KEY)
    template = prompt_row.body if prompt_row else DEFAULT_PROMPT
    return run_task(
        db,
        task_key=TASK_KEY,
        rendered_prompt=build_prompt(db, template, source, channels),
        max_output_tokens=MAX_OUTPUT_TOKENS,
        target_type="content",
        target_id=record_id,
        actor_type=actor_type,
        actor_id=actor_id,
    )


def drafts_for_record(db: Session, record, *, brand_id: int) -> list[dict]:
    """Every draft run for one record, newest first, with what is on the record
    now beside each proposal: a field's current text and a category's current
    score, so the page can leave what is already filled unticked."""
    from app.ai.db_models import AIPromptDB, AIRunDB
    from app.content.service import catalogue_fields, content_assignments

    labels = {f["name"]: f for f in catalogue_fields()}
    stored = record.content or {}
    assigned = {a["category_id"]: a for a in content_assignments(db, record.id, brand_id=brand_id) or []}
    from app.ai.service import RUNNING

    # A running run is no result yet (ADR-144 addendum 2026-10-17).
    runs = (db.query(AIRunDB).filter(AIRunDB.task_key == TASK_KEY, AIRunDB.target_type == "content",
                                     AIRunDB.target_id == record.id, AIRunDB.status != RUNNING)
            .order_by(AIRunDB.created_at.desc(), AIRunDB.id.desc()).limit(25).all())
    versions = {p.id: p.version for p in db.query(AIPromptDB).filter(
        AIPromptDB.id.in_({r.prompt_id for r in runs if r.prompt_id}))}
    result = []
    for run in runs:
        proposal = read_proposal(db, run.output_text or "") if run.status == "ok" else \
            {"fields": [], "categories": [], "notices": []}
        notices = ([run.message] if run.status == "ok" and run.message else []) + proposal["notices"]
        result.append({
            "run_id": run.id, "status": run.status, "created_at": run.created_at, "provider": run.provider,
            "model": run.model, "prompt_version": versions.get(run.prompt_id),
            "input_tokens": run.input_tokens or 0, "output_tokens": run.output_tokens or 0,
            "fields": [{**f, "label": labels[f["name"]].get("label") or f["name"],
                        "channel": labels[f["name"]].get("channel"),
                        "current": stored.get(f["name"]) if isinstance(stored.get(f["name"]), str) else ""}
                       for f in proposal["fields"]],
            "categories": [{**c, "assigned_score": assigned[c["category_id"]]["score"]
                            if c["category_id"] in assigned else None,
                            "assignment_id": assigned[c["category_id"]]["assignment_id"]
                            if c["category_id"] in assigned else None}
                           for c in proposal["categories"]],
            "notices": notices,
            "reply": (run.output_text or "").strip(),
            "message": run.message,
        })
    return result
