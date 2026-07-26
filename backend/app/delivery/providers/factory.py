from app.delivery.providers.mock import MockProvider
from app.delivery.providers.resend import ResendProvider


def get_provider(provider_name: str, from_address: str | None = None):

    if provider_name == "mock":
        return MockProvider()

    if provider_name == "resend":
        # A per-send verified sender overrides the RESEND_FROM env default;
        # None keeps the adapter's env fallback (mock ignores it entirely).
        return ResendProvider(from_address=from_address)

    raise ValueError(
        f"Unsupported provider: {provider_name}"
    )