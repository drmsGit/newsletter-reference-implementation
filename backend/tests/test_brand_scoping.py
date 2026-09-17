"""Brand scoping — ADR-150 point 2, accepted 2026-09-14.

Multi-brand is the ordinary case: the first pilot customer runs around ten
brands and adds several a year. Until this work, `role_assignments.brand_id`
was the only brand foreign key in the database, so a grant saying "Manager on
brand 2" had nothing to be checked against.

**The most important test here is the one-brand one.** ADR-150 point 4 promises
that a company using brands as a logo and a palette "never has to think about
the switcher". That promise is the reason the scope was designed in from the
start rather than retrofitted, so it is the claim most worth pinning down — if
it quietly stops being true, the design's own justification goes with it.

Runs against the shared dev database like the rest of the suite, and removes
everything it creates.
"""
import uuid

import pytest

from app.audience import service as audience_service
from app.audience.db_models import AudienceGroupDB
from app.audit.db_models import AuditEventDB
from app.auth import service as auth
from app.auth.db_models import BrandDB, RoleAssignmentDB, RoleDB, SessionDB, UserDB
from app.auth.permissions import MANAGER
from app.campaigns.db_models import CampaignDB, VariantDB
from app.delivery.db_models import SendInstanceDB
from app.campaigns.service import create_campaign, list_campaigns
from app.content.db_models import ContentRecordDB
from app.content.service import create_content, list_content_records
from app.database import SessionLocal


@pytest.fixture
def db():
    session = SessionLocal()
    auth.bootstrap(session)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def default_brand(db):
    return auth.ensure_default_brand(db)


@pytest.fixture
def temp_brand(db):
    """A second brand, so "multi-brand" is an actual state and not a theory."""
    created: list[int] = []

    def make(label: str = "second") -> BrandDB:
        brand = BrandDB(key=f"{label}-{uuid.uuid4().hex[:8]}", name=f"Test {label}")
        db.add(brand)
        db.commit()
        db.refresh(brand)
        created.append(brand.id)
        return brand

    yield make

    # Every table that carries a brand FK, or the delete fails and the brand
    # survives the run. That is not hypothetical: a MUTATION run left two
    # brands behind in the shared dev database, because disabling the guard
    # under test let a POST that should have been refused create a campaign —
    # and campaigns were missing from this list. Mutation testing deliberately
    # breaks the code that refuses things, so cleanup here has to assume the
    # test did the opposite of what it asserts.
    for brand_id in created:
        campaign_ids = [
            c.id for c in db.query(CampaignDB).filter(CampaignDB.brand_id == brand_id).all()
        ]
        if campaign_ids:
            db.query(VariantDB).filter(VariantDB.campaign_id.in_(campaign_ids)).delete(
                synchronize_session=False
            )
            db.query(CampaignDB).filter(CampaignDB.id.in_(campaign_ids)).delete(
                synchronize_session=False
            )
        db.query(SendInstanceDB).filter(SendInstanceDB.brand_id == brand_id).delete()
        db.query(ContentRecordDB).filter(ContentRecordDB.brand_id == brand_id).delete()
        db.query(AudienceGroupDB).filter(AudienceGroupDB.brand_id == brand_id).delete()
        db.query(RoleAssignmentDB).filter(RoleAssignmentDB.brand_id == brand_id).delete()
        db.query(SessionDB).filter(SessionDB.brand_id == brand_id).update({"brand_id": None})
        db.query(BrandDB).filter(BrandDB.id == brand_id).delete()
    db.commit()


