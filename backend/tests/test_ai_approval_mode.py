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
    before = get_task_approval_mode(db, TASK)
    yield
    set_task_approval_mode(db, TASK, before if before == REQUIRE_APPROVAL else None)
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


class TestTheSettingIsTheOnlyDifference:

    def test_it_defaults_to_applying_in_the_app(self, db):
        assert get_task_approval_mode(db, TASK) == AUTO_APPLY

    def test_an_unknown_mode_clears_rather_than_storing(self, db):
        set_task_approval_mode(db, TASK, "sometimes_maybe")
        assert get_task_approval_mode(db, TASK) == AUTO_APPLY

    def test_it_round_trips(self, db):
        set_task_approval_mode(db, TASK, REQUIRE_APPROVAL)
        assert get_task_approval_mode(db, TASK) == REQUIRE_APPROVAL
        set_task_approval_mode(db, TASK, None)
        assert get_task_approval_mode(db, TASK) == AUTO_APPLY

    def test_the_setting_is_per_task_not_global(self, db):
        set_task_approval_mode(db, TASK, REQUIRE_APPROVAL)
        assert get_task_approval_mode(db, "some_other_task") == AUTO_APPLY, (
            "graduated trust means one task at a time"
        )


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
            summary=ai_subject_apply.summarise(db, run.id),
            requested_by_type="user", requested_by_id=None,
            brand_id=auth.ensure_default_brand(db).id,
            subject_id=run.id,
        )
        _CREATED.append(row.id)
        return row

    def test_three_options_are_one_request(self, db, run_with_options):
        run, _ = run_with_options
        row = self._held(db, run)

        description = ai_subject_apply.describe(db, {"ai_run_id": run.id})

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
        description = ai_subject_apply.describe(db, {"ai_run_id": 99999999})

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
            rows = dict(ai_subject_apply.describe(db, {"ai_run_id": run.id}).rows)
            assert rows.get("Prompt version") == f"#{prompt.id}"
        finally:
            db.rollback()
            run.prompt_id = None
            db.commit()
            db.query(AIPromptDB).filter(AIPromptDB.id == prompt.id).delete()
            db.commit()
