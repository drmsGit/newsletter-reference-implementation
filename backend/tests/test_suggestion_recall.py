"""Past AI suggestions become readable again — `docs/backlog.md` #103.

The user found this from the UI without reading the backlog: ask for subject
lines, leave the page, and the other two options are gone. They were never
lost — `AIRunDB` kept the full reply, the prompt version and the cost — but the
only way to read them was SQL, so an audit trail existed without being usable
by the person it is for.

**The test that matters is `test_an_option_that_was_never_picked_is_still_
reachable`**, because that is the actual complaint. Everything else here is the
plumbing that makes it true.

Runs against the shared dev database and removes everything it creates.
"""
import uuid
from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.ai.db_models import AIRunDB
from app.ai.service import runs_for_brand, runs_for_target
from app.auth import service as auth
from app.campaigns.db_models import CampaignDB, VariantDB
from app.database import SessionLocal
from main import app

TAG = "recall"
THREE_OPTIONS = (
    "1. SUBJECT: Kept option one\n   PREHEADER: First preheader\n"
    "2. SUBJECT: Kept option two\n   PREHEADER: Second preheader\n"
    "3. SUBJECT: Kept option three\n   PREHEADER: Third preheader\n"
)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def variant(db):
    brand = auth.ensure_default_brand(db)
    campaign = CampaignDB(brand_id=brand.id, name=f"{TAG}-{uuid.uuid4().hex[:8]}")
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    row = VariantDB(campaign_id=campaign.id, name=f"{TAG} variant", channel="email")
    db.add(row)
    db.commit()
    db.refresh(row)
    try:
        yield row
    finally:
        db.rollback()
        db.query(AIRunDB).filter(
            AIRunDB.target_type == "variant", AIRunDB.target_id == row.id
        ).delete(synchronize_session=False)
        db.execute(text("DELETE FROM module_instances WHERE variant_id = :v"),
                   {"v": row.id})
        db.query(VariantDB).filter(VariantDB.id == row.id).delete()
        db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
        db.commit()


