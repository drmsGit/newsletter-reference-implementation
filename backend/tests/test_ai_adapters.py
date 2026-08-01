"""Tests for the AI model adapter (ADR-144).

Pure unit tests: no database, no network, no API key. That is the point of the
mock adapter — the AI layer must be testable without a paid account (ADR-143).
"""

import pytest

from app.ai.adapters.base import AIProvider
from app.ai.adapters.factory import get_ai_provider, DEFAULT_AI_PROVIDER
from app.ai.adapters.mock import MockAIProvider, MODEL_ID


class TestFactory:

    def test_defaults_to_mock(self):
        # The free, offline adapter is what you get unless you ask otherwise —
        # same posture as provider="mock" for sends.
        assert DEFAULT_AI_PROVIDER == "mock"
        assert isinstance(get_ai_provider(), MockAIProvider)

    def test_returns_mock_by_name(self):
        assert isinstance(get_ai_provider("mock"), MockAIProvider)

    def test_unknown_provider_rejected(self):
        # Unsupported names fail loudly rather than silently falling back to a
        # provider the deployment never enabled.
        with pytest.raises(ValueError, match="Unsupported AI provider"):
            get_ai_provider("definitely-not-a-model")

    def test_mock_satisfies_the_contract(self):
        assert isinstance(get_ai_provider("mock"), AIProvider)


class TestMockGeneration:

    def test_returns_text_and_usage(self):
        result = MockAIProvider().generate("Write three subject lines.", max_output_tokens=200)

        assert result.success is True
        assert result.text
        assert result.model == MODEL_ID
        assert result.stop_reason == "end_turn"
        # Usage must be populated or cost accounting has nothing to record.
        assert result.usage is not None
        assert result.usage.input_tokens > 0
        assert result.usage.output_tokens > 0

    def test_same_prompt_gives_same_output(self):
        provider = MockAIProvider()
        first = provider.generate("identical prompt", max_output_tokens=200)
        second = provider.generate("identical prompt", max_output_tokens=200)
        assert first.text == second.text

    def test_different_prompts_give_different_output(self):
        provider = MockAIProvider()
        a = provider.generate("prompt A", max_output_tokens=200)
        b = provider.generate("prompt B", max_output_tokens=200)
        assert a.text != b.text

    def test_canned_response_overrides(self):
        provider = MockAIProvider(canned_response="Exactly this.")
        assert provider.generate("anything", max_output_tokens=200).text == "Exactly this."

    def test_failure_path(self):
        # A task has to degrade gracefully when the model is unavailable; that
        # branch needs to be reachable without unplugging anything.
        result = MockAIProvider(fail=True).generate("anything", max_output_tokens=200)

        assert result.success is False
        assert result.text is None
        assert result.usage is None


class TestOutputCeiling:

    def test_respects_max_output_tokens(self):
        # ADR-144: the task declares its own output ceiling, and the worst-case
        # total is only knowable in advance if the provider actually honours it.
        long_text = " ".join(["word"] * 500)
        result = MockAIProvider(canned_response=long_text).generate("p", max_output_tokens=20)

        assert result.usage.output_tokens <= 20
        assert result.stop_reason == "max_tokens"

    def test_truncated_output_is_still_returned(self):
        # Hitting the ceiling must not throw the partial away — the manager
        # should see what was produced, even though it is not committed.
        long_text = " ".join(["word"] * 500)
        result = MockAIProvider(canned_response=long_text).generate("p", max_output_tokens=20)

        assert result.success is True
        assert result.text


class TestPreCallGate:

    def test_counts_input_before_sending(self):
        # The spend cap is enforced *before* the call, so the worst case has to
        # be computable without generating anything.
        provider = MockAIProvider()
        assert provider.count_input_tokens("a few words here") > 0
        assert provider.count_input_tokens("") == 0

    def test_system_prompt_counts_towards_input(self):
        provider = MockAIProvider()
        without = provider.count_input_tokens("prompt")
        with_system = provider.count_input_tokens("prompt", system="a system prompt")
        assert with_system > without

    def test_worst_case_is_knowable_in_advance(self):
        # The whole pre-call gate reduces to this arithmetic.
        provider = MockAIProvider()
        prompt, ceiling = "some prompt text", 150

        worst_case = provider.count_input_tokens(prompt) + ceiling
        result = provider.generate(prompt, max_output_tokens=ceiling)
        actual = result.usage.input_tokens + result.usage.output_tokens

        assert actual <= worst_case
