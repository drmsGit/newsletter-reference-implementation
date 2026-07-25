"""Unit tests for the Resend outbound adapter — no network, no verified domain.

Mocks httpx so we can validate request-building and response-mapping before the
real DNS-verified send.
"""
import httpx

from app.delivery.providers.resend import ResendProvider, RESEND_API_URL


class FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json body")
        return self._payload


def test_builds_correct_request_and_maps_id(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs["headers"]
        captured["json"] = kwargs["json"]
        return FakeResponse(200, {"id": "abc-123"})

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = ResendProvider(api_key="re_test", from_address="News <news@d.com>")
    result = provider.send("anna@example.com", "Hello", "<p>hi</p>")

    assert result.success is True
    assert result.provider_message_id == "abc-123"
    assert captured["url"] == RESEND_API_URL
    assert captured["headers"]["Authorization"] == "Bearer re_test"
    assert captured["json"] == {
        "from": "News <news@d.com>",
        "to": ["anna@example.com"],
        "subject": "Hello",
        "html": "<p>hi</p>",
    }


def test_domain_not_verified_is_a_clean_failure(monkeypatch):
    monkeypatch.setattr(
        httpx, "post",
        lambda url, **kw: FakeResponse(403, {"message": "The domain is not verified."}),
    )
    result = ResendProvider(api_key="re_test").send("a@b.com", "s", "<p>x</p>")
    assert result.success is False
    assert result.provider_message_id is None  # no collision on the unique column
    assert "not verified" in result.message


def test_missing_api_key_fails_without_calling_out(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("should not hit the network without a key")

    monkeypatch.setattr(httpx, "post", boom)
    result = ResendProvider(api_key="").send("a@b.com", "s", "<p>x</p>")
    assert result.success is False
    assert "RESEND_API_KEY" in result.message


def test_network_error_is_caught(monkeypatch):
    def boom(url, **kw):
        raise httpx.ConnectError("no route to host")

    monkeypatch.setattr(httpx, "post", boom)
    result = ResendProvider(api_key="re_test").send("a@b.com", "s", "<p>x</p>")
    assert result.success is False
    assert "network error" in result.message