@pytest.fixture
def user_on(db):
    """A throwaway user granted Manager on exactly the brands named."""
    created: list[int] = []

    def make(*brands: BrandDB) -> UserDB:
        user = UserDB(email=f"brand-{uuid.uuid4().hex[:10]}@example.invalid", is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        created.append(user.id)

        role = db.query(RoleDB).filter(RoleDB.key == MANAGER).first()
        for brand in brands:
            db.add(RoleAssignmentDB(user_id=user.id, role_id=role.id, brand_id=brand.id))
        db.commit()
        return user

    yield make

    for user_id in created:
        db.query(SessionDB).filter(SessionDB.user_id == user_id).delete()
        db.query(RoleAssignmentDB).filter(RoleAssignmentDB.user_id == user_id).delete()
        # No FK from audit_events to users, deliberately (ADR-153 point 5), so
        # nothing cascades and a fixture that forgets this leaks silently.
        db.query(AuditEventDB).filter(
            (AuditEventDB.actor_id == user_id)
            | ((AuditEventDB.subject_type == "user") & (AuditEventDB.subject_id == user_id))
        ).delete(synchronize_session=False)
        db.query(UserDB).filter(UserDB.id == user_id).delete()
    db.commit()


@pytest.fixture
def temp_content(db):
    created: list[int] = []

    def make(brand: BrandDB) -> int:
        record = create_content(
            db,
            title=f"brandtest-{uuid.uuid4().hex[:10]}",
            content={"headline_medium": "x"},
            brand_id=brand.id,
        )
        created.append(record.id)
        return record.id

    yield make

    for record_id in created:
        db.query(ContentRecordDB).filter(ContentRecordDB.id == record_id).delete()
    db.commit()


class TestTheSingleBrandCompanyPaysNothing:
    """ADR-150 point 4 — the claim the whole design rests on.

    "One default brand always exists, so such a company never has to think
    about the switcher and never sees a second context." If that stops being
    true, brand scoping stops being a scope and becomes a feature every adopter
    is taxed for whether or not they use it.
    """

    def test_a_user_on_one_brand_gets_no_switcher(self, db, default_brand, user_on):
        user = user_on(default_brand)
        token = auth.create_session(db, user)

        summary = auth.current_brand_summary(db, token)

        assert summary is not None, "a user with a grant has no working brand at all"
        assert summary["id"] == default_brand.id
        assert summary["switchable"] is False, (
            "the navbar would render a brand switcher for a company with one "
            "brand — ADR-150 point 4 promises it never has to think about one"
        )

    def test_the_navbar_really_omits_it(self, db, default_brand, user_on, monkeypatch):
        """Over HTTP, because `switchable` being False proves nothing on its own.

        The template could ignore the flag and the unit test above would still
        pass — that is the shape of gap that let a CSRF guard be disabled
        without failing anything.
        """
        from fastapi.testclient import TestClient

        from main import app

        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        user = user_on(default_brand)
        token = auth.create_session(db, user)

        client = TestClient(app, follow_redirects=False)
        client.cookies.set(auth.SESSION_COOKIE, token)
        page = client.get("/ui/content")

        assert page.status_code == 200, f"expected the content page, got {page.status_code}"
        assert 'name="brand_id"' not in page.text, (
            "a brand switcher rendered for a single-brand company"
        )

    def test_creating_needs_no_brand_from_the_caller(self, db, default_brand, temp_content):
        """The working context supplies it, so nothing in the UI asks."""
        record_id = temp_content(default_brand)
        stored = db.query(ContentRecordDB).filter(ContentRecordDB.id == record_id).first()
        assert stored.brand_id == default_brand.id


class TestTheSwitcherAppearsOnlyWhenItIsUseful:

    def test_two_grants_make_it_switchable(self, db, default_brand, temp_brand, user_on):
        user = user_on(default_brand, temp_brand())
        token = auth.create_session(db, user)

        assert auth.current_brand_summary(db, token)["switchable"] is True

    def test_switching_to_a_granted_brand_sticks(self, db, default_brand, temp_brand, user_on):
        second = temp_brand()
        user = user_on(default_brand, second)
        token = auth.create_session(db, user)

        assert auth.set_session_brand(db, token, second.id) is not None
        assert auth.current_brand_summary(db, token)["id"] == second.id

    def test_switching_to_an_ungranted_brand_is_refused(
        self, db, default_brand, temp_brand, user_on
    ):
        ungranted = temp_brand()
        user = user_on(default_brand)
        token = auth.create_session(db, user)

        assert auth.set_session_brand(db, token, ungranted.id) is None
        assert auth.current_brand_summary(db, token)["id"] == default_brand.id, (
            "a refused switch still moved the working brand"
        )

    def test_a_revoked_grant_stops_taking_effect_immediately(
        self, db, default_brand, temp_brand, user_on
    ):
        """The stored brand is a cache of a choice, not an authority.

        ADR-151 point 3 makes session revocation immediate; a grant revoked
        after the user picked that brand has to bite just as fast, or the
        session row becomes a way to keep access somebody took away.
        """
        second = temp_brand()
        user = user_on(default_brand, second)
        token = auth.create_session(db, user)
        auth.set_session_brand(db, token, second.id)
        assert auth.current_brand_summary(db, token)["id"] == second.id

        db.query(RoleAssignmentDB).filter(
            RoleAssignmentDB.user_id == user.id, RoleAssignmentDB.brand_id == second.id
        ).delete()
        db.commit()

        assert auth.current_brand_summary(db, token)["id"] == default_brand.id, (
            "the session kept working in a brand whose grant was revoked"
        )


class TestListsAreScopedToTheWorkingBrand:

    def test_content_is_invisible_from_another_brand(
        self, db, default_brand, temp_brand, temp_content
    ):
        other = temp_brand()
        record_id = temp_content(default_brand)

        here = [r.id for r in list_content_records(db, brand_id=default_brand.id)]
        there = [r.id for r in list_content_records(db, brand_id=other.id)]

        assert record_id in here
        assert record_id not in there, (
            "a content record was visible from a brand it does not belong to — "
            "ADR-150 point 2 makes the switcher a hard boundary"
        )

    def test_campaigns_are_scoped(self, db, default_brand, temp_brand):
        other = temp_brand()
        campaign = create_campaign(db, name=f"brandtest-{uuid.uuid4().hex[:8]}",
                                   brand_id=default_brand.id)
        try:
            assert campaign.id in [c.id for c in list_campaigns(db, brand_id=default_brand.id)]
            assert campaign.id not in [c.id for c in list_campaigns(db, brand_id=other.id)]
        finally:
            # create_campaign also creates an initial variant, so the child
            # goes first or the foreign key refuses the delete.
            db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).delete()
            db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
            db.commit()

    def test_no_brand_means_every_brand_and_is_not_the_default(
        self, db, default_brand, temp_brand, temp_content
    ):
        """`brand_id=None` spans brands on purpose, for counts and migrations.

        Pinned because it is the fail-open direction: if a caller forgets to
        pass a brand they get everything, so the behaviour should at least be
        deliberate and tested rather than incidental.
        """
        other = temp_brand()
        mine = temp_content(default_brand)
        theirs = create_content(db, title=f"brandtest-{uuid.uuid4().hex[:8]}",
                                content={"headline_medium": "x"}, brand_id=other.id)

        everything = [r.id for r in list_content_records(db)]
        assert mine in everything and theirs.id in everything


class TestTwoBrandsMayReuseAName:

    def test_same_audience_name_on_two_brands(self, db, default_brand, temp_brand):
        """The old index was globally unique on lower(name).

        It is why `ux_audience_groups_name_lower` had to be rescoped: two
        brands both wanting a list called "VIPs" is the ordinary case, not a
        collision.
        """
        other = temp_brand()
        name = f"VIPs-{uuid.uuid4().hex[:8]}"

        first = audience_service.create_group(db, name, brand_id=default_brand.id)
        second = audience_service.create_group(db, name, brand_id=other.id)
        try:
            assert first.id != second.id
            assert first.brand_id != second.brand_id
        finally:
            db.query(AudienceGroupDB).filter(
                AudienceGroupDB.id.in_([first.id, second.id])
            ).delete(synchronize_session=False)
            db.commit()

    def test_the_same_name_twice_in_one_brand_is_still_refused(self, db, default_brand):
        name = f"VIPs-{uuid.uuid4().hex[:8]}"
        first = audience_service.create_group(db, name, brand_id=default_brand.id)
        try:
            with pytest.raises(ValueError):
                audience_service.create_group(db, name, brand_id=default_brand.id)
        finally:
            db.query(AudienceGroupDB).filter(AudienceGroupDB.id == first.id).delete()
            db.commit()


