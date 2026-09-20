"""The approval inbox — ADR-142 §4, stage 2.

**The most valuable test here is `test_a_user_without_the_actions_permission_
cannot_decide`.** The policy table maps `/ui/approvals` to `view`, which looks
like the screen is barely guarded — and it is, on purpose: seeing that a send is
waiting is operational visibility, and *deciding* is answered per row against
the permission the action declares. That arrangement is only safe if the
row-level check actually refuses, so it needs a test that asserts the action did
not run, not merely that the response was a refusal.

Runs against the shared dev database like the rest of the suite, and removes
everything it creates — including its audit rows, which have no foreign keys.
"""
import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.approvals import service as approvals
from app.approvals.actions import registry as action_registry
from app.approvals.db_models import APPROVED, PENDING, REJECTED, PendingActionDB
from app.audit.db_models import AuditEventDB
from app.audit.service import ACTOR_USER
from app.auth import service as auth
from app.database import SessionLocal
from main import app

TAG = "apprui"
ACTION_KEY = "apprui.write_marker"
_CREATED: list[int] = []


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def planted_action(tmp_path):
    package = Path(action_registry.__file__).parent
    planted = package / f"{TAG}_marker.py"
    planted.write_text(
        "from app.approvals.actions.base import ApprovableAction, "
        "ActionDescription, ActionResult\n"
        "from pathlib import Path\n"
        "\n"
        f"META = ApprovableAction(key='{ACTION_KEY}', label='Write a marker',\n"
        "                        approve_permission='sends.execute',\n"
        "                        default_ttl_seconds=3600,\n"
        "                        subject_type='marker')\n"
        "\n"
        "def describe(db, payload, *, brand_id=None):\n"
        "    if payload.get('describe_explodes'):\n"
        "        raise RuntimeError('cannot describe this')\n"
        "    return ActionDescription(summary='writes a marker file',\n"
        "                             rows=[('Path', payload.get('path', ''))])\n"
        "\n"
        "def execute(db, payload, *, choice=None, brand_id=None):\n"
        "    path = Path(payload['path'])\n"
        "    with path.open('a') as handle:\n"
        "        handle.write('ran')\n"
        "    return ActionResult(ok=True)\n"
    )
    action_registry._registry_mtime = None
    try:
        yield {"path": str(tmp_path / "marker.txt")}
    finally:
        planted.unlink(missing_ok=True)
        action_registry._registry_mtime = None


@pytest.fixture(autouse=True)
def _sweep(db):
    yield
    db.rollback()
    if _CREATED:
        db.query(AuditEventDB).filter(
            AuditEventDB.subject_type == approvals.SUBJECT,
            AuditEventDB.subject_id.in_(_CREATED),
        ).delete(synchronize_session=False)
        db.query(PendingActionDB).filter(
            PendingActionDB.id.in_(_CREATED)
        ).delete(synchronize_session=False)
        _CREATED.clear()
    for table in ("login_codes", "auth_sessions", "role_assignments"):
        db.execute(text(
            f"DELETE FROM {table} WHERE user_id IN "
            "(SELECT id FROM users WHERE email LIKE :p)"), {"p": f"{TAG}-%"})
    db.execute(text("DELETE FROM users WHERE email LIKE :p"), {"p": f"{TAG}-%"})
    db.commit()


def _signed_in(db, role_key):
    user = auth.create_user(
        db, email=f"{TAG}-{uuid.uuid4().hex[:8]}@example.invalid", role_key=role_key,
    )
    token = auth.create_session(db, user)
    client = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
    client.cookies.set(auth.SESSION_COOKIE, token)
    return client, user


def _csrf(client):
    import re

    match = re.search(r'name="csrf_token" value="([^"]+)"',
                      client.get("/ui/approvals").text)
    return match.group(1) if match else ""


def _held(db, payload, brand_id=None):
    row = approvals.request_approval(
        db, ACTION_KEY, payload=payload, summary="a held marker",
        requested_by_type="integration", requested_by_id=7,
        brand_id=brand_id or auth.ensure_default_brand(db).id,
        subject_id=int(uuid.uuid4().int % 10**8),
    )
    _CREATED.append(row.id)
    return row


