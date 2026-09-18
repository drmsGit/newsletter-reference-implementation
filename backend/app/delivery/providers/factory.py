"""Which adapter carries which channel — ADR-161 point 1 plus ADR-101.

The channel is part of the question now, not an assumption. Before push, every
send was email and `get_provider("resend")` could only mean one thing; asking
Resend to deliver a notification would have failed at the vendor with a
message about a malformed request, which is a poor way to find out somebody
configured a push send with an email provider.
"""

from app.delivery.providers.mock import MockProvider
from app.delivery.providers.resend import ResendProvider


def get_provider(provider_name: str, from_address: str | None = None,
                 channel: str | None = None):
    """The adapter for this provider, refused if it cannot carry the channel.

    `channel=None` skips the check, which is what the system-mail path and the
    standalone send-test page pass: both are email by construction and neither
    has a variant to read a channel from.
    """
    if provider_name == "mock":
        provider = MockProvider()
    elif provider_name == "resend":
        # A per-send verified sender overrides the RESEND_FROM env default;
        # None keeps the adapter's env fallback (mock ignores it entirely).
        provider = ResendProvider(from_address=from_address)
    else:
        raise ValueError(f"Unsupported provider: {provider_name}")

    if channel is not None and not provider.supports(channel):
        raise ValueError(
            f"provider '{provider_name}' cannot deliver on the '{channel}' "
            f"channel — it carries {', '.join(sorted(provider.channels))}"
        )
    return provider


#: Human labels for the picker. The mock's wording is channel-neutral on
#: purpose — "no real email" was accurate while email was the only channel and
#: became wrong the moment a push could be planned through it.
PROVIDER_LABELS = {
    "mock": "mock (nothing is sent)",
    "resend": "resend (real)",
}
#: Which adapters need a sender address. A push has no from-address, so
#: offering the field is noise; a letter would need a return address, which is
#: not the same field and is a question for whoever builds that channel.
PROVIDERS_WITH_FROM_ADDRESS = frozenset({"resend"})


def providers_for_channel(channel: str) -> list[dict]:
    """The adapters that can carry this channel, for a picker.

    Reads the same `channels` declaration `get_provider` enforces, so the form
    cannot offer something the factory will refuse. Before this, the send form
    listed resend for every variant — including a push, where planning it
    produced an error at trigger time about a channel the manager had never
    been asked to think about.
    """
    return [
        {
            "name": name,
            "label": PROVIDER_LABELS.get(name, name),
            "needs_from_address": name in PROVIDERS_WITH_FROM_ADDRESS,
        }
        for name, cls in (("mock", MockProvider), ("resend", ResendProvider))
        if cls().supports(channel)
    ]
