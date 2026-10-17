"""One run per task and target, and a cap that holds under concurrency
(task-387; ADR-144 addendum 2026-10-17).

The pre-call gate read the tokens used, called the model, and recorded the
run afterwards: two requests for one thing both ran and both were paid, and
two calls on different things could both pass the cap at its edge. A run is
now recorded as running, holding its worst case, before the call.

The provider here is a stand-in billed as a real one ("claude" by name), so
the cap counts it; nothing reaches a real model.
"""
import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

from app.ai import service as ai_service
from app.ai.adapters.base import AIResult, AIUsage
from app.ai.db_models import AIPromptDB, AIRunDB
from app.database import SessionLocal

TASK = "t387_task"
BILLED = "claude"


class StandIn:
    """Counts 100 input tokens, answers after `delay`, and lets a test look at
    the database while the call is in flight."""

    def __init__(self, delay=0.0, during=None):
        self.delay, self.during, self.calls, self.counts = delay, during, 0, 0

    def count_input_tokens(self, prompt, system=None):
        self.counts += 1
        return 100

    def generate(self, prompt, max_output_tokens, system=None):
        self.calls += 1
        if self.during:
            self.during()
        time.sleep(self.delay)
        return AIResult(success=True, text="done", usage=AIUsage(input_tokens=100, output_tokens=20),
                        model="stand-in", stop_reason="end_turn")


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.rollback()
    session.query(AIRunDB).filter(AIRunDB.task_key.like("t387%")).delete(synchronize_session=False)
    session.query(AIPromptDB).filter(AIPromptDB.task_key.like("t387%")).delete(synchronize_session=False)
    session.commit()
    session.close()


@pytest.fixture
def setup(db, monkeypatch):
    ai_service.publish_prompt(db, TASK, "Say {x}")
    state = {"provider": StandIn(), "cap": 1_000_000}
    monkeypatch.setattr(ai_service, "get_ai_provider", lambda name=None, model=None: state["provider"])
    monkeypatch.setattr(ai_service, "get_ai_spend_cap",
                        lambda db: {"warn_tokens": state["cap"], "hard_stop_tokens": state["cap"], "budget_usd": 0})
    # The budget counts this test's billed runs only, so other rows in the database do not move it.
    real_period = ai_service._in_period
    monkeypatch.setattr(ai_service, "_in_period",
                        lambda db_, query: real_period(db_, query).filter(AIRunDB.task_key.like("t387%")))
    return state


def _run(db, target_id=1, task=TASK, max_output=50):
    return ai_service.run_task(db, task_key=task, rendered_prompt="Say hi", max_output_tokens=max_output,
                               provider_name=BILLED, target_type="variant", target_id=target_id)


def _running(db, target_id=1, *, age=timedelta(0), reserved=150):
    row = AIRunDB(task_key=TASK, provider=BILLED, status=ai_service.RUNNING, target_type="variant",
                  target_id=target_id, input_tokens=100, output_tokens=reserved - 100,
                  created_at=datetime.now(timezone.utc) - age)
    db.add(row)
    db.commit()
    return row


def test_a_run_is_recorded_as_running_with_its_worst_case_before_the_call(db, setup):
    seen = {}

    def look():
        with SessionLocal() as other:
            row = other.query(AIRunDB).filter_by(task_key=TASK, status=ai_service.RUNNING).one()
            seen.update(tokens=(row.input_tokens, row.output_tokens), created=row.created_at)

    setup["provider"] = StandIn(during=look, delay=0.05)
    run = _run(db, max_output=50)
    assert seen["tokens"] == (100, 50)      # the counted input and the declared ceiling
    row = db.get(AIRunDB, run.run_id)
    db.refresh(row)
    assert (row.status, row.input_tokens, row.output_tokens, row.output_text) == ("ok", 100, 20, "done")
    # Stamped when it finished: it counts in the period it is recorded in (addendum 2026-10-11).
    assert row.created_at > seen["created"]


def test_a_second_request_for_the_same_task_and_thing_is_refused_without_a_call(db, setup):
    _running(db, target_id=7)
    before = db.query(AIRunDB).filter_by(task_key=TASK).count()
    with pytest.raises(ai_service.RunInFlight) as refused:
        _run(db, target_id=7)
    assert "already being written" in str(refused.value)
    # Refused before the provider is asked anything, counting tokens included (a call of its own).
    assert setup["provider"].calls == 0 and setup["provider"].counts == 0
    assert db.query(AIRunDB).filter_by(task_key=TASK).count() == before


def test_another_thing_or_another_task_is_not_held_up(db, setup):
    _running(db, target_id=7)
    ai_service.publish_prompt(db, "t387_other", "Say {x}")
    assert _run(db, target_id=8).ok
    assert _run(db, target_id=7, task="t387_other").ok


def test_a_run_running_for_over_ten_minutes_is_failed_and_frees_the_thing(db, setup):
    stale = _running(db, target_id=9, age=timedelta(minutes=11))
    assert _run(db, target_id=9).ok
    db.refresh(stale)
    assert stale.status == "error" and "never finished" in stale.message
    assert (stale.input_tokens, stale.output_tokens) == (0, 0)


def test_the_cap_counts_what_running_runs_hold(db, setup):
    setup["cap"] = 300
    _running(db, target_id=1, reserved=200)
    run = _run(db, target_id=2, max_output=50)      # worst case 150, only 100 left
    assert not run.ok and "exceeds the 100 remaining" in run.message
    assert setup["provider"].calls == 0


