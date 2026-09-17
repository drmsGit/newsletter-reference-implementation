"""Channel is an attribute on the variant — ADR-160 point 4, built 2026-09-17.

Until this landed, the word "channel" appeared in one column in the whole
database: `delivery_executions.channel`, defaulting to `'email'`. That is a
**denormalised copy written at plan time**, not the model's home for it, so a
system that had designed six ADRs' worth of omni-channel could not say what
channel anything *was* until it was already being sent.

The two tests worth reading first are `test_the_column_refuses_a_variant_with
_no_channel` and `test_an_unregistered_channel_is_refused_even_by_a_hand_
crafted_post`. Both pin fail-closed decisions that are invisible when they work
and silent when they break: a default on the column would quietly make every
un-channelled variant an email, and a dropdown that hides a channel while the
route still accepts it is not a control.
"""
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.audit.db_models import AuditEventDB
from app.auth import service as auth
from app.auth.db_models import RoleAssignmentDB, RoleDB, SessionDB, UserDB
from app.auth.permissions import ADMIN
from app.campaigns import duplication
from app.campaigns.db_models import CampaignDB, ModuleInstanceDB, VariantDB
from app.campaigns.service import create_campaign, create_variant_for_campaign
from app.channels.registry import get_channel, list_channels, max_modules_for
from app.database import SessionLocal
from app.settings.service import (
    CHANNEL_AVAILABILITY_KEY, available_channels, channel_available,
    set_channel_available, set_config,
)

PREFIX = "chantest"


def _name(label: str) -> str:
    return f"{PREFIX}-{label}-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def db():
    session = SessionLocal()
    auth.bootstrap(session)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _restore_availability():
    """Availability is a shared config row, so a test that changes it must put
    it back — otherwise the next test runs against a deployment where somebody
    switched push off."""
    from app.settings.db_models import AppConfigDB

    session = SessionLocal()
    row = session.query(AppConfigDB).filter(
        AppConfigDB.key == CHANNEL_AVAILABILITY_KEY
    ).first()
    original = dict(row.value) if row and isinstance(row.value, dict) else None
    session.close()
    yield
    session = SessionLocal()
    if original is None:
        session.query(AppConfigDB).filter(
            AppConfigDB.key == CHANNEL_AVAILABILITY_KEY
        ).delete()
    else:
        set_config(session, CHANNEL_AVAILABILITY_KEY, original)
    session.commit()
    session.close()


@pytest.fixture(scope="module", autouse=True)
def _sweep():
    yield
    session = SessionLocal()
    ids = [c.id for c in session.query(CampaignDB).filter(
        CampaignDB.name.like(f"{PREFIX}-%")).all()]
    vids = [v.id for v in session.query(VariantDB).filter(
        VariantDB.campaign_id.in_(ids or [-1])).all()]
    session.query(ModuleInstanceDB).filter(
        ModuleInstanceDB.variant_id.in_(vids or [-1])).delete(synchronize_session=False)
    session.query(VariantDB).filter(
        VariantDB.id.in_(vids or [-1])).delete(synchronize_session=False)
    session.query(CampaignDB).filter(
        CampaignDB.id.in_(ids or [-1])).delete(synchronize_session=False)
    session.commit()
    session.close()


@pytest.fixture
def campaign(db):
    brand = auth.ensure_default_brand(db)
    made = create_campaign(db, name=_name("campaign"), brand_id=brand.id, channel="email")
    return db.get(CampaignDB, made.id)


class TestTheManifestIsTheChannel:
    """ADR-160 point 6 — two files, no config step, no registry table."""

    def test_push_declares_one_module_and_email_declares_none(self, db):
        assert max_modules_for("push") == 1, (
            "push must declare max one module. ADR-160 point 2 requires that to "
            "be 'a declared capability rather than the composition code "
            "special-casing push' — a number in a file is how that promise is kept"
        )
        assert max_modules_for("email") is None, "email is unbounded"

    def test_an_unknown_channel_answers_one_not_unbounded(self, db):
        """Fail-closed. The caller is about to refuse it anyway, and guessing
        'unlimited' for something nobody declared is the wrong way to be wrong."""
        assert max_modules_for(f"no-such-channel-{uuid.uuid4().hex[:6]}") == 1

    def test_registering_is_not_the_same_as_being_available(self, db):
        """ADR-160 point 8's whole distinction, in one assertion."""
        assert get_channel("push") is not None, "push is registered on disk"
        set_channel_available(db, "push", False)
        assert get_channel("push") is not None, (
            "disabling a channel must not unregister it — a company without a "
            "contract still has the files, and deleting them is not how anyone "
            "manages a contract they do not hold"
        )
        assert channel_available(db, "push") is False
        assert "push" not in [c.name for c in available_channels(db)]


