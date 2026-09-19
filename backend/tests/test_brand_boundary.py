"""The brand boundary on the JSON plane — ADR-172, accepted 2026-09-19.

Brand scoping was enforced in `app/frontend/router.py` and essentially nowhere
else: fifteen call sites there passed `brand_id`, and the JSON routers passed
it at none. Since the Jinja UI has a deletion date (ADR-170), that arrangement
did not *hold* the boundary so much as *borrow* it from a layer we are about to
delete.

The tests in this file are the wiring checks — the ones that answer "is the
rule still in force everywhere", as distinct from "does this route behave".
They are written **before** the rule exists, asserting today's trivially-true
state, so that the day one of them goes red it is the code that moved and not
the test that was adjusted to match it.

Same idiom as `test_api_guard.py`'s `test_every_json_router_carries_the_csrf_guard`
and `test_exactly_one_route_is_exempt_as_provider_signed`, and for the same
reason `policy.py:62` gives for the latter: *"A test asserts each list exactly,
so widening either is an edit somebody has to justify."*
"""
import pathlib
import re

APP = pathlib.Path(__file__).resolve().parent.parent / "app"

#: The functions allowed to read across every brand at once.
#:
#: ADR-172 point 4 makes `brand_id` a required argument, which leaves the
#: genuine spanning callers — platform counts, migrations, seeds, tests — with
#: nowhere to go. `list_all_*()` is that somewhere, and its whole value is that
#: it says in its own name what it is doing.
#:
#: **Empty on purpose, today.** The entries arrive with stages 3, 4 and 5:
#: `list_all_content_records`, `list_all_campaigns`, `list_all_audience_groups`.
#: A fourth is not forbidden — it is a diff that has to be argued for, which is
#: the entire mechanism.
SPANNING_FUNCTIONS: set[str] = set()


def _service_sources() -> dict[pathlib.Path, str]:
    return {p: p.read_text() for p in APP.rglob("service.py")}


def _router_sources() -> dict[pathlib.Path, str]:
    return {p: p.read_text() for p in APP.rglob("router.py")}


def test_the_spanning_functions_are_exactly_these():
    """Widening the escape hatch must be an edit somebody signed.

    An escape hatch that nobody counts stops being an escape hatch and becomes
    the road. Asserting the set exactly — rather than "these exist" — means a
    fourth spanning function cannot arrive quietly as a convenience while
    somebody was fixing something else.
    """
    found = set()
    for path, source in _service_sources().items():
        found |= set(re.findall(r"^def (list_all_[a-z0-9_]+)\(", source, re.M))

    assert found == SPANNING_FUNCTIONS, (
        f"the set of brand-spanning functions changed: {found ^ SPANNING_FUNCTIONS}. "
        "If that is deliberate, edit SPANNING_FUNCTIONS in this file and say in "
        "the commit message which caller needed to span every brand and why it "
        "could not name one."
    )


def test_no_router_reaches_for_a_spanning_function():
    """The escape hatch is for callers that have no request, not for routes.

    Every route has a working brand — that is ADR-172 point 1, and the whole
    reason the dependency exists. So a router calling `list_all_*` is not a
    caller that legitimately spans brands; it is one that had a brand available
    and did not use it.

    Checked by reading the source rather than by calling anything, because the
    failure this catches is a route that *works* — it returns rows, the tests
    pass, and it returns every brand's rows. Point 7's reasoning exactly: a
    forgotten filter in a router is invisible.
    """
    offenders = []
    for path, source in _router_sources().items():
        for match in re.finditer(r"\blist_all_[a-z0-9_]+", source):
            line = source[: match.start()].count("\n") + 1
            offenders.append(f"{path.relative_to(APP.parent)}:{line} — {match.group(0)}")

    assert not offenders, (
        "a router reached for a brand-spanning function:\n  "
        + "\n  ".join(offenders)
        + "\nA route has a working brand (ADR-172 point 1). Pass it."
    )
