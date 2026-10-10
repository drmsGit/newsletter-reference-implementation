"""A real send never carries an unsubscribe link to localhost (task-330).

The link in every marketing email is built from PUBLIC_BASE_URL, which fell
back to http://localhost:8000 when unset — silently, and the link is fixed into
each mail for good. ADR-191 already said the address "must be configured";
nothing enforced it. Decided 2026-10-09 (interview review, Audience Q6): a
provider that reaches real inboxes refuses a marketing send whose base URL is
unset or not https, before anything is sent. The mock keeps the localhost
default, so development and tests are unaffected.
"""
import pytest

from app.delivery import service as delivery
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.delivery.providers.base import DeliveryProvider, SendResult
from app.delivery.service import send_send_instance
from app.snapshots.service import create_snapshot_for_variant
from tests import test_render_skip as _render_skip

db = _render_skip.db
world = _render_skip.world


class RealInboxes(DeliveryProvider):
    """Stands in for Resend: reaches real inboxes, delivers nothing here."""

    channels = frozenset({"email"})

    def __init__(self):
        self.sent: list[tuple[str, object]] = []

    def send(self, address, artifact):
        self.sent.append((address, artifact))
        return SendResult(success=True, provider_message_id=f"real-{len(self.sent)}")


@pytest.fixture
def real(monkeypatch):
    provider = RealInboxes()
    monkeypatch.setattr(delivery, "get_provider", lambda *a, **k: provider)
    return provider


def _planned(db, world, *, purpose="marketing", provider="resend") -> SendInstanceDB:
    brand = world["brand"]
    variant = world["variant"](static=True, slots=0)
    snapshot = create_snapshot_for_variant(db, variant.id, brand_id=brand.id)
    world["made"]["snapshots"].append(snapshot.id)
    send = SendInstanceDB(snapshot_id=snapshot.id, brand_id=brand.id, name="task-330", status="draft", provider=provider)
    db.add(send)
    db.flush()
    world["made"]["sends"].append(send.id)
    db.add(DeliveryExecutionDB(send_instance_id=send.id, recipient_id=world["person"]().id, status="created",
                               provider=provider, channel="email", purpose=purpose))
    db.commit()
    return send


@pytest.mark.parametrize("base_url", [None, "", "http://news.example.com", "https://"])
def test_a_real_send_without_a_public_https_address_is_refused(db, world, real, monkeypatch, base_url):
    if base_url is None:
        monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    else:
        monkeypatch.setenv("PUBLIC_BASE_URL", base_url)
    send = _planned(db, world)

    with pytest.raises(ValueError, match="PUBLIC_BASE_URL"):
        send_send_instance(db, send.id, brand_id=world["brand"].id)
    assert real.sent == [], "the refusal must come before any mail leaves"
    db.expire_all()
    assert db.get(SendInstanceDB, send.id).status == "draft", "refused before the claim, so it can be retried"


def test_a_real_send_with_a_public_https_address_carries_it(db, world, real, monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://news.example.com/")
    send = _planned(db, world)

    assert send_send_instance(db, send.id, brand_id=world["brand"].id) == "sent"
    [(_, artifact)] = real.sent
    assert artifact.envelope["list_unsubscribe"].startswith("https://news.example.com/unsubscribe/")


def test_the_mock_keeps_the_development_default(db, world, monkeypatch):
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    send = _planned(db, world, provider="mock")
    world["delivered"].clear()

    assert send_send_instance(db, send.id, brand_id=world["brand"].id) == "sent"
    assert len(world["delivered"]) == 1


def test_a_real_send_that_carries_no_unsubscribe_link_is_not_refused(db, world, real, monkeypatch):
    """Only a marketing email carries the link (footer_for); nothing else needs the address."""
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    send = _planned(db, world, purpose="transactional")

    send_send_instance(db, send.id, brand_id=world["brand"].id)   # not refused
    db.expire_all()
    assert db.get(SendInstanceDB, send.id).status != "draft", "the send ran"
