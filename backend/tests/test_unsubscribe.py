"""Unsubscribe: a per-message token, a confirm page and one-click (task-56, ADR-191).

Decided with the user 2026-10-09, one question at a time:
  - every sent marketing email carries a random token stored with its
    delivery row, a footer line with the link, and the RFC 8058 headers;
  - opening the link only shows a page; a POST opts out — the page's button,
    or a mail client's one-click;
  - the default scope is marketing on the message's channel from the sending
    brand; "everything" (all brands, all channels, marketing) only while the
    company setting offers it, which starts off;
  - transactional consent is never touched; an unknown token learns nothing.
"""
import pytest
from fastapi.testclient import TestClient

from app.delivery.db_models import DeliveryExecutionDB
from app.delivery.providers import resend as resend_module
from app.recipients.consent import MARKETING, latest_consent_status, record_consent
from app.recipients.db_models import ConsentEventDB
from app.settings import service as settings
from main import app
from tests import test_render_skip as _render_skip

api = TestClient(app, raise_server_exceptions=False)
db = _render_skip.db
world = _render_skip.world


@pytest.fixture
def sent(db, world):
    """One marketing email delivered to one consenting person."""
    variant = world["variant"]("email", static=True, slots=0)
    person = world["person"]("email")
    world["send"](variant, [person])
    db.expire_all()
    execution = (db.query(DeliveryExecutionDB).filter_by(recipient_id=person.id)
                 .order_by(DeliveryExecutionDB.id.desc()).first())
    return execution, person


@pytest.fixture
def offer_everything(db):
    before = settings.get_unsubscribe_offer_everything(db)

    def set_to(value: bool):
        settings.set_unsubscribe_offer_everything(db, value)

    yield set_to
    settings.set_unsubscribe_offer_everything(db, before)


def _status(db, person_id, brand_id, channel="email", purpose=MARKETING):
    db.expire_all()
    return latest_consent_status(db, person_id, brand_id, channel=channel, purpose=purpose)


