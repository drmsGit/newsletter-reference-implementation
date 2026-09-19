"""The pending-action spine — ADR-142 §4, stage 1.

The spine ships wired to nothing: no route can reach it yet and no real action
is registered. So every test here drives a **planted** action file, which is
also the only honest way to test a drop-a-file registry — the one real action
lands in a later commit and would prove that the registry works for exactly the
module somebody remembered to import.

**The test that carries the ADR's constraint** is
`test_deleting_every_pending_row_loses_no_accountability`. ADR-142 §4 says the
action history "extends the ADR-140 audit surface; it is not a second log", and
the way that promise dies quietly is by `pending_actions` gradually becoming the
record of who decided what. Asserting the history survives the table is what
keeps `status` a cache rather than a fact.

Runs against the shared dev database like the rest of the suite, and removes
everything it creates — including its audit rows, which have no foreign keys
and therefore do not cascade.
"""
import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.approvals import service as approvals
from app.approvals.actions import registry as action_registry
from app.approvals.db_models import (
    APPROVED, EXPIRED, FAILED, PENDING, REJECTED, PendingActionDB,
)
from app.audit.db_models import AuditEventDB
from app.audit.service import ACTOR_USER, events_for_subject
from app.database import SessionLocal

TAG = "apprtest"
ACTION_KEY = "apprtest.write_marker"
BROKEN_KEY = "apprtest.no_execute"


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def planted_action(tmp_path):
    """Drop a real action file into the package, the way a company would.

    `_registry_mtime = None` is mandatory, not tidiness: `_ensure_fresh()`
    recomputes from the directory mtime, so a registry left primed from an
    earlier test silently ignores the new file.
    """
    package = Path(action_registry.__file__).parent
    good = package / f"{TAG}_marker.py"
    good.write_text(
        "from app.approvals.actions.base import ApprovableAction, "
        "ActionDescription, ActionResult\n"
        "from pathlib import Path\n"
        "\n"
        f"META = ApprovableAction(key='{ACTION_KEY}', label='Write a marker',\n"
        "                        approve_permission='sends.execute',\n"
        "                        default_ttl_seconds=3600,\n"
        "                        subject_type='marker')\n"
        "\n"
        "def describe(db, payload):\n"
        "    return ActionDescription(summary='writes a marker file',\n"
        "                             rows=[('Path', payload.get('path', ''))])\n"
        "\n"
        "def execute(db, payload, *, choice=None):\n"
        "    if payload.get('explode'):\n"
        "        raise RuntimeError('the action blew up')\n"
        "    if payload.get('decline'):\n"
        "        return ActionResult(ok=False, message='the action declined')\n"
        "    path = Path(payload['path'])\n"
        "    # APPENDS — deliberately not idempotent, so a double execution is\n"
        "    # visible rather than absorbed.\n"
        "    with path.open('a') as handle:\n"
        "        handle.write((choice or {}).get('text') or payload.get('text', 'x'))\n"
        "    return ActionResult(ok=True, audit_action='marker.written',\n"
        "                        audit_detail={'path': str(path)})\n"
    )
    action_registry._registry_mtime = None
    try:
        yield {"path": str(tmp_path / "marker.txt")}
    finally:
        good.unlink(missing_ok=True)
        action_registry._registry_mtime = None


#: Every pending action this module creates, remembered as it is created.
_CREATED: list[int] = []


@pytest.fixture(autouse=True)
def _sweep(db):
    """Remove pending actions AND their audit rows.

    Audit entries carry no foreign keys — an accountability record has to
    outlive what it references — so nothing cascades, and a fixture that forgets
    them leaks. This repo has been bitten twice.

    **The ids are remembered as they are created, never looked up afterwards.**
    The first version of this fixture resolved them by querying
    `pending_actions`, which works for every test except the one that proves the
    audit log outlives that table: it deletes the pending row on purpose, and
    its audit entries then had nothing left to be found by. A cleanup that reads
    the thing it is cleaning up cannot cope with a test whose subject is the
    separation of the two.
    """
    yield
    db.rollback()
    if _CREATED:
        db.query(AuditEventDB).filter(
            AuditEventDB.subject_type == approvals.SUBJECT,
            AuditEventDB.subject_id.in_(_CREATED),
        ).delete(synchronize_session=False)
        # By verb, not by id: `detail` is a JSON column (not JSONB), so it has
        # no `.astext` to filter on — and "marker.written" is written by the
        # planted action in this file and by nothing else, so the verb IS the
        # scope.
        db.query(AuditEventDB).filter(
            AuditEventDB.action == "marker.written"
        ).delete(synchronize_session=False)
        db.query(PendingActionDB).filter(
            PendingActionDB.id.in_(_CREATED)
        ).delete(synchronize_session=False)
        _CREATED.clear()
    db.commit()


