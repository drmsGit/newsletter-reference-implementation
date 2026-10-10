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

from app.auth.permissions import (
    AUDIENCES_MANAGE, AUDIENCES_PIN, CAMPAIGNS_MANAGE, CONTENT_MANAGE,
    RECIPIENTS_CONSENT, RECIPIENTS_MANAGE, SENDS_EXECUTE, VIEW,
)
from app.auth.service import ensure_default_brand
from main import app
from tests.machine import machine

client = TestClient(app, raise_server_exceptions=False)

APP = pathlib.Path(__file__).resolve().parent.parent / "app"

#: The functions allowed to read across every brand at once.
#:
#: ADR-172 point 4 makes `brand_id` a required argument, which leaves the
#: genuine spanning callers — platform counts, migrations, seeds, tests — with
#: nowhere to go. `list_all_*()` is that somewhere, and its whole value is that
#: it says in its own name what it is doing.
#:
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
    "list_all_audience_groups",
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

    def test_a_records_versions_answer_as_absent_from_another_brand(self, foreign_api):
        """The version list too (task-277): it answered `200 []`, so "no
        versions yet" and "not yours, or not there" read the same."""
        record_id = self._default_brand_record()
        try:
            with foreign_api([VIEW]) as headers:
                assert client.get(f"/content/{record_id}/versions", headers=headers).status_code == 404
                assert client.get("/content/999999999/versions", headers=headers).status_code == 404
            with machine([VIEW]) as headers:
                own = client.get(f"/content/{record_id}/versions", headers=headers)
                assert (own.status_code, own.json()) == (200, []), "a record of one's own with no versions"
        finally:
            self._remove(record_id)

    def test_a_list_carries_only_the_declared_brands_records(self, foreign_api):
        record_id = self._default_brand_record()
        try:
            with foreign_api([VIEW]) as headers:
                # Newest first (ADR-185 point 4), so a record created just now
                # would be on this page if the brand boundary let it through.
                response = client.get("/content/", params={"limit": 200}, headers=headers)
                assert response.status_code == 200, response.text
                assert record_id not in [row["id"] for row in response.json()["items"]]
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
                # Neither the rows nor the count may say the slot has any (ADR-185).
                assert (response.json()["items"], response.json()["total"]) == ([], 0)
        finally:
            self._remove(ids)


# --- audience, stage 5 ------------------------------------------------------

class TestAudienceGroupsAreOwnedByOneBrand:
    """ADR-172 points 4-6 for `audience_groups` and its two child tables.

    `get_group` is the choke point here — update, delete, the member functions
    and the block functions all resolve through it — so the interesting test is
    not that one route refuses but that the children refuse with it.
    """

    def _group_in_default_brand(self):
        from app.audience import service
        from app.auth.service import ensure_default_brand
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            brand = ensure_default_brand(db).id
            group = service.create_group(
                db, f"boundary-{uuid.uuid4().hex[:8]}", brand_id=brand)
            block = service.add_block(
                db, group_id=group.id, kind="include",
                criteria={"language": "de"}, label="not yours", brand_id=brand)
            return {"group": group.id, "block": block.id, "brand": brand}
        finally:
            db.close()

    def _remove(self, ids):
        from app.audience.db_models import (
            AudienceGroupDB, AudienceGroupMemberDB, AudienceRuleBlockDB,
        )
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            db.query(AudienceRuleBlockDB).filter(
                AudienceRuleBlockDB.group_id == ids["group"]).delete()
            db.query(AudienceGroupMemberDB).filter(
                AudienceGroupMemberDB.group_id == ids["group"]).delete()
            db.query(AudienceGroupDB).filter(
                AudienceGroupDB.id == ids["group"]).delete()
            db.commit()
        finally:
            db.close()

    def test_a_group_in_another_brand_answers_as_absent(self, foreign_api):
        ids = self._group_in_default_brand()
        try:
            with foreign_api([VIEW]) as headers:
                assert client.get(
                    f"/api/audience-groups/{ids['group']}", headers=headers
                ).status_code == 404
        finally:
            self._remove(ids)

    def test_its_blocks_are_not_listable_either(self, foreign_api):
        """The child follows the parent, which is the whole of point 5.

        A rule block is the sentence that says who a group means. Listing
        another brand's blocks would leak the targeting rules even if the group
        row itself stayed hidden.
        """
        ids = self._group_in_default_brand()
        try:
            with foreign_api([VIEW]) as headers:
                response = client.get(
                    f"/api/audience-groups/{ids['group']}/blocks", headers=headers)
                assert response.status_code == 200, response.text
                assert response.json() == []
        finally:
            self._remove(ids)

    def test_a_block_cannot_be_edited_across_the_boundary(self, foreign_api):
        from app.audience.db_models import AudienceRuleBlockDB
        from app.database import SessionLocal

        ids = self._group_in_default_brand()
        try:
            with foreign_api([VIEW, AUDIENCES_MANAGE]) as headers:
                response = client.patch(
                    f"/api/audience-groups/{ids['group']}/blocks/{ids['block']}",
                    json={"label": "hijacked"}, headers=headers)
                assert response.status_code == 404, response.text

            db = SessionLocal()
            try:
                assert db.query(AudienceRuleBlockDB).filter(
                    AudienceRuleBlockDB.id == ids["block"]
                ).first().label == "not yours", "the edit landed anyway"
            finally:
                db.close()
        finally:
            self._remove(ids)

    def test_a_recipient_cannot_be_pinned_into_another_brands_group(self, foreign_api):
        """The write direction. A read filter would not catch this: the pin
        would be created and only then be unreachable."""
        from app.audience.db_models import AudienceGroupMemberDB
        from app.database import SessionLocal
        from app.recipients.db_models import RecipientDB

        ids = self._group_in_default_brand()
        db = SessionLocal()
        try:
            recipient = db.query(RecipientDB).order_by(RecipientDB.id).first()
            with foreign_api([VIEW, AUDIENCES_PIN]) as headers:
                response = client.post(
                    f"/api/audience-groups/{ids['group']}/members/{recipient.id}",
                    headers=headers)
                assert response.status_code == 404, response.text

            assert db.query(AudienceGroupMemberDB).filter(
                AudienceGroupMemberDB.group_id == ids["group"]
            ).count() == 0, "the pin was written across the boundary"
        finally:
            db.close()
            self._remove(ids)


