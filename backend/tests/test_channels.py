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

    # Sends first: a send instance references a snapshot, which references a
    # variant. Deleting inwards-out is the only order that works, and every
    # table added to these tests has to be added here — nothing cascades.
    from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB
    from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
    from app.recipients.db_models import AddressabilityDB, ConsentEventDB, RecipientDB

    snap_ids = [r.id for r in session.query(SnapshotDB).filter(
        SnapshotDB.variant_id.in_(vids or [-1])).all()]
    send_ids = [r.id for r in session.query(SendInstanceDB).filter(
        SendInstanceDB.snapshot_id.in_(snap_ids or [-1])).all()]
    session.query(DeliveryExecutionDB).filter(
        DeliveryExecutionDB.send_instance_id.in_(send_ids or [-1])).delete(synchronize_session=False)
    session.query(SendInstanceDB).filter(
        SendInstanceDB.id.in_(send_ids or [-1])).delete(synchronize_session=False)

    group_ids = [r.id for r in session.query(AudienceGroupDB).filter(
        AudienceGroupDB.name.like(f"{PREFIX}-%")).all()]
    session.query(AudienceGroupMemberDB).filter(
        AudienceGroupMemberDB.group_id.in_(group_ids or [-1])).delete(synchronize_session=False)
    session.query(AudienceGroupDB).filter(
        AudienceGroupDB.id.in_(group_ids or [-1])).delete(synchronize_session=False)

    recipient_ids = [r.id for r in session.query(RecipientDB).filter(
        RecipientDB.external_id.like(f"{PREFIX}-%")).all()]
    session.query(ConsentEventDB).filter(
        ConsentEventDB.recipient_id.in_(recipient_ids or [-1])).delete(synchronize_session=False)
    session.query(AddressabilityDB).filter(
        AddressabilityDB.recipient_id.in_(recipient_ids or [-1])).delete(synchronize_session=False)
    session.query(DeliveryExecutionDB).filter(
        DeliveryExecutionDB.recipient_id.in_(recipient_ids or [-1])).delete(synchronize_session=False)
    session.query(RecipientDB).filter(
        RecipientDB.id.in_(recipient_ids or [-1])).delete(synchronize_session=False)

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


