"""The zero-cost AI adapter — the DEV default, mirroring MockProvider for sends.

This is not scaffolding to delete later. It is permanent infrastructure:
  - the test suite must not depend on a paid external service;
  - ADR-143 requires development to work without production credentials, and an
    API key is a production credential like any other;
  - the whole Mode A flow (prompt → result → approval inbox → publish) can be
    built and demonstrated before anyone funds an API account.

What it cannot do is tell you whether a prompt is any *good*. Quality tuning
needs a real model; everything structural does not.
"""

import hashlib
import re

from app.ai.adapters.base import (
    AIProvider,
    AIResult,
    AIUsage,
)

MODEL_ID = "mock-1"

# Fallback when the prompt shows no example format to imitate.
DEFAULT_RESPONSE = (
    "1. Mock option one\n"
    "2. Mock option two\n"
    "3. Mock option three"
)

# A prompt that specifies its output format usually demonstrates it with
# angle-bracket placeholders, e.g. "SUBJECT: <subject>".
_PLACEHOLDER = re.compile(r"<([a-z_ ]{2,30})>", re.IGNORECASE)


def imitate_requested_format(prompt: str, options: int = 3) -> str | None:
    """Reproduce the output shape the prompt asked for, with mock values.

    A mock's job is to stand in *plausibly*: if a task's prompt demonstrates the
    layout it wants, real parsing code should get something in that layout back,
    or the pipeline can only ever be tested against a format nobody requested.
    Doing it by reading the prompt keeps the adapter task-agnostic — it never
    learns what a "subject line" is, so this works for future tasks too.

    Returns None when the prompt shows no example to imitate.
    """
    template_lines = [
        line for line in prompt.splitlines() if _PLACEHOLDER.search(line)
    ]
    if not template_lines:
        return None

    # Keep one cycle of the example (prompts usually repeat it 2-3 times).
    seen: list[str] = []
    for line in template_lines:
        normalised = _PLACEHOLDER.sub("<>", line.strip().lstrip("0123456789. "))
        if normalised in seen:
            break
        seen.append(normalised)
    cycle = template_lines[: len(seen)]

    blocks = []
    for n in range(1, options + 1):
        rendered = []
        for line in cycle:
            filled = _PLACEHOLDER.sub(
                lambda m: f"Mock {m.group(1).strip().lower()} {n}", line
            )
            rendered.append(filled.strip().lstrip("0123456789. "))
        blocks.append(f"{n}. " + "\n   ".join(rendered))
    return "\n".join(blocks)


def estimate_tokens(text: str) -> int:
    """Rough word-based approximation — good enough for a provider that bills nothing.

    Real adapters must report provider-counted tokens instead: the spend cap is
    only as trustworthy as its arithmetic, and a guess would quietly make the
    cap wrong (ADR-144).
    """
    if not text:
        return 0
    return max(1, int(len(text.split()) * 1.3))


class MockAIProvider(AIProvider):

    def __init__(
        self,
        canned_response: str | None = None,
        fail: bool = False,
    ):
        # `fail` exists so callers can exercise the failure path — a task must
        # degrade gracefully when the model is unavailable, and that branch needs
        # a way to be tested without unplugging anything.
        self.canned_response = canned_response
        self.fail = fail

    def generate(
        self,
        prompt: str,
        max_output_tokens: int,
        system: str | None = None,
    ) -> AIResult:

        if self.fail:
            return AIResult(
                success=False,
                model=MODEL_ID,
                message="mock provider configured to fail",
            )

        text = self.canned_response
        if text is None:
            # Same prompt in, same text out, so tests and previews are stable.
            digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
            body = imitate_requested_format(prompt) or DEFAULT_RESPONSE
            text = f"{body}\n\n[mock:{digest}]"

        output_tokens = estimate_tokens(text)
        stop_reason = "end_turn"

        # Honour the output ceiling the task declared, so callers can exercise
        # the truncation branch without paying a real model to overrun.
        if output_tokens > max_output_tokens:
            words = text.split()
            text = " ".join(words[: max(1, int(max_output_tokens / 1.3))])
            output_tokens = estimate_tokens(text)
            stop_reason = "max_tokens"

        return AIResult(
            success=True,
            text=text,
            usage=AIUsage(
                input_tokens=self.count_input_tokens(prompt, system),
                output_tokens=output_tokens,
            ),
            model=MODEL_ID,
            stop_reason=stop_reason,
            message="mock generation",
        )

    def count_input_tokens(
        self,
        prompt: str,
        system: str | None = None,
    ) -> int:
        return estimate_tokens(prompt) + estimate_tokens(system or "")