# --- the derived plane, stage 6 ---------------------------------------------

class TestASendCannotBeFiredFromAnotherBrand:
    """**The external review's P1-02 in its sharpest form.**

    The finding: "an integration with `sends.execute` on brand A can send
    `X-Brand: A` while addressing a known send-instance ID belonging to brand
    B." Nothing downstream would have noticed — the send instance carries its
    own brand and the send loop reads it, so brand B's list gets brand B's
    content, sent by a credential that holds nothing in brand B.
    """

    def _draft_send_in_default_brand(self):
        from app.database import SessionLocal
        from app.delivery.db_models import SendInstanceDB

        db = SessionLocal()
        try:
            source = db.query(SendInstanceDB).order_by(SendInstanceDB.id).first()
            instance = SendInstanceDB(
                snapshot_id=source.snapshot_id,
                brand_id=source.brand_id,
                name=f"boundary-{uuid.uuid4().hex[:8]}",
                status="draft",
                provider="mock",
            )
            db.add(instance)
            db.commit()
            db.refresh(instance)
            return instance.id
        finally:
            db.close()

    def _remove(self, send_id):
        from app.database import SessionLocal
        from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB

        db = SessionLocal()
        try:
            db.query(DeliveryExecutionDB).filter(
                DeliveryExecutionDB.send_instance_id == send_id).delete()
            db.query(SendInstanceDB).filter(SendInstanceDB.id == send_id).delete()
            db.commit()
        finally:
            db.close()

    def test_an_unattended_machine_cannot_fire_another_brands_send(self, foreign_api):
        """**The external review's P1-02, directly.**

        A credential flagged for unattended sending goes straight past the
        approval gate into `send_send_instance` — so this is the path where the
        brand predicate inside the locked query is the only thing standing
        between brand A's credential and brand B's mail.

        The status code alone would not prove it. `send_send_instance` commits
        `status='sending'` as its very first act, so a boundary enforced after
        the row was loaded would leave this instance wedged in `sending`
        forever. Asserting it is still `draft` is what separates "refused" from
        "refused too late".
        """
        from app.auth import integrations as ints
        from app.auth.db_models import IntegrationCredentialDB, IntegrationDB
        from app.database import SessionLocal
        from app.delivery.db_models import SendInstanceDB

        send_id = self._draft_send_in_default_brand()
        db = SessionLocal()
        try:
            with foreign_api([VIEW, SENDS_EXECUTE]) as headers:
                key_id = headers["Authorization"].split()[1].split(".")[0]
                integration = db.query(IntegrationDB).join(
                    IntegrationCredentialDB,
                    IntegrationCredentialDB.integration_id == IntegrationDB.id,
                ).filter(IntegrationCredentialDB.key_id == key_id).first()
                ints.set_unattended_sending(db, integration.id, True)

                response = client.post(
                    f"/delivery/send-instances/{send_id}/send", headers=headers)
                assert response.status_code != 202, "it should not have been held"
                assert response.status_code in (404, 409), response.text

            db.expire_all()
            row = db.query(SendInstanceDB).filter(SendInstanceDB.id == send_id).first()
            assert row.status == "draft", (
                f"the send was claimed across the brand boundary — status {row.status!r}"
            )
            assert row.sent_count == 0
        finally:
            db.close()
            self._remove(send_id)

    def test_a_held_request_naming_another_brands_send_discloses_nothing(self, foreign_api):
        """The other half of P1-02 — and since 2026-09-29 it refuses rather
        than queues (task-9).

        An unflagged machine hits `ApprovalRequired` in the guard, which cannot
        know what the path parameter names. Until task-9 the handler held the
        request anyway: a 202, and a row branded A whose subject was B's send.
        Its content was safe, and this test used to pin exactly that. What it
        missed is that the row's subject occupied B's send in the one-open-
        request index — see `test_a_foreign_request_cannot_occupy_this_brands_send`.

        Now the handler asks the action whether the subject is in the declared
        brand before creating anything, and answers **word for word what the
        unattended path answers** for a foreign or missing send, so comparing
        the two cannot reveal that the id exists elsewhere.

        The summary/panel/execute checks stay, for any row created before the
        fix: those still resolve within the row's brand.
        """
        from app.approvals.actions import send_fire
        from app.approvals.db_models import PendingActionDB
        from app.database import SessionLocal
        from app.delivery.db_models import SendInstanceDB

        send_id = self._draft_send_in_default_brand()
        db = SessionLocal()
        try:
            with foreign_api([VIEW, SENDS_EXECUTE]) as headers:
                foreign_brand = int(headers["X-Brand"])
                response = client.post(
                    f"/delivery/send-instances/{send_id}/send", headers=headers)

            assert response.status_code == 409, response.text
            assert response.json()["detail"] == f"SendInstance {send_id} not found", (
                "the held path answered differently from the unattended path, "
                "which tells a caller the id exists in another brand"
            )
            assert db.query(PendingActionDB).filter(
                PendingActionDB.subject_type == "send_instance",
                PendingActionDB.subject_id == send_id,
            ).count() == 0, "a held request was created for another brand's send"

            # Defence for rows that predate the check.
            summary = send_fire.summarise(db, send_id, brand_id=foreign_brand)
            assert "no longer present" in summary, (
                f"the frozen summary quoted another brand's send: {summary!r}"
            )
            described = send_fire.describe(
                db, {"send_instance_id": send_id}, brand_id=foreign_brand)
            assert described.blocked_reason, "the review panel offered the button"
            assert "mock" not in str(described.rows), "the panel leaked the provider"
            result = send_fire.execute(
                db, {"send_instance_id": send_id}, brand_id=foreign_brand)
            assert not result.ok, "approving fired another brand's send"

            db.expire_all()
            assert db.query(SendInstanceDB).filter(
                SendInstanceDB.id == send_id).first().status == "draft"
        finally:
            db.close()
            self._remove(send_id)

    def test_a_foreign_request_cannot_occupy_this_brands_send(self, foreign_api):
        """task-9, and the reason its entry's "noise, not risk" was wrong.

        The one-open-request-per-subject index is keyed on (action_key,
        subject_type, subject_id) with no brand — and the subject is lifted from
        the path. So brand A's machine naming brand B's send id stored B's id
        under brand A, and B's OWN machine asking to fire its own send then hit
        `DuplicateRequest`. The retry branch, looking for the held row without
        a brand filter, found A's and answered B with A's pending_action_id:
        B's orchestrator believed its send was held for review, in an inbox
        where nobody can see it, for as long as the foreign row lived — and A
        could take the slot again the moment it lapsed.

        Not a leak of content — the summary and panel resolve within the row's
        brand — but a brand blocking another brand's sending, which is the
        boundary ADR-172 draws.
        """
        from tests.machine import machine
        from app.approvals.db_models import PendingActionDB
        from app.database import SessionLocal

        send_id = self._draft_send_in_default_brand()
        db = SessionLocal()
        created: list[int] = []
        try:
            with foreign_api([VIEW, SENDS_EXECUTE]) as headers:
                squat = client.post(
                    f"/delivery/send-instances/{send_id}/send", headers=headers)
            if squat.status_code == 202:
                created.append(squat.json()["pending_action_id"])

            with machine([VIEW, SENDS_EXECUTE]) as home:
                response = client.post(
                    f"/delivery/send-instances/{send_id}/send", headers=home)
            assert response.status_code == 202, response.text
            held_id = response.json()["pending_action_id"]
            created.append(held_id)

            held = db.query(PendingActionDB).filter(PendingActionDB.id == held_id).first()
            home_brand = self._brand_of_send(db, send_id)
            assert held.brand_id == home_brand, (
                f"brand {home_brand}'s request to fire its own send was answered "
                f"with a held request belonging to brand {held.brand_id} — a "
                "foreign request is occupying this send"
            )
        finally:
            db.rollback()
            if created:
                db.query(PendingActionDB).filter(
                    PendingActionDB.id.in_(created)).delete(synchronize_session=False)
                db.commit()
            db.close()
            self._remove(send_id)

    def test_an_action_that_cannot_place_its_subject_is_refused_not_held(
        self, monkeypatch
    ):
        """Fail closed. The check needs the action to say whose its subject is;
        an action that names a subject and cannot answer is refused from the
        guard rather than held — the same posture as a route with no approvable
        action mapped at all."""
        from tests.machine import machine
        from app.approvals.actions import send_fire
        from app.approvals.db_models import PendingActionDB
        from app.database import SessionLocal

        monkeypatch.delattr(send_fire, "subject_in_brand")
        send_id = self._draft_send_in_default_brand()
        db = SessionLocal()
        try:
            with machine([VIEW, SENDS_EXECUTE]) as home:
                response = client.post(
                    f"/delivery/send-instances/{send_id}/send", headers=home)
            assert response.status_code == 403, response.text
            assert db.query(PendingActionDB).filter(
                PendingActionDB.subject_id == send_id).count() == 0
        finally:
            db.close()
            self._remove(send_id)

    def test_a_slot_held_by_another_brand_is_never_answered_with_its_id(
        self, foreign_api
    ):
        """Rows created before the subject check existed can still occupy a
        send's slot until they lapse. The retry lookup is brand-filtered, so
        this brand is told the slot is taken — and is not handed the other
        brand's pending_action_id as if it were its own."""
        from tests.machine import machine
        from app.approvals import service as approvals
        from app.approvals.db_models import PendingActionDB
        from app.audit.service import ACTOR_INTEGRATION
        from app.database import SessionLocal

        send_id = self._draft_send_in_default_brand()
        db = SessionLocal()
        legacy = None
        try:
            with foreign_api([VIEW]) as headers:
                foreign_brand = int(headers["X-Brand"])
            legacy = approvals.request_approval(   # as the pre-fix handler did
                db, "send.fire_send_instance", payload={"send_instance_id": send_id},
                summary="legacy", requested_by_type=ACTOR_INTEGRATION,
                requested_by_id=None, brand_id=foreign_brand, subject_id=send_id,
            )

            with machine([VIEW, SENDS_EXECUTE]) as home:
                response = client.post(
                    f"/delivery/send-instances/{send_id}/send", headers=home)

            assert response.status_code == 409, response.text
            assert str(legacy.id) not in response.text, (
                "this brand was answered with another brand's pending_action_id"
            )
        finally:
            db.rollback()
            if legacy is not None:
                db.query(PendingActionDB).filter(
                    PendingActionDB.id == legacy.id).delete(synchronize_session=False)
                db.commit()
            db.close()
            self._remove(send_id)

    @staticmethod
    def _brand_of_send(db, send_id):
        from app.delivery.db_models import SendInstanceDB

        return db.query(SendInstanceDB.brand_id).filter(
            SendInstanceDB.id == send_id).scalar()

    # --- task-28: the deliveries read surface ---------------------------------

    def test_the_deliveries_list_shows_this_brand_and_hides_others(self, foreign_api):
        from tests.machine import machine

        send_id = self._draft_send_in_default_brand()
        try:
            with machine([VIEW]) as home:
                mine = client.get("/delivery/send-instances", params={"limit": 200}, headers=home)
            with foreign_api([VIEW]) as headers:
                theirs = client.get("/delivery/send-instances", params={"limit": 200}, headers=headers)

            assert mine.status_code == 200, mine.text
            assert send_id in {s["id"] for s in mine.json()["items"]}
            assert send_id not in {s["id"] for s in theirs.json()["items"]}, (
                "another brand's deliveries list included this brand's send"
            )
        finally:
            self._remove(send_id)

    def test_the_list_is_newest_first_and_paged(self):
        from tests.machine import machine

        first = self._draft_send_in_default_brand()
        second = self._draft_send_in_default_brand()
        try:
            with machine([VIEW]) as home:
                page = client.get("/delivery/send-instances", params={"limit": 1}, headers=home)
                too_many = client.get("/delivery/send-instances", params={"limit": 500}, headers=home)

            assert [s["id"] for s in page.json()["items"]] == [second], "not newest first, or not limited"
            assert page.json()["total"] >= 2, "the total counts every send, not the page"
            assert too_many.status_code == 422, "an unbounded page was accepted"
        finally:
            self._remove(first)
            self._remove(second)

    def test_a_send_can_be_read_by_id_and_not_from_another_brand(self, foreign_api):
        from tests.machine import machine

        send_id = self._draft_send_in_default_brand()
        try:
            with machine([VIEW]) as home:
                mine = client.get(f"/delivery/send-instances/{send_id}", headers=home)
            with foreign_api([VIEW]) as headers:
                theirs = client.get(f"/delivery/send-instances/{send_id}", headers=headers)

            assert mine.status_code == 200 and mine.json()["id"] == send_id, mine.text
            assert theirs.status_code == 404, theirs.text
        finally:
            self._remove(send_id)

    def test_the_detail_explains_the_gap_by_stage(self):
        """The interview's question 5.5: what explains approved-versus-sent.
        Exclusions are counted per stage of the ADR-163 point 7 stack."""
        from tests.machine import machine
        from app.database import SessionLocal
        from app.delivery.db_models import DeliveryExecutionDB
        from app.recipients.db_models import RecipientDB

        send_id = self._draft_send_in_default_brand()
        db = SessionLocal()
        try:
            ids = [r.id for r in db.query(RecipientDB.id).order_by(RecipientDB.id).limit(4)]
            for recipient_id, reason in zip(ids, (
                "addressability: no active address on the email channel",
                "consent: no grant for (email, marketing)",
                "consent: no grant for (email, marketing)",
                None,
            )):
                db.add(DeliveryExecutionDB(
                    send_instance_id=send_id, recipient_id=recipient_id, provider="mock",
                    status="excluded" if reason else "sent", exclusion_reason=reason,
                    channel="email", purpose="marketing",
                ))
            db.commit()

            with machine([VIEW]) as home:
                detail = client.get(f"/delivery/send-instances/{send_id}", headers=home).json()

            assert detail["execution_count"] == 4
            assert detail["exclusions_by_stage"] == {"addressability": 1, "consent": 2}
        finally:
            db.close()
            self._remove(send_id)

    def test_its_executions_are_not_listable_from_another_brand(self, foreign_api):
        send_id = self._draft_send_in_default_brand()
        try:
            with foreign_api([VIEW]) as headers:
                response = client.get(
                    f"/delivery/send-instances/{send_id}/executions", headers=headers)
                assert response.status_code == 200, response.text
                assert (response.json()["items"], response.json()["total"]) == ([], 0)
        finally:
            self._remove(send_id)


