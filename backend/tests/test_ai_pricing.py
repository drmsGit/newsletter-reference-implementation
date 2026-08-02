"""Tests for the money view of the token ledger (ADR-144 §5).

The two defaults here point in opposite directions on purpose, and both are
the safe direction for their own question: an unknown *provider* is assumed to
cost money (so the cap never under-counts), while an unknown *model* has no
price (so the money figure is never quietly wrong).
"""
import pytest

from app.ai.pricing import MODEL_PRICING, cost_usd, is_billable


class TestBillability:

    def test_mock_is_free(self):
        assert is_billable("mock") is False

    def test_claude_is_billable(self):
        assert is_billable("claude") is True

    def test_unknown_provider_is_assumed_to_cost_money(self):
        # A paid adapter added without being priced must still consume the cap.
        # Degrading to conservative is safe; degrading to permissive is not.
        assert is_billable("some-future-vendor") is True


class TestCost:

    def test_prices_a_real_run(self):
        # 698 in + 224 out on Opus 5 at $5 / $25 per million.
        expected = (698 * 5.00 + 224 * 25.00) / 1_000_000
        assert cost_usd("claude-opus-5", 698, 224) == pytest.approx(expected)
        assert cost_usd("claude-opus-5", 698, 224) == pytest.approx(0.00909)

    def test_output_costs_five_times_input_on_opus(self):
        # Why a token cap only approximates a dollar cap: the same token count
        # costs very different amounts depending on the mix.
        all_in = cost_usd("claude-opus-5", 1000, 0)
        all_out = cost_usd("claude-opus-5", 0, 1000)
        assert all_out == pytest.approx(all_in * 5)

    def test_mock_costs_nothing(self):
        assert cost_usd("mock-1", 10_000, 10_000) == 0.0

    def test_unknown_model_has_no_price(self):
        # None, not 0.0 — the caller has to decide what to do about it rather
        # than folding an unknown into a total that then reads as authoritative.
        assert cost_usd("claude-something-unreleased", 1000, 1000) is None
        assert cost_usd(None, 1000, 1000) is None

    def test_zero_tokens_costs_zero(self):
        assert cost_usd("claude-opus-5", 0, 0) == 0.0

    def test_every_priced_model_has_both_rates(self):
        for model, rates in MODEL_PRICING.items():
            assert len(rates) == 2, model
            assert all(rate >= 0 for rate in rates), model
