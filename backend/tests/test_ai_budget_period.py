"""The AI spend cap refills each period, and every run records who started it
(task-345; ADR-144 addenda of 2026-10-09 and 2026-10-11).

One company-wide pot. The period is month (the default), quarter, year or
lifetime, starting at midnight UTC. A run counts in the period it is recorded
in. Every new run records a person, an integration, or `system`.
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.ai import service as ai
from app.ai.db_models import AIRunDB
from app.audit.db_models import AuditEventDB
from app.auth.permissions import SETTINGS_MANAGE, VIEW
from app.database import SessionLocal
from app.settings import service as settings
from app.settings.db_models import AppConfigDB
from main import app
from tests.machine import machine
from tests.test_api_guard import signed_in

client = TestClient(app, raise_server_exceptions=False)
UTC = timezone.utc


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def ledger(db):
    """Billable runs at chosen times, alone in the ledger for the test."""
    saved = [(r.id, r.provider) for r in db.query(AIRunDB).all()]
    # Make every existing run free for the duration, so only ours count.
    db.query(AIRunDB).update({"provider": "mock"}, synchronize_session=False)
    db.commit()
    made: list[int] = []

    def add(at: datetime, tokens: int, provider: str = "claude") -> AIRunDB:
        row = AIRunDB(task_key="subject_preheader", provider=provider, model="claude-sonnet-5-5",
                      status="ok", input_tokens=tokens, output_tokens=0, created_at=at)
        db.add(row)
        db.commit()
        made.append(row.id)
        return row

    yield add
    db.rollback()
    db.query(AIRunDB).filter(AIRunDB.id.in_(made)).delete(synchronize_session=False)
    for run_id, provider in saved:
        db.query(AIRunDB).filter(AIRunDB.id == run_id).update({"provider": provider}, synchronize_session=False)
    db.query(AppConfigDB).filter(AppConfigDB.key == settings.AI_BUDGET_PERIOD_KEY).delete()
    db.commit()


@pytest.fixture
def at(monkeypatch):
    def freeze(moment: datetime):
        monkeypatch.setattr(ai, "now", lambda: moment)
    return freeze


# --- the period -------------------------------------------------------------------

@pytest.mark.parametrize("period, moment, start", [
    ("month", datetime(2026, 10, 11, 9, tzinfo=UTC), datetime(2026, 10, 1, tzinfo=UTC)),
    ("quarter", datetime(2026, 11, 20, tzinfo=UTC), datetime(2026, 10, 1, tzinfo=UTC)),
    ("quarter", datetime(2026, 3, 31, 23, 59, tzinfo=UTC), datetime(2026, 1, 1, tzinfo=UTC)),
    ("year", datetime(2026, 10, 11, tzinfo=UTC), datetime(2026, 1, 1, tzinfo=UTC)),
    ("lifetime", datetime(2026, 10, 11, tzinfo=UTC), None),
])
def test_periods_start_at_midnight_utc(db, ledger, at, period, moment, start):
    settings.save_ai_budget_period(db, period)
    at(moment)
    assert ai.period_start(db) == start


def test_the_default_is_the_calendar_month(db, ledger):
    assert settings.get_ai_budget_period(db) == "month"


def test_only_the_current_period_counts(db, ledger, at):
    at(datetime(2026, 10, 11, 9, tzinfo=UTC))
    ledger(datetime(2026, 9, 30, 23, 59, tzinfo=UTC), 1000)   # last month
    ledger(datetime(2026, 10, 1, 0, 0, tzinfo=UTC), 300)       # the first minute of this one
    ledger(datetime(2026, 10, 10, tzinfo=UTC), 200)
    ledger(datetime(2026, 10, 10, tzinfo=UTC), 5000, provider="mock")   # free, never counts
    assert ai.tokens_used(db) == 500
    settings.save_ai_budget_period(db, "lifetime")
    assert ai.tokens_used(db) == 1500


def test_the_budget_status_says_which_period(db, ledger, at):
    at(datetime(2026, 10, 11, tzinfo=UTC))
    status = settings.ai_budget_status(db)
    assert status["period"] == "month"
    assert status["period_start"] == datetime(2026, 10, 1, tzinfo=UTC)


@pytest.fixture
def prompt(db):
    """A published prompt for the task, so a run reaches the budget check."""
    from app.ai.db_models import AIPromptDB

    before = {r.id: r.is_published for r in db.query(AIPromptDB).filter(AIPromptDB.task_key == "subject_preheader")}
    row = AIPromptDB(task_key="subject_preheader", version=9999, body="Say hello.", is_published=True)
    db.query(AIPromptDB).filter(AIPromptDB.task_key == "subject_preheader").update({"is_published": False})
    db.add(row)
    db.commit()
    yield row
    db.rollback()
    db.query(AIRunDB).filter(AIRunDB.prompt_id == row.id).delete(synchronize_session=False)
    db.query(AIPromptDB).filter(AIPromptDB.id == row.id).delete()
    for prompt_id, published in before.items():
        db.query(AIPromptDB).filter(AIPromptDB.id == prompt_id).update({"is_published": published})
    db.commit()


def test_the_pre_call_gate_uses_the_period(db, ledger, at, prompt):
    """Last month's spend does not block a run this month."""
    cap = settings.get_ai_spend_cap(db)
    at(datetime(2026, 10, 11, tzinfo=UTC))
    ledger(datetime(2026, 9, 15, tzinfo=UTC), cap["hard_stop_tokens"] + 10)
    run = ai.run_task(db, task_key="subject_preheader", rendered_prompt="hello", max_output_tokens=50,
                      provider_name="mock", actor_type="user", actor_id=None)
    assert run.ok, run.message


