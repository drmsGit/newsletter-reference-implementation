"""The **addressed** delivery interface — ADR-161 point 1.

One interface for every channel that delivers to an address: email, push, SMS,
WhatsApp and (per point 5) letter, "with the payload type declared by the
manifest". Not one interface per channel, and emphatically not one interface
with optional methods — that is a capability system whose capabilities are
discovered by calling and catching, which is the thing ADR-101 exists to
prevent.

The second interface ADR-161 names is **audience-delegated** (paid social,
roughly `sync_audience` + `attach_creative`). It is not built, because paid
social is deferred. When it is, it lives beside this one rather than growing
optional methods here, and the typed contracts buy fail-closed behaviour for
free: code that only knows how to address recipients cannot be handed a
delegated provider, because the type does not fit.

**Why `send` takes an artifact rather than subject + html.** A `subject`
parameter is an email concern that every other channel would have to ignore,
and a push has no document to put in `html`. The artifact carries its own
payload and its own envelope, so the interface says the same thing for all of
them: deliver this, to this address.
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel

from app.rendering.renderers.base import RenderedArtifact


class SendResult(BaseModel):
    success: bool
    # None on failure — a failed send has no provider message id, and the
    # DeliveryExecution column is nullable+unique (multiple nulls are fine),
    # so failures don't collide on an empty string.
    provider_message_id: str | None = None
    message: str | None = None


class DeliveryProvider(ABC):
    """A vendor that delivers to an address.

    `channels` is the adapter's own declaration of what it can carry, and the
    factory refuses a mismatch rather than letting it fail at the vendor —
    ADR-101's "capabilities are explicit", applied to the one capability that
    is now ambiguous: Resend cannot deliver a push, and asking it to is a
    configuration error worth naming at the point of the request.
    """

    #: Channel names this adapter can deliver. Empty means every channel,
    #: which only a mock should claim.
    channels: frozenset[str] = frozenset()

    def supports(self, channel: str) -> bool:
        return not self.channels or channel in self.channels

    @abstractmethod
    def send(self, address: str, artifact: RenderedArtifact) -> SendResult:
        ...