class TestPushContentIsAuthoredNotDerived:
    """ADR-160 point 3: "channel fields are **separate and required — never
    derived from email fields**", because deriving a 40-character push title
    from a 60-character headline at render time is the rendering-time
    transformation point 1 rejects.

    Which means the content form needs a place to write them. Until this, push
    rendering worked and no manager could reach it — the record had to be
    created in Python.
    """

    def _admin(self, db):
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

    def test_the_routes_accept_exactly_the_fields_the_manifest_declares(self):
        """FastAPI needs the form parameters spelled out, so the route holds a
        hand-written list beside a manifest — which is where drift lives. This
        is the assertion that makes adding a push field to the manifest and
        forgetting the route a failing test rather than a silent no-op."""
        from app.frontend.router import PUSH_CONTENT_FIELDS

        declared = tuple(v.name for v in get_manifest("push", "notification").variables)
        assert set(PUSH_CONTENT_FIELDS) == set(declared), (
            f"the content form accepts {sorted(PUSH_CONTENT_FIELDS)} but the push "
            f"manifest declares {sorted(declared)} — a field in one and not the "
            "other is either unauthorable or silently dropped"
        )

    def test_the_rendered_form_carries_its_own_section_marker(self, db, monkeypatch):
        """The marker is what makes "cleared" expressible, so the form has to
        actually emit it — a route reading a field no template sends is a
        guard that silently never fires."""
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        client, token, user = self._admin(db)
        try:
            page = client.get("/ui/content")
            assert 'name="channel_sections_present"' in page.text
            assert 'value="push"' in page.text
        finally:
            self._cleanup(db, user)

    def test_a_manager_can_author_push_copy_through_the_form(self, db, monkeypatch):
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        from app.content.db_models import ContentRecordDB

        client, token, user = self._admin(db)
        title = _name("authored")
        try:
            page = client.get("/ui/content")
            assert 'name="push_title"' in page.text, (
                "the create form has no push fields, so push copy cannot be written"
            )

            response = client.post("/ui/content", data={
                "title": title, "headline_medium": "Winter spa",
                "push_title": "Fresh snow", "push_body": "2m base.",
                "csrf_token": auth.csrf_token_for(token)})
            assert response.status_code == 303

            record = db.query(ContentRecordDB).filter(
                ContentRecordDB.title == title).first()
            assert record is not None
            assert record.content["push_title"] == "Fresh snow"
            assert record.content["headline_medium"] == "Winter spa", (
                "the email fields must survive alongside the push ones"
            )
        finally:
            db.query(ContentRecordDB).filter(ContentRecordDB.title == title).delete()
            db.commit()
            self._cleanup(db, user)

    def test_an_empty_push_title_is_absent_rather_than_blank(self, db, monkeypatch):
        """ADR-161 point 7's rider makes catalogue readiness "push fields not
        empty". Storing "" would make every record in the catalogue look
        push-ready, and a decision slot filtering on it would select copy that
        says nothing."""
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        from app.content.db_models import ContentRecordDB

        client, token, user = self._admin(db)
        title = _name("emailonly")
        try:
            client.post("/ui/content", data={
                "title": title, "headline_medium": "Just an email",
                "push_title": "", "push_body": "",
                "csrf_token": auth.csrf_token_for(token)})
            record = db.query(ContentRecordDB).filter(
                ContentRecordDB.title == title).first()
            assert "push_title" not in record.content, (
                f"an empty push title was stored as {record.content.get('push_title')!r}, "
                "so this record now looks prepared for a channel nobody prepared it for"
            )
        finally:
            db.query(ContentRecordDB).filter(ContentRecordDB.title == title).delete()
            db.commit()
            self._cleanup(db, user)

    def test_editing_with_push_switched_off_does_not_erase_push_copy(
        self, db, monkeypatch
    ):
        """**The reason the form fields default to None rather than "".**

        The edit route used to rebuild `content` from scratch, so any key the
        form did not carry was dropped. Harmless while the form knew every
        field; a data-loss bug the moment a section is conditionally rendered.
        """
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        from app.content.db_models import ContentRecordDB
        from app.content.service import create_content

        client, token, user = self._admin(db)
        record = create_content(
            db, title=_name("haspush"), brand_id=auth.ensure_default_brand(db).id,
            content={"headline_medium": "Spa", "push_title": "Booked out soon",
                     "push_body": "Only 3 rooms left."})
        set_channel_available(db, "push", False)
        try:
            page = client.get(f"/ui/content/{record.id}")
            assert 'name="push_title"' not in page.text, (
                "push is switched off but its fields are still rendered"
            )
            # The form the manager submits carries no push fields at all.
            client.post(f"/ui/content/{record.id}/edit", data={
                "title": record.title, "headline_medium": "Spa, revised",
                "csrf_token": auth.csrf_token_for(token)})

            stored = db.get(ContentRecordDB, record.id)
            db.refresh(stored)
            assert stored.content["headline_medium"] == "Spa, revised"
            assert stored.content.get("push_title") == "Booked out soon", (
                "editing a record while push was switched off erased its push "
                "copy — the form not asking about a field is not the author "
                "clearing it"
            )
        finally:
            db.query(ContentRecordDB).filter(ContentRecordDB.id == record.id).delete()
            db.commit()
            self._cleanup(db, user)

    def test_clearing_a_push_field_on_a_form_that_asks_does_remove_it(
        self, db, monkeypatch
    ):
        """Without this, the test above could pass by never removing anything."""
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        from app.content.db_models import ContentRecordDB
        from app.content.service import create_content

        client, token, user = self._admin(db)
        record = create_content(
            db, title=_name("clearable"), brand_id=auth.ensure_default_brand(db).id,
            content={"headline_medium": "Spa", "push_title": "Remove me"})
        try:
            client.post(f"/ui/content/{record.id}/edit", data={
                "title": record.title, "headline_medium": "Spa",
                # The marker the rendered form carries. Its presence is what
                # says "this form asked about push", which is the only way an
                # empty value can mean "cleared" — FastAPI gives None for an
                # absent AND an empty `str | None`, so the parameter itself
                # cannot carry that distinction.
                "channel_sections_present": "push",
                "push_title": "", "push_body": "",
                "csrf_token": auth.csrf_token_for(token)})
            stored = db.get(ContentRecordDB, record.id)
            db.refresh(stored)
            assert "push_title" not in stored.content, (
                "an author cleared the push title and it survived"
            )
        finally:
            db.query(ContentRecordDB).filter(ContentRecordDB.id == record.id).delete()
            db.commit()
            self._cleanup(db, user)