# --- the classification table, stage 7 --------------------------------------

def _guarded_router_prefixes() -> set[str]:
    """Every router `enforce_api_policy` is actually wired onto.

    Read from the resolved `dependant`, not from `route.dependencies` — FastAPI
    merges router-level dependencies into the former and the latter holds only
    what a route declared for itself. Asserting against the wrong one produced
    an empty list once, and a test that could never have caught its own bug.
    """
    from main import app

    prefixes = set()
    for route in app.routes:
        dependant = getattr(route, "dependant", None)
        names = {
            getattr(d.call, "__name__", "")
            for d in getattr(dependant, "dependencies", [])
        }
        if "enforce_api_policy" not in names:
            continue
        parts = getattr(route, "path", "").strip("/").split("/")
        prefixes.add("/" + ("/".join(parts[:2]) if parts[0] == "api" else parts[0]))
    return prefixes


def test_every_guarded_router_is_classified_as_brand_owned_or_not():
    """**The answer to ADR-168's eleven-of-twelve hazard.**

    That record's `### Negative` names the failure precisely: "a guard added to
    eleven of twelve routers fails identically and reports identically: a gate
    that reads as closed over a plane that is open." A brand-boundary rollout
    across twelve routers has exactly that shape for as long as it is in
    progress — and the thing that distinguishes "not done yet" from "decided
    not to" is a list naming every router, including the ones the rule does not
    apply to.

    So the list has to be exhaustive, and nothing but this makes it so. A
    thirteenth router added without a line in `BRAND_OWNED` turns this red,
    which is the whole point: classifying it is a sentence somebody writes, not
    a thing they can omit by not thinking about it.
    """
    from app.auth.policy import BRAND_OWNED

    guarded = _guarded_router_prefixes()
    unclassified = guarded - set(BRAND_OWNED)
    stale = set(BRAND_OWNED) - guarded

    assert not unclassified, (
        f"these routers are guarded but not classified: {sorted(unclassified)}. "
        "Add a line to BRAND_OWNED in app/auth/policy.py saying whether the "
        "router owns brand-scoped rows, and why."
    )
    assert not stale, (
        f"BRAND_OWNED names routers that no longer exist: {sorted(stale)}. "
        "A classification table describing a plane that has moved is worse "
        "than none, because it reads as current."
    )


