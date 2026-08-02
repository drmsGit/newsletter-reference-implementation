"""Unit tests for the Claude adapter — no network, no API key, no spend.

Mocks httpx so request-building and response-mapping are validated before any
real call. The behaviour that matters most here is the pre-call gate: the
adapter must report *provider-counted* input tokens, and must refuse to invent
a number when it cannot get one (ADR-144 §5).
"""
import httpx
import pytest

from app.ai.adapters.base import AIProvider, TokenCountUnavailable
from app.ai.adapters.claude import (
    ANTHROPIC_VERSION,
    COUNT_TOKENS_URL,
    DEFAULT_MODEL,
    MESSAGES_URL,
    ClaudeProvider,
    extract_text,
)
from app.ai.adapters.factory import AVAILABLE_AI_PROVIDERS, get_ai_provider


class FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json body")
        return self._payload


def ok_message(text="1. SUBJECT: A\n   PREHEADER: B", **overrides):
    payload = {
        "model": "claude-opus-5",
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": text}],
        "usage": {"input_tokens": 812, "output_tokens": 143},
    }
    payload.update(overrides)
    return payload


class TestRegistration:

    def test_claude_is_selectable(self):
        assert "claude" in AVAILABLE_AI_PROVIDERS
        assert isinstance(get_ai_provider("claude"), ClaudeProvider)

    def test_satisfies_the_contract(self):
        assert isinstance(get_ai_provider("claude"), AIProvider)

    def test_mock_is_still_the_default(self):
        # Selecting a paid model stays a deliberate act.
        assert AVAILABLE_AI_PROVIDERS[0] == "mock"
        assert not isinstance(get_ai_provider(), ClaudeProvider)


class TestGeneration:

    def test_builds_the_request(self, monkeypatch):
        captured = {}

        def fake_post(url, **kwargs):
            captured["url"] = url
            captured["headers"] = kwargs["headers"]
            captured["json"] = kwargs["json"]
            return FakeResponse(200, ok_message())

        monkeypatch.setattr(httpx, "post", fake_post)
        ClaudeProvider(api_key="sk-test").generate("Write subject lines.", 400)

        assert captured["url"] == MESSAGES_URL
        assert captured["headers"]["x-api-key"] == "sk-test"
        assert captured["headers"]["anthropic-version"] == ANTHROPIC_VERSION
        assert captured["json"]["model"] == DEFAULT_MODEL
        assert captured["json"]["max_tokens"] == 400
        assert captured["json"]["messages"] == [
            {"role": "user", "content": "Write subject lines."}
        ]

    def test_thinking_is_off_by_default(self, monkeypatch):
        # max_tokens caps thinking *plus* reply, so leaving thinking on would let
        # a task with a small ceiling spend its whole budget reasoning.
        captured = {}
        monkeypatch.setattr(
            httpx, "post",
            lambda url, **kw: captured.update(kw["json"]) or FakeResponse(200, ok_message()),
        )
        ClaudeProvider(api_key="sk-test").generate("p", 400)
        assert captured["thinking"] == {"type": "disabled"}

    def test_thinking_can_be_enabled(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            httpx, "post",
            lambda url, **kw: captured.update(kw["json"]) or FakeResponse(200, ok_message()),
        )
        ClaudeProvider(api_key="sk-test", thinking=True).generate("p", 4000)
        assert "thinking" not in captured

    def test_system_prompt_is_sent_when_given(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            httpx, "post",
            lambda url, **kw: captured.update(kw["json"]) or FakeResponse(200, ok_message()),
        )
        ClaudeProvider(api_key="sk-test").generate("p", 400, system="be terse")
        assert captured["system"] == "be terse"

    def test_maps_text_and_reported_usage(self, monkeypatch):
        monkeypatch.setattr(httpx, "post", lambda url, **kw: FakeResponse(200, ok_message()))
        result = ClaudeProvider(api_key="sk-test").generate("p", 400)

        assert result.success is True
        assert result.text == "1. SUBJECT: A\n   PREHEADER: B"
        assert result.model == "claude-opus-5"
        assert result.stop_reason == "end_turn"
        # Provider-reported, not estimated — this is what the ledger records.
        assert result.usage.input_tokens == 812
        assert result.usage.output_tokens == 143

    def test_joins_multiple_text_blocks_and_skips_others(self):
        blocks = [
            {"type": "thinking", "thinking": "not editorial output"},
            {"type": "text", "text": "first"},
            {"type": "text", "text": "second"},
        ]
        assert extract_text(blocks) == "first\nsecond"

    def test_truncated_output_is_reported_not_hidden(self, monkeypatch):
        monkeypatch.setattr(
            httpx, "post",
            lambda url, **kw: FakeResponse(200, ok_message(stop_reason="max_tokens")),
        )
        result = ClaudeProvider(api_key="sk-test").generate("p", 400)

        # The partial is still returned (display is not commit) but flagged.
        assert result.success is True
        assert result.text
        assert result.stop_reason == "max_tokens"


