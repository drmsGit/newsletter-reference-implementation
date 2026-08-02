"""What a run actually cost — the money view of the token ledger (ADR-144 §5).

The cap is enforced in *tokens*, deliberately: tokens are the unit the pre-call
gate can compute a worst case in, and they move in visible increments where a
currency figure would sit at $0.00 for the first few hundred runs. Money is the
unit a manager budgets in, though, so it is reported alongside — one enforced
number, one human number, never two competing gates.

Two rules here are worth stating because they point in opposite directions, and
each is the safe direction for its own question:

  - **Billability is decided by provider, defaulting to "it costs money."** A
    provider is free only if it is named as free. Add a paid adapter and forget
    to price it, and its tokens still count against the cap — the gate degrades
    to conservative, never to permissive.
  - **Cost is decided by model, defaulting to "unknown."** An unpriced model
    contributes nothing to the money figure and is reported separately, because
    silently pricing it at zero would show a manager a total that is wrong in
    the one direction that matters.
"""

# Published list prices in USD per million tokens, as (input, output).
# Verified 2026-08-02. These are vendor facts with no API to read them from, so
# they need re-checking when a model is added or a price changes; a stale entry
# shows a wrong total rather than failing, which is why the date is recorded.
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-5": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    # The mock adapter bills nothing; priced explicitly so it reads as a
    # deliberate zero rather than a model somebody forgot to add.
    "mock-1": (0.00, 0.00),
}

# Adapters that cannot cost money, whatever they report. Everything else is
# assumed billable — see the module docstring.
FREE_PROVIDERS = frozenset({"mock"})


def is_billable(provider: str | None) -> bool:
    """Whether a run's tokens should count against the spend cap."""
    return provider not in FREE_PROVIDERS


def cost_usd(
    model: str | None,
    input_tokens: int,
    output_tokens: int,
) -> float | None:
    """Cost of one run, or None when the model has no published price here."""
    rates = MODEL_PRICING.get(model or "")
    if rates is None:
        return None
    input_rate, output_rate = rates
    return (
        (input_tokens or 0) * input_rate + (output_tokens or 0) * output_rate
    ) / 1_000_000
