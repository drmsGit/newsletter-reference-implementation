"""No test reaches a real vendor, whatever .env holds (task-346).

`main.py` loads `.env` into the environment when a test imports the app, so the
real RESEND_API_KEY and ANTHROPIC_API_KEY are set for the rest of the run. On
2026-10-10 a test planned a send with provider "resend" without faking it, and
two real Resend calls went out. `conftest.py` now refuses any `httpx.post` to
the two vendor hosts; a test that fakes `httpx.post` itself still decides what
its adapter sees.
"""
import httpx
import pytest

from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.delivery.providers.resend import RESEND_API_URL, ResendProvider
from app.delivery.service import send_send_instance
from app.rendering.renderers.base import RenderedArtifact
from app.snapshots.service import create_snapshot_for_variant
from tests import test_render_skip as _render_skip

db = _render_skip.db
world = _render_skip.world


@pytest.mark.parametrize("url", [RESEND_API_URL, "https://api.anthropic.com/v1/messages"])
def test_a_request_to_a_vendor_fails_the_test(url):
    with pytest.raises(RuntimeError, match="real vendor"):
        httpx.post(url, json={})


def test_the_adapter_cannot_send_for_real():
    artifact = RenderedArtifact.email("<p>x</p>", subject="Hi")
    with pytest.raises(RuntimeError, match="real vendor"):
        ResendProvider(api_key="test").send("a@example.invalid", artifact)


def test_the_send_that_leaked_on_2026_10_10_now_fails_loudly(db, world):
    """Planned with provider "resend" and nothing faked — exactly the leak."""
    brand = world["brand"]
    snapshot = create_snapshot_for_variant(db, world["variant"](static=True, slots=0).id, brand_id=brand.id)
    world["made"]["snapshots"].append(snapshot.id)
    send = SendInstanceDB(snapshot_id=snapshot.id, brand_id=brand.id, name="task-346", status="draft", provider="resend")
    db.add(send)
    db.flush()
    world["made"]["sends"].append(send.id)
    db.add(DeliveryExecutionDB(send_instance_id=send.id, recipient_id=world["person"]().id, status="created",
                               provider="resend", channel="email", purpose="marketing"))
    db.commit()

    with pytest.raises(RuntimeError, match="real vendor"):
        send_send_instance(db, send.id, brand_id=brand.id)


def test_a_test_that_fakes_httpx_still_decides(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda url, **kw: "faked")
    assert httpx.post(RESEND_API_URL, json={}) == "faked"
