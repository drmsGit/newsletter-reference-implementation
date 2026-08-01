"""Storage for the AI layer: manager-owned prompts, and the audit trail.

Two tables, one per ADR:

  AIPromptDB — ADR-140 §4. Prompts are the manager's domain (marketing/BI), so
  they live in the DB and are edited in the frontend, versioned and published
  like content. The dev-owned task file only *references* a prompt; it never
  embeds one.

  AIRunDB — ADR-140 §3/§5. Every AI action is audited with the standard fields
  plus the published prompt-version id. Because the live prompt is a DB row and
  not a git blob, that id is what makes a past decision reproducible — the row
  does not need a copy of the prompt text, the id resolves it. The same table is
  the cost ledger the spend cap reads (ADR-144 §5).
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)

from app.database import Base


class AIPromptDB(Base):
    __tablename__ = "ai_prompts"

    id = Column(Integer, primary_key=True, index=True)
    # Which task this prompt belongs to, e.g. "subject_preheader". Matches the
    # dev-owned task file's declared key (ADR-141 §1).
    task_key = Column(String(100), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    body = Column(Text, nullable=False)
    # Exactly one published version per task_key is the live one. Editing
    # creates a new version rather than mutating a published row, so an audit
    # row that references version 3 keeps pointing at the text version 3 had.
    is_published = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AIRunDB(Base):
    __tablename__ = "ai_runs"

    id = Column(Integer, primary_key=True, index=True)
    task_key = Column(String(100), nullable=False, index=True)
    # Nullable so a run that was refused *before* calling a model (spend cap,
    # missing prompt) is still recorded — a blocked attempt is an auditable
    # event, not a non-event.
    prompt_id = Column(Integer, ForeignKey("ai_prompts.id"), nullable=True)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=True)
    # "ok" | "blocked" | "error" — blocked means the pre-call gate refused it.
    status = Column(String(20), nullable=False)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    # What the task was pointed at (e.g. a variant id), so a run can be traced
    # back to the record it acted on.
    target_type = Column(String(50), nullable=True)
    target_id = Column(Integer, nullable=True)
    # What the model returned. ADR-140 §3 lists the output among the audited
    # fields, and storing it also means a suggestion survives the redirect after
    # the POST that produced it — the run row is the source of truth for what
    # was offered, rather than server-side session state.
    output_text = Column(Text, nullable=True)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