class TestTheContentOverviewShowsEveryChannelsCopy:
    """Reported by the user 2026-09-17: push copy could be written and then
    became invisible — the read view listed only the email fields, so the only
    way to see what a record said on push was to open the editor.

    Tabs rather than one stacked list, deliberately. ADR-160 point 3 keeps the
    two sets **separately authored**, and stacking them invites reading the
    email text as a fallback for a missing push title — which is the derivation
    that ADR rejects, arriving through the UI instead of through the renderer.
    """

    def _admin(self, db):
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

    def _cleanup(self, db, user, record_ids=()):
        from app.content.db_models import ContentRecordDB

        if record_ids:
            db.query(ContentRecordDB).filter(
                ContentRecordDB.id.in_(record_ids)).delete(synchronize_session=False)
        db.query(SessionDB).filter(SessionDB.user_id == user.id).delete()
        db.query(RoleAssignmentDB).filter(RoleAssignmentDB.user_id == user.id).delete()
        db.query(AuditEventDB).filter(AuditEventDB.actor_id == user.id).delete(
            synchronize_session=False)
        db.query(UserDB).filter(UserDB.id == user.id).delete()
        db.commit()

    def test_stored_push_copy_is_visible_without_opening_the_editor(
        self, db, monkeypatch
    ):
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        from app.content.service import create_content

        client, token, user = self._admin(db)
        record = create_content(
            db, title=_name("readable"), brand_id=auth.ensure_default_brand(db).id,
            content={"headline_medium": "Praia da Marinha", "body_medium": "Go early.",
                     "push_title": "Beat the crowds", "push_body": "Arrive before 09:00."})
        try:
            page = client.get(f"/ui/content/{record.id}")
            assert page.status_code == 200

            # **Scoped to the read pane, and that is the whole test.** Asserting
            # the string appears anywhere on the page passes even with the read
            # tabs deleted, because the edit form carries the same value in an
            # `<input value="...">` — which is precisely the state the user
            # reported: stored, and visible only to someone who opens the
            # editor. A mutation proved the unscoped version useless.
            assert 'id="read-push"' in page.text, "the push read pane is missing"
            read_pane = page.text.split('id="read-push"')[1].split("</div>")[0]
            assert "Beat the crowds" in read_pane, (
                "the record's push copy is stored but does not appear in the "
                "overview — it can only be seen by opening the edit form"
            )
            assert 'data-bs-target="#read-push"' in page.text
        finally:
            self._cleanup(db, user, [record.id])

    def test_a_record_with_no_push_copy_says_so_rather_than_showing_the_email_text(
        self, db, monkeypatch
    ):
        """The failure mode worth preventing: a blank push tab that quietly
        borrows the headline would be the derivation ADR-160 point 3 forbids,
        implemented in a template."""
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        from app.content.service import create_content

        client, token, user = self._admin(db)
        record = create_content(
            db, title=_name("emailonly"), brand_id=auth.ensure_default_brand(db).id,
            content={"headline_medium": "A headline for an inbox",
                     "body_medium": "Long-form body copy."})
        try:
            page = client.get(f"/ui/content/{record.id}")
            read_pane = page.text.split('id="read-push"')[1].split("</div>")[0]
            push_tab = read_pane
            assert "A headline for an inbox" not in push_tab, (
                "the push tab showed the email headline — a notification is not "
                "a shortened email, and presenting one as the other is exactly "
                "what ADR-160 point 3 refuses"
            )
            # A neutral statement of fact, NOT a readiness verdict. An earlier
            # version said "not push-ready", which asserts a status the manager
            # alone grants by activating the record and freezing a version —
            # and which is undefined per-record anyway, since `required` lives
            # on a module's manifest variable rather than on the record.
            assert "Nothing written for this channel yet" in page.text
            assert "ready" not in read_pane.lower(), (
                "a readiness verdict came back — usability is gated by "
                "activation and a frozen version, not by which fields are full"
            )
        finally:
            self._cleanup(db, user, [record.id])

    def test_a_single_channel_deployment_sees_no_tabs_at_all(self, db, monkeypatch):
        """Same promise ADR-150 point 4 makes about the brand switcher: a
        company using one channel never has to think about the switcher."""
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        from app.content.service import create_content

        client, token, user = self._admin(db)
        record = create_content(
            db, title=_name("single"), brand_id=auth.ensure_default_brand(db).id,
            content={"headline_medium": "Just email", "body_medium": "."})
        set_channel_available(db, "push", False)
        try:
            page = client.get(f"/ui/content/{record.id}")
            assert 'data-bs-target="#read-push"' not in page.text
            assert "nav-tabs" not in page.text, (
                "a one-channel deployment was shown a channel switcher"
            )
            assert "Just email" in page.text, "the email copy must still render"
        finally:
            self._cleanup(db, user, [record.id])


