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
from app.campaigns.service import (
    create_campaign, create_module_for_variant, create_variant_for_campaign,
)
from app.channels.registry import get_channel, list_channels, max_modules_for
from app.modules.registry import get_manifest, list_manifests
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
    # In foreign-key order, and covering everything these tests can create
    # even when they fail. An override row blocked the module delete once,
    # which is the same shape of leak the duplication fixtures hit: the sweep
    # has to know about every table the tests touch, because nothing cascades.
    from pathlib import Path

    from app.content.db_models import ContentRecordDB, ContentVersionDB
    from app.overrides.db_models import ContentOverrideDB
    from app.snapshots.db_models import SnapshotDB

    ids = [c.id for c in session.query(CampaignDB).filter(
        CampaignDB.name.like(f"{PREFIX}-%")).all()]
    vids = [v.id for v in session.query(VariantDB).filter(
        VariantDB.campaign_id.in_(ids or [-1])).all()]
    mids = [m.id for m in session.query(ModuleInstanceDB).filter(
        ModuleInstanceDB.variant_id.in_(vids or [-1])).all()]

    session.query(ContentOverrideDB).filter(
        ContentOverrideDB.module_instance_id.in_(mids or [-1])).delete(synchronize_session=False)
    # A snapshot that wrote a file leaves one behind too — an inline one does
    # not, which is half the point of storing it in the row.
    for row in session.query(SnapshotDB).filter(SnapshotDB.variant_id.in_(vids or [-1])).all():
        if row.html_storage_type != "inline" and row.html_location not in ("pending", ""):
            Path(row.html_location).unlink(missing_ok=True)
    session.query(SnapshotDB).filter(
        SnapshotDB.variant_id.in_(vids or [-1])).delete(synchronize_session=False)
    session.query(ModuleInstanceDB).filter(
        ModuleInstanceDB.variant_id.in_(vids or [-1])).delete(synchronize_session=False)
    session.query(VariantDB).filter(
        VariantDB.id.in_(vids or [-1])).delete(synchronize_session=False)
    session.query(CampaignDB).filter(
        CampaignDB.id.in_(ids or [-1])).delete(synchronize_session=False)

    cids = [r.id for r in session.query(ContentRecordDB).filter(
        ContentRecordDB.title.like(f"{PREFIX}-%")).all()]
    session.query(ContentVersionDB).filter(
        ContentVersionDB.content_record_id.in_(cids or [-1])).delete(synchronize_session=False)
    session.query(ContentRecordDB).filter(
        ContentRecordDB.id.in_(cids or [-1])).delete(synchronize_session=False)
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