class TestTheColumnIsFailClosed:

    def test_the_column_refuses_a_variant_with_no_channel(self, db, campaign):
        """**The most important test here.** A server default would make this
        pass silently and turn every un-channelled variant into an email —
        harmless exactly until a second channel exists, which is now."""
        db.add(VariantDB(campaign_id=campaign.id, name=_name("orphan"), status="draft"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_the_model_declares_no_server_default_either(self):
        """The migration uses a DEFAULT to backfill and then drops it; the model
        must not put one back.

        This is asserted separately from the IntegrityError above because the
        two cover different databases. `server_default` is DDL-generation only,
        so adding one to the model changes nothing about the table that already
        exists — it changes the table `create_all()` builds on a **fresh**
        database, where a caller that forgets the channel would then silently
        get an email variant. That divergence is invisible to every test that
        runs against the migrated database, which is all of them.
        """
        assert VariantDB.__table__.c.channel.server_default is None, (
            "the model grew a server default for channel. The migration "
            "deliberately drops it, so a fresh database built by create_all() "
            "would now disagree with a migrated one"
        )

    def test_every_variant_that_existed_before_today_is_email(self, db):
        """The migration's backfill claim, which is true by construction —
        email was the only thing the system could render or send."""
        assert db.query(VariantDB).filter(VariantDB.channel.is_(None)).count() == 0

    def test_a_variant_keeps_the_channel_it_was_created_with(self, db, campaign):
        variant = create_variant_for_campaign(
            db, campaign_id=campaign.id, name=_name("push"), channel="push"
        )
        assert variant.channel == "push"
        assert db.get(VariantDB, variant.id).channel == "push"

    def test_a_push_variant_carries_no_subject_or_preheader(self, db, campaign):
        """Those are fields of an *email*. ADR-162 point 1 moves them into a
        `header` module and is unbuilt, so they are still columns — which makes
        it possible for a push row to assert an email property of something
        that is not an email. The route drops them; this pins that it does."""
        from fastapi.testclient import TestClient

        from main import app

        user = UserDB(email=f"{PREFIX}-{uuid.uuid4().hex[:8]}@example.invalid", is_active=True)
        db.add(user); db.commit(); db.refresh(user)
        role = db.query(RoleDB).filter(RoleDB.key == ADMIN).first()
        db.add(RoleAssignmentDB(user_id=user.id, role_id=role.id,
                                brand_id=auth.ensure_default_brand(db).id))
        db.commit()
        token = auth.create_session(db, user)
        client = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
        client.cookies.set(auth.SESSION_COOKIE, token)
        try:
            name = _name("pushvariant")
            response = client.post(
                f"/ui/campaigns/{campaign.id}/variants",
                data={"name": name, "channel": "push",
                      "subject": "This should not survive",
                      "preheader": "Nor this",
                      "csrf_token": auth.csrf_token_for(token)},
            )
            assert response.status_code == 303
            variant = db.query(VariantDB).filter(VariantDB.name == name).first()
            assert variant is not None and variant.channel == "push"
            assert variant.subject is None and variant.preheader is None, (
                "a push variant kept an email subject line — a hand-crafted POST "
                "never sees the form that hides the field, so hiding it in the "
                "template is not the control"
            )
        finally:
            db.query(SessionDB).filter(SessionDB.user_id == user.id).delete()
            db.query(RoleAssignmentDB).filter(RoleAssignmentDB.user_id == user.id).delete()
            db.query(AuditEventDB).filter(AuditEventDB.actor_id == user.id).delete(
                synchronize_session=False)
            db.query(UserDB).filter(UserDB.id == user.id).delete()
            db.commit()


class TestTheRouteRefusesWhatTheDropdownHides:
    """ADR-160 point 8: a disabled channel "disappears from the variant-creation
    UI **and is refused server-side if requested directly**". Two halves, and
    only the second one is a control."""

    def _client(self, db):
        from fastapi.testclient import TestClient

        from main import app

        user = UserDB(email=f"{PREFIX}-{uuid.uuid4().hex[:8]}@example.invalid", is_active=True)
        db.add(user); db.commit(); db.refresh(user)
        role = db.query(RoleDB).filter(RoleDB.key == ADMIN).first()
        db.add(RoleAssignmentDB(user_id=user.id, role_id=role.id,
                                brand_id=auth.ensure_default_brand(db).id))
        db.commit()
        token = auth.create_session(db, user)
        client = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
        client.cookies.set(auth.SESSION_COOKIE, token)
        return client, token, user

    def _cleanup(self, db, user):
        db.query(SessionDB).filter(SessionDB.user_id == user.id).delete()
        db.query(RoleAssignmentDB).filter(RoleAssignmentDB.user_id == user.id).delete()
        db.query(AuditEventDB).filter(AuditEventDB.actor_id == user.id).delete(
            synchronize_session=False)
        db.query(UserDB).filter(UserDB.id == user.id).delete()
        db.commit()

    def test_an_unregistered_channel_is_refused_even_by_a_hand_crafted_post(
        self, db, campaign, monkeypatch
    ):
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        client, token, user = self._client(db)
        name = _name("smuggled")
        try:
            response = client.post(
                f"/ui/campaigns/{campaign.id}/variants",
                data={"name": name, "channel": "carrier-pigeon",
                      "csrf_token": auth.csrf_token_for(token)},
            )
            assert "error=" in response.headers.get("location", ""), (
                "a channel with no manifest on disk was accepted"
            )
            assert db.query(VariantDB).filter(VariantDB.name == name).count() == 0
        finally:
            self._cleanup(db, user)

    def test_a_registered_but_disabled_channel_is_refused_too(
        self, db, campaign, monkeypatch
    ):
        """Without this, the test above could pass by only checking the disk."""
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        set_channel_available(db, "push", False)
        client, token, user = self._client(db)
        name = _name("disabled")
        try:
            response = client.post(
                f"/ui/campaigns/{campaign.id}/variants",
                data={"name": name, "channel": "push",
                      "csrf_token": auth.csrf_token_for(token)},
            )
            assert "error=" in response.headers.get("location", ""), (
                "push was accepted although this deployment has it switched off"
            )
            assert db.query(VariantDB).filter(VariantDB.name == name).count() == 0
        finally:
            self._cleanup(db, user)

    def test_the_same_request_succeeds_when_the_channel_is_on(
        self, db, campaign, monkeypatch
    ):
        """Without this, both tests above could pass by refusing everything."""
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        client, token, user = self._client(db)
        name = _name("allowed")
        try:
            response = client.post(
                f"/ui/campaigns/{campaign.id}/variants",
                data={"name": name, "channel": "push",
                      "csrf_token": auth.csrf_token_for(token)},
            )
            assert "error=" not in response.headers.get("location", "")
            assert db.query(VariantDB).filter(VariantDB.name == name).count() == 1
        finally:
            self._cleanup(db, user)

    def test_a_disabled_channel_disappears_from_the_creation_ui(
        self, db, campaign, monkeypatch
    ):
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        client, token, user = self._client(db)
        try:
            page = client.get(f"/ui/campaigns/{campaign.id}")
            assert 'value="push"' in page.text, "push should be offered while enabled"
            set_channel_available(db, "push", False)
            page = client.get(f"/ui/campaigns/{campaign.id}")
            assert 'value="push"' not in page.text, (
                "a channel this deployment switched off was still offered"
            )
        finally:
            self._cleanup(db, user)


class TestDuplicationCarriesTheChannel:

    def test_a_copied_push_variant_is_still_a_push_variant(self, db, campaign):
        """Channel is fixed at creation (ADR-160 point 5), so a copy cannot
        re-choose it — and a copy of a push variant whose modules are push
        modules is a push variant by construction."""
        create_variant_for_campaign(
            db, campaign_id=campaign.id, name=_name("original"), channel="push"
        )
        report = duplication.duplicate_campaign(
            db,
            campaign_id=campaign.id,
            target_brand_id=campaign.brand_id,
            name=_name("copy"),
            content_mode=duplication.KEEP,
        )
        copied = db.query(VariantDB).filter(
            VariantDB.campaign_id == report.campaign_id
        ).all()
        assert sorted(v.channel for v in copied) == ["email", "push"], (
            f"the copy's channels came out as {[v.channel for v in copied]} — a "
            "duplicated push variant that arrives as email would render with the "
            "wrong renderer and carry modules its channel does not accept"
        )