class TestNoReadinessVerdictIsClaimed:
    """Corrected 2026-09-17 after the user pushed back on a "ready" badge.

    Three reasons it had to go, and the third is the one that kills the concept
    rather than the wording:

      1. **Inconsistent** — push carried a badge and email did not.
      2. **It asserts a status nobody granted.** Whether a record may be used
         is gated by the manager activating it and freezing a version. "Ready"
         beside an inactive draft is simply false.
      3. **Per-record readiness is undefined.** `required` belongs to a
         MODULE's manifest variable. A record with no `headline_medium` cannot
         fill `single_stack` and fills `cta` perfectly well — so the question
         has no answer until a module is named.

    ADR-161 point 7's catalogue-readiness rider is not contradicted by this: it
    describes a candidate filter for decision slots, where a module is in
    scope. It was turned into a record badge here, which is a different claim.
    """

    def _admin(self, db):
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

    def _cleanup(self, db, user, record_ids=()):
        from app.content.db_models import ContentRecordDB

        if record_ids:
            db.query(ContentRecordDB).filter(
                ContentRecordDB.id.in_(record_ids)).delete(synchronize_session=False)
        db.query(SessionDB).filter(SessionDB.user_id == user.id).delete()
        db.query(RoleAssignmentDB).filter(RoleAssignmentDB.user_id == user.id).delete()
        db.query(AuditEventDB).filter(AuditEventDB.actor_id == user.id).delete(
            synchronize_session=False)
        db.query(UserDB).filter(UserDB.id == user.id).delete()
        db.commit()

    def test_a_fully_filled_record_is_not_called_ready(self, db, monkeypatch):
        """The case that prompted the correction: every push field written, on
        a record the manager has not published a version of."""
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        from app.content.db_models import ContentVersionDB
        from app.content.service import create_content

        client, token, user = self._admin(db)
        record = create_content(
            db, title=_name("complete"), brand_id=auth.ensure_default_brand(db).id,
            content={"headline_medium": "Full", "body_medium": "Everything filled.",
                     "push_title": "Full", "push_body": "Everything filled.",
                     "push_image_url": "https://x.example/i.jpg",
                     "push_link": "https://x.example"})
        try:
            assert db.query(ContentVersionDB).filter(
                ContentVersionDB.content_record_id == record.id).count() == 0, (
                "fixture assumption: this record has no frozen version, so any "
                "claim that it is usable is false"
            )
            page = client.get(f"/ui/content/{record.id}")
            assert page.status_code == 200
            assert ">ready<" not in page.text, (
                "a record with no frozen version was labelled ready — usability "
                "is granted by activating and publishing, not by filling fields"
            )
            assert "-ready" not in page.text
        finally:
            self._cleanup(db, user, [record.id])

    def test_a_partially_filled_record_is_not_called_unready_either(
        self, db, monkeypatch
    ):
        """The user's layout point: half the email fields is perfectly workable
        for a module that does not declare the rest, so calling the record
        unready would be wrong in the other direction."""
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        from app.content.service import create_content

        client, token, user = self._admin(db)
        record = create_content(
            db, title=_name("partial"), brand_id=auth.ensure_default_brand(db).id,
            content={"headline_medium": "Half", "push_title": "Half"})
        try:
            page = client.get(f"/ui/content/{record.id}")
            assert "-ready" not in page.text, (
                "a record missing one optional field was declared unready, but "
                "which fields matter is the module's business, not the record's"
            )
        finally:
            self._cleanup(db, user, [record.id])