class TestBrandsCanActuallyBeAdministered:
    """The gap that made the first cut of this feature unreachable.

    Brand scoping shipped with no way to create a brand: `ensure_default_brand`
    was the only code that ever made one, `assign_role` was called without a
    brand so every grant landed on the default, and no form offered the field.
    The switcher therefore could not appear for anybody, ever — the scope was
    enforced and unadministrable, which is worse than absent because it looks
    finished.
    """

    def test_a_brand_can_be_created_and_renamed(self, db):
        key = f"admin-{uuid.uuid4().hex[:8]}"
        brand = auth.create_brand(db, key=key, name="Created")
        try:
            assert brand is not None and brand.key == key
            assert auth.rename_brand(db, brand.id, "Renamed").name == "Renamed"
            assert db.query(BrandDB).filter(BrandDB.id == brand.id).first().key == key, (
                "renaming moved the key — it is permanent, because deployment "
                "configuration and per-brand asset paths reference it"
            )
        finally:
            db.query(BrandDB).filter(BrandDB.id == brand.id).delete()
            db.commit()

    def test_a_duplicate_key_is_refused(self, db, default_brand):
        assert auth.create_brand(db, key=default_brand.key, name="Impostor") is None

    def test_the_default_brand_cannot_be_deleted(self, db, default_brand):
        error = auth.delete_brand(db, default_brand.id)

        assert error is not None, "the default brand was deletable"
        # Asserting on the specific refusal, not just on "default" appearing:
        # the brand is NAMED "Default", so the generic in-use message
        # ("Default still has 144 content records…") contains that word too,
        # and an earlier version of this test passed with the guard removed.
        assert "cannot be deleted" in error, (
            f"refused for the wrong reason — the in-use check caught it rather "
            f"than the default-brand guard: {error!r}"
        )

    def test_a_brand_in_use_cannot_be_deleted(self, db, temp_brand, temp_content):
        brand = temp_brand()
        temp_content(brand)

        error = auth.delete_brand(db, brand.id)

        assert error is not None, (
            "a brand was deleted out from under its content — every row in "
            "four tables carries a NOT NULL brand, so this either fails at the "
            "foreign key or needs an invented rule for where orphans go"
        )
        assert "content record" in error, f"the refusal did not say why: {error!r}"

    def test_an_empty_brand_can_be_deleted(self, db, temp_brand):
        brand = temp_brand()
        assert auth.delete_brand(db, brand.id) is None

    def test_a_grant_lands_on_the_brand_it_was_given(self, db, default_brand, temp_brand, user_on):
        """The defect in one line: `assign_role(db, user_id, role_id)`.

        Without the brand argument every grant silently went to the default,
        so a second brand could exist and still be unreachable.
        """
        second = temp_brand()
        user = user_on(default_brand)
        role = db.query(RoleDB).filter(RoleDB.key == MANAGER).first()

        # Over HTTP, because the defect was in the ROUTE dropping the argument,
        # not in `assign_role` refusing it. Calling the service directly proves
        # nothing about the thing that was broken — reverting the route passed
        # an earlier version of this test.
        from fastapi.testclient import TestClient

        from main import app

        admin = db.query(UserDB).join(
            RoleAssignmentDB, RoleAssignmentDB.user_id == UserDB.id
        ).join(RoleDB, RoleDB.id == RoleAssignmentDB.role_id).filter(
            RoleDB.key == "admin", UserDB.is_active.is_(True)
        ).first()
        if admin is None:
            pytest.skip("no active admin in this database to act as")

        admin_token = auth.create_session(db, admin)
        client = TestClient(app, follow_redirects=False)
        client.cookies.set(auth.SESSION_COOKIE, admin_token)

        response = client.post(
            f"/ui/users/{user.id}/roles",
            data={
                "role_id": role.id,
                "brand_id": second.id,
                "csrf_token": auth.csrf_token_for(admin_token),
            },
        )
        db.expire_all()
        assert response.status_code == 303, f"the form was refused: {response.status_code}"

        brands = {b.id for b in auth.brands_for_user(db, user)}
        assert second.id in brands, (
            "the grant landed on the default brand instead of the one the form "
            "named — which is what made a second brand unreachable"
        )
        assert auth.current_brand_summary(db, auth.create_session(db, user))["switchable"] is True
    def test_the_users_page_actually_renders_the_brands_panel(self, db, monkeypatch):
        """The whole visible half of the fix, asserted over HTTP.

        Everything else in this class exercises the service layer, and the
        original defect was not there — it was that no page offered any of it.
        A panel that stops rendering would leave brand creation unreachable
        again while every other test here still passed.
        """
        from fastapi.testclient import TestClient

        from main import app

        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        admin = db.query(UserDB).join(
            RoleAssignmentDB, RoleAssignmentDB.user_id == UserDB.id
        ).join(RoleDB, RoleDB.id == RoleAssignmentDB.role_id).filter(
            RoleDB.key == "admin", UserDB.is_active.is_(True)
        ).first()
        if admin is None:
            pytest.skip("no active admin in this database to act as")

        token = auth.create_session(db, admin)
        client = TestClient(app, follow_redirects=False)
        client.cookies.set(auth.SESSION_COOKIE, token)

        page = client.get("/ui/users")

        assert page.status_code == 200, f"users page returned {page.status_code}"
        assert 'action="/ui/brands"' in page.text, (
            "the users page offers no way to create a brand — which is how "
            "brand scoping shipped enforced and unadministrable"
        )
        for brand in auth.list_brands(db):
            assert brand.name in page.text, f"brand {brand.name!r} is not listed"