class TestTheScreen:

    def test_a_waiting_request_is_listed(self, db, planted_action):
        row = _held(db, planted_action)
        client, user = _signed_in(db, "admin")

        page = client.get("/ui/approvals").text

        assert "a held marker" in page
        assert f"/ui/approvals/{row.id}" in page

    def test_the_default_filter_hides_decided_requests(self, db, planted_action):
        row = _held(db, planted_action)
        approvals.reject(db, row.id, approver_type=ACTOR_USER, approver_id=None)
        client, user = _signed_in(db, "admin")

        assert "a held marker" not in client.get("/ui/approvals").text
        assert "a held marker" in client.get("/ui/approvals?status=decided").text
        assert "a held marker" in client.get("/ui/approvals?status=all").text

    def test_a_request_past_its_deadline_reads_as_expired_without_a_sweep(
        self, db, planted_action
    ):
        """No sweeper is scheduled, so the screen must read the clock rather
        than the column — otherwise the inbox offers an Approve button for
        something `approve()` would refuse."""
        row = _held(db, planted_action)
        row.expires_at = approvals.now() - timedelta(minutes=1)
        db.commit()
        client, user = _signed_in(db, "admin")

        assert row.status == PENDING, "the column has deliberately not caught up"
        assert "a held marker" not in client.get("/ui/approvals").text
        assert "Expired" in client.get("/ui/approvals?status=all").text

    def test_the_detail_page_shows_live_and_frozen_side_by_side(
        self, db, planted_action
    ):
        row = _held(db, planted_action)
        client, user = _signed_in(db, "admin")

        page = client.get(f"/ui/approvals/{row.id}").text

        assert "writes a marker file" in page, "describe() runs live"
        assert "a held marker" in page, "the frozen summary is kept"
        assert "approval.requested" in page, "the audit trail is the history"

    def test_a_description_that_raises_does_not_hide_the_request(
        self, db, planted_action
    ):
        """A reviewer still needs to see that something is waiting, and still
        needs to be able to reject it."""
        row = _held(db, {**planted_action, "describe_explodes": True})
        client, user = _signed_in(db, "admin")

        response = client.get(f"/ui/approvals/{row.id}")

        assert response.status_code == 200
        assert "cannot describe this" in response.text


class TestWhoMayDecide:

    def test_an_admin_may(self, db, planted_action):
        row = _held(db, planted_action)
        client, user = _signed_in(db, "admin")

        response = client.post(f"/ui/approvals/{row.id}/approve",
                               data={"csrf_token": _csrf(client)})

        assert response.status_code == 303
        db.refresh(row)
        assert row.status == APPROVED
        assert Path(planted_action["path"]).read_text() == "ran"

    def test_a_user_without_the_actions_permission_cannot_decide(
        self, db, planted_action
    ):
        """**The test the whole arrangement rests on.**

        The policy table lets any signed-in user reach this route, because the
        permission depends on which row was clicked. So the row-level check is
        the only thing standing between a Viewer and a real send — and asserting
        the 303 alone would pass even if the action had already run.
        """
        row = _held(db, planted_action)
        client, user = _signed_in(db, "viewer")

        response = client.post(f"/ui/approvals/{row.id}/approve",
                               data={"csrf_token": _csrf(client)})

        assert response.status_code == 303
        assert "sends.execute" in response.headers["location"]
        db.refresh(row)
        assert row.status == PENDING, "still waiting"
        assert not Path(planted_action["path"]).exists(), (
            "the action RAN despite the refusal — the redirect said no and the "
            "code said yes"
        )

    def test_a_viewer_sees_the_screen_but_gets_no_buttons(self, db, planted_action):
        row = _held(db, planted_action)
        client, user = _signed_in(db, "viewer")

        page = client.get("/ui/approvals")

        assert page.status_code == 200, "seeing what is waiting is not a secret"
        assert "not yours to decide" in page.text
        assert f"/ui/approvals/{row.id}/approve" not in page.text

    def test_rejecting_needs_the_same_permission_as_approving(
        self, db, planted_action
    ):
        """Refusing is as much a decision as accepting — a Viewer who can reject
        can cancel a send somebody else queued."""
        row = _held(db, planted_action)
        client, user = _signed_in(db, "viewer")

        client.post(f"/ui/approvals/{row.id}/reject",
                    data={"csrf_token": _csrf(client)})

        db.refresh(row)
        assert row.status == PENDING