def test_a_stale_running_run_holds_no_budget_even_before_anyone_claims(db, setup):
    before = ai_service.tokens_used(db)
    _running(db, target_id=3, age=timedelta(minutes=11), reserved=5000)
    assert ai_service.tokens_used(db) == before
    _running(db, target_id=4, reserved=5000)
    assert ai_service.tokens_used(db) == before + 5000


def test_money_spent_counts_finished_runs_only(db, setup, monkeypatch):
    monkeypatch.setattr(ai_service, "cost_usd", lambda model, i, o: (i + o) / 1000)
    _running(db, target_id=1, reserved=1000)
    assert ai_service.spend_to_date(db)["usd"] == 0


def test_two_requests_at_once_make_one_call(db, setup, monkeypatch):
    setup["provider"] = StandIn(delay=0.3)
    outcomes = []
    # Widen the gap between "nothing is running" and recording the run, so
    # without the lock both requests would pass it.
    real_used = ai_service.tokens_used
    monkeypatch.setattr(ai_service, "tokens_used", lambda db_: (time.sleep(0.2), real_used(db_))[1])

    def ask():
        with SessionLocal() as session:
            try:
                outcomes.append(_run(session, target_id=11).ok)
            except ai_service.RunInFlight:
                outcomes.append("refused")

    threads = [threading.Thread(target=ask) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(map(str, outcomes)) == ["True", "refused"]
    assert setup["provider"].calls == 1


# --- what readers and callers see ------------------------------------------------------

def test_a_running_run_is_no_suggestion_and_a_duplicate_route_answers_409(db, setup, monkeypatch):
    from app.ai.tasks import subject_preheader
    from app.auth.service import ensure_default_brand
    from app.campaigns.db_models import VariantDB
    from app.campaigns.service import create_campaign
    from tests.test_api_guard import signed_in

    campaign = create_campaign(db, name="t387 campaign", brand_id=ensure_default_brand(db).id, channel="email")
    variant = db.query(VariantDB).filter_by(campaign_id=campaign.id).one()
    running = AIRunDB(task_key=subject_preheader.TASK_KEY, provider=BILLED, status=ai_service.RUNNING,
                      target_type="variant", target_id=variant.id, input_tokens=1, output_tokens=1)
    db.add(running)
    db.commit()
    # A variant with content, so the subject task would otherwise call the model.
    monkeypatch.setattr(subject_preheader, "gather_inputs", lambda db_, vid: "- Lisbon\n  Trams")
    published = ai_service.get_published_prompt(db, subject_preheader.TASK_KEY) is None
    if published:
        ai_service.publish_prompt(db, subject_preheader.TASK_KEY, subject_preheader.DEFAULT_PROMPT)
    try:
        with signed_in(db) as (client, _token, csrf):
            listed = client.get(f"/campaigns/variants/{variant.id}/suggestions").json()
            response = client.post(f"/campaigns/variants/{variant.id}/suggest-subject",
                                   headers={"X-CSRF-Token": csrf})
            page = client.post(f"/ui/campaigns/{campaign.id}/variants/{variant.id}/suggest-subject",
                               data={"csrf_token": csrf}, headers={"X-CSRF-Token": csrf}, follow_redirects=False)
        assert listed == []
        assert response.status_code == 409 and "already being written" in response.text
        # The Jinja page is sent back with the reason, not a JSON 409.
        assert page.status_code == 303 and "already%20being%20written" in page.headers["location"]
        assert setup["provider"].calls == 0
    finally:
        from app.campaigns.db_models import CampaignDB, ModuleInstanceDB

        db.rollback()
        db.query(AIRunDB).filter_by(id=running.id).delete()
        if published:
            db.query(AIPromptDB).filter_by(task_key=subject_preheader.TASK_KEY).delete()
        db.query(ModuleInstanceDB).filter_by(variant_id=variant.id).delete()
        db.query(VariantDB).filter_by(id=variant.id).delete()
        db.query(CampaignDB).filter_by(id=campaign.id).delete()
        db.commit()


def test_a_duplicate_on_another_tasks_route_answers_409_in_words(db, setup):
    from app.ai.tasks import content_draft
    from app.auth.service import ensure_default_brand
    from app.content.db_models import ContentRecordDB
    from app.content.service import create_content
    from tests.test_api_guard import signed_in

    record = create_content(db, title="t387 record", content={}, brand_id=ensure_default_brand(db).id)
    ai_service.publish_prompt(db, content_draft.TASK_KEY, content_draft.DEFAULT_PROMPT)
    running = AIRunDB(task_key=content_draft.TASK_KEY, provider=BILLED, status=ai_service.RUNNING,
                      target_type="content", target_id=record.id, input_tokens=1, output_tokens=1)
    db.add(running)
    db.commit()
    try:
        with signed_in(db) as (client, _token, csrf):
            response = client.post(f"/content/{record.id}/drafts", json={"source": "Lisbon", "channels": ["email"]},
                                   headers={"X-CSRF-Token": csrf})
            listed = client.get(f"/content/{record.id}/drafts").json()
        assert response.status_code == 409 and "already being written" in response.json()["detail"]
        assert listed == [] and setup["provider"].calls == 0
    finally:
        db.rollback()
        db.query(AIRunDB).filter_by(id=running.id).delete()
        db.query(AIPromptDB).filter_by(task_key=content_draft.TASK_KEY).delete()
        db.query(ContentRecordDB).filter_by(id=record.id).delete()
        db.commit()
