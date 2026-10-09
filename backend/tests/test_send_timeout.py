"""A provider timeout after the request may have arrived is "maybe sent" (task-327).

The Resend adapter caught every network error, a read timeout included, and
reported a plain failure; the send recorded "failed", and a retry sent the mail
again — though the provider may have accepted it before the answer was lost.
task-318's uncertain marker only covered an exception escaping the adapter,
which this one never raises. Found by ChatGPT 2026-10-09 (draft-2).

Decided: the user's task-318 rule applies — never risk a duplicate. A
connection that never opened is a real failure and stays retryable; anything
after the request could have been sent is `uncertain` and is never resent. And
every send carries an idempotency key, stable across retries, so Resend itself
refuses a second copy within 24 hours (decided with the user 2026-10-09).
"""
import httpx
import pytest

from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.delivery.providers import mock as mock_module
from app.delivery.providers.base import SendResult
from app.delivery.providers.resend import ResendProvider
from app.delivery.service import send_send_instance
from app.rendering.renderers.base import RenderedArtifact
from app.snapshots.service import create_snapshot_for_variant
from tests import test_render_skip as _render_skip

db = _render_skip.db
world = _render_skip.world


def _artifact(key: str | None = "delivery-execution-7-20261009T120000000000") -> RenderedArtifact:
    artifact = RenderedArtifact.email("<p>x</p>", subject="Hi")
    artifact.idempotency_key = key
    return artifact


class TestTheAdapter:

    @pytest.mark.parametrize("error", [
        httpx.ConnectError("no route to host"),
        httpx.ConnectTimeout("connect timed out"),
        httpx.PoolTimeout("no connection free"),
    ])
    def test_a_request_that_never_left_is_a_plain_failure(self, monkeypatch, error):
        def boom(*a, **k):
            raise error

        monkeypatch.setattr(httpx, "post", boom)
        result = ResendProvider(api_key="test").send("a@example.invalid", _artifact())
        assert (result.success, result.uncertain) == (False, False)

    @pytest.mark.parametrize("error", [
        httpx.ReadTimeout("read timed out"),
        httpx.WriteTimeout("write timed out"),
        httpx.RemoteProtocolError("server disconnected"),
        httpx.ReadError("connection reset"),
    ])
    def test_a_request_that_may_have_arrived_is_uncertain(self, monkeypatch, error):
        def boom(*a, **k):
            raise error

        monkeypatch.setattr(httpx, "post", boom)
        result = ResendProvider(api_key="test").send("a@example.invalid", _artifact())
        assert (result.success, result.uncertain) == (False, True)

    def test_every_send_carries_its_idempotency_key(self, monkeypatch):
        captured = {}

        class Answer:
            status_code = 200

            def json(self):
                return {"id": "msg-1"}

        monkeypatch.setattr(httpx, "post", lambda url, **kw: captured.update(kw) or Answer())
        ResendProvider(api_key="test").send("a@example.invalid", _artifact("delivery-execution-7-x"))
        assert captured["headers"]["Idempotency-Key"] == "delivery-execution-7-x"


def _planned(db, world, people) -> SendInstanceDB:
    brand = world["brand"]
    variant = world["variant"](static=True, slots=0)
    snapshot = create_snapshot_for_variant(db, variant.id, brand_id=brand.id)
    world["made"]["snapshots"].append(snapshot.id)
    send = SendInstanceDB(snapshot_id=snapshot.id, brand_id=brand.id, name="task-327", status="draft", provider="mock")
    db.add(send)
    db.flush()
    world["made"]["sends"].append(send.id)
    for person in people:
        db.add(DeliveryExecutionDB(send_instance_id=send.id, recipient_id=person.id, status="created",
                                   provider="mock", channel="email", purpose="marketing"))
    db.commit()
    return send


def test_an_uncertain_result_is_never_resent(db, world, monkeypatch):
    people = [world["person"](), world["person"]()]
    send = _planned(db, world, people)
    capture = mock_module.MockProvider.send
    keys: list[str] = []
    calls = {"n": 0}

    def second_times_out(self, address, artifact):
        keys.append(artifact.idempotency_key)
        calls["n"] += 1
        if calls["n"] == 2:
            return SendResult(success=False, uncertain=True, message="read timed out")
        return capture(self, address, artifact)

    monkeypatch.setattr(mock_module.MockProvider, "send", second_times_out)
    assert send_send_instance(db, send.id, brand_id=world["brand"].id) == "partial_failed"
    db.expire_all()
    rows = {e.recipient_id: e for e in db.query(DeliveryExecutionDB).filter_by(send_instance_id=send.id)}
    [maybe] = [e for e in rows.values() if e.status == "uncertain"]
    assert "not sent again" in maybe.exclusion_reason

    world["delivered"].clear()
    monkeypatch.setattr(mock_module.MockProvider, "send", capture)
    assert send_send_instance(db, send.id, brand_id=world["brand"].id) == "partial_failed"
    assert world["delivered"] == [], "the retry resent a maybe-sent recipient"
    assert len(set(keys)) == 2 and all(keys), "each message carries its own, non-empty key"


def test_a_retried_recipient_carries_the_same_key(db, world, monkeypatch):
    """The key only protects anything if a retry sends the same one."""
    person = world["person"]()
    send = _planned(db, world, [person])
    capture = mock_module.MockProvider.send
    keys: list[str] = []

    def refused(self, address, artifact):
        keys.append(artifact.idempotency_key)
        return SendResult(success=False, message="mailbox full")     # a definite failure: retryable

    monkeypatch.setattr(mock_module.MockProvider, "send", refused)
    assert send_send_instance(db, send.id, brand_id=world["brand"].id) == "failed"

    def accepted(self, address, artifact):
        keys.append(artifact.idempotency_key)
        return capture(self, address, artifact)

    monkeypatch.setattr(mock_module.MockProvider, "send", accepted)
    assert send_send_instance(db, send.id, brand_id=world["brand"].id) == "sent"
    assert len(keys) == 2 and keys[0] == keys[1], keys