class TestTheAccessListResolvesOverlappingRoles:
    """Several roles on one brand stay legal — it is how customised roles
    combine — but the effective access must be visible rather than inferred.

    Permissions are grants with no DENY, so two roles on one brand produce the
    union. An access list showing "Manager on Default" and "Admin on Default"
    as two lines leaves a reader to work that out in their head, and the
    resulting set is one nobody chose explicitly.
    """

    def test_a_single_role_per_brand_shows_nothing_extra(self, db, default_brand, user_on):
        """No noise in the ordinary case, which is almost every case."""
        user = user_on(default_brand)
        row = next(r for r in auth.access_list(db) if r["user"].id == user.id)
        assert row["combined"] == [], (
            "the effective-permissions line rendered for a user with one role "
            "on one brand, where there is nothing to resolve"
        )

    def test_two_roles_on_one_brand_resolve_to_their_union(self, db, default_brand, user_on):
        user = user_on(default_brand)  # Manager
        admin_role = db.query(RoleDB).filter(RoleDB.key == "admin").first()
        auth.assign_role(db, user.id, admin_role.id, brand_id=default_brand.id)

        row = next(r for r in auth.access_list(db) if r["user"].id == user.id)

        assert len(row["combined"]) == 1, (
            f"expected one resolved brand, got {row['combined']}"
        )
        resolved = row["combined"][0]
        assert resolved["brand"] == default_brand.name
        # users.manage comes from Admin and not from Manager, so its presence
        # proves the union was actually computed rather than one role echoed.
        assert "users.manage" in resolved["permissions"]
        assert "campaigns.manage" in resolved["permissions"]

    def test_roles_on_different_brands_are_not_merged(
        self, db, default_brand, temp_brand, user_on
    ):
        """ADR-150 point 6 — Manager on one, Viewer on another, is the design.

        The union is per brand. Merging across brands would be the bug this
        display is meant to expose, not commit.
        """
        second = temp_brand()
        user = user_on(default_brand, second)

        row = next(r for r in auth.access_list(db) if r["user"].id == user.id)

        assert row["combined"] == [], (
            "one role on each of two brands was reported as an overlap — the "
            "union is per brand, not across them"
        )

    def test_the_union_is_scoped_to_its_own_brand(
        self, db, default_brand, temp_brand, user_on
    ):
        """The union must not leak permissions in from another brand.

        Written after a mutation exposed the gap: the earlier test gave the
        user roles on one brand only, so "every brand" and "this brand"
        returned the same set and dropping the brand argument entirely changed
        nothing. Here Admin sits on a DIFFERENT brand, so `users.manage` can
        only appear in the resolved set if the scoping was lost.
        """
        second = temp_brand()
        user = user_on(default_brand)              # Manager on default
        viewer = db.query(RoleDB).filter(RoleDB.key == "viewer").first()
        admin = db.query(RoleDB).filter(RoleDB.key == "admin").first()
        auth.assign_role(db, user.id, viewer.id, brand_id=default_brand.id)
        auth.assign_role(db, user.id, admin.id, brand_id=second.id)

        row = next(r for r in auth.access_list(db) if r["user"].id == user.id)
        resolved = next(c for c in row["combined"] if c["brand"] == default_brand.name)

        assert "campaigns.manage" in resolved["permissions"], "Manager's own grant is missing"
        assert "users.manage" not in resolved["permissions"], (
            "a permission held only on another brand appeared in this brand's "
            "resolved set — the union is not scoped"
        )


