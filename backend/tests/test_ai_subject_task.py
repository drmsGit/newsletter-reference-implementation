"""Tests for the subject/preheader task's pure logic (ADR-141 §3).

Parsing and mock-format imitation are the two fragile pieces here and neither
needs a database, so they are tested directly. The spend gate in ai/service.py
is DB-backed and covered by manual verification for now.
"""

import re
from pathlib import Path

import jinja2

from app.ai.adapters.mock import imitate_requested_format
from app.ai.tasks import subject_preheader
from app.ai.tasks.subject_preheader import (
    REQUESTED_OPTIONS,
    option_notices,
    parse_options,
)

TRUNCATED = "output hit its ceiling and is truncated"


class TestParseOptions:

    def test_parses_the_requested_format(self):
        text = (
            "1. SUBJECT: Early mornings at Praia da Marinha\n"
            "   PREHEADER: The cliffs hold shade until nine\n"
            "2. SUBJECT: Beat the Algarve crowds\n"
            "   PREHEADER: Parking fills before the sun does\n"
        )
        options = parse_options(text)

        assert len(options) == 2
        assert options[0]["subject"] == "Early mornings at Praia da Marinha"
        assert options[0]["preheader"] == "The cliffs hold shade until nine"
        assert options[1]["subject"] == "Beat the Algarve crowds"

    def test_tolerates_a_missing_preheader(self):
        # A model that drifts from the layout should cost us an option's
        # preheader, never an exception in the request path.
        options = parse_options("1. SUBJECT: Only a subject here")

        assert len(options) == 1
        assert options[0]["preheader"] == ""

    def test_ignores_surrounding_chatter(self):
        text = (
            "Sure! Here are three options:\n"
            "1. SUBJECT: A real one\n"
            "   PREHEADER: With a preheader\n"
            "Let me know if you want more.\n"
        )
        assert len(parse_options(text)) == 1

    def test_empty_and_unparseable_input_yield_no_options(self):
        assert parse_options("") == []
        assert parse_options("no recognisable structure at all") == []


class TestMockImitatesRequestedFormat:

    def test_reproduces_the_prompts_own_layout(self):
        # The mock reads the format from the prompt rather than knowing about
        # subjects, so the task's real parser gets something in the right shape.
        prompt = (
            "Return exactly 3 options in this format:\n"
            "1. SUBJECT: <subject>\n"
            "   PREHEADER: <preheader>\n"
        )
        produced = imitate_requested_format(prompt)

        assert produced is not None
        options = parse_options(produced)
        assert len(options) == 3
        assert options[0]["subject"] == "Mock subject 1"
        assert options[2]["preheader"] == "Mock preheader 3"

    def test_returns_none_when_no_format_is_demonstrated(self):
        assert imitate_requested_format("Just write me something nice.") is None

    def test_works_for_a_format_it_was_never_told_about(self):
        # The point of reading the prompt: a future task gets this for free.
        prompt = "Answer as:\nTAG: <tag>\nREASON: <reason>\n"
        produced = imitate_requested_format(prompt, options=2)

        assert produced is not None
        assert "Mock tag 1" in produced
        assert "Mock reason 2" in produced


def _option(n: int) -> dict[str, str]:
    return {"subject": f"Subject {n}", "preheader": f"Preheader {n}"}


class TestOptionNotices:
    """The two facts the page used to swallow (backlog: AI suggestion UI)."""

    def test_a_truncation_message_is_passed_through_verbatim(self):
        # The run row already recorded this; the manager never saw it.
        full = [_option(i) for i in range(REQUESTED_OPTIONS)]
        assert option_notices(full, TRUNCATED) == [TRUNCATED]

    def test_a_short_option_list_is_called_out(self):
        notices = option_notices([_option(1), _option(2)], None)

        assert len(notices) == 1
        assert "2 of the 3" in notices[0]

    def test_both_are_reported_together(self):
        notices = option_notices([_option(1)], TRUNCATED)

        assert notices[0] == TRUNCATED
        assert "1 of the 3" in notices[1]

    def test_a_clean_full_run_says_nothing(self):
        full = [_option(i) for i in range(REQUESTED_OPTIONS)]
        assert option_notices(full, None) == []

    def test_no_count_notice_when_nothing_parsed(self):
        # Zero options is already reported as an error by the caller; a second
        # "0 of 3" line beside it would be noise, not information.
        assert option_notices([], None) == []
        assert option_notices([], TRUNCATED) == [TRUNCATED]


