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

from app.auth.permissions import CAMPAIGNS_MANAGE, CONTENT_MANAGE, VIEW
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
#: The remaining entry arrives with stage 5: `list_all_audience_groups`.
#: A further one is not forbidden — it is a diff
#: that has to be argued for, which is the entire mechanism.
#:
#: `list_all_content_records` (stage 3, 2026-09-19) replaces
#: `list_content_records(db)` with no brand, which returned every brand's rows
#: to anyone who forgot an argument. The callers that genuinely span brands are
#: the demo seed and the platform counts on the dashboard.
SPANNING_FUNCTIONS: set[str] = {
    "list_all_content_records",
    "list_all_campaigns",
}


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


# --- campaigns and the nested chain, stage 4 --------------------------------

class TestTheNestedChainIsWalkedNotTrusted:
    """ADR-172 point 5 over `campaign -> variant -> module / slot / resolution`.

    Nothing below `campaigns` carries a `brand_id`, so every one of these is a
    join rather than a column comparison. The deepest is three hops, and the
    2026-09-20 addendum measured it at eight buffers — the joins are not the
    expensive part, a missing index on `decision_slot_id` is.
    """

    def _campaign_in_default_brand(self):
        from app.auth.service import ensure_default_brand
        from app.campaigns.service import (
            create_campaign, create_decision_slot_for_variant,
            create_module_for_variant,
        )
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            brand = ensure_default_brand(db).id
            campaign = create_campaign(
                db, name=f"boundary-{uuid.uuid4().hex[:8]}", brand_id=brand,
                channel="email",
            )
            variant = campaign.variants[0]
            module = create_module_for_variant(
                db, variant_id=variant.id, module_type="cta",
                module_data={"label": "not yours"}, brand_id=brand,
            )
            slot = create_decision_slot_for_variant(
                db, variant_id=variant.id, name="slot", brand_id=brand,
            )
            return {
                "campaign": campaign.id, "variant": variant.id,
                "module": module.id, "slot": slot.id,
            }
        finally:
            db.close()

    def _remove(self, ids):
        from app.campaigns.db_models import (
            CampaignDB, DecisionSlotDB, ModuleInstanceDB, VariantDB,
        )
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            db.query(ModuleInstanceDB).filter(
                ModuleInstanceDB.variant_id == ids["variant"]).delete()
            db.query(DecisionSlotDB).filter(
                DecisionSlotDB.variant_id == ids["variant"]).delete()
            db.query(VariantDB).filter(VariantDB.campaign_id == ids["campaign"]).delete()
            db.query(CampaignDB).filter(CampaignDB.id == ids["campaign"]).delete()
            db.commit()
        finally:
            db.close()

    def test_a_module_two_hops_away_is_not_reachable(self, foreign_api):
        """`module -> variant -> campaign -> brand`, and the module carries none
        of it. Deleting is the sharpest verb available on this route."""
        from app.campaigns.db_models import ModuleInstanceDB
        from app.database import SessionLocal

        ids = self._campaign_in_default_brand()
        try:
            with foreign_api([VIEW, CAMPAIGNS_MANAGE]) as headers:
                response = client.delete(
                    f"/campaigns/modules/{ids['module']}", headers=headers)
                assert response.status_code == 404, response.text

            db = SessionLocal()
            try:
                assert db.query(ModuleInstanceDB).filter(
                    ModuleInstanceDB.id == ids["module"]
                ).first() is not None, "the module was deleted across the boundary"
            finally:
                db.close()
        finally:
            self._remove(ids)

    def test_a_variants_modules_are_not_listable_from_another_brand(self, foreign_api):
        ids = self._campaign_in_default_brand()
        try:
            with foreign_api([VIEW]) as headers:
                response = client.get(
                    f"/campaigns/variants/{ids['variant']}/modules", headers=headers)
                assert response.status_code == 200, response.text
                assert response.json() == [], (
                    "another brand's modules were listed"
                )
        finally:
            self._remove(ids)

    def test_a_variant_cannot_be_renamed_from_another_brand(self, foreign_api):
        from app.campaigns.db_models import VariantDB
        from app.database import SessionLocal

        ids = self._campaign_in_default_brand()
        try:
            with foreign_api([VIEW, CAMPAIGNS_MANAGE]) as headers:
                response = client.put(
                    f"/campaigns/variants/{ids['variant']}",
                    json={"name": "seized"}, headers=headers)
                assert response.status_code == 404, response.text

            db = SessionLocal()
            try:
                assert db.query(VariantDB).filter(
                    VariantDB.id == ids["variant"]).first().name != "seized"
            finally:
                db.close()
        finally:
            self._remove(ids)

    def test_a_variant_cannot_be_hung_off_another_brands_campaign(self, foreign_api):
        """The create direction, which no filter on a read would catch.

        `create_variant_for_campaign` resolves the parent within the brand
        before it writes, so the row is refused rather than created and then
        found to be unreachable — which would leave a variant nobody can see
        attached to a campaign nobody meant.
        """
        from app.campaigns.db_models import VariantDB
        from app.database import SessionLocal

        ids = self._campaign_in_default_brand()
        try:
            with foreign_api([VIEW, CAMPAIGNS_MANAGE]) as headers:
                response = client.post(
                    f"/campaigns/{ids['campaign']}/variants",
                    json={"name": "smuggled", "channel": "email"}, headers=headers)
                assert response.status_code in (400, 404), response.text

            db = SessionLocal()
            try:
                assert db.query(VariantDB).filter(
                    VariantDB.campaign_id == ids["campaign"],
                    VariantDB.name == "smuggled",
                ).first() is None, "the variant was created across the boundary"
            finally:
                db.close()
        finally:
            self._remove(ids)

    def test_resolutions_three_hops_away_are_not_listable(self, foreign_api):
        """The deepest chain: `resolution -> slot -> variant -> campaign`."""
        ids = self._campaign_in_default_brand()
        try:
            with foreign_api([VIEW]) as headers:
                response = client.get(
                    f"/campaigns/decision-slots/{ids['slot']}/resolutions",
                    headers=headers)
                assert response.status_code == 200, response.text
                assert response.json() == []
        finally:
            self._remove(ids)