def _request(db, payload, **kwargs):
    row = _remember(approvals.request_approval(
        db, ACTION_KEY, payload=payload, summary="a marker",
        requested_by_type=ACTOR_USER, requested_by_id=None,
        brand_id=kwargs.pop("brand_id", 1),
        subject_id=kwargs.pop("subject_id", None) or int(uuid.uuid4().int % 10**8),
        **kwargs,
    ))
    return row


def _remember(row):
    _CREATED.append(row.id)
    return row


class TestTheRegistry:

    def test_a_planted_action_is_discovered(self):
        assert ACTION_KEY in [a.key for a in action_registry.list_actions()]

    def test_base_and_registry_are_not_actions(self):
        keys = [a.key for a in action_registry.list_actions()]
        assert "base" not in keys and "registry" not in keys

    def test_a_declaration_without_execute_is_refused(self):
        """An action that cannot run is worse than one that does not exist: it
        would accept requests, fill the inbox, and fail at the moment somebody
        approves it."""
        package = Path(action_registry.__file__).parent
        broken = package / f"{TAG}_broken.py"
        broken.write_text(
            "from app.approvals.actions.base import ApprovableAction\n"
            f"META = ApprovableAction(key='{BROKEN_KEY}', label='No execute',\n"
            "                        approve_permission='view',\n"
            "                        default_ttl_seconds=60)\n"
        )
        try:
            action_registry._registry_mtime = None
            assert BROKEN_KEY not in [a.key for a in action_registry.list_actions()]
            assert ACTION_KEY in [a.key for a in action_registry.list_actions()], (
                "one unusable file must not take the registry down"
            )
        finally:
            broken.unlink(missing_ok=True)
            action_registry._registry_mtime = None


class TestTheLifecycle:

    def test_request_holds_the_action_and_runs_nothing(self, db, planted_action):
        row = _request(db, planted_action)

        assert row.status == PENDING
        assert row.subject_type == "marker", "taken from the declaration, not the caller"
        assert row.expires_at is not None
        assert not Path(planted_action["path"]).exists(), (
            "requesting must not execute — the whole point is that it is held"
        )

    def test_approving_executes_it(self, db, planted_action):
        row = _request(db, {**planted_action, "text": "ran"})

        result = approvals.approve(
            db, row.id, approver_type=ACTOR_USER, approver_id=None,
        )

        assert result.ok, result.message
        assert Path(planted_action["path"]).read_text() == "ran"
        db.refresh(row)
        assert row.status == APPROVED
        assert row.decided_at is not None

    def test_rejecting_does_not(self, db, planted_action):
        row = _request(db, planted_action)

        assert approvals.reject(
            db, row.id, approver_type=ACTOR_USER, approver_id=None, reason="no",
        )
        db.refresh(row)
        assert row.status == REJECTED
        assert row.decision_reason == "no"
        assert not Path(planted_action["path"]).exists()

    def test_a_decided_request_cannot_be_decided_again(self, db, planted_action):
        row = _request(db, planted_action)
        approvals.approve(db, row.id, approver_type=ACTOR_USER, approver_id=None)

        again = approvals.approve(db, row.id, approver_type=ACTOR_USER, approver_id=None)

        assert not again.ok
        assert Path(planted_action["path"]).read_text() == "x", (
            "the action appends, so a second execution would be visible"
        )

    def test_an_exploding_action_is_failed_not_rejected(self, db, planted_action):
        """"A human said no" and "the run blew up" are different facts."""
        row = _request(db, {**planted_action, "explode": True})

        result = approvals.approve(db, row.id, approver_type=ACTOR_USER, approver_id=None)

        assert not result.ok
        db.refresh(row)
        assert row.status == FAILED
        assert row.status != REJECTED
        assert "blew up" in (row.execution_error or "")

    def test_an_action_that_declines_is_also_failed(self, db, planted_action):
        row = _request(db, {**planted_action, "decline": True})

        approvals.approve(db, row.id, approver_type=ACTOR_USER, approver_id=None)

        db.refresh(row)
        assert row.status == FAILED, "nobody said no — the action refused itself"