class TestAChannelOnlyOffersItsOwnModules:
    """ADR-161 point 7: a channel is "an attribute on the variant **plus which
    manifests it accepts**". ADR-162 point 5 makes that a directory plus a
    declaration plus an assertion.

    This is the leak that made the directory restructure part of the channel
    work rather than a later tidy-up: the registry was flat and global, and the
    add-module dropdown was built once per page, so the moment a second
    channel's manifest existed an email composer was offered it.
    """

    def test_an_email_composer_is_not_offered_push_modules(self):
        email = {m.name for m in list_manifests("email")}
        push = {m.name for m in list_manifests("push")}
        assert push, "no push modules are registered, so this proves nothing"
        assert email, "no email modules are registered, so this proves nothing"
        assert email.isdisjoint(push), (
            f"these modules are offered on both channels: {email & push}. A "
            "manager composing an email would be able to add a module whose "
            "renderer cannot take it"
        )
        assert "notification" not in email

    def test_the_same_name_on_two_channels_resolves_to_different_modules(self):
        """The reason the key is (channel, name) and not name."""
        assert get_manifest("email", "cta") is not None
        assert get_manifest("push", "cta") is None, (
            "an email module resolved on the push channel — the lookup is "
            "ignoring the channel, which is what namespacing exists to prevent"
        )

    def test_a_push_module_loads_without_a_template_file(self):
        """ADR-160 point 2: "a push renderer fills fields and has no layout
        job", because the receiving OS does the rendering. The registry skips a
        manifest with no `.html` counterpart, so push would silently vanish
        without this — declared per module, which keeps ADR-161 point 7's split
        intact (module manifest = fields and limits; channel = cardinality)."""
        manifest = get_manifest("push", "notification")
        assert manifest is not None, "the push module was skipped for having no template"
        assert manifest.has_template is False
        from app.modules.registry import get_template_html
        assert get_template_html("push", "notification") is None

    def test_a_misfiled_manifest_fails_loudly_rather_than_being_offered(self):
        """ADR-162 point 5: "**the assertion matters more than either**" — a
        misfiled manifest would otherwise surface as a manager being offered a
        module that cannot render.

        Deliberately raises rather than logging-and-skipping, which is how a
        merely malformed manifest is treated. The difference: a typo costs that
        one module; a manifest in the wrong directory offers it on a channel
        whose renderer will not take it.
        """
        import json

        from app.modules import registry
        from app.modules.registry import MisfiledManifestError

        misfiled = registry.MODULES_DIR / "push" / f"{PREFIX}_misfiled.json"
        misfiled.write_text(json.dumps({
            "label": "Misfiled", "channel": "email", "cms": False,
            "has_template": False, "variables": [],
        }))
        try:
            registry._registry_mtime = None  # force rediscovery
            with pytest.raises(MisfiledManifestError, match="declares channel"):
                registry.list_manifests("push")
        finally:
            misfiled.unlink(missing_ok=True)
            registry._registry_mtime = None
        # And the registry recovers once the file is gone.
        assert get_manifest("push", "notification") is not None

    def test_the_add_module_form_offers_only_the_variant_s_channel(
        self, db, campaign, monkeypatch
    ):
        """The page-level version of the same thing — the form is rendered per
        variant, so two variants on one page offer different modules."""
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        from fastapi.testclient import TestClient

        from main import app

        create_variant_for_campaign(
            db, campaign_id=campaign.id, name=_name("push"), channel="push"
        )
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
            page = client.get(f"/ui/campaigns/{campaign.id}")
            assert page.status_code == 200
            assert 'value="notification"' in page.text, (
                "the push variant was not offered its own module"
            )
            assert 'value="single_stack"' in page.text, (
                "the email variant was not offered its own module"
            )
            # Both appear on the page because both variants are on it. What
            # must not happen is one form offering the other's — counted rather
            # than asserted on the page as a whole.
            assert page.text.count('value="notification"') == 1, (
                "the push module appears more than once — an email variant's "
                "form is offering it"
            )
        finally:
            db.query(SessionDB).filter(SessionDB.user_id == user.id).delete()
            db.query(RoleAssignmentDB).filter(RoleAssignmentDB.user_id == user.id).delete()
            db.query(AuditEventDB).filter(AuditEventDB.actor_id == user.id).delete(
                synchronize_session=False)
            db.query(UserDB).filter(UserDB.id == user.id).delete()
            db.commit()


class TestCardinalityIsDeclaredNotCodedIn:
    """ADR-160 point 2: push is one message rather than a composition, and
    **"the channel declares max one module as a declared capability rather than
    the composition code special-casing push"**.

    That sentence is the test. Nothing in `create_module_for_variant` knows what
    push is — it reads a number out of a manifest. Which is also why a channel
    added later needs no change here.
    """

    def test_a_push_variant_refuses_a_second_module(self, db, campaign):
        variant = create_variant_for_campaign(
            db, campaign_id=campaign.id, name=_name("push"), channel="push"
        )
        first = create_module_for_variant(
            db, variant_id=variant.id, module_type="notification",
            module_data={"push_title": "Snow is here"},
        )
        assert first is not None

        with pytest.raises(ValueError, match="already does"):
            create_module_for_variant(
                db, variant_id=variant.id, module_type="notification",
                module_data={"push_title": "And again"},
            )
        assert db.query(ModuleInstanceDB).filter(
            ModuleInstanceDB.variant_id == variant.id
        ).count() == 1

    def test_an_email_variant_is_not_limited(self, db, campaign):
        """Without this, the test above could pass by refusing every second
        module on every channel."""
        variant = create_variant_for_campaign(
            db, campaign_id=campaign.id, name=_name("email"), channel="email"
        )
        for _ in range(3):
            create_module_for_variant(
                db, variant_id=variant.id, module_type="cta", module_data={},
            )
        assert db.query(ModuleInstanceDB).filter(
            ModuleInstanceDB.variant_id == variant.id
        ).count() == 3, "email declares no limit, so three modules must fit"

    def test_the_limit_comes_from_the_manifest_not_from_the_code(self, db, campaign):
        """Change the declared number and the behaviour changes with it —
        which is what "declared capability" has to mean to be worth the words."""
        import json

        from app.channels import registry as channel_registry

        path = channel_registry.CHANNELS_DIR / "email.json"
        original = path.read_text()
        variant = create_variant_for_campaign(
            db, campaign_id=campaign.id, name=_name("capped"), channel="email"
        )
        try:
            data = json.loads(original)
            data["max_modules"] = 1
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            channel_registry._registry_mtime = None

            create_module_for_variant(
                db, variant_id=variant.id, module_type="cta", module_data={})
            with pytest.raises(ValueError, match="already does"):
                create_module_for_variant(
                    db, variant_id=variant.id, module_type="cta", module_data={})
        finally:
            path.write_text(original)
            channel_registry._registry_mtime = None