class TestThePermissionCheckIsBrandAware:
    """ADR-150's 2026-09-15 addendum, enforced.

    Before this, `require_permission` and `enforce_policy` called
    `has_permission` with no brand, so the check unioned across every grant a
    person held: a Viewer on brand B who was Admin on brand A passed an Admin
    check **while working in brand B**. The grant table recorded the brand and
    the check ignored it.

    Driven over HTTP on purpose. The service layer has accepted a `brand_id`
    all along — the defect was that nobody passed one, so a test calling
    `has_permission` directly proves nothing about the thing that was broken.
    """

    @pytest.fixture
    def split_user(self, db, default_brand, temp_brand, user_on):
        """Admin on one brand, Viewer on another — the case from the question."""
        second = temp_brand()
        user = user_on(default_brand)          # Manager on default, from the fixture
        admin = db.query(RoleDB).filter(RoleDB.key == "admin").first()
        viewer = db.query(RoleDB).filter(RoleDB.key == "viewer").first()
        # Admin where the fixture put them, Viewer on the second brand.
        auth.assign_role(db, user.id, admin.id, brand_id=default_brand.id)
        db.query(RoleAssignmentDB).filter(
            RoleAssignmentDB.user_id == user.id,
            RoleAssignmentDB.brand_id == default_brand.id,
            RoleAssignmentDB.role_id != admin.id,
        ).delete(synchronize_session=False)
        auth.assign_role(db, user.id, viewer.id, brand_id=second.id)
        db.commit()
        return user, default_brand, second

    def _client(self, db, user, brand):
        from fastapi.testclient import TestClient

        from main import app

        token = auth.create_session(db, user)
        auth.set_session_brand(db, token, brand.id)
        client = TestClient(app, follow_redirects=False)
        client.cookies.set(auth.SESSION_COOKIE, token)
        return client, token

    def test_a_brand_scoped_permission_is_refused_on_the_wrong_brand(
        self, db, split_user, monkeypatch
    ):
        """The hole itself: Admin on A must not act as Admin on B."""
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        user, _admin_brand, viewer_brand = split_user
        client, token = self._client(db, user, viewer_brand)

        response = client.post(
            "/ui/campaigns",
            data={"name": f"sneaky-{uuid.uuid4().hex[:8]}",
                  "csrf_token": auth.csrf_token_for(token)},
        )

        assert response.status_code == 403, (
            f"expected 403, got {response.status_code} — a Viewer on this brand "
            "created a campaign because they are Admin on a different one, "
            "which is the union the addendum exists to stop"
        )

    def test_the_same_permission_is_allowed_on_the_right_brand(
        self, db, split_user, monkeypatch
    ):
        """Without this the test above could pass by refusing everything."""
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        user, admin_brand, _viewer_brand = split_user
        client, token = self._client(db, user, admin_brand)

        name = f"legit-{uuid.uuid4().hex[:8]}"
        response = client.post(
            "/ui/campaigns",
            data={"name": name, "csrf_token": auth.csrf_token_for(token)},
        )
        try:
            assert response.status_code == 303, (
                f"an Admin was refused on their own brand: {response.status_code}"
            )
        finally:
            campaign = db.query(CampaignDB).filter(CampaignDB.name == name).first()
            if campaign:
                db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).delete()
                db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
                db.commit()

    def test_a_platform_level_permission_ignores_the_working_brand(
        self, db, split_user, monkeypatch
    ):
        """users.manage is platform-level, so being on the Viewer brand is irrelevant.

        This is the half that makes the split worth having: without it, scoping
        the check would mean switching brand to reach Users — even though there
        is one user list, which ADR-150 point 2 already establishes.
        """
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        user, _admin_brand, viewer_brand = split_user
        client, _token = self._client(db, user, viewer_brand)

        response = client.get("/ui/users")

        assert response.status_code == 200, (
            f"got {response.status_code} — users.manage was checked against the "
            "working brand, so an Admin has to switch brand to manage users"
        )

    def test_a_brand_scoped_permission_with_no_working_brand_is_refused(
        self, db, default_brand, user_on
    ):
        """The defensive branch, pinned because it fails in the dangerous direction.

        `brand_id=None` means "any brand this user holds" — the union — so
        falling through to `has_permission(db, user, permission)` when there is
        no working brand would quietly restore the exact hole the addendum
        closes. A mutation proved nothing else covers this: every other test
        here goes through a request that HAS a working brand, so the fallback
        could be reverted and the suite stayed green.

        Checked directly rather than over HTTP because the state is not
        reachable through a normal request — which is the point. Unreachable
        today is not the same as unreachable after the next refactor.
        """
        from types import SimpleNamespace

        from app.auth.dependencies import _permitted

        user = user_on(default_brand)  # Manager, so they DO hold campaigns.manage

        assert auth.has_permission(db, user, "campaigns.manage") is True, (
            "fixture is wrong — the union must say yes, or this proves nothing"
        )

        request = SimpleNamespace(state=SimpleNamespace())
        assert _permitted(request, db, user, "campaigns.manage") is False, (
            "a brand-scoped permission was granted with no working brand, by "
            "falling back to the union across every brand the user holds"
        )

    def test_a_platform_level_permission_survives_no_working_brand(
        self, db, default_brand, user_on
    ):
        """The other half — otherwise the test above could pass by refusing all."""
        from types import SimpleNamespace

        from app.auth.dependencies import _permitted

        user = user_on(default_brand)
        request = SimpleNamespace(state=SimpleNamespace())
        assert _permitted(request, db, user, "view") is True


