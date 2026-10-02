"""Rule blocks over JSON — the half of an audience group the API could not say.

Groups and individual pins existed; **rule blocks did not**. A group's audience
is evaluated live from its blocks rather than stored as a member list, so the
API could create a group and had no way to express who it meant. That is most
of what the audience screen does, and it is MVP screen two.

Runs against the isolated test database and removes what it creates.
"""
import uuid

import pytest
from sqlalchemy import text

from app.audience import service
from app.audience.db_models import AudienceGroupDB, AudienceRuleBlockDB
from app.auth import service as auth
from app.database import SessionLocal
from tests.machine import machine
from tests.test_api_guard import client

TAG = "audapi"


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def group(db):
    row = service.create_group(
        db, f"{TAG}-{uuid.uuid4().hex[:8]}",
        brand_id=auth.ensure_default_brand(db).id,
    )
    try:
        yield row
    finally:
        db.rollback()
        db.execute(text("DELETE FROM audience_rule_blocks WHERE group_id = :g"), {"g": row.id})
        db.execute(text("DELETE FROM audience_group_members WHERE group_id = :g"), {"g": row.id})
        db.query(AudienceGroupDB).filter(AudienceGroupDB.id == row.id).delete()
        db.commit()


@pytest.fixture
def api():
    from app.auth.permissions import AUDIENCES_MANAGE, AUDIENCES_PIN, VIEW

    with machine([VIEW, AUDIENCES_MANAGE, AUDIENCES_PIN]) as headers:
        yield headers


class TestRuleBlocks:

    def test_a_group_can_finally_say_who_it_means(self, db, group, api):
        response = client.post(
            f"/api/audience-groups/{group.id}/blocks",
            json={"kind": "include", "label": "Hikers",
                  "criteria": {"category_ids": [1]}},
            headers=api,
        )

        assert response.status_code == 201, response.text
        blocks = service.list_blocks(db, group.id, brand_id=group.brand_id)
        assert len(blocks) == 1
        assert blocks[0].kind == "include"
        assert blocks[0].label == "Hikers"

    def test_source_cannot_be_claimed_by_the_caller(self, db, group, api):
        """A block the system suggested and one a person wrote are different
        facts, and the UI shows the difference. A caller that could claim
        `suggested` could make a hand-written rule wear the system's badge.
        """
        client.post(
            f"/api/audience-groups/{group.id}/blocks",
            json={"kind": "include", "source": "suggested",
                  "criteria": {"category_ids": [1]}},
            headers=api,
        )

        assert service.list_blocks(db, group.id, brand_id=group.brand_id)[0].source == "manual"

    def test_an_invalid_kind_is_refused(self, db, group, api):
        response = client.post(
            f"/api/audience-groups/{group.id}/blocks",
            json={"kind": "maybe", "criteria": {}}, headers=api,
        )

        assert response.status_code == 400
        assert service.list_blocks(db, group.id, brand_id=group.brand_id) == []

    def test_a_block_can_be_edited_and_deleted(self, db, group, api):
        created = client.post(
            f"/api/audience-groups/{group.id}/blocks",
            json={"kind": "include", "label": "Before"}, headers=api,
        ).json()

        client.patch(
            f"/api/audience-groups/{group.id}/blocks/{created['id']}",
            json={"label": "After"}, headers=api,
        )
        assert service.get_block(db, created["id"], brand_id=group.brand_id).label == "After"

        assert client.delete(
            f"/api/audience-groups/{group.id}/blocks/{created['id']}",
            headers=api,
        ).status_code == 204
        assert service.get_block(db, created["id"], brand_id=group.brand_id) is None

    def test_a_block_from_another_group_is_not_reachable(self, db, group, api):
        """The block id alone is not authority — it has to belong to the group
        in the path, or one group can edit another's rules by guessing."""
        other = service.create_group(
            db, f"{TAG}-other-{uuid.uuid4().hex[:8]}",
            brand_id=auth.ensure_default_brand(db).id,
        )
        try:
            stray = service.add_block(
                db, group_id=other.id, kind="include", brand_id=other.brand_id)
            response = client.patch(
                f"/api/audience-groups/{group.id}/blocks/{stray.id}",
                json={"label": "hijacked"}, headers=api,
            )
            assert response.status_code == 404
            assert service.get_block(db, stray.id, brand_id=other.brand_id).label != "hijacked"
        finally:
            db.rollback()
            db.execute(text("DELETE FROM audience_rule_blocks WHERE group_id = :g"),
                       {"g": other.id})
            db.query(AudienceGroupDB).filter(AudienceGroupDB.id == other.id).delete()
            db.commit()