class TestAModuleMustBelongToItsVariantsChannel:

    def test_a_push_module_cannot_be_added_to_an_email_variant(self, db, campaign):
        """The composer's dropdown is scoped per channel — but a dropdown is
        not a control, and a hand-crafted POST never sees it. Same shape as the
        channel-availability hole one level up."""
        variant = create_variant_for_campaign(
            db, campaign_id=campaign.id, name=_name("email"), channel="email"
        )
        with pytest.raises(ValueError, match="not a Email module"):
            create_module_for_variant(
                db, variant_id=variant.id, module_type="notification", module_data={})

    def test_an_email_module_cannot_be_added_to_a_push_variant(self, db, campaign):
        variant = create_variant_for_campaign(
            db, campaign_id=campaign.id, name=_name("push"), channel="push"
        )
        with pytest.raises(ValueError, match="not a Push notification module"):
            create_module_for_variant(
                db, variant_id=variant.id, module_type="single_stack", module_data={})

    def test_each_channel_still_accepts_its_own(self, db, campaign):
        """Without this, both tests above could pass by refusing everything."""
        email = create_variant_for_campaign(
            db, campaign_id=campaign.id, name=_name("email"), channel="email")
        push = create_variant_for_campaign(
            db, campaign_id=campaign.id, name=_name("push"), channel="push")
        assert create_module_for_variant(
            db, variant_id=email.id, module_type="single_stack", module_data={}) is not None
        assert create_module_for_variant(
            db, variant_id=push.id, module_type="notification", module_data={}) is not None

    def test_a_full_variant_is_not_offered_the_add_module_form(
        self, db, campaign, monkeypatch
    ):
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        from fastapi.testclient import TestClient

        from main import app

        variant = create_variant_for_campaign(
            db, campaign_id=campaign.id, name=_name("push"), channel="push")
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
            page = client.get(f"/ui/campaigns/{campaign.id}")
            assert 'value="notification"' in page.text, "the empty push variant should offer its module"

            create_module_for_variant(
                db, variant_id=variant.id, module_type="notification",
                module_data={"push_title": "Full now"})

            page = client.get(f"/ui/campaigns/{campaign.id}")
            assert "already does" in page.text, (
                "a full push variant still showed an add-module form with no "
                "explanation of why submitting it would fail"
            )
        finally:
            db.query(SessionDB).filter(SessionDB.user_id == user.id).delete()
            db.query(RoleAssignmentDB).filter(RoleAssignmentDB.user_id == user.id).delete()
            db.query(AuditEventDB).filter(AuditEventDB.actor_id == user.id).delete(
                synchronize_session=False)
            db.query(UserDB).filter(UserDB.id == user.id).delete()
            db.commit()