class TestAPushSendGoesOutAsAPush:
    """Step 5. Until this, `delivery_executions.channel` defaulted to 'email'
    for every send ever made, and `delivery/service.py` carried a comment
    saying so: channel and purpose "fall to their column defaults … When a
    variant carries a channel (ADR-160 …)". It does now.

    The test that matters most is the one asserting a recipient with no device
    token is **excluded rather than emailed**. Three separate things had to be
    channel-aware for that to come out right, and all three defaulted to email.
    """

    def _push_campaign(self, db, brand):
        from app.content.service import create_content, create_content_version

        record = create_content(
            db, title=_name("alert"), brand_id=brand.id,
            content={"push_title": "Fresh snow", "push_body": "2m base at Arosa."})
        create_content_version(db, content_record_id=record.id, created_by="test")
        campaign = create_campaign(
            db, name=_name("campaign"), brand_id=brand.id, channel="email")
        variant = create_variant_for_campaign(
            db, campaign_id=campaign.id, name=_name("push"), channel="push")
        create_module_for_variant(
            db, variant_id=variant.id, module_type="notification",
            content_record_id=record.id)
        return campaign, variant

    def _recipients(self, db, brand, with_push_token: bool):
        from app.recipients.consent import record_consent
        from app.recipients.db_models import AddressabilityDB, RecipientDB

        recipient = RecipientDB(external_id=_name("r"), status="active")
        db.add(recipient); db.commit(); db.refresh(recipient)
        if with_push_token:
            db.add(AddressabilityDB(
                recipient_id=recipient.id, channel="push",
                value={"token": f"apns-{uuid.uuid4().hex[:8]}", "platform": "apns"}))
        else:
            db.add(AddressabilityDB(
                recipient_id=recipient.id, channel="email",
                value={"email": f"{_name('a')}@example.invalid"}))
        db.commit()
        record_consent(db, recipient.id, "opted_in", brand.id, channel="push", source="test")
        record_consent(db, recipient.id, "opted_in", brand.id, channel="email", source="test")
        return recipient

    def _plan(self, db, brand, variant, recipients):
        from app.audience.service import add_member, create_group
        from app.delivery.service import prepare_send_from_audience
        from app.snapshots.service import create_snapshot_for_variant

        group = create_group(db, name=_name("group"), brand_id=brand.id)
        for recipient in recipients:
            add_member(db, group.id, recipient.id)
        snapshot = create_snapshot_for_variant(db, variant_id=variant.id)
        return prepare_send_from_audience(
            db, snapshot_id=snapshot.id, name=_name("send"),
            audience_group_id=group.id, provider="mock")

    def test_executions_carry_the_variants_channel_not_the_default(self, db):
        from app.delivery.db_models import DeliveryExecutionDB

        brand = auth.ensure_default_brand(db)
        _campaign, variant = self._push_campaign(db, brand)
        recipient = self._recipients(db, brand, with_push_token=True)
        send = self._plan(db, brand, variant, [recipient])

        channels = {
            e.channel for e in db.query(DeliveryExecutionDB).filter(
                DeliveryExecutionDB.send_instance_id == send.id).all()
        }
        assert channels == {"push"}, (
            f"executions were planned as {channels} — the column defaulted to "
            "email for every send ever made, and an inbound bounce weeks later "
            "has only this row to say which channel it was about"
        )

    def test_a_push_goes_to_the_device_token_with_its_fields(self, db):
        from app.delivery.service import send_send_instance

        brand = auth.ensure_default_brand(db)
        _campaign, variant = self._push_campaign(db, brand)
        recipient = self._recipients(db, brand, with_push_token=True)
        send = self._plan(db, brand, variant, [recipient])

        captured = {}
        from app.delivery.providers import mock as mock_module

        original = mock_module.MockProvider.send

        def capture(self, address, artifact):
            captured["address"] = address
            captured["artifact"] = artifact
            return original(self, address, artifact)

        mock_module.MockProvider.send = capture
        try:
            send_send_instance(db, send.id)
        finally:
            mock_module.MockProvider.send = original

        assert captured["address"].startswith("apns-"), (
            f"the provider was handed {captured['address']!r} — an email "
            "address was resolved for a push send, which is what the "
            "addressability stage did for every channel before this"
        )
        assert captured["artifact"].body is None
        assert captured["artifact"].fields["push_title"] == "Fresh snow"

    def test_a_recipient_with_no_device_token_is_excluded_not_emailed(self, db):
        """**The one to keep.** Three things defaulted to email — the audience
        consent floor, the addressability stage, and the address's JSON key —
        and each one alone would have produced a "successful" push delivered to
        somebody's inbox."""
        from app.delivery.db_models import DeliveryExecutionDB
        from app.delivery.service import send_send_instance

        brand = auth.ensure_default_brand(db)
        _campaign, variant = self._push_campaign(db, brand)
        reachable = self._recipients(db, brand, with_push_token=True)
        unreachable = self._recipients(db, brand, with_push_token=False)
        send = self._plan(db, brand, variant, [reachable, unreachable])
        send_send_instance(db, send.id)
        db.expire_all()

        rows = {
            e.recipient_id: e for e in db.query(DeliveryExecutionDB).filter(
                DeliveryExecutionDB.send_instance_id == send.id).all()
        }
        assert rows[reachable.id].status == "sent"
        assert rows[unreachable.id].status == "excluded", (
            "a recipient with only an email address was sent a push — the "
            "addressability stage resolved their email and called it a push "
            "address, which the exclusion reason would then have denied"
        )
        assert "push" in rows[unreachable.id].exclusion_reason

    def test_the_audience_is_gated_on_the_sends_own_channel(self, db):
        """A push send planned against email consent asks the wrong question
        twice: it admits people who accepted email and never accepted
        notifications, and refuses the reverse. Before this it made a push send
        unplannable — the planner reported "0 consenting recipients"."""
        from app.recipients.consent import record_consent
        from app.recipients.db_models import AddressabilityDB, RecipientDB

        brand = auth.ensure_default_brand(db)
        _campaign, variant = self._push_campaign(db, brand)

        # Consented to push, never to email — invisible to an email-gated plan.
        recipient = RecipientDB(external_id=_name("pushonly"), status="active")
        db.add(recipient); db.commit(); db.refresh(recipient)
        db.add(AddressabilityDB(
            recipient_id=recipient.id, channel="push",
            value={"token": f"apns-{uuid.uuid4().hex[:8]}", "platform": "apns"}))
        db.commit()
        record_consent(db, recipient.id, "opted_in", brand.id, channel="push", source="test")

        send = self._plan(db, brand, variant, [recipient])
        assert send.id is not None, (
            "a recipient who consented to push was not found by a push send's "
            "audience, because the consent floor asked about email"
        )

    def test_an_email_provider_refuses_a_push_channel(self, db):
        """ADR-101: capabilities are explicit. Handing a notification to Resend
        would fail at the vendor with a message about a malformed request,
        which is a poor way to learn about a configuration mistake."""
        from app.delivery.providers.factory import get_provider

        assert get_provider("resend", channel="email") is not None
        with pytest.raises(ValueError, match="cannot deliver on the 'push' channel"):
            get_provider("resend", channel="push")
        # The mock carries everything, or push would be untestable without an
        # APNs certificate — which nobody has on a laptop.
        assert get_provider("mock", channel="push") is not None