@pytest.mark.parametrize("period", ["weekly", "", "Month"])
def test_an_unknown_period_is_refused(db, ledger, period):
    with pytest.raises(settings.SettingsInvalid):
        settings.save_ai_budget_period(db, period)


# --- who started a run -------------------------------------------------------------

def test_a_run_records_who_started_it(db, ledger):
    run = ai.run_task(db, task_key="subject_preheader", rendered_prompt="hello", max_output_tokens=50,
                      provider_name="mock", actor_type="integration", actor_id=42)
    row = db.get(AIRunDB, run.run_id)
    assert (row.actor_type, row.actor_id) == ("integration", 42)
    db.delete(row)
    db.commit()


def test_a_suggestion_through_the_api_records_the_person(db, ledger):
    """The whole chain: route, orchestration, task, ledger."""
    from app.campaigns.db_models import VariantDB

    variant = db.query(VariantDB).filter(VariantDB.channel == "email").order_by(VariantDB.id).first()
    before = db.query(AIRunDB.id).order_by(AIRunDB.id.desc()).first()
    with signed_in(db) as (cookied, token, csrf):
        from app.auth import service as auth

        user = auth.user_for_token(db, token)
        cookied.post(f"/campaigns/variants/{variant.id}/suggest-subject", headers={"X-CSRF-Token": csrf})
        db.expire_all()
        run = db.query(AIRunDB).filter(AIRunDB.id > (before[0] if before else 0)).order_by(AIRunDB.id.desc()).first()
        assert run is not None, "no AI run was recorded"
        assert (run.actor_type, run.actor_id) == ("user", user.id)
        db.delete(run)
        db.commit()


# --- the setting through the API ------------------------------------------------------

def test_a_person_sets_the_period_and_it_is_audited(db, ledger):
    with signed_in(db) as (cookied, _token, csrf):
        response = cookied.put("/settings/ai/budget-period", json={"period": "quarter"},
                               headers={"X-CSRF-Token": csrf})
        assert response.status_code == 200, response.text
        assert cookied.get("/settings").json()["ai_budget"]["period"] == "quarter"
    entry = (db.query(AuditEventDB).filter(AuditEventDB.action == "settings.changed")
             .order_by(AuditEventDB.id.desc()).first())
    assert entry.detail["setting"] == "ai_budget_period"


def test_an_unknown_period_through_the_api_is_a_422(db, ledger):
    with signed_in(db) as (cookied, _token, csrf):
        response = cookied.put("/settings/ai/budget-period", json={"period": "weekly"},
                               headers={"X-CSRF-Token": csrf})
    assert response.status_code == 422


def test_a_machine_cannot_change_the_period(db, ledger):
    with machine([VIEW, SETTINGS_MANAGE]) as headers:
        response = client.put("/settings/ai/budget-period", json={"period": "year"}, headers=headers)
    assert response.status_code == 403


def test_a_successful_run_records_who_started_it(db, ledger, prompt):
    run = ai.run_task(db, task_key="subject_preheader", rendered_prompt="hello", max_output_tokens=50,
                      provider_name="mock", actor_type="user", actor_id=7)
    assert run.ok, run.message
    row = db.get(AIRunDB, run.run_id)
    assert (row.status, row.actor_type, row.actor_id) == ("ok", "user", 7)
