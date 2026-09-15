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
