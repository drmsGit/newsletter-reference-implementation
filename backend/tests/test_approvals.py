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

from app.auth.service import ensure_default_brand
from app.approvals import service as approvals
from app.approvals.actions import registry as action_registry
from app.approvals.db_models import (
    APPROVED, EXECUTING, EXPIRED, FAILED, PENDING, REJECTED, PendingActionDB,
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
        "                        requester_may_decide=True,\n"
        "                        subject_type='marker')\n"
        "\n"
        "def describe(db, payload, *, brand_id=None):\n"
        "    return ActionDescription(summary='writes a marker file',\n"
        "                             rows=[('Path', payload.get('path', ''))])\n"
        "\n"
        "def execute(db, payload, *, choice=None, brand_id=None):\n"
        "    if payload.get('explode'):\n"
        "        raise RuntimeError('the action blew up')\n"
        "    if payload.get('decline'):\n"
        "        return ActionResult(ok=False, message='the action declined')\n"
        "    if payload.get('gate'):\n"
        "        # What send_send_instance does: commit mid-action, ending any\n"
        "        # transaction the caller was holding a lock in. Then say we are\n"
        "        # inside and wait, so a second approver can arrive in the window.\n"
        "        import time\n"
        "        db.commit()\n"
        "        gate = Path(payload['gate'])\n"
        "        with Path(str(gate) + '.entered').open('a') as handle:\n"
        "            handle.write('1')\n"
        "        for _ in range(200):\n"
        "            if gate.exists():\n"
        "                break\n"
        "            time.sleep(0.05)\n"
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
            "                        default_ttl_seconds=60,\n"
            "                        requester_may_decide=True)\n"
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

    def test_describing_a_vanished_send_blocks_instead_of_raising(self, db):
        """A request whose subject was deleted must still be rejectable.

        Raising here would make the detail page unreachable, leaving the row
        stuck: not approvable, and not refusable either.
        """
        from app.approvals.actions import send_fire

        description = send_fire.describe(db, {"send_instance_id": 99999999}, brand_id=ensure_default_brand(db).id)

        assert description.blocked_reason
        assert "deleted" in description.blocked_reason.lower()

    def test_an_already_sent_send_is_blocked_not_merely_warned_about(self, db):
        """The distinction that cost a real click.

        A warning says "think about this" and must not block. This says
        "approving will be refused" — and the first version of the contract had
        only warnings, so the detail page cautioned the reviewer and then handed
        them the button anyway.
        """
        from app.approvals.actions import send_fire
        from app.delivery.db_models import SendInstanceDB

        sent = db.query(SendInstanceDB).filter(
            SendInstanceDB.status == "sent"
        ).first()
        if sent is None:
            pytest.skip("no sent send instance in this database")

        description = send_fire.describe(db, {"send_instance_id": sent.id}, brand_id=ensure_default_brand(db).id)

        assert description.blocked_reason, "already sent must block, not warn"
        assert "already sent" in description.blocked_reason.lower()

    def test_a_draft_send_is_not_blocked(self, db):
        """The other direction, so `blocked_reason` cannot just always be set."""
        from app.approvals.actions import send_fire
        from app.delivery.db_models import SendInstanceDB

        from app.rendering.service import missing_required_fields
        from app.snapshots.db_models import SnapshotDB

        # **A draft whose variant is complete.** `describe()` now also blocks on
        # a missing required field (ADR-174 point 3), and most drafts in a dev
        # database are unfinished — so "the first draft" would fail this test
        # for the very reason the test is not about, and the assertion would
        # read as "blocked_reason is always set" when it is not.
        draft = None
        for candidate in db.query(SendInstanceDB).filter(
            SendInstanceDB.status == "draft"
        ).limit(50).all():
            snapshot = db.query(SnapshotDB).filter(
                SnapshotDB.id == candidate.snapshot_id
            ).first()
            if snapshot and not missing_required_fields(db, snapshot.variant_id):
                draft = candidate
                break
        if draft is None:
            # Build one rather than skip: skipping would delete the only guard
            # that `blocked_reason` is not always set, which is the whole point
            # of the test. A variant with no modules declares no required
            # fields, so it passes the gate without a module or storage path.
            from app.campaigns.db_models import CampaignDB, VariantDB

            brand = ensure_default_brand(db)
            campaign = CampaignDB(brand_id=brand.id, name=f"draft-{uuid.uuid4()}")
            db.add(campaign); db.flush()
            variant = VariantDB(
                campaign_id=campaign.id, channel="email",
                name="not-blocked fixture", status="draft",
            )
            db.add(variant); db.flush()
            from app.rendering.frame import build_frame

            # A frame (ADR-183): a frameless snapshot is blocked, correctly.
            snapshot = SnapshotDB(
                variant_id=variant.id,
                render_context=build_frame(db, variant.id),
            )
            db.add(snapshot); db.flush()
            draft = SendInstanceDB(
                snapshot_id=snapshot.id, brand_id=brand.id,
                name=f"not-blocked-{uuid.uuid4()}", status="draft", provider="mock",
            )
            db.add(draft); db.flush()

        assert send_fire.describe(db, {"send_instance_id": draft.id}, brand_id=ensure_default_brand(db).id).blocked_reason is None

    def test_executing_without_a_send_id_declines_rather_than_crashing(self, db):
        from app.approvals.actions import send_fire
        from app.auth.service import ensure_default_brand

        result = send_fire.execute(db, {}, brand_id=ensure_default_brand(db).id)

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

        result = send_fire.execute(
            db, {"send_instance_id": sent.id}, brand_id=sent.brand_id,
        )

        assert not result.ok
        assert "already" in (result.message or "").lower()

    def test_the_summary_survives_its_subject(self, db):
        """What gets frozen onto the row. It has to read after the send is gone,
        which is why it is a string and not a join."""
        from app.approvals.actions import send_fire

        assert "no longer present" in send_fire.summarise(
            db, 99999999, brand_id=ensure_default_brand(db).id)


class TestRunOnce:
    """ADR-142 addendum 2026-09-29 (task-4): a held action runs once.

    The old guard was a row lock held across `module.execute` — and released
    by the first commit the action made, because the action runs on the same
    session. `send_send_instance` commits inside itself, so the lock let go
    while the row still read `pending`, and a second approver could claim it and
    run it again. Nothing in the suite noticed, because the send action's own
    status guard stopped the second run — the masking the lock's docstring
    named as the reason the lock existed.

    The planted action here commits mid-run exactly as the send does, then
    waits, so the second approver arrives in precisely that window. And it
    APPENDS, so a second run is visible rather than absorbed.
    """

    def test_a_second_approver_cannot_run_an_action_that_committed_mid_run(
        self, planted_action, tmp_path
    ):
        import threading
        import time

        gate = tmp_path / "release"
        entered = Path(str(gate) + ".entered")
        marker = Path(planted_action["path"])

        with SessionLocal() as setup:
            row = _request(setup, {**planted_action, "gate": str(gate)})
        results = {}

        def approve_as(name):
            with SessionLocal() as session:
                results[name] = approvals.approve(
                    session, row.id, approver_type=ACTOR_USER, approver_id=None,
                )

        first = threading.Thread(target=approve_as, args=("first",))
        first.start()
        for _ in range(200):
            if entered.exists():
                break
            time.sleep(0.05)
        assert entered.exists(), "the first approval never reached the action"

        # The first run has committed and is waiting inside the action. Under
        # the lock this is where the guard had already let go.
        second = threading.Thread(target=approve_as, args=("second",))
        second.start()
        second.join(timeout=3)
        gate.write_text("go")
        first.join(timeout=15)
        second.join(timeout=15)

        assert results["first"].ok, results["first"].message
        assert not results["second"].ok
        assert "executing" in results["second"].message, results["second"].message
        assert entered.read_text() == "1", "the action was entered twice"
        assert marker.read_text() == "x", (
            f"the action ran {len(marker.read_text())} times — two approvers both "
            "executed a request whose action commits mid-run"
        )
        with SessionLocal() as check:
            assert check.get(PendingActionDB, row.id).status == APPROVED

    def test_a_request_whose_action_is_gone_stays_pending(self, db, planted_action):
        """Looked up before the claim, so it is not stranded in `executing` by a
        lookup that was always going to fail — `executing` is sticky by design,
        so getting there by accident would be permanent."""
        row = _request(db, planted_action)
        db.query(PendingActionDB).filter(PendingActionDB.id == row.id).update(
            {"action_key": "apprtest.never_registered"}, synchronize_session=False)
        db.commit()

        result = approvals.approve(db, row.id, approver_type=ACTOR_USER, approver_id=None)

        assert not result.ok
        db.expire_all()
        assert db.get(PendingActionDB, row.id).status == PENDING

    def test_an_executing_request_still_occupies_its_subject(self, db, planted_action):
        """The partial unique index covers both open states. Otherwise a second
        held request could be created for a thing whose approved action is
        running right now."""
        row = _request(db, planted_action, subject_id=424242)
        db.query(PendingActionDB).filter(PendingActionDB.id == row.id).update(
            {"status": EXECUTING, "decided_at": approvals.now()},
            synchronize_session=False)
        db.commit()

        with pytest.raises(approvals.DuplicateRequest):
            _request(db, planted_action, subject_id=424242)


class TestExpiryCannotOverwriteADecision:
    """task-13. A sweep reads its due rows, and time passes before it writes.

    `_mark_expired` used to set the status on the ORM object it was handed and
    commit, so a request decided in between was recorded as lapsed — approved,
    executed, mailed, and filed as expired. The stale object is the sweep's
    own: `expire_due_pending_actions` reads every due row first and expires
    them one by one, so these tests hand `_expire` a row read before the
    decision, which is exactly what the sweep does.
    """

    def _due(self, db, planted_action):
        row = _request(db, planted_action)
        db.query(PendingActionDB).filter(PendingActionDB.id == row.id).update(
            {"expires_at": approvals.now() - timedelta(minutes=1)},
            synchronize_session=False)
        db.commit()
        return row

    def test_a_sweep_holding_a_stale_row_does_not_expire_a_rejected_request(
        self, db, planted_action
    ):
        row = self._due(db, planted_action)
        with SessionLocal() as sweep:
            stale = sweep.get(PendingActionDB, row.id)   # read: pending, due
            with SessionLocal() as person:
                assert approvals.reject(
                    person, row.id, approver_type=ACTOR_USER, approver_id=None)

            assert approvals._expire(sweep, stale) is False

        db.expire_all()
        assert db.get(PendingActionDB, row.id).status == REJECTED, (
            "the sweep wrote 'expired' over a decision made after it read the row"
        )
        lapsed = [e for e in events_for_subject(db, approvals.SUBJECT, row.id)
                  if e.action == approvals.LAPSED]
        assert lapsed == []

    def test_two_sweeps_emit_one_expiry(self, db, planted_action):
        row = self._due(db, planted_action)
        with SessionLocal() as one, SessionLocal() as two:
            first, second = one.get(PendingActionDB, row.id), two.get(PendingActionDB, row.id)
            outcomes = [approvals._expire(one, first), approvals._expire(two, second)]

        assert sorted(outcomes) == [False, True]
        lapsed = [e for e in events_for_subject(db, approvals.SUBJECT, row.id)
                  if e.action == approvals.LAPSED]
        assert len(lapsed) == 1, f"{len(lapsed)} approval.expired events for one request"


class TestEveryHeldRequestNamesItsSubject:
    """task-15, ADR-142 addendum of 2026-09-29 (third).

    The one-open-request index is keyed on (action_key, subject_type,
    subject_id) and Postgres treats NULLs as distinct in a unique index — so a
    request with no subject escapes it, and two identical ones can both sit
    open. Two roads led there, and both are closed where rows are created.
    """

    @pytest.fixture
    def subjectless_action(self):
        """A planted action that declares no subject — the dataclass default,
        so this is what forgetting looks like."""
        package = Path(action_registry.__file__).parent
        planted = package / f"{TAG}_nosubject.py"
        planted.write_text(
            "from app.approvals.actions.base import ApprovableAction, "
            "ActionDescription, ActionResult\n"
            "META = ApprovableAction(key='apprtest.no_subject', label='No subject',\n"
            "                        approve_permission='sends.execute',\n"
            "                        default_ttl_seconds=3600,\n"
            "                        requester_may_decide=True)\n"
            "def describe(db, payload, *, brand_id=None):\n"
            "    return ActionDescription(summary='nothing', rows=[])\n"
            "def execute(db, payload, *, choice=None, brand_id=None):\n"
            "    return ActionResult(ok=True)\n"
        )
        action_registry._registry_mtime = None
        try:
            yield "apprtest.no_subject"
        finally:
            planted.unlink(missing_ok=True)
            action_registry._registry_mtime = None

    def test_an_action_declaring_no_subject_cannot_be_held(self, db, subjectless_action):
        before = db.query(PendingActionDB).filter(
            PendingActionDB.action_key == subjectless_action).count()

        with pytest.raises(approvals.SubjectRequired, match="declares no subject"):
            approvals.request_approval(
                db, subjectless_action, payload={}, summary="x",
                requested_by_type=ACTOR_USER, brand_id=1,
            )
        db.rollback()

        assert db.query(PendingActionDB).filter(
            PendingActionDB.action_key == subjectless_action).count() == before

    def test_an_action_with_a_subject_type_but_no_id_cannot_be_held(self, db, planted_action):
        """The road the index entry did not name: the guard lifts the id from
        the path by the `<subject_type>_id` convention, so a route whose
        parameter is named otherwise produced a NULL id for an action that does
        declare a subject."""
        with pytest.raises(approvals.SubjectRequired, match="names no marker"):
            approvals.request_approval(
                db, ACTION_KEY, payload=planted_action, summary="x",
                requested_by_type=ACTOR_USER, brand_id=1, subject_id=None,
            )
        db.rollback()

    def test_the_guard_answers_the_refusal_with_403_not_500(self, monkeypatch):
        """Nothing caught `NotApprovable` before, so from the guard this would
        have surfaced as a server error rather than a refusal."""
        from tests.machine import machine
        from tests.test_api_guard import client
        from app.auth.permissions import SENDS_EXECUTE, VIEW

        refused = []

        def refuse(*args, **kwargs):
            refused.append(True)
            raise approvals.SubjectRequired("no subject")

        # Past task-9's brand check, which would otherwise answer 409 for a send
        # that does not exist and never reach the refusal under test. Patched on
        # the module the REGISTRY returns: this file's autouse fixture makes the
        # registry rediscover its actions, which loads fresh module objects, so
        # patching `app.approvals.actions.send_fire` would miss the handler's.
        live = action_registry.get_action_module("send.fire_send_instance")
        monkeypatch.setattr(live, "subject_in_brand", lambda *a, **k: True)
        monkeypatch.setattr(approvals, "request_approval", refuse)
        with machine([VIEW, SENDS_EXECUTE]) as headers:
            response = client.post("/delivery/send-instances/999999999/send", headers=headers)

        assert refused, "the request never reached request_approval — this tests nothing"
        assert response.status_code == 403, response.text


AGELESS_KEY = "apprtest.ageless"
FORGETFUL_KEY = "apprtest.forgetful"


@pytest.fixture
def ageless_action(planted_action):
    """An action type that declares no deadline (task-210; ADR-142 §4,
    addendum 2026-09-24): "is this copy good" does not go stale."""
    package = Path(action_registry.__file__).parent
    path = package / f"{TAG}_ageless.py"
    path.write_text(
        "from app.approvals.actions.base import ApprovableAction, ActionDescription, ActionResult\n"
        f"META = ApprovableAction(key='{AGELESS_KEY}', label='Never stale',\n"
        "                        approve_permission='sends.execute',\n"
        "                        default_ttl_seconds=None,\n"
        "                        requester_may_decide=True,\n"
        "                        subject_type='marker')\n"
        "def describe(db, payload, *, brand_id=None):\n"
        "    return ActionDescription(summary='never stale', rows=[])\n"
        "def execute(db, payload, *, choice=None, brand_id=None):\n"
        "    return ActionResult(ok=True)\n"
    )
    action_registry._registry_mtime = None
    try:
        yield
    finally:
        path.unlink(missing_ok=True)
        action_registry._registry_mtime = None


def _ageless(db):
    return _remember(approvals.request_approval(
        db, AGELESS_KEY, payload={}, summary="never stale", requested_by_type=ACTOR_USER,
        requested_by_id=None, brand_id=1, subject_id=int(uuid.uuid4().int % 10**8)))


class TestAnActionWithNoDeadline:
    """A held action whose type declares no deadline never expires: every reader
    takes an empty deadline as "never", not as "already" (ADR-142 addendum)."""

    def test_it_is_held_with_no_deadline_and_reads_as_pending(self, db, ageless_action):
        row = _ageless(db)
        db.refresh(row)
        assert row.expires_at is None
        assert approvals.effective_status(row, at=approvals.now() + timedelta(days=3650)) == PENDING

    def test_it_is_in_the_inbox_and_the_badge(self, db, ageless_action):
        row = _ageless(db)
        assert row.id in [r.id for r in approvals.list_for_brand(db, 1, PENDING)]
        before = approvals.pending_count(db, 1)
        other = _ageless(db)
        assert approvals.pending_count(db, 1) == before + 1, "the badge counts it"
        assert other.id in [r.id for r in approvals.list_for_brand(db, 1, PENDING)]

    def test_the_sweep_never_retires_it(self, db, ageless_action):
        row = _ageless(db)
        assert row.id not in approvals.expire_due_pending_actions(db)
        db.refresh(row)
        assert row.status == PENDING

    def test_it_can_be_approved_whenever_somebody_gets_to_it(self, db, ageless_action):
        row = _ageless(db)
        result = approvals.approve(db, row.id, approver_type=ACTOR_USER, approver_id=None)
        assert result.ok, result.message

    def test_the_route_says_it_has_none(self, db, ageless_action):
        from app.approvals.router import _row  # what the inbox route answers with

        assert _row(_ageless(db)).expires_at is None

    def test_a_declaration_that_says_nothing_about_a_deadline_is_still_refused(self, ageless_action):
        """No deadline is a declaration, never an omission: a forgetful module
        must not mint an immortal request."""
        package = Path(action_registry.__file__).parent
        forgetful = package / f"{TAG}_forgetful.py"
        forgetful.write_text(
            "from app.approvals.actions.base import ApprovableAction\n"
            f"META = ApprovableAction(key='{FORGETFUL_KEY}', label='Forgot',\n"
            "                        approve_permission='view',\n"
            "                        requester_may_decide=True)\n"
            "def describe(db, payload, *, brand_id=None): pass\n"
            "def execute(db, payload, *, choice=None, brand_id=None): pass\n"
        )
        try:
            action_registry._registry_mtime = None
            keys = [a.key for a in action_registry.list_actions()]
            assert FORGETFUL_KEY not in keys
            assert AGELESS_KEY in keys
        finally:
            forgetful.unlink(missing_ok=True)
            action_registry._registry_mtime = None