class TestBrandIsolation:

    def test_another_brands_request_is_neither_listed_nor_reachable(
        self, db, planted_action
    ):
        """**The user deliberately holds Admin on BOTH brands.**

        The first version of this test signed in an Admin of the default brand
        only, and it passed against a version of `_decide` with brand isolation
        removed — because `_may_decide` refused instead, the user holding no
        grant on the other brand. Two guards, each refusing independently, each
        hiding the other's absence. Granting the role on both brands leaves the
        working-brand filter as the only thing that can say no, which is the
        property this test claims to be about.
        """
        from app.auth.db_models import BrandDB, RoleAssignmentDB, RoleDB

        other = BrandDB(key=f"{TAG}-{uuid.uuid4().hex[:8]}", name="Another brand")
        db.add(other)
        db.commit()
        db.refresh(other)
        try:
            row = _held(db, planted_action, brand_id=other.id)
            client, user = _signed_in(db, "admin")
            admin_role = db.query(RoleDB).filter(RoleDB.key == "admin").first()
            db.add(RoleAssignmentDB(
                user_id=user.id, role_id=admin_role.id, brand_id=other.id,
            ))
            db.commit()

            assert "a held marker" not in client.get("/ui/approvals?status=all").text
            assert client.get(f"/ui/approvals/{row.id}").status_code == 404

            response = client.post(f"/ui/approvals/{row.id}/approve",
                                   data={"csrf_token": _csrf(client)})
            assert response.status_code == 303
            db.refresh(row)
            assert row.status == PENDING, (
                "a request in another brand was decided from this one"
            )
            assert not Path(planted_action["path"]).exists()
        finally:
            # FK order. The grant this test adds on the second brand is what
            # makes the assertion meaningful, and it is also what stops the
            # brand being deleted — so it has to go first, here, rather than in
            # the module sweep which runs afterwards.
            db.rollback()
            db.query(RoleAssignmentDB).filter(
                RoleAssignmentDB.brand_id == other.id
            ).delete(synchronize_session=False)
            db.query(PendingActionDB).filter(
                PendingActionDB.brand_id == other.id
            ).delete(synchronize_session=False)
            db.query(BrandDB).filter(BrandDB.id == other.id).delete()
            db.commit()