class TestExpiry:
    """`expires_at` is authoritative; `status` is a cache. Two guards, and they
    are tested in both directions because a single test with an `or` in its
    assertion would pass with either one removed."""

    def test_a_pending_row_past_its_deadline_cannot_be_approved(
        self, db, planted_action
    ):
        row = _request(db, planted_action)
        row.expires_at = approvals.now() - timedelta(minutes=1)
        db.commit()

        result = approvals.approve(db, row.id, approver_type=ACTOR_USER, approver_id=None)

        assert not result.ok and "expired" in (result.message or "")
        assert not Path(planted_action["path"]).exists()

    def test_an_expired_row_with_a_future_deadline_cannot_be_approved(
        self, db, planted_action
    ):
        """The other direction: the column says expired, the clock disagrees."""
        row = _request(db, planted_action)
        row.status = EXPIRED
        row.decided_at = approvals.now()
        db.commit()

        result = approvals.approve(db, row.id, approver_type=ACTOR_USER, approver_id=None)

        assert not result.ok
        assert not Path(planted_action["path"]).exists()

    def test_the_sweep_retires_what_is_due_and_executes_nothing(
        self, db, planted_action
    ):
        row = _request(db, planted_action)
        row.expires_at = approvals.now() - timedelta(minutes=1)
        db.commit()

        expired = approvals.expire_due_pending_actions(db)

        assert row.id in expired
        db.refresh(row)
        assert row.status == EXPIRED
        assert row.decided_by_type is None, "nobody decided an expiry"
        assert not Path(planted_action["path"]).exists()

    def test_the_sweep_is_idempotent(self, db, planted_action):
        row = _request(db, planted_action)
        row.expires_at = approvals.now() - timedelta(minutes=1)
        db.commit()

        approvals.expire_due_pending_actions(db)
        assert approvals.expire_due_pending_actions(db) == []

    def test_the_list_reads_the_clock_not_the_column(self, db, planted_action):
        """No sweeper is scheduled, so a row can sit at `pending` with a dead
        deadline. The inbox must agree with what `approve()` would do."""
        row = _request(db, planted_action)
        row.expires_at = approvals.now() - timedelta(minutes=1)
        db.commit()

        assert row.status == PENDING
        assert approvals.effective_status(row) == EXPIRED
        assert row.id not in [r.id for r in approvals.list_for_brand(db, 1, PENDING)]


class TestOneOpenRequestPerSubject:
    """Both guards exist and each is tested alone, because either one would make
    the other's test pass."""

    def test_the_service_refuses_a_duplicate(self, db, planted_action):
        subject_id = int(uuid.uuid4().int % 10**8)
        _request(db, planted_action, subject_id=subject_id)

        with pytest.raises(approvals.DuplicateRequest):
            _request(db, planted_action, subject_id=subject_id)

    def test_the_database_refuses_it_too(self, db, planted_action):
        """Straight past the service, the way a second process would arrive."""
        subject_id = int(uuid.uuid4().int % 10**8)
        first = _request(db, planted_action, subject_id=subject_id)

        db.add(PendingActionDB(
            action_key=first.action_key, payload={}, summary="duplicate",
            requested_by_type=ACTOR_USER, subject_type="marker",
            subject_id=subject_id, brand_id=1, status=PENDING,
            expires_at=approvals.now() + timedelta(hours=1),
        ))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_a_decided_request_frees_the_subject(self, db, planted_action):
        """The index is partial — `WHERE status = 'pending'` — so a rejected
        request must not block the next one."""
        subject_id = int(uuid.uuid4().int % 10**8)
        first = _request(db, planted_action, subject_id=subject_id)
        approvals.reject(db, first.id, approver_type=ACTOR_USER, approver_id=None)

        second = _request(db, planted_action, subject_id=subject_id)
        assert second.id != first.id