class TestADeviceContactCanBeSyncedIn:
    """[[ADR-167]], accepted 2026-09-18: a push audience arrives as ordinary
    contacts minted by the source system, so the sync path has to admit a
    contact whose only contact point is a device token. It could not.

    Three things were email-shaped and one of them was a compliance defect
    rather than an inconvenience — `create_recipient` recorded its consent
    event with no channel, so a synced contact was granted EMAIL consent
    whatever it had actually agreed to. Invisible while email was the only
    channel, because the default was always right.
    """

    def _client(self):
        from fastapi.testclient import TestClient

        from main import app

        return TestClient(app, follow_redirects=False, raise_server_exceptions=False)

    def test_a_device_contact_is_created_with_a_push_address(self, db):
        from app.recipients.db_models import AddressabilityDB, RecipientDB

        brand = auth.ensure_default_brand(db)
        external_id = _name("device")
        token = f"apns-{uuid.uuid4().hex[:10]}"

        response = self._client().post("/recipients/", json={
            "brand_id": brand.id, "external_id": external_id,
            "address": token, "channel": "push", "consent_status": "opted_in",
        })
        assert response.status_code == 200, response.text

        recipient = db.query(RecipientDB).filter(
            RecipientDB.external_id == external_id).first()
        assert recipient is not None, (
            "a contact with a device token and no inbox could not be created — "
            "`email` was a required positional on the only production path"
        )
        rows = db.query(AddressabilityDB).filter(
            AddressabilityDB.recipient_id == recipient.id).all()
        assert [r.channel for r in rows] == ["push"]
        assert rows[0].value == {"token": token}, (
            f"the address row holds {rows[0].value} — a push address is "
            '{"token": ...}, and writing {"email": ...} would make the '
            "recipient unaddressable on the only channel they have"
        )

    def test_a_device_contact_is_not_granted_email_consent(self, db):
        """**The one that matters.** A grant nobody gave is a compliance
        defect, not a shortcut — and it would have been written on every
        device contact ever synced."""
        from app.recipients.consent import latest_consent_status
        from app.recipients.db_models import RecipientDB

        brand = auth.ensure_default_brand(db)
        external_id = _name("device")
        self._client().post("/recipients/", json={
            "brand_id": brand.id, "external_id": external_id,
            "address": f"apns-{uuid.uuid4().hex[:10]}", "channel": "push",
            "consent_status": "opted_in",
        })
        recipient = db.query(RecipientDB).filter(
            RecipientDB.external_id == external_id).first()

        assert latest_consent_status(
            db, recipient.id, brand.id, channel="push") == "opted_in"
        assert latest_consent_status(
            db, recipient.id, brand.id, channel="email") is None, (
            "a contact that agreed to notifications was recorded as having "
            "granted email consent — the consent event was written with no "
            "channel, so it landed on the default"
        )

    def test_an_email_contact_still_syncs_unchanged(self, db):
        """Without this, the tests above could pass by breaking the path that
        every existing recipient came through."""
        from app.recipients.consent import latest_consent_status
        from app.recipients.db_models import AddressabilityDB, RecipientDB

        brand = auth.ensure_default_brand(db)
        external_id = _name("person")
        address = f"{_name('a')}@example.invalid"
        response = self._client().post("/recipients/", json={
            "brand_id": brand.id, "external_id": external_id,
            "address": address, "consent_status": "opted_in",
        })
        assert response.status_code == 200, response.text

        recipient = db.query(RecipientDB).filter(
            RecipientDB.external_id == external_id).first()
        row = db.query(AddressabilityDB).filter(
            AddressabilityDB.recipient_id == recipient.id).first()
        assert row.channel == "email" and row.value == {"email": address}, (
            "the channel default stopped being email, which every existing "
            "caller relies on"
        )
        assert latest_consent_status(db, recipient.id, brand.id) == "opted_in"

    def test_a_person_with_an_inbox_and_a_device_is_two_calls_one_recipient(self, db):
        """The design call this records: one address per call, upserted on
        external_id. A list would be more general and would need rules for
        partial failure that nothing is asking for."""
        from app.recipients.consent import latest_consent_status
        from app.recipients.db_models import AddressabilityDB, RecipientDB

        brand = auth.ensure_default_brand(db)
        external_id = _name("both")
        client = self._client()
        client.post("/recipients/", json={
            "brand_id": brand.id, "external_id": external_id,
            "address": f"{_name('a')}@example.invalid", "consent_status": "opted_in"})
        client.post("/recipients/", json={
            "brand_id": brand.id, "external_id": external_id,
            "address": f"apns-{uuid.uuid4().hex[:10]}", "channel": "push",
            "consent_status": "opted_in"})

        matches = db.query(RecipientDB).filter(
            RecipientDB.external_id == external_id).all()
        assert len(matches) == 1, "the second call created a second recipient"
        channels = sorted(r.channel for r in db.query(AddressabilityDB).filter(
            AddressabilityDB.recipient_id == matches[0].id).all())
        assert channels == ["email", "push"]
        assert latest_consent_status(db, matches[0].id, brand.id, channel="email") == "opted_in"
        assert latest_consent_status(db, matches[0].id, brand.id, channel="push") == "opted_in"