class TestEachChannelRendersItsOwnShape:
    """ADR-162 point 4 — one renderer per channel, keyed by channel and
    auto-registering. The artifact belongs to the channel; the provider merely
    transmits it, so a push artifact is the same whether FCM or OneSignal
    carries it."""

    def _push_variant_with_content(self, db, campaign, **content):
        from app.content.service import create_content

        record = create_content(
            db,
            title=_name("pushcontent"),
            brand_id=campaign.brand_id,
            content={"push_title": "Snow is here",
                     "push_body": "Two metres at 1800m.",
                     "push_link": "https://winter.example/snow", **content},
        )
        variant = create_variant_for_campaign(
            db, campaign_id=campaign.id, name=_name("push"), channel="push")
        create_module_for_variant(
            db, variant_id=variant.id, module_type="notification",
            content_record_id=record.id)
        return variant, record

    def test_a_push_variant_renders_fields_not_html(self, db, campaign):
        from app.rendering.renderers.base import ROLE_PAYLOAD
        from app.rendering.service import render_variant

        variant, _ = self._push_variant_with_content(db, campaign)
        artifact = render_variant(db, variant.id, mode="preview")

        assert artifact.role == ROLE_PAYLOAD
        assert artifact.body is None, (
            "the push renderer produced a document. ADR-160 point 2: the "
            "receiving OS does all rendering, so a push renderer fills fields "
            "and has no layout job"
        )
        assert artifact.fields["push_title"] == "Snow is here"
        assert artifact.fields["push_body"] == "Two metres at 1800m."

    def test_an_email_variant_still_renders_html(self, db, campaign):
        """Without this, the test above could pass by breaking email."""
        from app.rendering.renderers.base import ROLE_HTML
        from app.rendering.service import render_variant

        variant = create_variant_for_campaign(
            db, campaign_id=campaign.id, name=_name("email"), channel="email")
        create_module_for_variant(
            db, variant_id=variant.id, module_type="cta",
            module_data={"label": "Book", "url": "https://x.example"})
        artifact = render_variant(db, variant.id, mode="preview")
        assert artifact.role == ROLE_HTML
        assert artifact.fields is None
        assert "<" in (artifact.body or ""), "email stopped producing markup"

    def test_a_channel_with_no_renderer_refuses_rather_than_falling_back(
        self, db, campaign
    ):
        """A fallback to email would render a push variant as an HTML email and
        deliver something nobody composed."""
        from app.rendering.service import render_variant

        variant = create_variant_for_campaign(
            db, campaign_id=campaign.id, name=_name("orphan"), channel="push")
        db.query(VariantDB).filter(VariantDB.id == variant.id).update(
            {"channel": "letterpress"})
        db.commit()
        with pytest.raises(ValueError, match="no renderer is registered"):
            render_variant(db, variant.id, mode="preview")

    def test_an_override_reaches_a_push_field(self, db, campaign):
        """ADR-162 point 1 claims moving fields into modules means "overrides
        work unchanged". That is only true if every channel resolves its fields
        through one path — so this is the test that keeps the second copy of
        that loop from being written."""
        from app.overrides.models import ContentOverrideCreate
        from app.overrides.service import create_content_override
        from app.rendering.service import render_variant

        variant, _ = self._push_variant_with_content(db, campaign)
        module = db.query(ModuleInstanceDB).filter(
            ModuleInstanceDB.variant_id == variant.id).first()
        create_content_override(db, ContentOverrideCreate(
            module_instance_id=module.id,
            field_overrides={"push_title": "Overridden title"},
            overridden_by="test",
        ))
        artifact = render_variant(db, variant.id, mode="preview")
        assert artifact.fields["push_title"] == "Overridden title", (
            "the override layer did not reach a push field — push is resolving "
            "its content through its own path instead of the shared one"
        )