class TestBulkAdd:

    def test_it_reports_added_separately_from_requested(self, db, group, api):
        """Already being in the group is not an error and is not counted twice,
        so the two numbers genuinely differ and both are useful."""
        recipients = [
            r[0] for r in db.execute(text("SELECT id FROM recipients LIMIT 3")).all()
        ]
        if len(recipients) < 2:
            pytest.skip("not enough recipients in the test database")

        first = client.post(
            f"/api/audience-groups/{group.id}/members",
            json={"recipient_ids": recipients}, headers=api,
        ).json()
        again = client.post(
            f"/api/audience-groups/{group.id}/members",
            json={"recipient_ids": recipients}, headers=api,
        ).json()

        assert first["added"] == len(recipients)
        assert first["requested"] == len(recipients)
        assert again["added"] == 0, "a second call re-added existing pins"
        assert again["requested"] == len(recipients)

    def test_it_needs_only_the_pin_permission(self, db, group):
        """ADR-166 point 2's split, reaching a real route: adding members is
        `audiences.pin`, not the `audiences.manage` that restructures a group.
        """
        from app.auth.permissions import AUDIENCES_PIN, VIEW

        with machine([VIEW, AUDIENCES_PIN]) as headers:
            response = client.post(
                f"/api/audience-groups/{group.id}/members",
                json={"recipient_ids": []}, headers=headers,
            )
            assert response.status_code == 200

    def test_pinning_does_not_grant_restructuring(self, db, group):
        from app.auth.permissions import AUDIENCES_PIN, VIEW

        with machine([VIEW, AUDIENCES_PIN]) as headers:
            response = client.post(
                f"/api/audience-groups/{group.id}/blocks",
                json={"kind": "include"}, headers=headers,
            )
            assert response.status_code == 403, (
                "a caller that may pin a member rewrote the group's rules"
            )


class TestRecalculate:

    def test_a_group_with_no_source_campaign_says_so(self, db, group, api):
        """Rather than succeeding silently, which would read as 'recalculated
        and nothing changed' — a different and misleading fact."""
        response = client.post(
            f"/api/audience-groups/{group.id}/recalculate", headers=api,
        )

        assert response.status_code == 400
        assert "no source campaign" in response.json()["detail"]


