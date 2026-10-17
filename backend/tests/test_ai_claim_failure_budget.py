"""Claims protect the shared budget and are released on failure (ADR-144)."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock

import pytest

from app.ai import service
from app.ai.db_models import AIRunDB
from app.database import SessionLocal
from tests import test_ai_runs_in_flight as fixtures

db = fixtures.db
setup = fixtures.setup


def test_different_targets_cannot_both_claim_the_last_budget(db, setup, monkeypatch):
    setup["cap"] = 200
    setup["provider"] = fixtures.StandIn(delay=0.2)
    used = service.tokens_used
    second_read = Event()
    lock = Lock()
    reads = 0

    def overlap(session):
        nonlocal reads
        amount = used(session)
        with lock:
            position = reads
            reads += 1
        if position == 0:
            # A serialized reader may not enter until the first claim commits.
            # Without serialization both readers can see the same remainder.
            second_read.wait(1)
        else:
            second_read.set()
        return amount

    monkeypatch.setattr(service, "tokens_used", overlap)

    def ask(target):
        with SessionLocal() as session:
            return fixtures._run(session, target_id=target).ok

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(ask, target) for target in (101, 102)]
        outcomes = [future.result(timeout=10) for future in futures]
    assert sorted(outcomes) == [False, True]
    assert setup["provider"].calls == 1
    assert service.tokens_used(db) <= setup["cap"]


def test_provider_exception_releases_the_claim_and_retry_can_run(db, setup):
    class Broken(fixtures.StandIn):
        def generate(self, prompt, max_output_tokens, system=None):
            self.calls += 1
            raise RuntimeError("synthetic provider interruption")

    setup["provider"] = Broken()
    with pytest.raises(RuntimeError, match="synthetic provider interruption"):
        fixtures._run(db, target_id=103)
    row = db.query(AIRunDB).filter_by(task_key=fixtures.TASK, target_id=103).one()
    assert row.status == "error"
    assert (row.input_tokens, row.output_tokens) == (0, 0)
    assert "synthetic provider interruption" in row.message
    setup["provider"] = fixtures.StandIn()
    assert fixtures._run(db, target_id=103).ok
    assert setup["provider"].calls == 1
    assert sorted(status for (status,) in db.query(AIRunDB.status).filter_by(
        task_key=fixtures.TASK, target_id=103)) == ["error", "ok"]