class TestTheRecipientPageShowsEveryChannelsConsent:
    """Asked for by the user 2026-09-18, and the mirror of the sync-path fix:
    writes went per-channel with ADR-163's addendum, reads did not. The page
    showed one badge — the (email, marketing) cell — presented as though it
    were the whole answer.

    The test worth reading is `test_a_channel_never_asked_about_is_not_shown_as
    _opted_out`. Consent is fail-closed on absence, so "never asked" and
    "refused" behave identically at the send gate — which is exactly why an
    operator has to be able to tell them apart, since only one of them is
    fixable by asking.
    """

    def _admin_client(self, db):
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
        return client, user

    def _cleanup(self, db, user, recipient=None):
        from app.recipients.db_models import AddressabilityDB, ConsentEventDB, RecipientDB

        if recipient is not None:
            db.query(ConsentEventDB).filter(
                ConsentEventDB.recipient_id == recipient.id).delete(synchronize_session=False)
            db.query(AddressabilityDB).filter(
                AddressabilityDB.recipient_id == recipient.id).delete(synchronize_session=False)
            db.query(RecipientDB).filter(RecipientDB.id == recipient.id).delete()
        db.query(SessionDB).filter(SessionDB.user_id == user.id).delete()
        db.query(RoleAssignmentDB).filter(RoleAssignmentDB.user_id == user.id).delete()
        db.query(AuditEventDB).filter(AuditEventDB.actor_id == user.id).delete(
            synchronize_session=False)
        db.query(UserDB).filter(UserDB.id == user.id).delete()
        db.commit()

    def _recipient(self, db):
        from app.recipients.db_models import RecipientDB

        recipient = RecipientDB(external_id=_name("r"), status="active")
        db.add(recipient); db.commit(); db.refresh(recipient)
        return recipient

    def test_each_channels_consent_is_shown_separately(self, db, monkeypatch):
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        from app.recipients.consent import record_consent

        brand = auth.ensure_default_brand(db)
        recipient = self._recipient(db)
        record_consent(db, recipient.id, "opted_in", brand.id, channel="email", source="crm")
        record_consent(db, recipient.id, "opted_out", brand.id, channel="push", source="form")
        client, user = self._admin_client(db)
        try:
            page = client.get(f"/ui/recipients/{recipient.id}")
            assert page.status_code == 200
            rows = page.text.split("<tbody>")[1].split("</tbody>")[0]
            assert "email" in rows and "push" in rows
            assert "opted-in" in rows and "opted-out" in rows, (
                "one badge cannot express a recipient who accepted email and "
                "refused push, which is the ordinary case once a second "
                "channel exists"
            )
        finally:
            self._cleanup(db, user, recipient)

    def test_a_channel_never_asked_about_is_not_shown_as_opted_out(
        self, db, monkeypatch
    ):
        """Both are non-consenting at the gate. Only one of them is a question
        nobody has put to the person yet, and conflating them would tell an
        operator a refusal happened that never did."""
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        from app.recipients.consent import record_consent

        brand = auth.ensure_default_brand(db)
        recipient = self._recipient(db)
        record_consent(db, recipient.id, "opted_in", brand.id, channel="email", source="crm")
        client, user = self._admin_client(db)
        try:
            page = client.get(f"/ui/recipients/{recipient.id}")
            assert "never asked" in page.text, (
                "a channel with no consent event was not distinguished from a "
                "refusal — the absence of a decision is not a decision"
            )
        finally:
            self._cleanup(db, user, recipient)

    def test_the_append_only_history_is_visible(self, db, monkeypatch):
        """"Opted out" does not say whether they refused at signup or
        complained after a send. The log does, and it is the record — a status
        is only ever its newest row."""
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        from app.recipients.consent import record_consent

        brand = auth.ensure_default_brand(db)
        recipient = self._recipient(db)
        record_consent(db, recipient.id, "opted_in", brand.id,
                       channel="email", source="form", note="signup form")
        record_consent(db, recipient.id, "opted_out", brand.id,
                       channel="email", source="provider", note="complaint reported")
        client, user = self._admin_client(db)
        try:
            page = client.get(f"/ui/recipients/{recipient.id}")
            assert "complaint reported" in page.text and "signup form" in page.text, (
                "the earlier event vanished — showing only the latest turns an "
                "append-only record into a mutable field"
            )
        finally:
            self._cleanup(db, user, recipient)

    def test_the_grid_is_scoped_to_the_working_brand(self, db, monkeypatch):
        """Consent is to a sender (ADR-163 addendum). A grant to brand B must
        not read as a grant on brand A's page."""
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        from app.recipients.consent import consent_grid, record_consent

        from app.auth.db_models import BrandDB

        brand = auth.ensure_default_brand(db)
        other = BrandDB(key=_name("brand"), name="Other sender")
        db.add(other); db.commit(); db.refresh(other)
        recipient = self._recipient(db)
        record_consent(db, recipient.id, "opted_in", other.id, channel="email", source="crm")
        try:
            grid = consent_grid(db, recipient.id, brand.id, ["email", "push"])
            assert all(cell["status"] is None for cell in grid), (
                "a grant given to another brand showed up on this brand's grid"
            )
            assert any(c["consenting"] for c in consent_grid(
                db, recipient.id, other.id, ["email"]))
        finally:
            from app.recipients.db_models import ConsentEventDB, RecipientDB

            db.query(ConsentEventDB).filter(
                ConsentEventDB.recipient_id == recipient.id).delete(synchronize_session=False)
            db.query(RecipientDB).filter(RecipientDB.id == recipient.id).delete()
            db.query(BrandDB).filter(BrandDB.id == other.id).delete()
            db.commit()