class TestNoticesReachThePage:
    """The template must render what the router now passes it.

    Renders the notice block out of campaign_detail.html standalone — no DB and
    no network (the shape tests/test_campaign_module_options.py uses).
    """

    @staticmethod
    def _notice_block() -> str:
        templates = Path(subject_preheader.__file__).parent.parent.parent / "templates"
        html = (templates / "campaign_detail.html").read_text()
        match = re.search(
            r"\{% if ai_notices is defined and ai_notices %\}.*?\{% endif %\}",
            html,
            re.S,
        )
        assert match, "the AI notice block is missing from campaign_detail.html"
        return match.group(0)

    def _render(self, **context) -> str:
        env = jinja2.Environment(autoescape=True)
        return env.from_string(self._notice_block()).render(**context)

    def test_each_notice_is_rendered(self):
        out = self._render(ai_notices=[TRUNCATED, "2 of the 3 requested options"])

        assert TRUNCATED in out
        assert "2 of the 3 requested options" in out

    def test_nothing_is_rendered_without_notices(self):
        assert self._render(ai_notices=[]).strip() == ""

    def test_survives_a_context_that_never_set_the_variable(self):
        # Other renders of this page pass no AI context at all.
        assert self._render().strip() == ""


class TestTruncationNoticeReachesThePage:
    """The router plumbing, not just the pure function beside it.

    `option_notices` and the template block are both covered above, and both
    pass with the router line that connects them removed — which is exactly the
    defect this fix was for: the run row's message was read only in the error
    branch, so a successful-but-truncated run dropped it on the floor. A test
    that never renders the page cannot see that.
    """

    def test_a_truncated_ok_run_shows_its_message_on_the_campaign_page(self):
        import uuid

        from fastapi.testclient import TestClient

        from main import app
        from app.ai.db_models import AIRunDB
        from app.auth import service as auth
        from app.auth.db_models import UserDB
        from app.campaigns.db_models import CampaignDB, VariantDB
        from app.database import SessionLocal

        db = SessionLocal()
        marker = f"stopped early at the token ceiling {uuid.uuid4().hex[:6]}"
        run = None
        try:
            # A campaign that actually has a variant: the notice renders inside
            # the block for the variant its run targeted, which is correct —
            # a notice belongs to the variant it was produced for.
            variant = (
                db.query(VariantDB).order_by(VariantDB.id.asc()).first()
            )
            if variant is None:
                pytest.skip("no variant in this database")
            campaign = (
                db.query(CampaignDB)
                .filter(CampaignDB.id == variant.campaign_id)
                .first()
            )
            if campaign is None:
                pytest.skip("no campaign for that variant")

            # status ok AND a message: the combination the old code ignored.
            run = AIRunDB(
                task_key="subject_preheader",
                provider="mock",
                status="ok",
                output_text="1. A subject line\n2. Another one\n",
                message=marker,
                target_type="variant",
                target_id=variant.id,
            )
            db.add(run)
            db.commit()
            db.refresh(run)

            user = db.query(UserDB).filter(UserDB.is_active.is_(True)).first()
            if user is None:
                pytest.skip("no active user to sign in as")
            token = auth.verify_login_code(
                db, user.email, auth.request_login_code(db, user.email)
            )
            client = TestClient(app, follow_redirects=False)
            client.cookies.set(auth.SESSION_COOKIE, token)

            response = client.get(f"/ui/campaigns/{campaign.id}?ai_run={run.id}")

            assert response.status_code == 200
            assert marker in response.text, (
                "a successful run carrying a truncation message rendered without "
                "it — the message is recorded but the manager never sees it, "
                "which is the defect this fix addresses"
            )
        finally:
            if run is not None:
                db.query(AIRunDB).filter(AIRunDB.id == run.id).delete()
                db.commit()
            db.close()