class TestAPushSnapshotLivesInTheRowNotOnDisk:
    """Decided 2026-09-17 (user). Writing a push payload to a .json beside the
    .html files was the smaller diff and was rejected: it hardens the artifact
    the project has a recorded lean away from, and leaves columns named html_*
    holding a push payload.

    This does NOT decide the open snapshot-storage question. It makes push the
    first channel whose artifact lives in a table.
    """

    def test_a_push_snapshot_writes_no_file(self, db, campaign):
        from app.snapshots.db_models import SnapshotDB
        from app.snapshots.service import SNAPSHOT_STORAGE_DIR, create_snapshot_for_variant
        from app.content.service import create_content, create_content_version

        record = create_content(
            db, title=_name("pushcontent"), brand_id=campaign.brand_id,
            content={"push_title": "Ready", "push_body": "Go."})
        create_content_version(db, content_record_id=record.id, created_by="test")
        variant = create_variant_for_campaign(
            db, campaign_id=campaign.id, name=_name("push"), channel="push")
        create_module_for_variant(
            db, variant_id=variant.id, module_type="notification",
            content_record_id=record.id)

        before = set(SNAPSHOT_STORAGE_DIR.glob("*")) if SNAPSHOT_STORAGE_DIR.exists() else set()
        snapshot = create_snapshot_for_variant(db, variant_id=variant.id)
        try:
            after = set(SNAPSHOT_STORAGE_DIR.glob("*")) if SNAPSHOT_STORAGE_DIR.exists() else set()
            assert after == before, f"a push snapshot wrote files: {after - before}"

            row = db.get(SnapshotDB, snapshot.id)
            assert row.html_storage_type == "inline"
            assert row.html_location == "inline:render_context"
            stored = row.render_context["artifact"]
            assert stored["role"] == "payload"
            assert stored["fields"]["push_title"] == "Ready"
            assert row.html_size > 0, "an inline artifact still has a size"
        finally:
            db.query(SnapshotDB).filter(SnapshotDB.id == snapshot.id).delete()
            db.commit()

    def test_a_push_snapshot_still_refuses_unpublished_content(self, db, campaign):
        """The same rule email has (ADR-128). Storage shape changed; the
        publication gate did not."""
        from app.rendering.service import UnpublishedContentError
        from app.snapshots.service import create_snapshot_for_variant
        from app.content.service import create_content

        record = create_content(
            db, title=_name("unpublished"), brand_id=campaign.brand_id,
            content={"push_title": "Draft", "push_body": "Not frozen."})
        variant = create_variant_for_campaign(
            db, campaign_id=campaign.id, name=_name("push"), channel="push")
        create_module_for_variant(
            db, variant_id=variant.id, module_type="notification",
            content_record_id=record.id)

        with pytest.raises(UnpublishedContentError):
            create_snapshot_for_variant(db, variant_id=variant.id)

    def test_the_artifact_reads_back_for_both_shapes(self, db, campaign):
        from app.snapshots.db_models import SnapshotDB
        from app.snapshots.service import create_snapshot_for_variant, get_snapshot_artifact
        from app.content.service import create_content, create_content_version

        record = create_content(
            db, title=_name("both"), brand_id=campaign.brand_id,
            content={"push_title": "Hi", "push_body": "There",
                     "headline_medium": "Hi", "body_medium": "There"})
        create_content_version(db, content_record_id=record.id, created_by="test")

        push = create_variant_for_campaign(
            db, campaign_id=campaign.id, name=_name("push"), channel="push")
        create_module_for_variant(db, variant_id=push.id,
                                  module_type="notification", content_record_id=record.id)
        email = create_variant_for_campaign(
            db, campaign_id=campaign.id, name=_name("email"), channel="email")
        create_module_for_variant(db, variant_id=email.id,
                                  module_type="single_stack", content_record_id=record.id)

        push_snap = create_snapshot_for_variant(db, variant_id=push.id)
        email_snap = create_snapshot_for_variant(db, variant_id=email.id)
        try:
            assert get_snapshot_artifact(db, push_snap.id)["role"] == "payload"
            assert get_snapshot_artifact(db, email_snap.id)["role"] == "html", (
                "email's snapshot stopped reading back — the inline branch is "
                "catching a case it should not"
            )
        finally:
            from pathlib import Path
            row = db.get(SnapshotDB, email_snap.id)
            if row and row.html_location not in ("pending", "inline:render_context"):
                Path(row.html_location).unlink(missing_ok=True)
            db.query(SnapshotDB).filter(
                SnapshotDB.id.in_([push_snap.id, email_snap.id])).delete(
                    synchronize_session=False)
            db.commit()
