"""What an audit entry may say, enforced where it is written (task-52; ADR-153 addendum 2026-10-08).

Decided with the user one question at a time:
  1. one vocabulary of action names, and an unknown one is refused at write;
  2. a detail holding an email-shaped value is refused at write — internal
     identifiers only (ADR-153 point 5); the two entries that copied a person's
     address carry the actor's type and id, or drop the label;
  3. filtering one actor's history by brand keeps the entries with no brand
     (sign-ins, platform settings), which belong to the person, not a brand.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.audit import service as audit
from app.audit.db_models import AuditEventDB
from app.database import SessionLocal

TAG = f"audit-{uuid.uuid4().hex[:6]}"


@pytest.fixture
def db():
    session = SessionLocal()
    made = []
    session.made = made
    try:
        yield session
    finally:
        session.rollback()
        if made:
            session.query(AuditEventDB).filter(AuditEventDB.id.in_(made)).delete(synchronize_session=False)
            session.commit()
        session.close()


class TestOneVocabulary:
    def test_every_action_the_platform_writes_is_in_it(self):
        assert {"user.signed_in", "approval.requested", "approval.granted", "send.fired",
                "ai.suggestion_applied", "content.ready_marked"} <= audit.ACTIONS

    def test_an_unknown_action_is_refused(self, db):
        with pytest.raises(ValueError, match="not an audit action"):
            audit.record(db, "content.updatd", subject_type="content", subject_id=1, commit=False)

    def test_a_known_action_is_written(self, db):
        event = audit.record(db, audit.CONTENT_UPDATED, subject_type="content", subject_id=1,
                             detail={"title": TAG}, commit=True)
        db.made.append(event.id)
        assert event.action == "content.updated"

    def test_the_approval_lifecycle_names_come_from_the_vocabulary(self):
        from app.approvals import service as approvals

        assert {approvals.REQUESTED, approvals.GRANTED, approvals.DENIED, approvals.LAPSED,
                approvals.EXECUTION_FAILED} <= audit.ACTIONS


class TestNoContactDetails:
    @pytest.mark.parametrize("detail", [
        {"was": "ana@example.invalid"},
        {"nested": {"deeper": ["ok", "Ana.Smith@Example.COM"]}},
    ])
    def test_a_detail_with_an_email_address_is_refused(self, db, detail):
        with pytest.raises(ValueError, match="email"):
            audit.record(db, audit.CONTENT_UPDATED, subject_type="content", subject_id=1, detail=detail,
                         commit=False)

    def test_internal_identifiers_and_ordinary_text_pass(self, db):
        event = audit.record(db, audit.CONTENT_UPDATED, subject_type="content", subject_id=1, commit=True,
                             detail={"recipient_id": 7, "reason": "VIP at the event", "url": "https://a.test/x"})
        db.made.append(event.id)
        assert event is not None


    def test_authored_copy_may_mention_an_address(self, db):
        """Decided with the user 2026-10-08: a name, a title and an envelope are
        copy a person wrote, not somebody's contact detail. "Reply to
        hello@brand.test" in a preheader must not fail the save it records."""
        event = audit.record(db, audit.VARIANT_UPDATED, subject_type="variant", subject_id=1, commit=True,
                             detail={"name": "Ask ana@brand.test", "title": "x@brand.test",
                                     "envelope": {"preheader": "Reply to hello@brand.test"}})
        db.made.append(event.id)
        assert event.detail["envelope"]["preheader"] == "Reply to hello@brand.test"

    def test_the_exemption_is_by_top_level_key_only(self, db):
        """A key called `name` deeper down is not copy by that fact alone."""
        with pytest.raises(ValueError, match="email"):
            audit.record(db, audit.VARIANT_UPDATED, subject_type="variant", subject_id=1, commit=False,
                         detail={"was": {"name": "ana@example.invalid"}})


class TestFilteringByBrand:
    def test_an_actors_history_in_one_brand_keeps_what_has_no_brand(self, db, default_brand, foreign_brand):
        actor = 900_000 + uuid.uuid4().int % 10_000
        now = datetime.now(timezone.utc)
        rows = [
            AuditEventDB(actor_type=audit.ACTOR_USER, actor_id=actor, action=audit.SIGNED_IN, brand_id=None,
                         created_at=now - timedelta(minutes=3)),
            AuditEventDB(actor_type=audit.ACTOR_USER, actor_id=actor, action=audit.CONTENT_UPDATED,
                         brand_id=default_brand.id, created_at=now - timedelta(minutes=2)),
            AuditEventDB(actor_type=audit.ACTOR_USER, actor_id=actor, action=audit.CONTENT_UPDATED,
                         brand_id=foreign_brand.id, created_at=now - timedelta(minutes=1)),
        ]
        db.add_all(rows)
        db.commit()
        db.made.extend(r.id for r in rows)
        here = audit.events_by_actor(db, actor, brand_id=default_brand.id)
        assert [(e.action, e.brand_id) for e in here] == [
            (audit.CONTENT_UPDATED, default_brand.id), (audit.SIGNED_IN, None)]
        assert len(audit.events_by_actor(db, actor)) == 3, "no brand given: everything, as before"