def test_the_partial_routers_say_what_the_exception_is():
    """"Partial" is the only interesting value, so it has to carry a reason.

    A table that reduced to yes/no would flatten exactly the part worth
    reading — that `/content` is brand-owned except for the global category
    vocabulary, and that `/recipients` has one route writing a brand off the
    request body. Those two sentences are the table's actual content.
    """
    from app.auth.policy import BRAND_OWNED

    for prefix, reason in BRAND_OWNED.items():
        if reason.startswith("partial"):
            assert "—" in reason or "-" in reason, prefix
            assert len(reason) > 80, (
                f"{prefix} is classified 'partial' with no explanation of "
                "which part. That is the only thing a reader needs from it."
            )


# --- consent, 2026-09-20 ----------------------------------------------------

class TestAConsentRecordLandsOnTheBrandItWasAuthorisedFor:
    """ADR-150's 2026-09-20 addendum.

    `recipients.consent` guards `consent_events`, which have carried a brand
    since ADR-163's addendum — so it is brand-scoped by ADR-150's own rule, and
    was filed platform-level on a justification about recipients that was true
    and about the wrong table.

    A consent record is the row ADR-142 §7 names as the answer to a UWG §7
    complaint, so "somebody wrote it to a brand nobody checked" is the
    expensive version of this bug.
    """

    def _external_id(self):
        from app.database import SessionLocal
        from app.recipients.db_models import RecipientDB

        db = SessionLocal()
        try:
            return db.query(RecipientDB).order_by(RecipientDB.id).first().external_id
        finally:
            db.close()

    def _payload(self, brand_id):
        return {
            "consent_status": "opted_in",
            "brand_id": brand_id,
            "source": "boundary-test",
            "purpose": "marketing",     # required since task-343
        }

    # --- task-16: the same hole on the create route -------------------------

    def _create(self, headers, brand_id):
        import uuid as _uuid

        external_id = f"bb16-{_uuid.uuid4().hex[:8]}"
        response = client.post("/recipients/", headers=headers, json={
            "brand_id": brand_id, "external_id": external_id,
            "address": f"{external_id}@example.invalid",
            "consent_status": "opted_in",
        })
        return external_id, response

    def _consent_events_for(self, db, external_id):
        from sqlalchemy import text as sql

        return db.execute(sql(
            "SELECT count(*) FROM consent_events WHERE recipient_id IN "
            "(SELECT id FROM recipients WHERE external_id = :e)"), {"e": external_id}).scalar()

    def _cleanup(self, db, external_id):
        from sqlalchemy import text as sql

        db.rollback()
        for statement in (
            "DELETE FROM consent_events WHERE recipient_id IN (SELECT id FROM recipients WHERE external_id = :e)",
            "DELETE FROM recipient_addresses WHERE recipient_id IN (SELECT id FROM recipients WHERE external_id = :e)",
            "DELETE FROM recipients WHERE external_id = :e",
        ):
            db.execute(sql(statement), {"e": external_id})
        db.commit()

    def test_creating_a_recipient_cannot_assert_consent_for_another_brand(self, foreign_brand):
        """task-16. `POST /recipients/` is guarded as `recipients.manage`
        (platform-level) and then checked `recipients.consent` with NO brand —
        the union — while writing the consent for the body's brand. So the
        consent route's rule, header authorises and body must agree, never
        reached this one: a caller authorised on brand A could create a
        recipient carrying brand B's consent."""
        from app.database import SessionLocal

        db = SessionLocal()
        external_id = None
        try:
            with machine([VIEW, RECIPIENTS_MANAGE, RECIPIENTS_CONSENT],
                         brand_id=foreign_brand.id) as headers:
                external_id, response = self._create(headers, ensure_default_brand(db).id)

            assert response.status_code == 409, response.text
            assert self._consent_events_for(db, external_id) == 0, (
                "a consent record was written for a brand the caller was not "
                "authorised in"
            )
        finally:
            if external_id:
                self._cleanup(db, external_id)
            db.close()

    def test_the_consent_grant_must_be_held_on_the_declared_brand(self, foreign_brand):
        """The union, directly: `recipients.consent` held on ANOTHER brand only.
        Checked with no brand, the union says yes."""
        from app.auth import integrations as ints
        from app.auth.db_models import IntegrationCredentialDB, IntegrationDB
        from app.database import SessionLocal

        db = SessionLocal()
        external_id = None
        try:
            home = ensure_default_brand(db).id
            with machine([VIEW, RECIPIENTS_MANAGE], brand_id=home) as headers:
                key_id = headers["Authorization"].split()[1].split(".")[0]
                integration = db.query(IntegrationDB).join(
                    IntegrationCredentialDB,
                    IntegrationCredentialDB.integration_id == IntegrationDB.id,
                ).filter(IntegrationCredentialDB.key_id == key_id).first()
                assert ints.grant(db, integration.id, RECIPIENTS_CONSENT, foreign_brand.id)

                external_id, response = self._create(headers, home)

            assert response.status_code == 403, response.text
            assert self._consent_events_for(db, external_id) == 0
        finally:
            if external_id:
                self._cleanup(db, external_id)
            db.close()

    def test_the_body_and_the_header_must_agree(self, foreign_brand):
        """The sharp one: both are present, and they disagree.

        A caller legitimately authorised on its own brand asserts consent for
        another. Reading the body would write a record nobody checked; reading
        the header would silently overwrite what the CRM actually said. Neither
        is acceptable, so it refuses.
        """
        from app.database import SessionLocal
        from app.recipients.db_models import ConsentEventDB

        external_id = self._external_id()
        db = SessionLocal()
        try:
            before = db.query(ConsentEventDB).filter(
                ConsentEventDB.source == "boundary-test").count()

            with machine([VIEW, RECIPIENTS_CONSENT], brand_id=foreign_brand.id) as headers:
                response = client.post(
                    f"/recipients/{external_id}/consent",
                    json=self._payload(ensure_default_brand(db).id),
                    headers=headers,
                )
                assert response.status_code == 409, response.text

            assert db.query(ConsentEventDB).filter(
                ConsentEventDB.source == "boundary-test"
            ).count() == before, "a consent event was written despite the refusal"
        finally:
            db.close()

    def test_asserting_for_a_brand_the_caller_holds_nothing_on_is_refused(self):
        """The permission check, now that it has a brand to check against.

        The caller declares the brand it is asserting for — so body and header
        agree — but holds no grant there. Before 2026-09-20 this was admitted,
        because a platform-level permission is checked without a brand at all.
        """
        from app.database import SessionLocal

        external_id = self._external_id()
        db = SessionLocal()
        try:
            default = ensure_default_brand(db).id
        finally:
            db.close()

        with machine([VIEW, RECIPIENTS_CONSENT], brand_id=default) as headers:
            headers["X-Brand"] = "999999"
            response = client.post(
                f"/recipients/{external_id}/consent",
                json=self._payload(999999), headers=headers,
            )
            assert response.status_code == 403, response.text

    def test_holding_the_permission_on_another_brand_is_not_holding_it_here(
        self, foreign_brand
    ):
        """**The only test that proves the reclassification.**

        Written after the obvious two failed to: reverting
        `recipients.consent` to platform-level left both of them green, because
        ADR-172 point 2 already refuses a declared brand the caller holds
        *nothing* on, and the missing-header 400 comes from the dependency. Two
        guards each refusing independently, so neither test could see the one
        under examination — the masking pattern this repo keeps finding.

        This caller holds `view` on the brand it declares, so point 2 is
        satisfied and stays out of the way. It holds `recipients.consent` only
        on a *different* brand. Platform-level, that is enough — the permission
        is checked with no brand at all and it does hold the key somewhere.
        Brand-scoped, it is not.
        """
        from app.auth import integrations as ints
        from app.auth.db_models import IntegrationCredentialDB, IntegrationDB
        from app.database import SessionLocal
        from app.recipients.db_models import ConsentEventDB

        external_id = self._external_id()
        db = SessionLocal()
        try:
            default = ensure_default_brand(db).id
            before = db.query(ConsentEventDB).filter(
                ConsentEventDB.source == "boundary-test").count()

            with machine([VIEW], brand_id=foreign_brand.id) as headers:
                key_id = headers["Authorization"].split()[1].split(".")[0]
                integration = db.query(IntegrationDB).join(
                    IntegrationCredentialDB,
                    IntegrationCredentialDB.integration_id == IntegrationDB.id,
                ).filter(IntegrationCredentialDB.key_id == key_id).first()
                # The permission, but on the brand it is NOT declaring.
                ints.grant(db, integration.id, RECIPIENTS_CONSENT, default)

                response = client.post(
                    f"/recipients/{external_id}/consent",
                    json=self._payload(foreign_brand.id), headers=headers,
                )
                assert response.status_code == 403, response.text

            assert db.query(ConsentEventDB).filter(
                ConsentEventDB.source == "boundary-test"
            ).count() == before
        finally:
            db.close()

    def test_no_declared_brand_is_refused_rather_than_defaulted(self):
        from app.database import SessionLocal

        external_id = self._external_id()
        db = SessionLocal()
        try:
            default = ensure_default_brand(db).id
        finally:
            db.close()

        with machine([VIEW, RECIPIENTS_CONSENT], brand_id=default) as headers:
            headers.pop("X-Brand")
            response = client.post(
                f"/recipients/{external_id}/consent",
                json=self._payload(default), headers=headers,
            )
            assert response.status_code == 400, response.text
            assert "X-Brand" in response.json()["detail"]