class TestFailurePaths:

    def test_missing_key_is_a_clean_failure(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = ClaudeProvider().generate("p", 400)

        assert result.success is False
        assert "ANTHROPIC_API_KEY" in result.message

    def test_network_error_does_not_raise(self, monkeypatch):
        def boom(url, **kwargs):
            raise httpx.ConnectError("no route to host")

        monkeypatch.setattr(httpx, "post", boom)
        result = ClaudeProvider(api_key="sk-test").generate("p", 400)

        assert result.success is False
        assert "network error" in result.message

    def test_api_error_surfaces_the_message(self, monkeypatch):
        monkeypatch.setattr(
            httpx, "post",
            lambda url, **kw: FakeResponse(
                401, {"type": "error", "error": {"type": "authentication_error",
                                                 "message": "invalid x-api-key"}}
            ),
        )
        result = ClaudeProvider(api_key="sk-bad").generate("p", 400)

        assert result.success is False
        assert "401" in result.message
        assert "invalid x-api-key" in result.message

    def test_refusal_is_a_failure_not_an_empty_success(self, monkeypatch):
        # A declined request returns HTTP 200 with empty content. Reporting it as
        # a success would show the manager "not in the requested format" instead
        # of what actually happened.
        monkeypatch.setattr(
            httpx, "post",
            lambda url, **kw: FakeResponse(200, ok_message(
                content=[], stop_reason="refusal",
                stop_details={"type": "refusal", "category": "cyber"},
            )),
        )
        result = ClaudeProvider(api_key="sk-test").generate("p", 400)

        assert result.success is False
        assert result.stop_reason == "refusal"
        assert "declined" in result.message
        assert "cyber" in result.message


class TestTokenCounting:

    def test_uses_the_count_tokens_endpoint(self, monkeypatch):
        captured = {}

        def fake_post(url, **kwargs):
            captured["url"] = url
            captured["json"] = kwargs["json"]
            return FakeResponse(200, {"input_tokens": 812})

        monkeypatch.setattr(httpx, "post", fake_post)
        count = ClaudeProvider(api_key="sk-test").count_input_tokens("some prompt")

        assert count == 812
        assert captured["url"] == COUNT_TOKENS_URL
        # Counting must describe the request that will actually be sent.
        assert captured["json"]["messages"] == [{"role": "user", "content": "some prompt"}]
        # max_tokens is an output ceiling; it has no place in an input count.
        assert "max_tokens" not in captured["json"]

    def test_counts_the_system_prompt_too(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            httpx, "post",
            lambda url, **kw: captured.update(kw["json"]) or FakeResponse(200, {"input_tokens": 9}),
        )
        ClaudeProvider(api_key="sk-test").count_input_tokens("p", system="s")
        assert captured["system"] == "s"

    def test_missing_key_refuses_rather_than_guessing(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(TokenCountUnavailable, match="ANTHROPIC_API_KEY"):
            ClaudeProvider().count_input_tokens("p")

    def test_network_error_refuses_rather_than_guessing(self, monkeypatch):
        def boom(url, **kwargs):
            raise httpx.ConnectError("no route to host")

        monkeypatch.setattr(httpx, "post", boom)
        # A fallback estimate here would quietly turn the spend cap into a guess.
        with pytest.raises(TokenCountUnavailable):
            ClaudeProvider(api_key="sk-test").count_input_tokens("p")

    def test_api_error_refuses_rather_than_guessing(self, monkeypatch):
        monkeypatch.setattr(
            httpx, "post",
            lambda url, **kw: FakeResponse(429, {"error": {"message": "rate limited"}}),
        )
        with pytest.raises(TokenCountUnavailable, match="rate limited"):
            ClaudeProvider(api_key="sk-test").count_input_tokens("p")

    def test_unexpected_body_refuses_rather_than_guessing(self, monkeypatch):
        monkeypatch.setattr(httpx, "post", lambda url, **kw: FakeResponse(200, {}))
        with pytest.raises(TokenCountUnavailable):
            ClaudeProvider(api_key="sk-test").count_input_tokens("p")


class TestModelSelection:

    def test_defaults_to_opus(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        assert ClaudeProvider(api_key="sk-test").model == DEFAULT_MODEL

    def test_env_can_override(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-5")
        assert ClaudeProvider(api_key="sk-test").model == "claude-sonnet-5"

    def test_explicit_argument_wins(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-5")
        assert ClaudeProvider(api_key="sk-test", model="claude-haiku-4-5").model == "claude-haiku-4-5"