class TestConsentIsScopedToTheSendingBrand:
    """ADR-163 addendum 2026-09-15 — the change that makes the boundary real.

    Until this, the authoring side was scoped and the send side was not: a
    campaign belonging to brand B was filtered to brand B's content and
    audiences, and then reached **every consenting recipient**, because
    `is_consenting_filter()` had no brand in it. Measured before the change —
    41 recipients, all 41 passing the gate whichever brand asked.

    Consent is to a SENDER. Opting in to brand A says nothing about brand B,
    so a newly created brand starts with zero reachable recipients.
    """

    @pytest.fixture
    def consenting_recipient(self, db, default_brand):
        """A recipient who has opted in to the DEFAULT brand and nothing else."""
        from app.recipients.consent import record_consent
        from app.recipients.db_models import (
            AddressabilityDB, ConsentEventDB, RecipientDB,
        )

        recipient = RecipientDB(
            external_id=f"brandconsent-{uuid.uuid4().hex[:10]}",
            language="test-brand-consent",
            status="active",
        )
        db.add(recipient)
        db.commit()
        db.refresh(recipient)
        # An address as well as consent. The exclusion stack checks
        # addressability FIRST (ADR-163 point 7), so a consent-only fixture is
        # excluded at stage 1 and never reaches the stage under test — which
        # is how the first version of this test failed, for the wrong reason.
        db.add(AddressabilityDB(
            recipient_id=recipient.id,
            channel="email",
            value={"email": f"{uuid.uuid4().hex[:10]}@example.invalid"},
            status="active",
            is_primary=True,
        ))
        record_consent(db, recipient.id, "opted_in", default_brand.id, source="test")
        db.commit()

        yield recipient

        db.query(ConsentEventDB).filter(
            ConsentEventDB.recipient_id == recipient.id
        ).delete()
        db.query(AddressabilityDB).filter(
            AddressabilityDB.recipient_id == recipient.id
        ).delete()
        db.query(RecipientDB).filter(RecipientDB.id == recipient.id).delete()
        db.commit()

    def test_the_gate_admits_them_for_the_brand_they_opted_in_to(
        self, db, default_brand, consenting_recipient
    ):
        from app.recipients.consent import is_consenting_filter
        from app.recipients.db_models import RecipientDB

        found = db.query(RecipientDB).filter(
            RecipientDB.id == consenting_recipient.id,
            is_consenting_filter(default_brand.id),
        ).count()
        assert found == 1, "an opted-in recipient was gated out of their own brand"

    def test_the_gate_refuses_them_for_a_brand_they_never_opted_in_to(
        self, db, temp_brand, consenting_recipient
    ):
        """The defect itself. This is what a brand-B send used to reach."""
        from app.recipients.consent import is_consenting_filter
        from app.recipients.db_models import RecipientDB

        other = temp_brand()

        found = db.query(RecipientDB).filter(
            RecipientDB.id == consenting_recipient.id,
            is_consenting_filter(other.id),
        ).count()

        assert found == 0, (
            "a recipient who opted in to one brand was reachable by another — "
            "consent is to a sender, and this is the gap that let a brand-B "
            "campaign mail brand-A's subscribers"
        )

    def test_a_new_brand_starts_with_nobody(self, db, temp_brand):
        """Correct, and the consequence an adopter must not meet by surprise."""
        from app.recipients.consent import is_consenting_filter
        from app.recipients.db_models import RecipientDB

        fresh = temp_brand()
        reachable = db.query(RecipientDB).filter(is_consenting_filter(fresh.id)).count()

        assert reachable == 0, (
            f"{reachable} recipients were reachable by a brand created seconds "
            "ago that nobody has consented to"
        )

    def test_an_opt_out_on_one_brand_leaves_the_other_alone(
        self, db, default_brand, temp_brand, consenting_recipient
    ):
        """Opt-out scope follows consent scope (addendum point 2).

        A person genuinely subscribed to two brands should not lose both by
        leaving one. The "all brands" option exists for the other case, and is
        a company setting rather than the default.
        """
        from app.recipients.consent import is_consenting, record_consent
        from app.recipients.db_models import ConsentEventDB

        other = temp_brand()
        record_consent(db, consenting_recipient.id, "opted_in", other.id, source="test")
        assert is_consenting(db, consenting_recipient.id, other.id)

        record_consent(db, consenting_recipient.id, "opted_out", other.id, source="test")

        assert not is_consenting(db, consenting_recipient.id, other.id)
        assert is_consenting(db, consenting_recipient.id, default_brand.id), (
            "opting out of one brand withdrew consent for another"
        )
        db.query(ConsentEventDB).filter(
            ConsentEventDB.recipient_id == consenting_recipient.id,
            ConsentEventDB.brand_id == other.id,
        ).delete()
        db.commit()

    def test_resolve_audience_gates_on_the_GROUPS_brand(
        self, db, temp_brand, consenting_recipient
    ):
        """The audience path, not the filter helper.

        Written because a mutation exposed the gap: hardcoding brand 1 inside
        `resolve_audience` failed nothing, since every other test in the suite
        uses the default brand and could not tell the difference.
        """
        from app.audience.db_models import AudienceGroupDB, AudienceRuleBlockDB

        other = temp_brand()
        group = audience_service.create_group(
            db, f"crossbrand-{uuid.uuid4().hex[:8]}", brand_id=other.id
        )
        audience_service.add_block(
            db, group_id=group.id, kind="include",
            criteria={"language": "test-brand-consent"}, label="by language",
        )
        try:
            resolved = audience_service.resolve_audience(db, group.id)

            assert consenting_recipient.id not in {r.id for r in resolved}, (
                "a group on brand B resolved a recipient who only ever "
                "consented to brand A — the group's brand must gate it"
            )
        finally:
            db.query(AudienceRuleBlockDB).filter(
                AudienceRuleBlockDB.group_id == group.id
            ).delete()
            db.query(AudienceGroupDB).filter(AudienceGroupDB.id == group.id).delete()
            db.commit()

    def test_the_send_time_stack_excludes_on_the_sending_brand(
        self, db, default_brand, temp_brand, consenting_recipient
    ):
        """The exclusion stack — ADR-163 point 7, the stage that closed the P0.

        Also written after a mutation: hardcoding brand 1 in the consent stage
        failed nothing. This is the path a real send takes, so it is the one
        that matters most of the three.
        """
        from app.delivery.exclusion import run_exclusion_stack

        other = temp_brand()
        ids = {consenting_recipient.id}

        mine = run_exclusion_stack(db, ids, default_brand.id)
        assert consenting_recipient.id in mine.eligible, (
            "an opted-in recipient was excluded from their own brand's send"
        )

        theirs = run_exclusion_stack(db, ids, other.id)
        assert consenting_recipient.id not in theirs.eligible, (
            "a send as brand B would have mailed someone who only consented "
            "to brand A — this is the send-time half of the boundary"
        )
        assert any(
            e.recipient_id == consenting_recipient.id for e in theirs.exclusions
        ), "excluded without recording why — the exclusion reason is the audit trail"

    def test_a_manual_pin_does_not_survive_the_brand_consent_floor(
        self, db, temp_brand, consenting_recipient
    ):
        """Isolates the final consent floor, which nothing else reaches.

        Two mutations exposed why this is needed: breaking the criteria gate
        OR the final floor individually failed nothing, because each excludes
        independently and the survivor covers for the other. Defence in depth
        working, and a pair of untested paths hiding behind it.

        A manual pin bypasses criteria by design — ADR-163's rule is that a pin
        is a deliberate override that survives exclude blocks, with the consent
        floor as the one exception. So a pinned recipient reaches the floor and
        nothing else, which makes this the only way to test it alone.
        """
        from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB

        other = temp_brand()
        group = audience_service.create_group(
            db, f"pinned-{uuid.uuid4().hex[:8]}", brand_id=other.id
        )
        audience_service.add_member(db, group.id, consenting_recipient.id)
        try:
            resolved = audience_service.resolve_audience(db, group.id)

            assert consenting_recipient.id not in {r.id for r in resolved}, (
                "a recipient pinned into a brand-B group was resolved despite "
                "having consented only to brand A — the consent floor is the "
                "one thing a manual pin must not override"
            )
        finally:
            db.query(AudienceGroupMemberDB).filter(
                AudienceGroupMemberDB.group_id == group.id
            ).delete()
            db.query(AudienceGroupDB).filter(AudienceGroupDB.id == group.id).delete()
            db.commit()

    def test_find_by_criteria_gates_on_the_brand_it_is_given(
        self, db, default_brand, temp_brand, consenting_recipient
    ):
        """Isolates the criteria gate, for the same reason as the test above."""
        other = temp_brand()

        mine = audience_service.find_by_criteria(
            db, default_brand.id, language="test-brand-consent"
        )
        theirs = audience_service.find_by_criteria(
            db, other.id, language="test-brand-consent"
        )

        assert consenting_recipient.id in {r.id for r in mine}
        assert consenting_recipient.id not in {r.id for r in theirs}, (
            "the criteria search returned someone who never consented to the "
            "brand it was asked about"
        )