class TestExcludeBeatsPin:
    """ADR-176 point 1 — an exclusion segment removes a hand-pinned recipient.

    **This reverses the rule that stood from 2026-07-26**, and no test asserted
    the old one. The ADR measured that before deciding: every pin assertion in
    this suite is against the *consent floor*, which is untouched here. So the
    reversal shipped with nothing to fail, and this class is what was missing —
    the precedence between two people's intentions, asserted on its own.

    The recipient gets a language nobody else has, so the exclude block catches
    exactly them. Resolving against the shared dev database otherwise makes the
    assertion depend on rows this test did not create.
    """

    @pytest.fixture
    def pinned_and_excluded(self, db, group):
        """One consenting recipient, pinned to the group, and an exclude block
        that catches them by language. No include block: the pin is the only
        thing that could put them in the set, which is what makes the
        subtraction the single thing under test.

        **The email address was load-bearing until 2026-09-29 and no longer
        is.** A block's criteria used to resolve through a helper that dropped
        anyone unaddressable, so without an address the block resolved to
        nobody and this test passed against an empty exclude set rather than
        against the precedence. That asymmetry was task-233; the address is
        kept here because a realistic recipient has one, not because the
        assertion needs it — `TestExclusionReachesTheUnaddressable` below is
        the test that would fail if it came back.
        """
        from app.recipients.consent import record_consent
        from app.recipients.db_models import AddressabilityDB, RecipientDB

        language = f"zz-{uuid.uuid4().hex[:8]}"
        recipient = RecipientDB(
            external_id=f"{TAG}-{uuid.uuid4().hex[:8]}",
            status="active",
            language=language,
        )
        db.add(recipient)
        db.commit()
        db.refresh(recipient)
        db.add(AddressabilityDB(
            recipient_id=recipient.id, channel="email",
            value={"email": f"{TAG}-{uuid.uuid4().hex[:8]}@example.invalid"},
        ))
        db.commit()
        record_consent(
            db, recipient.id, "opted_in", group.brand_id,
            channel="email", source="test", purpose="marketing",
        )
        service.add_member(db, group.id, recipient.id, brand_id=group.brand_id)
        try:
            yield recipient, language
        finally:
            db.rollback()
            db.execute(
                text("DELETE FROM recipient_addresses WHERE recipient_id = :r"),
                {"r": recipient.id},
            )
            db.execute(
                text("DELETE FROM consent_events WHERE recipient_id = :r"),
                {"r": recipient.id},
            )
            db.execute(
                text("DELETE FROM audience_group_members WHERE recipient_id = :r"),
                {"r": recipient.id},
            )
            db.query(RecipientDB).filter(RecipientDB.id == recipient.id).delete()
            db.commit()

    def test_a_pinned_recipient_is_removed_by_an_exclude_block(
        self, db, group, pinned_and_excluded
    ):
        """The reversal itself. Under the 2026-07-26 rule this recipient came
        back, because pins were unioned in after the subtraction."""
        recipient, language = pinned_and_excluded

        service.add_block(
            db, group.id, kind="exclude", criteria={"language": language},
            brand_id=group.brand_id,
        )

        resolved = service.resolve_audience(db, group.id, "email")

        assert recipient.id not in {r.id for r in resolved}, (
            "a hand-pinned recipient survived an exclude block — the "
            "2026-07-26 precedence, which ADR-176 point 1 reverses"
        )

    def test_a_pin_still_reaches_the_audience_without_an_exclude_block(
        self, db, group, pinned_and_excluded
    ):
        """The other half, and the reason the first test proves anything. A pin
        that never resolved would satisfy the assertion above for a reason that
        has nothing to do with precedence — the group has no include block, so
        without this the whole class would pass against a broken pin path."""
        recipient, _language = pinned_and_excluded

        resolved = service.resolve_audience(db, group.id, "email")

        assert recipient.id in {r.id for r in resolved}, (
            "a pinned, consenting recipient did not resolve at all, so the "
            "exclusion test above proves nothing"
        )