def test_listing_recipients_returns_rather_than_raising():
    """`GET /recipients/` raised `TypeError` for as long as consent had a brand.

    `list_recipients` passed two arguments to a three-argument
    `to_recipients`. No test called the route, so a route that could not return
    looked fine — it was found by an unrelated test reaching for a
    platform-level route to assert something else against.
    """
    with machine([VIEW, RECIPIENTS_MANAGE]) as headers:
        response = client.get("/recipients/", headers=headers)
        assert response.status_code == 200, response.text
        assert isinstance(response.json()["items"], list)


class TestAPermittedWriteLandsOnTheDeclaredBrand:
    """task-39. The JSON create routes checked the permission against the
    declared brand and wrote the row to the DEFAULT brand: an integration
    granted `content.manage` on brand B, correctly declaring `X-Brand: B`,
    created its record in brand 1. Fixed on 2026-09-19 (ADR-168/172) by taking
    the brand from `working_brand` — and nothing tested it: every guard test
    checks a refusal, and the failure here is a write that is ALLOWED and goes
    to the wrong place. One test per create route, on a non-default brand,
    because the default brand is exactly where the bug put things.
    """

    def test_content(self, foreign_brand):
        from app.content.db_models import ContentRecordDB
        from app.database import SessionLocal
        from app.auth.permissions import CONTENT_MANAGE

        title = f"bb39-{uuid.uuid4().hex[:8]}"
        with machine([VIEW, CONTENT_MANAGE], brand_id=foreign_brand.id) as headers:
            response = client.post("/content/", headers=headers, json={
                "brand_id": foreign_brand.id, "title": title,
                "content": {"headline_medium": "x"},
            })
        assert response.status_code in (200, 201), response.text
        with SessionLocal() as db:
            row = db.query(ContentRecordDB).filter(ContentRecordDB.title == title).one()
            assert row.brand_id == foreign_brand.id, (
                f"authorised on brand {foreign_brand.id}, written to brand {row.brand_id}"
            )

    def test_campaign(self, foreign_brand):
        from app.campaigns.db_models import CampaignDB
        from app.database import SessionLocal
        from app.auth.permissions import CAMPAIGNS_MANAGE

        name = f"bb39-{uuid.uuid4().hex[:8]}"
        with machine([VIEW, CAMPAIGNS_MANAGE], brand_id=foreign_brand.id) as headers:
            response = client.post("/campaigns/", headers=headers, json={"name": name})
        assert response.status_code in (200, 201), response.text
        with SessionLocal() as db:
            row = db.query(CampaignDB).filter(CampaignDB.name == name).one()
            assert row.brand_id == foreign_brand.id

    def test_audience_group(self, foreign_brand):
        from app.audience.db_models import AudienceGroupDB
        from app.database import SessionLocal
        from app.auth.permissions import AUDIENCES_MANAGE

        name = f"bb39-{uuid.uuid4().hex[:8]}"
        with machine([VIEW, AUDIENCES_MANAGE], brand_id=foreign_brand.id) as headers:
            response = client.post("/api/audience-groups", headers=headers, json={"name": name})
        assert response.status_code in (200, 201), response.text
        with SessionLocal() as db:
            row = db.query(AudienceGroupDB).filter(AudienceGroupDB.name == name).one()
            assert row.brand_id == foreign_brand.id