class TestRetiringExpiredRequests:
    """ADR-142 §4's bookkeeping half — stage 4.

    **Nothing here is load-bearing, and that is the design.** `approve()`
    refuses an expired request by reading `expires_at`, so a deployment that
    never presses this button is safe; its status column merely lags the clock.
    These tests pin that the button makes the column agree, writes the entry
    §4 asks for, and — the part worth guarding — executes nothing.
    """

    def test_it_retires_what_is_due_and_runs_nothing(self, db, planted_action):
        row = _held(db, planted_action)
        row.expires_at = approvals.now() - timedelta(minutes=1)
        db.commit()
        client, user = _signed_in(db, "admin")

        response = client.post("/ui/approvals/process-expired",
                               data={"csrf_token": _csrf(client)})

        assert response.status_code == 303
        db.refresh(row)
        assert row.status == "expired"
        assert not Path(planted_action["path"]).exists(), (
            "a sweep that sends anything is not a sweep"
        )

    def test_it_writes_a_system_actor_entry(self, db, planted_action):
        """Nobody decided an expiry, so nobody is named as having."""
        from app.audit.service import events_for_subject

        row = _held(db, planted_action)
        row.expires_at = approvals.now() - timedelta(minutes=1)
        db.commit()
        client, user = _signed_in(db, "admin")

        client.post("/ui/approvals/process-expired",
                    data={"csrf_token": _csrf(client)})

        lapsed = [e for e in events_for_subject(db, approvals.SUBJECT, row.id)
                  if e.action == approvals.LAPSED]
        assert len(lapsed) == 1
        assert lapsed[0].actor_type == approvals.ACTOR_SYSTEM
        assert lapsed[0].actor_id is None
        db.refresh(row)
        assert row.decided_by_id is None and row.decided_by_type is None

    def test_it_leaves_a_live_request_alone(self, db, planted_action):
        row = _held(db, planted_action)
        client, user = _signed_in(db, "admin")

        client.post("/ui/approvals/process-expired",
                    data={"csrf_token": _csrf(client)})

        db.refresh(row)
        assert row.status == PENDING

    def test_the_button_is_disabled_when_nothing_is_due(self, db, planted_action):
        _held(db, planted_action)
        client, user = _signed_in(db, "admin")

        page = client.get("/ui/approvals").text

        assert "Retire expired" in page
        assert "disabled" in page.split("Retire expired")[0][-400:], (
            "an enabled button that does nothing invites a pointless click"
        )

    def test_the_button_is_enabled_and_counted_when_something_is(
        self, db, planted_action
    ):
        row = _held(db, planted_action)
        row.expires_at = approvals.now() - timedelta(minutes=1)
        db.commit()
        client, user = _signed_in(db, "admin")

        page = client.get("/ui/approvals").text

        head = page.split("Retire expired")[0][-400:]
        assert "disabled" not in head


class TestCsrf:

    def test_a_decision_without_a_token_is_refused(self, db, planted_action):
        row = _held(db, planted_action)
        client, user = _signed_in(db, "admin")

        response = client.post(f"/ui/approvals/{row.id}/approve")

        assert response.status_code == 403
        db.refresh(row)
        assert row.status == PENDING
        assert not Path(planted_action["path"]).exists()


class TestTheBadge:

    def test_it_counts_only_what_is_still_waiting(self, db, planted_action):
        """Asserted as a DELTA, not an absolute.

        The first version asserted the badge read "1", which was true only while
        the table happened to be empty — seeding four demo requests broke it.
        A count test that depends on how much other data exists is testing the
        database, not the badge.
        """
        import re

        def badge(client):
            match = re.search(
                r'badge bg-warning text-dark">\s*(\d+)',
                client.get("/ui/approvals").text,
            )
            return int(match.group(1)) if match else 0

        client, user = _signed_in(db, "admin")
        before = badge(client)

        row = _held(db, planted_action)
        assert badge(client) == before + 1, "a waiting request must be counted"

        approvals.reject(db, row.id, approver_type=ACTOR_USER, approver_id=None)
        assert badge(client) == before, "a decided request must not be"

    def test_a_request_past_its_deadline_stops_being_counted(
        self, db, planted_action
    ):
        """The badge reads `expires_at`, not `status`, so it drops the moment a
        deadline passes — with or without a sweep having run."""
        import re

        def badge(client):
            match = re.search(
                r'badge bg-warning text-dark">\s*(\d+)',
                client.get("/ui/approvals").text,
            )
            return int(match.group(1)) if match else 0

        client, user = _signed_in(db, "admin")
        before = badge(client)
        row = _held(db, planted_action)
        assert badge(client) == before + 1

        row.expires_at = approvals.now() - timedelta(minutes=1)
        db.commit()

        assert row.status == PENDING, "the column deliberately has not caught up"
        assert badge(client) == before