class TestTheMessageCarriesIt:

    def test_a_sent_marketing_email_has_a_token_a_footer_link_and_the_headers(self, db, sent, world):
        execution, _ = sent
        assert execution.status == "sent"
        assert execution.unsubscribe_token and len(execution.unsubscribe_token) >= 40
        record = execution.delivery_record["unsubscribe"]
        assert record["url"].endswith(f"/unsubscribe/{execution.unsubscribe_token}")
        assert record["brand"] == world["brand"].name

    def test_the_rebuilt_message_matches_what_was_sent(self, db, sent, world):
        """The footer is recorded, so a reconstruction (ADR-183) renders it too."""
        from app.delivery.service import reconstruct_delivery

        execution, _ = sent
        rebuilt = reconstruct_delivery(db, execution.id, brand_id=world["brand"].id)
        assert rebuilt["hash_matches"] is True
        assert rebuilt["envelope"]["list_unsubscribe"] == execution.delivery_record["unsubscribe"]["url"]

    def test_the_resend_payload_carries_the_one_click_headers(self, monkeypatch):
        from app.rendering.renderers.base import RenderedArtifact

        captured = {}

        class Answer:
            status_code = 200

            def json(self):
                return {"id": "msg-1"}

        monkeypatch.setattr(resend_module.httpx, "post", lambda url, **kw: captured.update(kw) or Answer())
        artifact = RenderedArtifact.email("<p>x</p>", subject="Hi")
        artifact.envelope["list_unsubscribe"] = "https://example.test/unsubscribe/abc"
        resend_module.ResendProvider(api_key="test").send("a@example.invalid", artifact)
        assert captured["json"]["headers"] == {
            "List-Unsubscribe": "<https://example.test/unsubscribe/abc>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        }


class TestThePage:

    def test_opening_the_link_shows_a_page_and_changes_nothing(self, db, sent, world):
        execution, person = sent
        response = api.get(f"/unsubscribe/{execution.unsubscribe_token}")
        assert response.status_code == 200
        assert world["brand"].name in response.text and 'method="post"' in response.text
        assert _status(db, person.id, world["brand"].id) == "opted_in"

    def test_the_button_opts_out_of_the_sending_brand_on_this_channel(self, db, sent, world, foreign_brand):
        execution, person = sent
        record_consent(db, person.id, "opted_in", foreign_brand.id, source="test", channel="email", purpose=MARKETING)
        response = api.post(f"/unsubscribe/{execution.unsubscribe_token}", data={"scope": "brand"})
        assert response.status_code == 200 and "unsubscribed" in response.text
        assert _status(db, person.id, world["brand"].id) == "opted_out"
        assert _status(db, person.id, foreign_brand.id) == "opted_in", "another brand was opted out too"

    def test_one_click_from_a_mail_client_opts_out_at_once(self, db, sent, world):
        execution, person = sent
        response = api.post(f"/unsubscribe/{execution.unsubscribe_token}",
                            data={"List-Unsubscribe": "One-Click"})
        assert response.status_code == 200
        assert _status(db, person.id, world["brand"].id) == "opted_out"

    def test_a_second_click_writes_nothing(self, db, sent):
        execution, person = sent
        api.post(f"/unsubscribe/{execution.unsubscribe_token}", data={"scope": "brand"})
        count = db.query(ConsentEventDB).filter_by(recipient_id=person.id).count()
        api.post(f"/unsubscribe/{execution.unsubscribe_token}", data={"List-Unsubscribe": "One-Click"})
        assert db.query(ConsentEventDB).filter_by(recipient_id=person.id).count() == count

    def test_an_unknown_token_learns_nothing(self):
        for method in ("get", "post"):
            response = getattr(api, method)("/unsubscribe/not-a-real-token")
            assert response.status_code == 404
            assert "not valid" in response.text


class TestEverything:

    def test_not_offered_by_default(self, db, sent, world, foreign_brand, offer_everything):
        execution, person = sent
        offer_everything(False)
        record_consent(db, person.id, "opted_in", foreign_brand.id, source="test", channel="email", purpose=MARKETING)
        assert 'value="everything"' not in api.get(f"/unsubscribe/{execution.unsubscribe_token}").text
        api.post(f"/unsubscribe/{execution.unsubscribe_token}", data={"scope": "everything"})
        assert _status(db, person.id, foreign_brand.id) == "opted_in", "an unoffered option was honoured"

    def test_when_offered_it_opts_out_every_brand_and_channel_but_not_transactional(
            self, db, sent, world, foreign_brand, offer_everything):
        execution, person = sent
        offer_everything(True)
        record_consent(db, person.id, "opted_in", foreign_brand.id, source="test", channel="push", purpose=MARKETING)
        record_consent(db, person.id, "opted_in", world["brand"].id, source="test", channel="email",
                       purpose="transactional")
        assert 'value="everything"' in api.get(f"/unsubscribe/{execution.unsubscribe_token}").text
        api.post(f"/unsubscribe/{execution.unsubscribe_token}", data={"scope": "everything"})
        assert _status(db, person.id, world["brand"].id) == "opted_out"
        assert _status(db, person.id, foreign_brand.id, channel="push") == "opted_out"
        assert _status(db, person.id, world["brand"].id, purpose="transactional") == "opted_in"

    def test_one_click_never_means_everything(self, db, sent, world, foreign_brand, offer_everything):
        execution, person = sent
        offer_everything(True)
        record_consent(db, person.id, "opted_in", foreign_brand.id, source="test", channel="email", purpose=MARKETING)
        api.post(f"/unsubscribe/{execution.unsubscribe_token}",
                 data={"List-Unsubscribe": "One-Click", "scope": "everything"})
        assert _status(db, person.id, foreign_brand.id) == "opted_in"


def test_the_next_send_leaves_the_unsubscribed_person_out(db, sent, world):
    """The opt-out is an ordinary consent event: the exclusion stack honours it."""
    execution, person = sent
    api.post(f"/unsubscribe/{execution.unsubscribe_token}", data={"scope": "brand"})
    world["delivered"].clear()
    _, outcome = world["send"](world["variant"]("email", static=True, slots=0), [person])
    assert world["delivered"] == []
    assert outcome[person.id][0] == "excluded"
