"""Task: suggest subject / preheader options for a variant.

The first Mode A action (ADR-141 §3). This file is the **dev-owned scaffold**
only — it declares what the task reads, what shape it returns, and where the
result lands. The prompt itself is *not* here: it lives in settings, owned and
versioned by the manager (ADR-140 §4), because a developer cannot meaningfully
evaluate marketing copy.

Placement is campaign level, not send level: `subject`/`preheader` belong to the
variant, and at send time they are captured into the snapshot (ADR-061/062) —
so a send is exactly the moment they must stop changing.

PII: the model sees the campaign's own editorial content and nothing about any
recipient (ADR-144 §4). Personalisation stays with merge variables resolved
locally at render, so no identity leaves the platform.
"""

from sqlalchemy.orm import Session

from app.ai.service import run_task
from app.ai.tasks.base import TaskMeta
from app.campaigns.db_models import ModuleInstanceDB, VariantDB
from app.content.db_models import ContentRecordDB

TASK_KEY = "subject_preheader"

# The task declares its own output ceiling — this is what makes the worst case
# computable before the call, and therefore what makes the spend cap a pre-call
# gate rather than a mid-run kill (ADR-144 §5).
MAX_OUTPUT_TOKENS = 400

# How many options the scaffold asks for. Declared here beside the ceiling for
# the same reason: the scaffold is dev-owned and states the shape of the result
# (see the module docstring), so the UI has something to compare the parsed
# count against. The prompt body itself is manager-owned and versioned — if a
# manager edits DEFAULT_PROMPT's "3" in Settings, this number is the one that
# should move with it.
REQUESTED_OPTIONS = 3

DEFAULT_PROMPT = """You write subject lines and preheaders for an email newsletter.

Below is the content of one newsletter edition. Suggest 3 subject line and
preheader pairs for it.

Rules:
- Subject: max 60 characters. Preheader: max 90 characters.
- The preheader must add information, never repeat the subject.
- Be concrete. Use a specific detail from the content.
- No exclamation marks, no "Discover", no emoji.

Return exactly 3 options in this format, nothing else:

1. SUBJECT: <subject>
   PREHEADER: <preheader>
2. SUBJECT: <subject>
   PREHEADER: <preheader>
3. SUBJECT: <subject>
   PREHEADER: <preheader>

The content:
{content}
"""


#: What the registry discovers. The constants above stay as they are — this
#: gathers them into one declaration so the settings page can render a card for
#: this task without importing it by name, which is what it used to do.
META = TaskMeta(
    key=TASK_KEY,
    label="Subject & preheader",
    description=(
        "Suggests subject line and preheader pairs for an email variant, from "
        "that edition's own content. The manager picks one; nothing is applied "
        "automatically."
    ),
    default_prompt=DEFAULT_PROMPT,
    max_output_tokens=MAX_OUTPUT_TOKENS,
)


def gather_inputs(db: Session, variant_id: int) -> str:
    """Collect the variant's editorial content — the task's declared input."""
    rows = (
        db.query(ContentRecordDB.title, ContentRecordDB.content)
        .join(ModuleInstanceDB, ModuleInstanceDB.content_record_id == ContentRecordDB.id)
        .filter(ModuleInstanceDB.variant_id == variant_id)
        .order_by(ModuleInstanceDB.position.asc())
        .all()
    )
    parts = []
    for title, content in rows:
        content = content or {}
        headline = content.get("headline_medium") or title
        body = content.get("body_medium") or ""
        parts.append(f"- {headline}\n  {body}".rstrip())
    return "\n".join(parts) if parts else "(this variant has no content yet)"


def parse_options(text: str) -> list[dict[str, str]]:
    """Turn the model's reply into structured options.

    Tolerant on purpose: a model that drifts from the requested layout should
    degrade to fewer options, never to an exception in the request path.
    """
    options: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for raw in (text or "").splitlines():
        line = raw.strip()
        upper = line.upper()
        if "SUBJECT:" in upper:
            if current.get("subject"):
                options.append(current)
                current = {}
            current["subject"] = line[upper.index("SUBJECT:") + len("SUBJECT:"):].strip()
        elif "PREHEADER:" in upper:
            current["preheader"] = line[upper.index("PREHEADER:") + len("PREHEADER:"):].strip()
    if current.get("subject"):
        options.append(current)
    return [
        {"subject": o.get("subject", ""), "preheader": o.get("preheader", "")}
        for o in options
        if o.get("subject")
    ]


def option_notices(
    options: list[dict[str, str]], run_message: str | None = None
) -> list[str]:
    """What the manager must be told about these options before using one.

    Both facts already exist in the system and were previously dropped on the
    way to the page: the run row's own `message` (which says when the output hit
    its ceiling and is truncated), and the gap between what the scaffold asked
    for and what `parse_options` could recover. ADR-144 keeps a partial result on
    screen — display is not commit — but showing it without saying it is partial
    is what this closes.
    """
    notices: list[str] = []
    if run_message:
        notices.append(run_message)
    if 0 < len(options) < REQUESTED_OPTIONS:
        notices.append(
            f"{len(options)} of the {REQUESTED_OPTIONS} requested options came "
            f"back in a usable form; the rest were not returned or could not be read."
        )
    return notices


def suggest(db: Session, variant_id: int, provider_name: str | None = None):
    """Run the task for one variant. Returns (options, TaskRun)."""
    variant = db.query(VariantDB).filter(VariantDB.id == variant_id).first()
    if variant is None:
        return [], None

    from app.ai.service import get_published_prompt

    prompt_row = get_published_prompt(db, TASK_KEY)
    template = prompt_row.body if prompt_row else DEFAULT_PROMPT
    rendered = template.replace("{content}", gather_inputs(db, variant_id))

    run = run_task(
        db,
        task_key=TASK_KEY,
        rendered_prompt=rendered,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        provider_name=provider_name,
        target_type="variant",
        target_id=variant_id,
    )
    return (parse_options(run.text) if run.ok else []), run
