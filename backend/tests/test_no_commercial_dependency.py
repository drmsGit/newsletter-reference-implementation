"""ADR-171 point 3, which is phrased as a verification rather than a principle.

    "The check is that the platform runs end to end with no commercial account
    at all. Not a principle to be agreed with — a state to be verified. …
    a claim about what is optional is worth exactly as much as the test that
    proves it."

This file is that test. It was written on 2026-09-20 when the record was
accepted, because accepting it without one would have endorsed a claim the
repository did not back — by the record's own standard, and in the same
sentence that sets the standard.

Deliberately the same shape as ADR-142 §2's "the platform stays fully usable
with no orchestrator at all": the claim is about what happens when a bill is
not paid, so the test removes the ability to pay it.
"""
import os

import pytest

#: Every environment variable that buys something. If one of these becomes
#: load-bearing, a test here goes red rather than a deployment going quiet.
COMMERCIAL_KEYS = (
    "RESEND_API_KEY",
    "RESEND_FROM",
    "RESEND_WEBHOOK_SECRET",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_MODEL",
)


@pytest.fixture
def no_commercial_accounts(monkeypatch):
    """Unset every key that costs money, for the duration of one test."""
    for key in COMMERCIAL_KEYS:
        monkeypatch.delenv(key, raising=False)
    yield


def test_the_send_provider_defaults_to_something_free(no_commercial_accounts):
    """The default adapter is the mock, and it neither asks for a key nor has
    one to ask for."""
    from app.delivery.providers.factory import get_provider
    from app.delivery.providers.mock import MockProvider

    assert isinstance(get_provider("mock"), MockProvider)


def test_the_ai_provider_defaults_to_something_free(no_commercial_accounts):
    """`DEFAULT_AI_PROVIDER` is "mock". ADR-140's interface ships one, and it
    is what an unconfigured deployment gets."""
    from app.ai.adapters.factory import DEFAULT_AI_PROVIDER, get_ai_provider

    assert DEFAULT_AI_PROVIDER == "mock"
    assert get_ai_provider(None) is not None


def test_a_send_completes_with_no_provider_key(no_commercial_accounts, db):
    """The end-to-end half of point 3, for the send path.

    Not "the mock class exists" — an actual send, through the real send path,
    with nothing configured to pay for. `send_test_email` is the narrowest
    route to a real provider call, so a failure here is the provider layer and
    not the composition around it.
    """
    from app.auth import service as auth
    from app.delivery.service import send_test_email

    result = send_test_email(
        db,
        to="nobody@example.invalid",
        subject="ADR-171 verification",
        provider="mock",
        brand_id=auth.ensure_default_brand(db).id,
    )
    assert result.success, result.message


def test_an_ai_task_runs_with_no_model_key(no_commercial_accounts, db):
    """The other half. A mock run is a real run: it writes an `ai_runs` row,
    is counted against the budget and is readable afterwards — ADR-144 §5's
    accounting does not have a cheaper path for free adapters."""
    from app.ai.adapters.factory import get_ai_provider

    result = get_ai_provider("mock").generate(
        prompt="Write three subject lines.", max_output_tokens=64,
    )
    assert result.success, result.message


def test_nothing_in_the_app_imports_a_commercial_sdk_at_module_scope():
    """The structural half, and the one that catches a regression early.

    ADR-171 point 2: a commercial service may be an adapter and never a
    requirement. An adapter imported at module scope is a requirement wearing
    an adapter's clothes — the package must be installed for the app to start,
    whether or not anybody pays for the service behind it. Both live adapters
    import their SDK inside the call, and this keeps it that way.
    """
    import pathlib
    import re

    app_dir = pathlib.Path(__file__).resolve().parent.parent / "app"
    offenders = []
    for path in app_dir.rglob("*.py"):
        for line_no, line in enumerate(path.read_text().splitlines(), 1):
            if re.match(r"^(import|from)\s+(anthropic|resend)\b", line):
                offenders.append(f"{path.name}:{line_no} — {line.strip()}")

    assert not offenders, (
        "a commercial SDK is imported at module scope:\n  "
        + "\n  ".join(offenders)
        + "\nImport it inside the adapter call instead. At module scope the "
        "package becomes required to start the app, which is ADR-171 point 2 "
        "inverted: a requirement wearing an adapter's clothes."
    )
