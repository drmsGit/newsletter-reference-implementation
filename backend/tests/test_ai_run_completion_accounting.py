"""New AI runs have a system actor and count at completion (ADR-144)."""
from types import SimpleNamespace

from sqlalchemy import text

from app.ai import service as ai
from app.ai.db_models import AIRunDB
from tests.test_ai_budget_period import db, ledger, prompt  # noqa: F401


def test_a_run_without_a_request_records_system_not_a_legacy_unknown(db, ledger, prompt):  # noqa: F811
    run = ai.run_task(db, task_key="subject_preheader", rendered_prompt="hello",
                      max_output_tokens=50, provider_name="mock")
    assert run.ok, run.message
    row = db.get(AIRunDB, run.run_id)
    assert (row.actor_type, row.actor_id) == ("system", None)


def test_a_run_spanning_a_period_boundary_counts_when_the_provider_answers(
    db, ledger, prompt, monkeypatch,  # noqa: F811
):
    adapter = ai.get_ai_provider("mock")
    boundary = [None]
    # Advance only the period window after the gate, to simulate a reset while
    # the model is in flight. PostgreSQL's clock supplies the real boundary;
    # no real model call or wall-clock sleep is needed.
    monkeypatch.setattr(ai, "period_start", lambda db: boundary[0])

    def generate(*args, **kwargs):
        result = adapter.generate(*args, **kwargs)
        boundary[0] = db.scalar(text("SELECT clock_timestamp()"))
        return result

    monkeypatch.setattr(ai, "get_ai_provider", lambda *args, **kwargs: SimpleNamespace(
        count_input_tokens=adapter.count_input_tokens, generate=generate))
    run = ai.run_task(db, task_key="subject_preheader", rendered_prompt="hello",
                      max_output_tokens=50, provider_name="claude",
                      actor_type="integration", actor_id=42)
    assert run.ok, run.message
    assert run.input_tokens + run.output_tokens > 0
    assert ai.tokens_used(db) == run.input_tokens + run.output_tokens
    assert db.get(AIRunDB, run.run_id).created_at >= boundary[0]