def _run(db, variant, text_out=THREE_OPTIONS, status="ok", message=None):
    run = AIRunDB(
        task_key="subject_preheader", provider="mock", model="mock",
        status=status, input_tokens=11, output_tokens=22,
        target_type="variant", target_id=variant.id,
        output_text=text_out, message=message,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _signed_in(db):
    user = auth.create_user(
        db, email=f"{TAG}-{uuid.uuid4().hex[:8]}@example.invalid", role_key="admin",
    )
    token = auth.create_session(db, user)
    client = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
    client.cookies.set(auth.SESSION_COOKIE, token)
    return client, user


def _cleanup_user(db, user):
    db.rollback()
    for table in ("login_codes", "auth_sessions", "role_assignments"):
        db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
    db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
    db.commit()


class TestTheHistoryPage:

    def test_an_option_that_was_never_picked_is_still_reachable(self, db, variant):
        """**The complaint, as a test.**

        Three options were generated, one was applied, the page was left. The
        other two must still be readable — and usable, because a manager who
        comes back is usually coming back to change their mind.
        """
        _run(db, variant)
        client, user = _signed_in(db)
        try:
            page = client.get(
                f"/ui/campaigns/{variant.campaign_id}/variants/{variant.id}/suggestions"
            )
            assert page.status_code == 200
            for option in ("Kept option one", "Kept option two", "Kept option three"):
                assert option in page.text, option
            assert page.text.count("Use this") >= 3, (
                "reachable is not enough — they have to be applicable"
            )
        finally:
            _cleanup_user(db, user)

    def test_every_run_is_listed_not_only_the_last(self, db, variant):
        """The backlog weighed "keep the last options on the variant" and chose
        a history for this reason: it covers every run."""
        _run(db, variant, "1. SUBJECT: Older idea\n   PREHEADER: x\n")
        _run(db, variant)
        client, user = _signed_in(db)
        try:
            page = client.get(
                f"/ui/campaigns/{variant.campaign_id}/variants/{variant.id}/suggestions"
            ).text
            assert "Older idea" in page and "Kept option one" in page
        finally:
            _cleanup_user(db, user)

    def test_the_prompt_version_and_cost_are_shown(self, db, variant):
        """ADR-140 §5 keeps these; the backlog says this page is where "which
        prompt version produced this?" naturally belongs."""
        _run(db, variant)
        client, user = _signed_in(db)
        try:
            page = client.get(
                f"/ui/campaigns/{variant.campaign_id}/variants/{variant.id}/suggestions"
            ).text
            assert "11 in / 22 out" in page
            assert "mock" in page
        finally:
            _cleanup_user(db, user)

    def test_a_reply_with_no_readable_options_is_shown_verbatim(self, db, variant):
        """The empty-variant refusal again: when the model talks instead of
        answering, the talk is the useful part."""
        _run(db, variant, "I don't have the newsletter content yet.")
        client, user = _signed_in(db)
        try:
            page = client.get(
                f"/ui/campaigns/{variant.campaign_id}/variants/{variant.id}/suggestions"
            ).text
            assert "No options could be read from this reply" in page
            assert "newsletter content yet" in page
        finally:
            _cleanup_user(db, user)

    def test_another_brands_variant_is_not_reachable(self, db, variant):
        from app.auth.db_models import BrandDB

        other = BrandDB(key=f"{TAG}-{uuid.uuid4().hex[:8]}", name="Elsewhere")
        db.add(other)
        db.commit()
        db.refresh(other)
        campaign = db.query(CampaignDB).filter(
            CampaignDB.id == variant.campaign_id
        ).first()
        campaign.brand_id = other.id
        db.commit()
        client, user = _signed_in(db)
        try:
            response = client.get(
                f"/ui/campaigns/{variant.campaign_id}/variants/{variant.id}/suggestions"
            )
            assert response.status_code == 303
            # The message is percent-encoded into the query string, so compare
            # after unquoting rather than against the wire form.
            assert "does not exist in this brand" in unquote(
                response.headers["location"]
            )
        finally:
            db.rollback()
            campaign.brand_id = auth.ensure_default_brand(db).id
            db.commit()
            db.query(BrandDB).filter(BrandDB.id == other.id).delete()
            db.commit()
            _cleanup_user(db, user)


class TestTheListingHelpers:

    def test_runs_for_target_is_newest_first(self, db, variant):
        first = _run(db, variant, "1. SUBJECT: One\n")
        second = _run(db, variant, "1. SUBJECT: Two\n")

        found = runs_for_target(db, "variant", variant.id)

        assert [r.id for r in found][:2] == [second.id, first.id]

    def test_runs_for_brand_excludes_other_brands(self, db, variant):
        from app.auth.db_models import BrandDB

        mine = _run(db, variant)
        other = BrandDB(key=f"{TAG}-{uuid.uuid4().hex[:8]}", name="Elsewhere")
        db.add(other)
        db.commit()
        db.refresh(other)
        try:
            assert mine.id in [
                r.id for r in runs_for_brand(db, auth.ensure_default_brand(db).id)
            ]
            assert mine.id not in [r.id for r in runs_for_brand(db, other.id)], (
                "a run was visible from a brand it has nothing to do with"
            )
        finally:
            db.rollback()
            db.query(BrandDB).filter(BrandDB.id == other.id).delete()
            db.commit()


class TestTheApprovalsFilter:

    def test_ai_runs_appear_under_their_own_source(self, db, variant):
        _run(db, variant)
        client, user = _signed_in(db)
        try:
            page = client.get("/ui/approvals?source=ai")
            assert page.status_code == 200
            assert variant.name in page.text
            assert "the other store, not the same rows" in page.text, (
                "the screen should say what it is showing, since an applied "
                "run has no request and never did"
            )
        finally:
            _cleanup_user(db, user)

    def test_the_default_view_is_still_pending_requests(self, db, variant):
        _run(db, variant)
        client, user = _signed_in(db)
        try:
            assert "the other store" not in client.get("/ui/approvals").text
        finally:
            _cleanup_user(db, user)