class TestSuggestAudienceSurvivedTheBrandWork:
    """Regression: "Suggest audience" was a 500 for a day.

    `create_group` gained `brand_id` as a required positional in brand step 1,
    and `create_suggested_group_for_campaign` was not updated — so every click
    raised `TypeError`. The route catches `ValueError`, not `TypeError`, so it
    surfaced as a 500 rather than a message.

    **Driven over HTTP deliberately.** A service-level test would have called
    the function with the right arguments and proved nothing: the defect was a
    caller that did not. This is the fourth time in this project that a test
    passing either side of a broken call has hidden it.
    """

    def _campaign_with_content(self, db, brand):
        """A campaign whose content has categories, so suggestions exist."""
        from app.content.db_models import ContentCategoryAssignmentDB, CategoryDB
        from app.campaigns.db_models import ModuleInstanceDB
        from app.campaigns.service import create_campaign
        from app.content.service import create_content

        campaign = create_campaign(
            db, name=f"suggest-{uuid.uuid4().hex[:8]}", brand_id=brand.id
        )
        record = create_content(
            db, title=f"suggest-{uuid.uuid4().hex[:8]}",
            content={"headline_medium": "x"}, brand_id=brand.id,
        )
        category = db.query(CategoryDB).first()
        if category is None:
            pytest.skip("no category in this database to suggest from")
        db.add(ContentCategoryAssignmentDB(
            content_id=record.id, category_id=category.id, score=10,
        ))
        variant_id = db.query(VariantDB.id).filter(
            VariantDB.campaign_id == campaign.id
        ).scalar()
        db.add(ModuleInstanceDB(
            variant_id=variant_id, module_type="img_left",
            content_record_id=record.id, position=1,
        ))
        db.commit()
        return campaign, record

    def test_suggest_audience_does_not_500(self, db, temp_brand, monkeypatch):
        from fastapi.testclient import TestClient

        from main import app
        from app.audience.db_models import AudienceGroupDB, AudienceRuleBlockDB
        from app.campaigns.db_models import CampaignDB, ModuleInstanceDB
        from app.content.db_models import ContentCategoryAssignmentDB, ContentRecordDB

        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        admin = db.query(UserDB).join(
            RoleAssignmentDB, RoleAssignmentDB.user_id == UserDB.id
        ).join(RoleDB, RoleDB.id == RoleAssignmentDB.role_id).filter(
            RoleDB.key == "admin", UserDB.is_active.is_(True)
        ).first()
        if admin is None:
            pytest.skip("no active admin in this database to act as")

        # A NON-default brand deliberately. With the campaign on brand 1 this
        # test could not tell a derived brand from a hardcoded one — a mutation
        # proved exactly that, so the fixture has to make the two differ.
        brand = temp_brand()
        admin_role = db.query(RoleDB).filter(RoleDB.key == "admin").first()
        auth.assign_role(db, admin.id, admin_role.id, brand_id=brand.id)

        campaign, record = self._campaign_with_content(db, brand)
        token = auth.create_session(db, admin)
        auth.set_session_brand(db, token, brand.id)
        client = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
        client.cookies.set(auth.SESSION_COOKIE, token)

        try:
            response = client.post(
                f"/ui/campaigns/{campaign.id}/suggest-audience",
                data={"csrf_token": auth.csrf_token_for(token)},
            )

            assert response.status_code < 500, (
                f"Suggest audience returned {response.status_code} — the route "
                "catches ValueError, so a TypeError from a changed signature "
                "arrives as a 500 with no message"
            )
            group = db.query(AudienceGroupDB).filter(
                AudienceGroupDB.source_campaign_id == campaign.id
            ).first()
            assert group is not None, "no group was created"
            assert group.brand_id == brand.id, (
                f"the suggested group landed on brand {group.brand_id} instead "
                f"of the campaign's {brand.id} — it must follow the campaign"
            )
        finally:
            groups = db.query(AudienceGroupDB).filter(
                AudienceGroupDB.source_campaign_id == campaign.id
            ).all()
            for g in groups:
                db.query(AudienceRuleBlockDB).filter(
                    AudienceRuleBlockDB.group_id == g.id
                ).delete()
            db.query(AudienceGroupDB).filter(
                AudienceGroupDB.source_campaign_id == campaign.id
            ).delete()
            db.query(ModuleInstanceDB).filter(
                ModuleInstanceDB.content_record_id == record.id
            ).delete()
            db.query(ContentCategoryAssignmentDB).filter(
                ContentCategoryAssignmentDB.content_id == record.id
            ).delete()
            db.query(ContentRecordDB).filter(ContentRecordDB.id == record.id).delete()
            db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).delete()
            db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
            db.query(SessionDB).filter(
                SessionDB.token_hash == auth.hash_secret(token)
            ).delete()
            db.commit()


class TestTheContentPickerIsScoped:
    """The campaign page's module content picker offered every brand's content.

    Found while designing duplication. It matters more than it looks: nothing
    downstream would have objected — only the decision strategies enforce brand
    on content, so a module bound to another brand's record renders happily.
    The picker was the one place a manager could create that state by hand, and
    it is exactly the state cross-brand duplication exists to make unnecessary.
    """

    def test_the_picker_offers_only_the_campaigns_own_brand(
        self, db, default_brand, temp_brand, monkeypatch
    ):
        from fastapi.testclient import TestClient

        from main import app
        from app.campaigns.db_models import CampaignDB
        from app.campaigns.service import create_campaign
        from app.content.db_models import ContentRecordDB
        from app.content.service import create_content

        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        admin = db.query(UserDB).join(
            RoleAssignmentDB, RoleAssignmentDB.user_id == UserDB.id
        ).join(RoleDB, RoleDB.id == RoleAssignmentDB.role_id).filter(
            RoleDB.key == "admin", UserDB.is_active.is_(True)
        ).first()
        if admin is None:
            pytest.skip("no active admin in this database to act as")

        other = temp_brand()
        # Content on the OTHER brand, with a title distinctive enough to find
        # in the rendered page.
        marker = f"PICKERLEAK-{uuid.uuid4().hex[:8]}"
        foreign = create_content(
            db, title=marker, content={"headline_medium": "x"}, brand_id=other.id
        )
        campaign = create_campaign(
            db, name=f"picker-{uuid.uuid4().hex[:8]}", brand_id=default_brand.id
        )
        token = auth.create_session(db, admin)
        client = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
        client.cookies.set(auth.SESSION_COOKIE, token)

        try:
            page = client.get(f"/ui/campaigns/{campaign.id}")

            assert page.status_code == 200
            assert marker not in page.text, (
                "the module content picker offered another brand's content — "
                "selecting it would bind brand B's record to a brand A "
                "campaign, and nothing in the render path would refuse it"
            )
        finally:
            db.query(ContentRecordDB).filter(ContentRecordDB.id == foreign.id).delete()
            db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).delete()
            db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
            db.query(SessionDB).filter(
                SessionDB.token_hash == auth.hash_secret(token)
            ).delete()
            db.commit()


