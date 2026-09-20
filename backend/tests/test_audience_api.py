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
