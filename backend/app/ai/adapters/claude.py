"""Claude adapter — the first *real* model behind the `AIProvider` contract.

Same shape and posture as the Resend outbound adapter (ADR-100/101): one file,
credentials from the environment, and nothing above it learns which vendor is
answering. Swapping to another model is another file plus one line in the
factory — that is the "no vendor lock-in" claim, demonstrated twice.

Credentials come from the environment, never code or the DB:
  ANTHROPIC_API_KEY   your Anthropic API key (sk-ant-...)     [required]
  ANTHROPIC_MODEL     override the model id (default below)   [optional]

Two things here are load-bearing for ADR-144's spend cap:

  1. `count_input_tokens()` calls Anthropic's own `count_tokens` endpoint. Not
     a word-count approximation — the cap is only as trustworthy as this
     number, and the whole point of a pre-call gate is that the arithmetic is
     real. When the count cannot be obtained the adapter raises rather than
     guessing (see TokenCountUnavailable).
  2. Usage is read back from the provider's own `usage` block, so the ledger
     records what was actually billed rather than what we predicted.
"""
import logging
import os

import httpx

from app.ai.adapters.base import (
    AIProvider,
    AIResult,
    AIUsage,
    TokenCountUnavailable,
)

logger = logging.getLogger(__name__)

API_BASE = "https://api.anthropic.com/v1"
MESSAGES_URL = f"{API_BASE}/messages"
COUNT_TOKENS_URL = f"{API_BASE}/messages/count_tokens"

# The dated API contract, not the model version — these move independently.
ANTHROPIC_VERSION = "2023-06-01"

DEFAULT_MODEL = "claude-opus-5"

# Generation is slower than a send; counting is a cheap round trip.
GENERATE_TIMEOUT = 60.0
COUNT_TIMEOUT = 15.0


def extract_text(blocks) -> str:
    """Join the text blocks of a Messages response.

    The reply is a list of typed content blocks, not a string. Only `text`
    blocks are editorial output; anything else the model emits is skipped
    rather than concatenated into copy a manager would be shown.
    """
    parts = [
        block.get("text") or ""
        for block in blocks or []
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    return "\n".join(part for part in parts if part).strip()


def error_detail(response) -> str:
    """Pull the human-readable message out of an API error body."""
    try:
        payload = response.json()
    except ValueError:
        return response.text
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict) and error.get("message"):
        return error["message"]
    return response.text


class ClaudeProvider(AIProvider):

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        thinking: bool = False,
    ):
        self.api_key = (
            api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY")
        )
        self.model = model or os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
        # Extended thinking is OFF by default, and that is a cost-cap decision
        # rather than a preference: `max_tokens` is a ceiling on thinking *plus*
        # reply, so on a task with a small output ceiling (subject lines declare
        # 400) the model could spend the entire budget reasoning and return a
        # truncated answer. Off, the ceiling means what the task intended and
        # the worst case stays tight. A future task that genuinely needs
        # reasoning turns it on here and raises its own ceiling to match.
        self.thinking = thinking

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key or "",
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

    def _body(self, prompt: str, system: str | None) -> dict:
        """The parts shared by generation and counting.

        Counting has to send the same prompt the call will send, or the number
        the gate is built on describes a different request.
        """
        body: dict = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system
        return body

    def generate(
        self,
        prompt: str,
        max_output_tokens: int,
        system: str | None = None,
    ) -> AIResult:

        if not self.api_key:
            return AIResult(
                success=False,
                model=self.model,
                message="ANTHROPIC_API_KEY is not set",
            )

        body = self._body(prompt, system)
        body["max_tokens"] = max_output_tokens
        if not self.thinking:
            body["thinking"] = {"type": "disabled"}

        try:
            response = httpx.post(
                MESSAGES_URL,
                headers=self._headers(),
                json=body,
                timeout=GENERATE_TIMEOUT,
            )
        except httpx.HTTPError as error:
            # Never raise for a failed generation — the task must degrade to a
            # recorded failure, not a 500 in the request path (as with sends).
            logger.warning("claude generate network error: %s", error)
            return AIResult(
                success=False,
                model=self.model,
                message=f"network error: {error}",
            )

        if response.status_code != 200:
            detail = error_detail(response)
            logger.warning(
                "claude generate failed: HTTP %s — %s", response.status_code, detail
            )
            return AIResult(
                success=False,
                model=self.model,
                message=f"HTTP {response.status_code}: {detail}",
            )

        payload = response.json()
        reported = payload.get("usage") or {}
        usage = AIUsage(
            input_tokens=int(reported.get("input_tokens") or 0),
            output_tokens=int(reported.get("output_tokens") or 0),
        )
        model = payload.get("model") or self.model
        stop_reason = payload.get("stop_reason")

        if stop_reason == "refusal":
            # A declined request still returns HTTP 200, with empty content. It
            # is a failure for the task (there is nothing to offer the manager),
            # so it is reported as one rather than as an empty success that the
            # UI would describe as a formatting problem.
            details = payload.get("stop_details") or {}
            category = details.get("category")
            logger.info("claude declined the request (category=%s)", category)
            return AIResult(
                success=False,
                usage=usage,
                model=model,
                stop_reason=stop_reason,
                message=(
                    "the model declined this request"
                    + (f" ({category})" if category else "")
                ),
            )

        logger.info(
            "claude generate ok: model=%s in=%s out=%s stop=%s",
            model, usage.input_tokens, usage.output_tokens, stop_reason,
        )
        return AIResult(
            success=True,
            text=extract_text(payload.get("content")),
            usage=usage,
            model=model,
            stop_reason=stop_reason,
            message="generated",
        )

    def count_input_tokens(
        self,
        prompt: str,
        system: str | None = None,
    ) -> int:
        """The provider's own count — never an estimate (ADR-144 §5).

        Raises TokenCountUnavailable rather than falling back to a guess: a
        cap computed from a guess would quietly stop being a cap.
        """
        if not self.api_key:
            raise TokenCountUnavailable("ANTHROPIC_API_KEY is not set")

        try:
            response = httpx.post(
                COUNT_TOKENS_URL,
                headers=self._headers(),
                json=self._body(prompt, system),
                timeout=COUNT_TIMEOUT,
            )
        except httpx.HTTPError as error:
            raise TokenCountUnavailable(f"network error: {error}") from error

        if response.status_code != 200:
            raise TokenCountUnavailable(
                f"HTTP {response.status_code}: {error_detail(response)}"
            )

        try:
            return int(response.json()["input_tokens"])
        except (ValueError, KeyError, TypeError) as error:
            raise TokenCountUnavailable(
                "the count_tokens response carried no input_tokens"
            ) from error