class TestAnActionThatCannotRun:
    """`blocked_reason` — a certainty, not a doubt.

    Found by the user approving a seeded request against an already-sent
    campaign: the page warned them it would be refused and offered the button
    anyway. Warnings must not block; this is not a warning.
    """

    @pytest.fixture
    def blocking_action(self, tmp_path):
        """A planted action that declares itself unable to run."""
        package = Path(action_registry.__file__).parent
        planted = package / f"{TAG}_blocked.py"
        planted.write_text(
            "from app.approvals.actions.base import ApprovableAction, "
            "ActionDescription, ActionResult\n"
            "from pathlib import Path\n"
            "\n"
            f"META = ApprovableAction(key='{TAG}.blocked', label='Blocked action',\n"
            "                        approve_permission='sends.execute',\n"
            "                        default_ttl_seconds=3600,\n"
            "                        subject_type='marker')\n"
            "\n"
            "def describe(db, payload, *, brand_id=None):\n"
            "    return ActionDescription(summary='cannot run',\n"
            "                             blocked_reason='the thing already happened')\n"
            "\n"
            "def execute(db, payload, *, choice=None, brand_id=None):\n"
            "    path = Path(payload['path'])\n"
            "    with path.open('a') as handle:\n"
            "        handle.write('ran')\n"
            "    return ActionResult(ok=True)\n"
        )
        action_registry._registry_mtime = None
        try:
            yield {"path": str(tmp_path / "blocked.txt")}
        finally:
            planted.unlink(missing_ok=True)
            action_registry._registry_mtime = None

    def _held_blocked(self, db, payload):
        row = approvals.request_approval(
            db, f"{TAG}.blocked", payload=payload, summary="a blocked request",
            requested_by_type="integration", requested_by_id=7,
            brand_id=auth.ensure_default_brand(db).id,
            subject_id=int(uuid.uuid4().int % 10**8),
        )
        _CREATED.append(row.id)
        return row

    def test_the_approve_button_is_disabled_and_says_why(self, db, blocking_action):
        row = self._held_blocked(db, blocking_action)
        client, user = _signed_in(db, "admin")

        page = client.get(f"/ui/approvals/{row.id}").text

        assert "the thing already happened" in page
        approve_form = page.split('/approve"', 1)[1].split("</form>", 1)[0]
        assert "disabled" in approve_form, (
            "the page said it would be refused and offered the button anyway"
        )

    def test_rejecting_is_still_offered(self, db, blocking_action):
        """A blocked request must stay refusable, or it is stuck forever."""
        row = self._held_blocked(db, blocking_action)
        client, user = _signed_in(db, "admin")

        page = client.get(f"/ui/approvals/{row.id}").text
        reject_form = page.split('/reject"', 1)[1].split("</form>", 1)[0]

        assert "disabled" not in reject_form

    def test_the_disabled_button_is_a_courtesy_not_a_control(
        self, db, blocking_action
    ):
        """`execute()` still runs if somebody posts anyway.

        A disabled attribute stops a click, not a request — so the point of
        this test is that `blocked_reason` was never load-bearing. The action's
        own refusal is, and an action that does not refuse itself is the one
        with the bug.
        """
        row = self._held_blocked(db, blocking_action)
        client, user = _signed_in(db, "admin")

        client.post(f"/ui/approvals/{row.id}/approve",
                    data={"csrf_token": _csrf(client)})

        db.refresh(row)
        assert row.status == APPROVED, (
            "this planted action does not refuse itself, so it ran — which is "
            "the point: the UI hint is not the guard"
        )


