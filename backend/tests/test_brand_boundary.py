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
import uuid

from fastapi.testclient import TestClient

from app.auth.permissions import CONTENT_MANAGE, VIEW
from main import app

client = TestClient(app, raise_server_exceptions=False)

APP = pathlib.Path(__file__).resolve().parent.parent / "app"

#: The functions allowed to read across every brand at once.
#:
#: ADR-172 point 4 makes `brand_id` a required argument, which leaves the
#: genuine spanning callers — platform counts, migrations, seeds, tests — with
#: nowhere to go. `list_all_*()` is that somewhere, and its whole value is that
#: it says in its own name what it is doing.
#:
#: The remaining entries arrive with stages 4 and 5: `list_all_campaigns`,
#: `list_all_audience_groups`. A further one is not forbidden — it is a diff
#: that has to be argued for, which is the entire mechanism.
#:
#: `list_all_content_records` (stage 3, 2026-09-19) replaces
#: `list_content_records(db)` with no brand, which returned every brand's rows
#: to anyone who forgot an argument. The callers that genuinely span brands are
#: the demo seed and the platform counts on the dashboard.
SPANNING_FUNCTIONS: set[str] = {"list_all_content_records"}


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


def test_the_guard_leaves_the_presentation_brand_alone():
    """`current_brand` and the working brand are two things (ADR-172 point 1).

    The middleware builds `request.state.current_brand` as a presentation
    summary — it carries `switchable`, and `base.html` reads it. Until
    2026-09-19 the API guard overwrote that with `{"id": brand_id}`, which was
    survivable only because it happened on brand-scoped writes and nowhere
    else. Point 1 resolves a brand on *every* request, so the same line would
    now run on every request: a rare shape collision becoming a universal one.

    Asserted against the source rather than a response, because the failure is
    invisible from outside — the JSON caller gets exactly what it expected and
    a template three layers away loses a key.
    """
    source = (APP / "auth" / "dependencies.py").read_text()
    offenders = [
        source[: m.start()].count("\n") + 1
        for m in re.finditer(r"request\.state\.current_brand\s*=", source)
    ]
    assert not offenders, (
        f"the API guard assigns request.state.current_brand at line(s) {offenders}. "
        "That attribute belongs to the middleware and carries a different shape; "
        "the resolved working brand goes to request.state.working_brand_id."
    )


# --- content, stage 3 -------------------------------------------------------

class TestContentIsAddressableOnlyWithinItsBrand:
    """ADR-172 points 4-6 over the JSON plane, for `content_records`.

    Every test here authorises the caller on `foreign_brand` and addresses a
    record in the default brand. That direction is deliberate: every fallback
    in this codebase returns the default brand, so a caller authorised on the
    default brand could not tell a working filter from a deleted one.
    """

    def _default_brand_record(self):
        from app.auth.service import ensure_default_brand
        from app.content.service import create_content
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            record = create_content(
                db,
                title=f"boundary-{uuid.uuid4().hex[:8]}",
                brand_id=ensure_default_brand(db).id,
                content={"headline_medium": "not yours"},
            )
            return record.id
        finally:
            db.close()

    def _remove(self, record_id):
        from app.content.db_models import ContentRecordDB
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            db.query(ContentRecordDB).filter(ContentRecordDB.id == record_id).delete()
            db.commit()
        finally:
            db.close()

    def test_a_record_in_another_brand_answers_as_absent(self, foreign_api):
        """404, and identical to a record that never existed (point 6).

        A guessable integer id is not a secret, so "you may not see this" and
        "this is not here" have to read the same from outside. The reason the
        caller actually wanted is in the server log, on our side of the wire.
        """
        record_id = self._default_brand_record()
        try:
            with foreign_api([VIEW]) as headers:
                assert client.get(f"/content/{record_id}", headers=headers).status_code == 404
                assert client.get("/content/999999999", headers=headers).status_code == 404
        finally:
            self._remove(record_id)

    def test_a_list_carries_only_the_declared_brands_records(self, foreign_api):
        record_id = self._default_brand_record()
        try:
            with foreign_api([VIEW]) as headers:
                response = client.get("/content/", headers=headers)
                assert response.status_code == 200, response.text
                assert record_id not in [row["id"] for row in response.json()]
        finally:
            self._remove(record_id)

    def test_a_write_across_the_boundary_changes_nothing(self, foreign_api):
        """**The status code alone would not catch this.**

        A boundary enforced by loading the row and then refusing would return
        404 here too — and would have written first if the refusal sat one line
        later. Point 5 puts the brand in the selecting query so the row is
        never in hand at all; asserting the row is untouched is what tells the
        two designs apart.
        """
        from app.content.db_models import ContentRecordDB
        from app.database import SessionLocal

        record_id = self._default_brand_record()
        try:
            with foreign_api([VIEW, CONTENT_MANAGE]) as headers:
                response = client.put(
                    f"/content/{record_id}",
                    json={"title": "seized", "content": {"headline_medium": "mine now"}},
                    headers=headers,
                )
                assert response.status_code == 404, response.text

            db = SessionLocal()
            try:
                row = db.query(ContentRecordDB).filter(
                    ContentRecordDB.id == record_id
                ).first()
                assert row.title != "seized", "the write landed before the refusal"
                assert row.content == {"headline_medium": "not yours"}
            finally:
                db.close()
        finally:
            self._remove(record_id)
