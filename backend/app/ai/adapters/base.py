"""The AI model adapter contract (ADR-144).

Deliberately the same shape as the outbound `DeliveryProvider` (ADR-100): a small
abstract base plus a pydantic result, so adding or swapping a model is one file
and the rest of the architecture never learns which vendor is behind it.
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel


class TokenCountUnavailable(RuntimeError):
    """Raised when an adapter cannot count a prompt's input tokens.

    Deliberately an error rather than a fallback estimate. ADR-144's spend cap
    is a *pre-call* gate, and a gate computed from a guess is not a gate — it
    would let a run start on a number nobody verified. So an adapter that
    cannot answer says so, and the caller refuses the run instead of spending
    against arithmetic it cannot trust.
    """


class AIUsage(BaseModel):
    """Tokens actually consumed by one call — the input to cost accounting."""

    input_tokens: int
    output_tokens: int


class AIResult(BaseModel):
    success: bool
    # None on failure, mirroring SendResult.provider_message_id.
    text: str | None = None
    usage: AIUsage | None = None
    # The concrete model that produced the text (not the adapter name), because
    # ADR-140 requires the audit row to record which model was used.
    model: str | None = None
    # Why generation stopped. "max_tokens" means the output hit its ceiling and
    # is truncated — the caller may still show the partial (ADR-144: display is
    # not the same as commit), it just must not treat it as complete.
    stop_reason: str | None = None
    message: str | None = None


class AIProvider(ABC):

    @abstractmethod
    def generate(
        self,
        prompt: str,
        max_output_tokens: int,
        system: str | None = None,
    ) -> AIResult:
        pass

    @abstractmethod
    def count_input_tokens(
        self,
        prompt: str,
        system: str | None = None,
    ) -> int:
        """Tokens this prompt will cost *before* it is sent.

        Required, not optional: ADR-144 enforces the spend cap as a pre-call gate,
        computing a task's worst case as count_input_tokens() + max_output_tokens
        and refusing to start anything that would not fit under the remaining cap.
        An adapter that cannot answer this cannot participate in the cap, so the
        capability is part of the contract rather than an extra (ADR-101).
        """
        pass
