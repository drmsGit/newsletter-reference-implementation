"""Adapter lookup by name — the same shape as delivery/providers/factory.py.

Adding a model is a new file plus one branch here. Kept as an explicit mapping
rather than auto-discovery on purpose: which models a deployment may call is a
governed choice (ADR-140's kill switch and per-company enablement), not
something that should follow from a file appearing on disk.
"""

from app.ai.adapters.base import AIProvider
from app.ai.adapters.claude import ClaudeProvider
from app.ai.adapters.mock import MockAIProvider

# The DEV default. Same reasoning as provider="mock" for sends: the safe,
# free, offline option is what you get unless a deployment opts into a real one.
DEFAULT_AI_PROVIDER = "mock"

# What a deployment is allowed to select, in UI order. The governed list itself
# (ADR-140) — a name absent here cannot be chosen or saved, which is why the
# settings form validates against it rather than accepting free text.
AVAILABLE_AI_PROVIDERS = ("mock", "claude")


def get_ai_provider(provider_name: str | None = None, model: str | None = None) -> AIProvider:
    """The adapter, optionally pinned to a model.

    `model=None` keeps the adapter's own default (env override, then its
    constant), which is what every caller did before per-task selection
    existed — so a deployment that has not chosen anything is unchanged.

    The mock ignores it deliberately: it bills nothing and returns a fixed
    shape, so pretending it honours a model choice would put a value in the
    audit row that meant nothing.
    """
    name = provider_name or DEFAULT_AI_PROVIDER

    if name == "mock":
        return MockAIProvider()

    if name == "claude":
        return ClaudeProvider(model=model)

    raise ValueError(
        f"Unsupported AI provider: {name}"
    )
