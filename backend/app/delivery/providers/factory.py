from app.delivery.providers.mock import MockProvider


def get_provider(provider_name: str):

    if provider_name == "mock":
        return MockProvider()

    raise ValueError(
        f"Unsupported provider: {provider_name}"
    )