class TestSwitchingBrandFromADetailPage:
    """Reported by the user 2026-09-16, and it is really one cause.

    The switcher returns you to the URL you were on, and that URL is a row
    belonging to the brand you just left. On a content record that produced a
    red banner accusing you of following a dead link; on a campaign it produced
    an internal error, because `campaign_detail` never learned the answer
    `content_detail` was taught when brand scoping made absence reachable.

    Fixing only the crash would have left the banner, so both are here.
    """

    def _client(self, db, user, brand):
        from fastapi.testclient import TestClient

        from main import app

        token = auth.create_session(db, user)
        auth.set_session_brand(db, token, brand.id)
        client = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
        client.cookies.set(auth.SESSION_COOKIE, token)
        return client, token

    def test_another_brand_s_campaign_answers_instead_of_crashing(
        self, db, default_brand, temp_brand, user_on, monkeypatch
    ):
        """The black screen. The assertion is on the status, because a 500 is
        what the user saw and a redirect is what they should have."""
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        other = temp_brand()
        user = user_on(default_brand, other)
        campaign = create_campaign(
            db, name=f"switchcrash-{uuid.uuid4().hex[:8]}", brand_id=default_brand.id
        )
        client, token = self._client(db, user, other)
        try:
            response = client.get(f"/ui/campaigns/{campaign.id}")

            assert response.status_code != 500, (
                "opening a campaign while working in another brand returned an "
                "internal error — `campaign_detail` hands a None campaign to a "
                "template that reads campaign.name unguarded"
            )
            assert response.status_code == 303
            assert response.headers["location"].startswith("/ui/campaigns?error="), (
                f"expected the campaigns list with a message, got "
                f"{response.headers['location']!r}"
            )
        finally:
            db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).delete()
            db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
            db.query(SessionDB).filter(
                SessionDB.token_hash == auth.hash_secret(token)
            ).delete()
            db.commit()

    def test_switching_brand_from_a_row_lands_on_that_section_s_list(
        self, db, default_brand, temp_brand, user_on, monkeypatch
    ):
        """And this is why the crash was reached at all."""
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        other = temp_brand()
        user = user_on(default_brand, other)
        client, token = self._client(db, user, default_brand)
        try:
            for origin, expected in (
                ("/ui/campaigns/12345", "/ui/campaigns"),
                ("/ui/content/12345", "/ui/content"),
                ("/ui/decisions/slots/12345", "/ui/decisions"),
                ("/ui/deliveries/send-instances/12345", "/ui/deliveries"),
                ("/ui/audience-groups/12345", "/ui/audience-groups"),
            ):
                response = client.post(
                    "/ui/brand",
                    data={
                        "brand_id": str(other.id),
                        "next": origin,
                        "csrf_token": auth.csrf_token_for(token),
                    },
                )
                assert response.status_code == 303
                assert response.headers["location"] == expected, (
                    f"switching brand from {origin} landed on "
                    f"{response.headers['location']!r} — a row id from the brand "
                    f"the user just left, which cannot resolve in the new one"
                )
        finally:
            db.query(SessionDB).filter(
                SessionDB.token_hash == auth.hash_secret(token)
            ).delete()
            db.commit()

    def test_switching_brand_on_a_recipient_leaves_you_where_you_are(
        self, db, default_brand, temp_brand, user_on, monkeypatch
    ):
        """Without this the rule above could be "always go to a list", which
        would be wrong: a recipient carries no brand (ADR-150 point 9), so the
        row survives the switch. What changes is the consent shown against it,
        and that is precisely what somebody switching brand there wants to see.
        """
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        other = temp_brand()
        user = user_on(default_brand, other)
        client, token = self._client(db, user, default_brand)
        try:
            response = client.post(
                "/ui/brand",
                data={
                    "brand_id": str(other.id),
                    "next": "/ui/recipients/12345",
                    "csrf_token": auth.csrf_token_for(token),
                },
            )
            assert response.headers["location"] == "/ui/recipients/12345", (
                "a brand switch bounced the user off a recipient that is still "
                "perfectly valid in the new brand"
            )
        finally:
            db.query(SessionDB).filter(
                SessionDB.token_hash == auth.hash_secret(token)
            ).delete()
            db.commit()

    def test_a_recipient_that_does_not_exist_answers_instead_of_crashing(
        self, db, default_brand, user_on, monkeypatch
    ):
        """Not a brand case at all — found by probing every detail-by-id route
        with a nonexistent id while fixing the campaign one. A typo'd URL
        reached `to_recipient` as None and raised."""
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        user = user_on(default_brand)
        client, token = self._client(db, user, default_brand)
        try:
            response = client.get("/ui/recipients/99999999")

            assert response.status_code != 500, "a mistyped recipient id crashed"
            assert response.headers["location"].startswith("/ui/recipients?error=")
        finally:
            db.query(SessionDB).filter(
                SessionDB.token_hash == auth.hash_secret(token)
            ).delete()
            db.commit()