class TestExclusionReachesTheUnaddressable:
    """task-233: a membership query must not ask whether somebody is reachable.

    Until 2026-09-29 a rule block's criteria resolved through a helper that
    dropped any recipient with no usable address. For an *exclude* block that
    is backwards — dropping somebody from an exclusion puts them back in the
    audience — so an unaddressable recipient could be pinned into a group and
    no exclude block could remove them.

    The two tests here are the two halves of the same root cause, and the
    second is the one that leaked: the helper asked about **email**
    addressability whatever channel was requested, so on a push send the
    exclusion was ignored for exactly the people the push could still reach.
    """

    @pytest.fixture
    def unaddressable(self, db, group):
        """Consenting on email, pinned, and reachable at no address at all."""
        from app.recipients.consent import record_consent
        from app.recipients.db_models import RecipientDB

        language = f"na-{uuid.uuid4().hex[:6]}"
        recipient = RecipientDB(
            external_id=f"{TAG}-{uuid.uuid4().hex[:8]}",
            status="active", language=language,
        )
        db.add(recipient)
        db.commit()
        db.refresh(recipient)
        record_consent(
            db, recipient.id, "opted_in", group.brand_id,
            channel="email", source="test", purpose="marketing",
        )
        service.add_member(db, group.id, recipient.id, brand_id=group.brand_id)
        try:
            yield recipient, language
        finally:
            db.rollback()
            db.execute(text("DELETE FROM consent_events WHERE recipient_id = :r"),
                       {"r": recipient.id})
            db.execute(text("DELETE FROM audience_group_members WHERE recipient_id = :r"),
                       {"r": recipient.id})
            db.query(RecipientDB).filter(RecipientDB.id == recipient.id).delete()
            db.commit()

    def test_an_exclude_block_removes_a_recipient_with_no_address(
        self, db, group, unaddressable
    ):
        recipient, language = unaddressable

        service.add_block(
            db, group.id, kind="exclude", criteria={"language": language},
            brand_id=group.brand_id,
        )

        resolved = service.resolve_audience(db, group.id, "email")

        assert recipient.id not in {r.id for r in resolved}, (
            "an exclude block could not reach a pinned recipient who has no "
            "address — the membership query filtered the exclusion by "
            "reachability, which is task-233"
        )


class TestPushCriteriaAskAboutPush:
    """The other half of task-233, and the larger one.

    A rule block's criteria consent-gated on **email** whatever channel was
    asked about, so a push-only recipient matched by an *include* block
    resolved into nothing. Rule-based push audiences did not work at all —
    only pins did — and nothing said so, because the resolver returned an empty
    list rather than an error.
    """

    @pytest.fixture
    def push_only(self, db, group):
        """A push token, push consent, and no email anything."""
        from app.recipients.consent import record_consent
        from app.recipients.db_models import AddressabilityDB, RecipientDB

        language = f"pu-{uuid.uuid4().hex[:6]}"
        recipient = RecipientDB(
            external_id=f"{TAG}-{uuid.uuid4().hex[:8]}",
            status="active", language=language,
        )
        db.add(recipient)
        db.commit()
        db.refresh(recipient)
        db.add(AddressabilityDB(
            recipient_id=recipient.id, channel="push",
            value={"token": f"apns-{uuid.uuid4().hex[:8]}", "platform": "apns"},
            status="active", is_primary=True,
        ))
        db.commit()
        record_consent(
            db, recipient.id, "opted_in", group.brand_id,
            channel="push", source="test", purpose="marketing",
        )
        try:
            yield recipient, language
        finally:
            db.rollback()
            db.execute(text("DELETE FROM recipient_addresses WHERE recipient_id = :r"),
                       {"r": recipient.id})
            db.execute(text("DELETE FROM consent_events WHERE recipient_id = :r"),
                       {"r": recipient.id})
            db.query(RecipientDB).filter(RecipientDB.id == recipient.id).delete()
            db.commit()

    def test_an_include_block_finds_a_push_only_recipient_on_push(
        self, db, group, push_only
    ):
        recipient, language = push_only

        service.add_block(
            db, group.id, kind="include", criteria={"language": language},
            brand_id=group.brand_id,
        )

        resolved = service.resolve_audience(db, group.id, "push")

        assert recipient.id in {r.id for r in resolved}, (
            "a push-consenting recipient was not found by a push audience's "
            "include block, because the criteria asked about email consent"
        )

    def test_the_same_recipient_is_not_in_the_email_audience(
        self, db, group, push_only
    ):
        """The channel is doing real work, not being ignored. Without this the
        test above would pass against a resolver that stopped consent-gating
        criteria at all — which would be a far worse bug than the one fixed."""
        recipient, language = push_only

        service.add_block(
            db, group.id, kind="include", criteria={"language": language},
            brand_id=group.brand_id,
        )

        resolved = service.resolve_audience(db, group.id, "email")

        assert recipient.id not in {r.id for r in resolved}, (
            "a recipient who consented to push and never to email was resolved "
            "into an email audience"
        )