class TestTheInboxOverJson:
    """ADR-168's 2026-09-19 addendum, built 2026-09-20.

    The same inbox the Jinja screens above work, reached the way the React
    client will: a session cookie and a CSRF header, no bearer. These tests sit
    beside the UI ones on purpose — one rule, two planes, and if they ever
    disagree it should be visible in one file.
    """

    def _api(self, db, role_key="admin"):
        client, user = _signed_in(db, role_key)
        token = client.cookies.get(auth.SESSION_COOKIE)
        client.headers.update({"X-CSRF-Token": auth.csrf_token_for(token)})
        return client, user

    def test_a_signed_in_person_can_approve(self, db, planted_action, tmp_path):
        """The whole point of the addendum: the SPA can work an inbox.

        Asserted through the action's own side effect rather than through the
        response, because a route that answered `{"ok": true}` without running
        anything would satisfy a status-code test perfectly.
        """
        marker = tmp_path / f"{uuid.uuid4().hex[:8]}.marker"
        row = _held(db, {"path": str(marker)})
        client, _user = self._api(db)

        response = client.post(f"/approvals/{row.id}/approve", json={"reason": "fine"})

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["ok"] is True, body
        assert body["status"] == "approved", body
        assert marker.exists(), "approving returned ok and did not run the action"

    def test_a_person_without_the_actions_permission_is_refused(self, db, planted_action):
        """403 and a message naming the permission — a different refusal from
        the machine one, which is not about permissions at all."""
        row = _held(db, {"path": "/tmp/never"})
        client, _user = self._api(db, role_key="viewer")

        response = client.post(f"/approvals/{row.id}/approve", json={})

        assert response.status_code == 403, response.text
        assert "permission" in response.json()["detail"].lower()

    def test_a_request_in_another_brand_is_not_found(self, db, planted_action):
        """404, exactly as a request that never existed (ADR-172 point 6)."""
        from app.auth.db_models import BrandDB

        other = BrandDB(key=f"{TAG}-{uuid.uuid4().hex[:8]}", name="Elsewhere")
        db.add(other); db.commit(); db.refresh(other)
        try:
            row = _held(db, {"path": "/tmp/never"}, brand_id=other.id)
            client, _user = self._api(db)

            assert client.get(f"/approvals/{row.id}").status_code == 404
            assert client.post(
                f"/approvals/{row.id}/approve", json={}).status_code == 404
        finally:
            db.query(BrandDB).filter(BrandDB.id == other.id).delete()
            db.commit()

    def test_the_detail_carries_the_live_description_and_the_frozen_line(
        self, db, planted_action
    ):
        """Both, because they answer different questions — the same split the
        detail screen makes, and the reason `describe` is a function."""
        row = _held(db, {"path": "/tmp/never"})
        client, _user = self._api(db)

        body = client.get(f"/approvals/{row.id}").json()

        assert body["summary"] == "a held marker"
        assert body["may_decide"] is True
        assert isinstance(body["rows"], list)

    def test_the_payload_is_not_a_field_of_the_response(self, db, planted_action):
        """ADR-153 §5 binds what may be published about an action, and a
        payload is an open dict the action author controls — so it is not a
        field of the API response, on either endpoint.

        **What an action's own `describe()` puts in its rows is a different
        question, and deliberately not this one.** Choosing what a reviewer
        needs to see is the entire job of `describe`; an action may well show
        an id or a path from its payload because that is what makes the request
        reviewable. The rule is that the payload is not published *wholesale*,
        not that its contents are secret — and the first version of this test
        asserted the latter and failed, correctly.
        """
        row = _held(db, {"path": "/tmp/secret-looking-path"})
        client, _user = self._api(db)

        listed = [r for r in client.get("/approvals/").json() if r["id"] == row.id][0]
        assert "payload" not in listed, listed
        # The list carries no description at all, so nothing of the payload
        # reaches it even by an action's choice.
        assert "secret-looking-path" not in str(listed)

        detail = client.get(f"/approvals/{row.id}").json()
        assert "payload" not in detail, detail

    def test_the_expiry_sweep_has_a_cron_seam(self, db, planted_action):
        """The reason `/delivery/process-due` has one. Bookkeeping only —
        approving already refuses an expired request whatever this has done."""
        from datetime import timedelta

        from app.approvals.db_models import PendingActionDB

        row = _held(db, {"path": "/tmp/never"})
        db.query(PendingActionDB).filter(PendingActionDB.id == row.id).update(
            {"expires_at": approvals.now() - timedelta(hours=1)}
        )
        db.commit()

        client, _user = self._api(db)
        response = client.post("/approvals/process-expired")

        assert response.status_code == 200, response.text
        assert row.id in response.json()["pending_action_ids"]
        db.refresh(row)
        assert row.status == "expired"
