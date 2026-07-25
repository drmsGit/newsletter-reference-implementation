from app.delivery.providers.mock import MockProvider
from app.delivery.providers.resend import ResendProvider


def get_provider(provider_name: str):

    if provider_name == "mock":
        return MockProvider()

    if provider_name == "resend":
        return ResendProvider()

    raise ValueError(
        f"Unsupported provider: {provider_name}"
    )