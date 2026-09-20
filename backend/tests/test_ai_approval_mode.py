"""Mode A through the approval inbox — ADR-141 §4, playbook 2026-07-31.

**Inline is the default and that is the decision**, not a convenience. ADR-140's
Context rejects routing every AI action through an approval layer because it
"buries managers in approvals", and ADR-141 §5's guard against the "80 records
to approve" problem only holds while the normal path does not queue. A company
that wants a second pair of eyes on one task turns it on for that task.

So the two tests worth the most here are the pair at the top: the same button
produces a suggestion on the page, or a held request, depending on one setting
and nothing else.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.approvals import service as approvals
from app.approvals.actions import ai_subject_apply
from app.approvals.db_models import APPROVED, PENDING, PendingActionDB
from app.audit.db_models import AuditEventDB
from app.auth import service as auth
from app.database import SessionLocal
from app.settings.service import (
    AUTO_APPLY, REQUIRE_APPROVAL, get_task_approval_mode, set_task_approval_mode,
)
from main import app
from app.auth.service import ensure_default_brand

TAG = "aimode"
TASK = "subject_preheader"
_CREATED: list[int] = []


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _restore_mode(db):
    """Leave the setting as it was found.

    It is one shared config row, so a test that flips it and dies leaves every
    later run — and the developer's own browser — in a state nobody chose.
    """
    # Read through the CONFIG, not through the accessor. A mutation run that
    # forces `get_task_approval_mode` to answer `require_approval` makes this
    # fixture read that as the original value and faithfully persist it — which
    # is how a mutation session left the developer's own deployment holding
    # every subject-line suggestion for approval. Reading the stored row cannot
    # be fooled by the function under test.
    from app.settings.service import task_approval_modes

    before = task_approval_modes(db).get(TASK)
    yield
    set_task_approval_mode(db, TASK, before)
    db.rollback()
    if _CREATED:
        db.query(AuditEventDB).filter(
            AuditEventDB.subject_type == approvals.SUBJECT,
            AuditEventDB.subject_id.in_(_CREATED),
        ).delete(synchronize_session=False)
        db.query(PendingActionDB).filter(
            PendingActionDB.id.in_(_CREATED)
        ).delete(synchronize_session=False)
        _CREATED.clear()
    db.execute(text("DELETE FROM audit_events WHERE action = 'ai.suggestion_applied'"))
    db.commit()


def _api_client():
    from fastapi.testclient import TestClient

    from main import app

    return TestClient(app, raise_server_exceptions=False)


class TestTheSettingIsTheOnlyDifference:

    def test_it_defaults_to_applying_in_the_app(self, db):
        assert get_task_approval_mode(db, TASK) == AUTO_APPLY

    def test_an_unknown_mode_clears_rather_than_storing(self, db):
        """Asserted against the STORED ROW, not the accessor.

        `task_approval_modes` filters unrecognised values on read, so a write
        that happily stores "sometimes_maybe" is invisible to anything that
        reads through `get_task_approval_mode` — the read guard does the write
        guard's job and hides its absence. Two guards, each refusing
        independently, masking each other. Found by a mutation that stored the
        junk and broke nothing.
        """
        from sqlalchemy import text

        set_task_approval_mode(db, TASK, "sometimes_maybe")

        stored = db.execute(text(
            "SELECT value FROM app_config WHERE key = 'ai_task_approval_modes'"
        )).scalar() or {}
        assert TASK not in stored, (
            f"an unrecognised mode was written to the database: {stored}"
        )
        assert get_task_approval_mode(db, TASK) == AUTO_APPLY

    def test_it_round_trips(self, db):
        set_task_approval_mode(db, TASK, REQUIRE_APPROVAL)
        assert get_task_approval_mode(db, TASK) == REQUIRE_APPROVAL
        set_task_approval_mode(db, TASK, None)
        assert get_task_approval_mode(db, TASK) == AUTO_APPLY

    def test_setting_one_task_leaves_the_others_alone(self, db):
        """**Two tasks, because one proves nothing.**

        The first version set a single task and checked that a different,
        never-configured task still read as default — which passes even if the
        setter throws away the whole dictionary on every write, since the
        untouched task reads as default either way. Graduated trust means a
        company turns tasks on one at a time and the earlier ones stay on.
        """
        other = f"{TAG}_other_task"
        try:
            set_task_approval_mode(db, TASK, REQUIRE_APPROVAL)
            set_task_approval_mode(db, other, REQUIRE_APPROVAL)

            assert get_task_approval_mode(db, TASK) == REQUIRE_APPROVAL, (
                "configuring a second task wiped the first"
            )
            assert get_task_approval_mode(db, other) == REQUIRE_APPROVAL
            assert get_task_approval_mode(db, "never_configured") == AUTO_APPLY
        finally:
            set_task_approval_mode(db, other, None)


class TestTheActionIsPickOneNotYesNo:
    """ADR-141 §4: "accept/reject per item, **pick-one for options**".

    N options are ONE pending action. The spine was shaped for this before
    there was an action that needed it, so these tests are what confirm the
    shape was right rather than merely plausible.
    """

    @pytest.fixture
    def run_with_options(self, db):
        from app.ai.db_models import AIRunDB
        from app.campaigns.db_models import VariantDB

        variant = db.query(VariantDB).filter(VariantDB.channel == "email").first()
        if variant is None:
            pytest.skip("no email variant in this database")
        run = AIRunDB(
            task_key=TASK, provider="mock", model="mock", status="ok",
            input_tokens=10, output_tokens=20,
            target_type="variant", target_id=variant.id,
            output_text=(
                "1. SUBJECT: First option\n   PREHEADER: First preheader\n"
                "2. SUBJECT: Second option\n   PREHEADER: Second preheader\n"
                "3. SUBJECT: Third option\n   PREHEADER: Third preheader\n"
            ),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        try:
            yield run, variant
        finally:
            db.rollback()
            db.query(AIRunDB).filter(AIRunDB.id == run.id).delete()
            db.commit()

    def _held(self, db, run):
        row = approvals.request_approval(
            db, ai_subject_apply.META.key,
            payload={"ai_run_id": run.id},
            summary=ai_subject_apply.summarise(
                db, run.id, brand_id=ensure_default_brand(db).id),
            requested_by_type="user", requested_by_id=None,
            brand_id=auth.ensure_default_brand(db).id,
            subject_id=run.id,
        )
        _CREATED.append(row.id)
        return row

    def test_three_options_are_one_request(self, db, run_with_options):
        run, _ = run_with_options
        row = self._held(db, run)

        description = ai_subject_apply.describe(db, {"ai_run_id": run.id}, brand_id=ensure_default_brand(db).id)

        assert len(description.options) == 3
        assert row.subject_type == "ai_run", (
            "the subject is the RUN, which is what gives it a decision record "
            "without migrating ai_runs"
        )

    def test_approving_without_choosing_refuses(self, db, run_with_options):
        """A pick-one with an implicit default turns "the manager approved it"
        into "the manager approved whatever was at the top"."""
        run, _ = run_with_options
        row = self._held(db, run)

        result = approvals.approve(
            db, row.id, approver_type="user", approver_id=None, choice=None,
        )

        assert not result.ok
        assert "pick one" in (result.message or "")

    def test_the_chosen_option_is_the_one_written(self, db, run_with_options):
        """Index 1, not 0 — a test that picks the first option passes against a
        hardcoded first-option bug."""
        from app.rendering.service import envelope_fields_for_variant

        run, variant = run_with_options
        row = self._held(db, run)

        result = approvals.approve(
            db, row.id, approver_type="user", approver_id=None,
            choice={"index": 1},
        )

        assert result.ok, result.message
        fields = envelope_fields_for_variant(db, variant.id, variant.channel)
        assert fields.get("subject") == "Second option"
        assert fields.get("preheader") == "Second preheader"

    def test_an_option_that_is_not_on_offer_is_refused(self, db, run_with_options):
        run, _ = run_with_options
        row = self._held(db, run)

        result = approvals.approve(
            db, row.id, approver_type="user", approver_id=None,
            choice={"index": 99},
        )

        assert not result.ok

    def test_approving_needs_a_different_permission_from_requesting(self):
        """Asking spends money (`ai.run`); applying writes the variant
        (`campaigns.manage`). The first action's two coincided, which is why
        this one is the proof that declaring it per action was right."""
        assert ai_subject_apply.META.approve_permission == "campaigns.manage"

    def test_a_vanished_run_blocks_rather_than_raising(self, db):
        description = ai_subject_apply.describe(db, {"ai_run_id": 99999999}, brand_id=ensure_default_brand(db).id)

        assert description.blocked_reason
        assert description.options is None

    def test_the_prompt_version_is_shown_to_whoever_decides(
        self, db, run_with_options
    ):
        """ADR-140 §5 requires the prompt-version id in the audit of every AI
        action. Showing it makes "which prompt produced this?" answerable by
        the person deciding, not only by a query."""
        from app.ai.db_models import AIPromptDB

        # A real prompt row: `ai_runs.prompt_id` is a foreign key, and the
        # first version of this test invented an id — which the database
        # rejected, correctly.
        prompt = AIPromptDB(
            task_key=TASK, version=999, body="planted", is_published=False,
        )
        db.add(prompt)
        db.commit()
        db.refresh(prompt)

        run, _ = run_with_options
        run.prompt_id = prompt.id
        db.commit()
        try:
            rows = dict(ai_subject_apply.describe(db, {"ai_run_id": run.id}, brand_id=ensure_default_brand(db).id).rows)
            assert rows.get("Prompt version") == f"#{prompt.id}"
        finally:
            db.rollback()
            run.prompt_id = None
            db.commit()
            db.query(AIPromptDB).filter(AIPromptDB.id == prompt.id).delete()
            db.commit()


class TestTheSpendGuardsReachBothPlanes:
    """Inventory B15, closed 2026-09-20.

    The envelope guard, the approval-mode branch and the duplicate case lived
    inside `POST /ui/campaigns/.../suggest-subject` and nowhere else. A JSON
    client would therefore have spent tokens on a channel with no subject line
    — which is the one thing a spend guard exists to stop, and the reason Mode
    A was asked for in the first place.
    """

    def _headers(self):
        from app.auth.permissions import AI_RUN, VIEW
        from tests.machine import machine

        return machine([VIEW, AI_RUN])

    def test_the_route_is_priced_as_ai_not_as_a_campaign_edit(self):
        """**The narrow entry has to sit above the broad prefix.**

        `/campaigns` resolves to `campaigns.manage` — "may restructure a
        campaign", which is not "may spend money on the model". This is the
        second time that shape has been caught: `/delivery/process-due`
        resolved to `sends.plan` through the broad `/delivery/` prefix hours
        after the ordering hazard was logged. Order is semantics in that table
        and nothing enforces it, so the pair is pinned here.
        """
        from app.auth.permissions import AI_RUN, CAMPAIGNS_MANAGE
        from app.auth.policy import required_permission

        assert required_permission(
            "POST", "/campaigns/variants/{variant_id}/suggest-subject"
        ) == AI_RUN
        assert required_permission("POST", "/campaigns/") == CAMPAIGNS_MANAGE

    def test_a_channel_with_no_subject_line_is_refused_without_spending(self, db):
        """A push variant has no envelope module, so there is nowhere to put a
        subject even if the model wrote one. Refused before the call."""
        from app.ai.db_models import AIRunDB
        from app.auth import service as auth
        from app.campaigns.service import create_campaign, create_variant_for_campaign

        brand = auth.ensure_default_brand(db)
        campaign = create_campaign(
            db, name=f"{TAG}-b15-{uuid.uuid4().hex[:6]}",
            brand_id=brand.id, channel="email",
        )
        push = create_variant_for_campaign(
            db, campaign_id=campaign.id, name="push", channel="push",
            brand_id=brand.id,
        )
        before = db.query(AIRunDB).count()
        try:
            with self._headers() as headers:
                response = _api_client().post(
                    f"/campaigns/variants/{push.id}/suggest-subject", headers=headers,
                )
                assert response.status_code == 409, response.text
                assert response.json()["detail"]["reason"] == "refused"

            assert db.query(AIRunDB).count() == before, (
                "a run row was written for a channel that cannot carry a subject "
                "— which means the model was called and tokens were spent"
            )
        finally:
            from app.campaigns.db_models import CampaignDB, VariantDB

            db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).delete()
            db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
            db.commit()

    def test_another_brands_variant_is_not_reachable(self, db):
        """The lookup was `VariantDB` by bare id in the router, so this was a
        small brand gap too — one ADR-172 would have missed, because it lived
        in a router rather than a service."""
        from app.ai.orchestration import suggest_subject_for_variant
        from app.audit.service import ACTOR_USER
        from app.auth import service as auth
        from app.campaigns.service import create_campaign

        brand = auth.ensure_default_brand(db)
        campaign = create_campaign(
            db, name=f"{TAG}-b15x-{uuid.uuid4().hex[:6]}",
            brand_id=brand.id, channel="email",
        )
        try:
            result = suggest_subject_for_variant(
                db, campaign.variants[0].id,
                brand_id=999999,
                requested_by_type=ACTOR_USER, requested_by_id=None,
            )
            assert result.outcome == "refused"
        finally:
            from app.campaigns.db_models import CampaignDB, VariantDB

            db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).delete()
            db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
            db.commit()
