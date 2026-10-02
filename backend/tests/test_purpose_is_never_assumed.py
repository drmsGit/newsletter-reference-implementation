"""A consent purpose is said, never assumed (task-42; ADR-163 and its
2026-09-15 addendum's reasoning about `brand_id`).

"A consent row whose brand was assumed is a consent record nobody gave." The
same holds for purpose: a row whose purpose was assumed is a marketing grant
nobody gave. These pin the two places an assumption could come back.
"""
import importlib
import inspect

import pytest

from app.delivery.db_models import DeliveryExecutionDB

_MODULES = ("app.recipients.consent", "app.recipients.service", "app.delivery.exclusion")


def _functions_taking_purpose():
    for name in _MODULES:
        module = importlib.import_module(name)
        for fname, fn in inspect.getmembers(module, inspect.isfunction):
            if fn.__module__ == name and "purpose" in inspect.signature(fn).parameters:
                yield f"{name}.{fname}", inspect.signature(fn).parameters["purpose"]


def test_there_are_consent_functions_to_check():
    """Guards the next test against passing because it found nothing."""
    assert len(list(_functions_taking_purpose())) >= 10


@pytest.mark.parametrize("qualified, parameter", list(_functions_taking_purpose()))
def test_no_consent_function_defaults_purpose(qualified, parameter):
    assert parameter.default is inspect.Parameter.empty, (
        f"{qualified} defaults purpose to {parameter.default!r}: a caller that "
        "forgets it records or checks a purpose nobody chose"
    )


@pytest.mark.parametrize("column", ["channel", "purpose"])
def test_an_execution_has_no_default_channel_or_purpose(column):
    """migrate_0024 dropped the database defaults; the Python-side ones are
    how a push send's late joiner was planned as an email (task-42)."""
    col = DeliveryExecutionDB.__table__.c[column]
    assert col.default is None and col.server_default is None, column
