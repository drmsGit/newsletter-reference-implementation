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