class TestTheAuditRelationship:

    def test_every_step_writes_an_entry(self, db, planted_action):
        row = _request(db, planted_action)
        approvals.approve(
            db, row.id, approver_type=ACTOR_USER, approver_id=None, reason="fine",
        )

        actions = [e.action for e in events_for_subject(db, approvals.SUBJECT, row.id)]
        assert approvals.REQUESTED in actions
        assert approvals.GRANTED in actions

    def test_the_actions_own_event_is_attributed_to_the_approver(
        self, db, planted_action
    ):
        """ADR-140 §5's "approver-if-gated" lands as the ACTOR of the domain
        event, not as a column on a domain table."""
        row = _request(db, planted_action)
        approvals.approve(db, row.id, approver_type=ACTOR_USER, approver_id=4242)

        written = db.query(AuditEventDB).filter(
            AuditEventDB.action == "marker.written"
        ).all()
        assert written, "the action declared an audit_action and it was not recorded"
        assert written[-1].actor_id == 4242
        assert written[-1].detail.get("pending_action_id") == row.id

    def test_an_expiry_is_attributed_to_the_system(self, db, planted_action):
        row = _request(db, planted_action)
        row.expires_at = approvals.now() - timedelta(minutes=1)
        db.commit()
        approvals.expire_due_pending_actions(db)

        lapsed = [
            e for e in events_for_subject(db, approvals.SUBJECT, row.id)
            if e.action == approvals.LAPSED
        ]
        assert len(lapsed) == 1
        assert lapsed[0].actor_type == approvals.ACTOR_SYSTEM
        assert lapsed[0].actor_id is None

    def test_the_payload_never_reaches_the_audit_log(self, db, planted_action):
        """ADR-153 §5 binds what may be written into an entry, and a payload is
        an open dict whose shape an action author controls. Audit points at the
        pending row; the pending row holds the arguments."""
        row = _request(db, {**planted_action, "secret_ish": "do-not-log-me"})

        for event in events_for_subject(db, approvals.SUBJECT, row.id):
            assert "do-not-log-me" not in str(event.detail)

    def test_deleting_every_pending_row_loses_no_accountability(
        self, db, planted_action
    ):
        """**The one that keeps `status` a cache rather than a fact.**

        ADR-142 §4: the action history "extends the ADR-140 audit surface; it is
        not a second log." If this table were the record, dropping it would
        destroy the answer to "who approved that send".
        """
        row = _request(db, planted_action)
        approvals.approve(
            db, row.id, approver_type=ACTOR_USER, approver_id=99, reason="why not",
        )
        pending_id = row.id

        db.query(PendingActionDB).filter(PendingActionDB.id == pending_id).delete()
        db.commit()

        history = events_for_subject(db, approvals.SUBJECT, pending_id)
        actions = [e.action for e in history]
        assert approvals.REQUESTED in actions and approvals.GRANTED in actions
        granted = next(e for e in history if e.action == approvals.GRANTED)
        assert granted.actor_id == 99
        assert granted.detail.get("reason") == "why not"


class TestTheSendAction:
    """`send.fire_send_instance` — the first real action (ADR-166 point 5).

    Shipped ahead of its caller: nothing raises a request for it yet, because
    turning `ApprovalRequired` from a refusal into a queue means reordering
    permission checks, which does not belong in the same commit as a new file.
    So these tests drive it directly, the way the seed script and the inbox do.
    """

    def test_it_is_registered(self):
        from app.approvals.actions.registry import get_action

        meta = get_action("send.fire_send_instance")
        assert meta is not None
        assert meta.approve_permission == "sends.execute"
        assert meta.subject_type == "send_instance"
        assert meta.default_ttl_seconds > 0, "ADR-142 §4: pending actions expire"

    def test_describing_a_vanished_send_warns_instead_of_raising(self, db):
        """A request whose subject was deleted must still be rejectable.

        Raising here would make the detail page unreachable, leaving the row
        stuck: not approvable, and not refusable either.
        """
        from app.approvals.actions import send_fire

        description = send_fire.describe(db, {"send_instance_id": 99999999})

        assert description.warnings
        assert "deleted" in " ".join(description.warnings).lower()

    def test_executing_without_a_send_id_declines_rather_than_crashing(self, db):
        from app.approvals.actions import send_fire

        result = send_fire.execute(db, {})

        assert not result.ok
        assert "names no send" in (result.message or "")

    def test_an_already_sent_instance_is_declined_not_raised(self, db):
        """`send_send_instance` refuses a sent instance with a ValueError.

        Caught and reported, because the approver did nothing wrong — the row
        should read `failed` with a readable reason, not blow up the request.
        """
        from app.approvals.actions import send_fire
        from app.delivery.db_models import SendInstanceDB

        sent = db.query(SendInstanceDB).filter(
            SendInstanceDB.status == "sent"
        ).first()
        if sent is None:
            pytest.skip("no sent send instance in this database")

        result = send_fire.execute(db, {"send_instance_id": sent.id})

        assert not result.ok
        assert "already" in (result.message or "").lower()

    def test_the_summary_survives_its_subject(self, db):
        """What gets frozen onto the row. It has to read after the send is gone,
        which is why it is a string and not a join."""
        from app.approvals.actions import send_fire

        assert "no longer present" in send_fire.summarise(db, 99999999)
