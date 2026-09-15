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
from app.auth import service as auth
from app.auth.db_models import BrandDB, RoleAssignmentDB, RoleDB, SessionDB, UserDB
from app.auth.permissions import MANAGER
from app.campaigns.db_models import CampaignDB, VariantDB
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

    for brand_id in created:
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

    def test_usage_counts_are_reported_per_brand(self, db, temp_brand, temp_content):
        brand = temp_brand()
        assert auth.brand_usage(db).get(brand.id) == 0
        temp_content(brand)
        assert auth.brand_usage(db).get(brand.id) == 1, (
            "the usage count shown beside Delete disagrees with what Delete "
            "will actually refuse"
        )


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
