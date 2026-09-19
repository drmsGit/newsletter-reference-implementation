"""The machine plane — ADR-166 stage 3, launch gate 3.

Until 2026-09-18 the JSON API was an unauthenticated control plane: 36
state-changing routes with no guard at all, sitting under a UI that was locked.
ADR-166's Context calls that worse than either state alone, "because it looks
protected". These tests are the gate closing.

**The most valuable test here is the last one**, which walks every write route
the app actually registers and fails if one has no policy entry. The failure
mode of route guards is the endpoint somebody forgot, and per-route decorators
fail *open* — the new route silently has none. Here it fails closed and loudly,
and this test moves the discovery from production to CI.

Runs against the shared dev database like the rest of the suite, and removes
everything it creates.
"""
import uuid
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth import integrations as ints
from app.auth import service as auth
from app.auth.db_models import (
    IntegrationAuthFailureDB, IntegrationCredentialDB,
)
from app.auth.permissions import (
    CONTENT_MANAGE, RECIPIENTS_CONSENT, RECIPIENTS_MANAGE, VIEW,
)
from app.auth.policy import PROVIDER_SIGNED, UNMAPPED, required_permission
from app.database import SessionLocal
from main import app
from tests.machine import machine

client = TestClient(app, raise_server_exceptions=False)


@contextmanager
def signed_in(db, role_key="admin"):
    """A browser session against the JSON API — what the SPA will be.

    Yields (client, session token, csrf token). The CSRF token is derived from
    the session token rather than stored, so the test computes it the same way
    the SPA will: from a value the server handed it.
    """
    user = auth.create_user(
        db, email=f"apitest-{uuid.uuid4().hex[:8]}@example.invalid", role_key=role_key,
    )
    token = auth.create_session(db, user)
    cookied = TestClient(app, raise_server_exceptions=False)
    cookied.cookies.set(auth.SESSION_COOKIE, token)
    try:
        yield cookied, token, auth.csrf_token_for(token)
    finally:
        db.rollback()
        for table in ("login_codes", "auth_sessions", "role_assignments"):
            db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
        db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
        db.commit()



@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _content_payload():
    return {
        "brand_id": 1,
        "title": f"apitest-{uuid.uuid4().hex[:8]}",
        "content_type": "cms",
        "content": {"headline": "x", "body_medium": "y"},
    }


class TestNothingGetsInWithoutACredential:

    def test_an_unauthenticated_write_is_refused(self):
        response = client.post("/content/", json=_content_payload())
        assert response.status_code == 401
        assert response.json()["detail"] == "Authentication required"

    def test_an_unauthenticated_read_is_refused(self):
        """`GET /recipients/` returned the recipient list to anybody who could
        reach the port. It is one of the four routes ADR-166's Context names."""
        assert client.get("/recipients/").status_code == 401

    def test_a_malformed_authorization_header_is_refused(self):
        for header in ("", "Bearer", "Bearer nodot", "Basic a.b", "nri_x.secret"):
            response = client.post(
                "/content/", json=_content_payload(),
                headers={"Authorization": header} if header else {},
            )
            assert response.status_code == 401, header

    def test_a_session_cookie_without_a_csrf_token_is_refused(self, db):
        """A cookie is an ambient credential; a header is not.

        ADR-168 put people back on this plane, so CSRF returned with them —
        carried in `X-CSRF-Token` rather than a form field, because the existing
        form-borne guard reads a JSON body as an empty FormData and would refuse
        every write while doing nothing at all on a bearer request.
        """
        with signed_in(db, "admin") as (cookied, _token, _csrf):
            response = cookied.post("/content/", json=_content_payload())
            assert response.status_code == 403
            assert "CSRF" in response.json()["detail"]

    def test_both_credentials_at_once_is_refused(self, db):
        """ADR-168 point 4, and the reason is about the audit row.

        A guard can always pick. What it cannot do is leave "who acted"
        derivable from what was sent, once it has picked silently.
        """
        from app.auth.permissions import CONTENT_MANAGE, VIEW

        with signed_in(db, "admin") as (cookied, _token, csrf):
            with machine([VIEW, CONTENT_MANAGE]) as headers:
                response = cookied.post(
                    "/content/", json=_content_payload(),
                    headers={**headers, "X-CSRF-Token": csrf},
                )
                assert response.status_code == 400
                assert "both" in response.json()["detail"].lower()


class TestAPersonMayUseTheJsonApi:
    """ADR-168 — what makes a React manager client possible at all.

    Between 2026-09-18 and 2026-09-19 this plane took machine credentials only,
    and the narrowing left the SPA with no way to authenticate. These tests pin
    the two halves of the answer: a session is accepted, and it brings its own
    working brand rather than being asked for a header it has no reason to send.
    """

    def test_a_session_with_a_csrf_token_is_admitted(self, db):
        with signed_in(db, "admin") as (cookied, _token, csrf):
            payload = _content_payload()
            payload["brand_id"] = auth.ensure_default_brand(db).id
            response = cookied.post(
                "/content/", json=payload, headers={"X-CSRF-Token": csrf},
            )
            assert response.status_code in (200, 201), response.text
            created = response.json()
        db.execute(text("DELETE FROM content_records WHERE id = :i"),
                   {"i": created["id"]})
        db.commit()

    def test_no_x_brand_header_is_needed(self, db):
        """**The prerequisite ADR-168's Notes call out.**

        `enforce_api_policy` raises `BrandNotDeclared` when a brand-scoped
        permission arrives without a working brand. A person sends no `X-Brand`
        — theirs is in the session — so landing the cookie half alone would have
        refused every brand-scoped SPA write with a 400: the whole campaign,
        content and audience surface.
        """
        with signed_in(db, "admin") as (cookied, _token, csrf):
            response = cookied.post(
                "/content/", json=_content_payload(),
                headers={"X-CSRF-Token": csrf},
            )
            assert response.status_code != 400, (
                "a person was asked for the header only a machine should send"
            )
            if response.status_code in (200, 201):
                db.execute(text("DELETE FROM content_records WHERE id = :i"),
                           {"i": response.json()["id"]})
                db.commit()

    def test_the_row_lands_in_the_brand_the_caller_was_authorised_for(self, db):
        """The other half of the same prerequisite.

        The routers used to check the permission against the declared brand and
        then write the row to the DEFAULT brand — authorising a caller for
        brand B and putting the row in brand A.

        **Asserted against a NON-DEFAULT brand, and that is the whole test.**
        The first version used the default brand, so deleting the write-back
        entirely still passed: `_request_brand` falls back to
        `ensure_default_brand`, which returned exactly the id being asserted. A
        fallback that equals the expected value is not a test.
        """
        from app.auth.db_models import BrandDB
        from app.auth.permissions import CONTENT_MANAGE, VIEW
        from app.content.db_models import ContentRecordDB

        other = BrandDB(key=f"apitest-{uuid.uuid4().hex[:8]}", name="Second brand")
        db.add(other)
        db.commit()
        db.refresh(other)
        created = None
        try:
            with machine([VIEW, CONTENT_MANAGE], brand_id=other.id) as headers:
                assert int(headers["X-Brand"]) == other.id
                response = client.post(
                    "/content/", json=_content_payload(), headers=headers,
                )
                assert response.status_code in (200, 201), response.text
                created = response.json()["id"]
            row = db.query(ContentRecordDB).filter(
                ContentRecordDB.id == created
            ).first()
            assert row.brand_id == other.id, (
                f"authorised for brand {other.id}, wrote to {row.brand_id}"
            )
        finally:
            db.rollback()
            if created:
                db.execute(text("DELETE FROM content_records WHERE id = :i"),
                           {"i": created})
            db.query(BrandDB).filter(BrandDB.id == other.id).delete()
            db.commit()

    def test_a_machine_still_needs_no_csrf_token(self, db):
        """A cross-site page cannot make a browser attach an Authorization
        header it does not know, so there is nothing for a token to defend."""
        from app.auth.permissions import CONTENT_MANAGE, VIEW

        with machine([VIEW, CONTENT_MANAGE]) as headers:
            response = client.post(
                "/content/", json=_content_payload(), headers=headers,
            )
            assert response.status_code in (200, 201), response.text
            db.execute(text("DELETE FROM content_records WHERE id = :i"),
                       {"i": response.json()["id"]})
            db.commit()

    def test_every_json_router_carries_the_csrf_guard(self):
        """**The line ADR-168's Negative section names as the dangerous one.**

        `enforce_csrf` was once wired onto the frontend router alone, leaving
        the thirteen most privileged forms in the system unprotected while the
        gate record said "CSRF on all 62 forms". A guard on eleven of twelve
        routers fails identically and reports identically.
        """
        from app.auth.dependencies import enforce_api_csrf

        guarded, unguarded = [], []
        for route in app.routes:
            path = getattr(route, "path", "")
            methods = getattr(route, "methods", set()) or set()
            if path.startswith("/ui") or path.startswith("/static"):
                continue
            if not (methods & {"POST", "PUT", "PATCH", "DELETE"}):
                continue
            # Read the resolved `dependant`, not `route.dependencies`: FastAPI
            # merges router-level dependencies into the former, and the latter
            # holds only what the route declared for itself. Asserting against
            # the wrong one produced an empty list and a test that could never
            # have caught the bug it is named after.
            deps = [
                d.call for d in route.dependant.dependencies
                if getattr(d, "call", None)
            ]
            (guarded if enforce_api_csrf in deps else unguarded).append(path)

        assert guarded, "no JSON write route carries the API CSRF guard at all"
        assert not unguarded, (
            "JSON write routes with no CSRF guard:\n  " + "\n  ".join(sorted(unguarded))
        )


class TestPermissionsDecideTheRest:

    def test_a_credential_without_the_permission_is_refused(self):
        with machine([VIEW]) as headers:
            response = client.post("/content/", json=_content_payload(), headers=headers)
            assert response.status_code == 403
            assert "content.manage" in response.json()["detail"]

    def test_a_credential_with_the_permission_is_admitted(self, db):
        with machine([VIEW, CONTENT_MANAGE]) as headers:
            payload = _content_payload()
            payload["brand_id"] = auth.ensure_default_brand(db).id
            response = client.post("/content/", json=payload, headers=headers)
            assert response.status_code in (200, 201), response.text
            created = response.json()
        db.execute(text("DELETE FROM content_records WHERE id = :i"), {"i": created["id"]})
        db.commit()

    def test_reads_need_view_and_a_machine_is_not_given_it_for_free(self):
        """`view` is implied by every role and by no grant. A machine that
        writes engagement events has no business listing recipients."""
        with machine([RECIPIENTS_MANAGE]) as headers:
            assert client.get("/recipients/", headers=headers).status_code == 403


class TestTheBrandHeader:
    """ADR-166 point 8: a machine declares its working brand, and declaring it
    grants nothing — it selects which grant is checked."""

    def test_a_brand_scoped_write_without_the_header_says_so(self):
        with machine([VIEW, CONTENT_MANAGE]) as headers:
            headers.pop("X-Brand")
            response = client.post("/content/", json=_content_payload(), headers=headers)
            assert response.status_code == 400, response.text
            detail = response.json()["detail"]
            assert "X-Brand" in detail
            # The mitigation named in point 8's Negative: this must not read
            # like a permission refusal, because that is how "somebody scoped
            # the integration to a second brand" becomes "permissions broke".
            assert "permission" not in detail.lower()

    def test_declaring_a_brand_the_integration_holds_nothing_on_is_refused(self):
        with machine([VIEW, CONTENT_MANAGE]) as headers:
            headers["X-Brand"] = "999999"
            response = client.post("/content/", json=_content_payload(), headers=headers)
            assert response.status_code == 403

    def test_a_malformed_brand_is_treated_as_absent(self):
        with machine([VIEW, CONTENT_MANAGE]) as headers:
            headers["X-Brand"] = "not-a-number"
            assert client.post(
                "/content/", json=_content_payload(), headers=headers
            ).status_code == 400


class TestTheSignedProviderDoorStaysOpen:
    """ADR-166 point 6: two inbound mechanisms coexist deliberately.

    A send provider cannot hold a credential this platform issued and will not
    be asked to. ADR-106 makes bounce and complaint feedback mandatory, so if
    authentication made this path awkward an adopter would disable it — and
    disabled feedback is a deliverability failure with a delay on it.
    """

    def test_the_webhook_is_not_asked_for_a_platform_credential(self):
        response = client.post("/provider/webhooks/resend", json={"type": "x"})
        assert response.status_code == 401
        # The distinction that matters: refused by the SIGNATURE check, not by
        # the credential guard. Same status, different door.
        assert response.json()["detail"] == "invalid webhook signature"

    def test_the_unsigned_sibling_is_not_exempt(self):
        """`POST /provider/events` reaches the same service function as the
        signed route, with the lock removed — forged engagement against real
        recipients, steering personalisation."""
        assert client.post("/provider/events", json={}).status_code == 401
        assert required_permission("POST", "/provider/events") != PROVIDER_SIGNED


class TestConsentIsNotASideEffectOfImporting:

    def test_importing_a_contact_cannot_assert_its_consent(self, db):
        """ADR-150 point 5's separation, enforced against the payload.

        The route is mapped to `recipients.manage`; the body carries
        `consent_status`. One mapping would have let the weaker grant assert
        consent through the body — the compliance record a UWG §7 complaint is
        answered with.
        """
        brand = auth.ensure_default_brand(db).id
        with machine([VIEW, RECIPIENTS_MANAGE]) as headers:
            response = client.post("/recipients/", headers=headers, json={
                "brand_id": brand,
                "external_id": f"apitest-{uuid.uuid4().hex[:8]}",
                "address": "nobody@example.invalid",
                "consent_status": "opted_in",
            })
            assert response.status_code == 403
            assert "recipients.consent" in response.json()["detail"]

    def test_both_grants_together_work(self, db):
        brand = auth.ensure_default_brand(db).id
        external_id = f"apitest-{uuid.uuid4().hex[:8]}"
        with machine([VIEW, RECIPIENTS_MANAGE, RECIPIENTS_CONSENT]) as headers:
            response = client.post("/recipients/", headers=headers, json={
                "brand_id": brand, "external_id": external_id,
                "address": f"{external_id}@example.invalid",
                "consent_status": "opted_in",
            })
            assert response.status_code in (200, 201), response.text
        db.execute(text(
            "DELETE FROM consent_events WHERE recipient_id IN "
            "(SELECT id FROM recipients WHERE external_id = :e)"), {"e": external_id})
        db.execute(text(
            "DELETE FROM recipient_addresses WHERE recipient_id IN "
            "(SELECT id FROM recipients WHERE external_id = :e)"), {"e": external_id})
        db.execute(text("DELETE FROM recipients WHERE external_id = :e"), {"e": external_id})
        db.commit()


class TestFailuresAreCountedNotListed:
    """ADR-153 §6, inherited by ADR-166 point 3.

    An unauthenticated attacker can generate these at will, so a row per
    attempt would hand whoever can reach the port an unbounded write.
    """

    def test_repeated_failures_share_one_row(self, db):
        key_id = f"nri_{uuid.uuid4().hex[:16]}"
        try:
            for _ in range(3):
                client.post("/content/", json=_content_payload(),
                            headers={"Authorization": f"Bearer {key_id}.wrong"})
            rows = db.query(IntegrationAuthFailureDB).filter(
                IntegrationAuthFailureDB.key_id == key_id
            ).all()
            assert len(rows) == 1, "one row per key, client and hour"
            assert rows[0].attempts == 3
        finally:
            db.query(IntegrationAuthFailureDB).filter(
                IntegrationAuthFailureDB.key_id == key_id
            ).delete()
            db.commit()


class TestNoRouteIsUnguarded:

    def test_every_json_write_route_has_a_policy_entry(self):
        """The UI half has had this test since gate 4. The JSON half is why
        gate 3 was open."""
        unmapped = []
        for route in app.routes:
            path = getattr(route, "path", "")
            if path.startswith("/ui") or path.startswith("/static"):
                continue
            for method in sorted(getattr(route, "methods", set()) or set()):
                if method in {"POST", "PUT", "PATCH", "DELETE"}:
                    if required_permission(method, path) == UNMAPPED:
                        unmapped.append(f"{method} {path}")
        assert not unmapped, (
            "JSON write routes with no entry in app/auth/policy.py:\n  "
            + "\n  ".join(unmapped)
        )

    def test_exactly_one_route_is_exempt_from_credentials(self):
        """The exemption list is a security boundary. It should be one door,
        and adding a second should require editing this assertion."""
        exempt = [
            f"{m} {getattr(r, 'path', '')}"
            for r in app.routes
            for m in sorted(getattr(r, "methods", set()) or set())
            if m in {"POST", "PUT", "PATCH", "DELETE"}
            and required_permission(m, getattr(r, "path", "")) == PROVIDER_SIGNED
        ]
        assert exempt == ["POST /provider/webhooks/resend"], exempt


class TestAHeldSendIsQueuedNotRefused:
    """ADR-166 point 5 finally meaning what it says (2026-09-19).

    Until the approval surface existed this path answered 403, because storing
    the flag and letting the send through would have shipped something that
    looks like a control and is not. It answers 202 now — "the flow calls an
    action, receives pending approval, and finishes" (ADR-142 §4).

    **The most important test in this class is the escalation one.** Moving the
    flag check below `has_permission` is what stops an integration with no
    `sends.execute` grant from minting a pending send for a human to approve.
    While both answers were 403 the ordering did not matter; the moment one of
    them hands out a queue slot, it does.
    """

    def _pending_rows(self, db):
        from app.approvals.db_models import PendingActionDB

        return db.query(PendingActionDB).filter(
            PendingActionDB.action_key == "send.fire_send_instance",
            PendingActionDB.requested_by_type == "integration",
        ).all()

    def _cleanup(self, db, integration_marker=None):
        """Delete by what this class creates, not by diffing against a snapshot.

        The first version diffed "rows now" against "rows before" — which leaks
        the moment a run fails partway, because the next run's `before` then
        includes the previous run's debris and the diff stops seeing it. One
        leaked row was enough to make a later test hit the duplicate path and
        fail for a reason that had nothing to do with what it tested.

        Rows raised through the API carry a real `requested_by_id`; the seeded
        demo rows use 0 and are deliberately left alone.
        """
        from app.approvals import service as approvals
        from app.approvals.db_models import PendingActionDB
        from app.audit.db_models import AuditEventDB

        db.rollback()
        ids = [
            r.id for r in self._pending_rows(db)
            if r.requested_by_id not in (None, 0)
        ]
        if ids:
            db.query(AuditEventDB).filter(
                AuditEventDB.subject_type == approvals.SUBJECT,
                AuditEventDB.subject_id.in_(ids),
            ).delete(synchronize_session=False)
            db.query(PendingActionDB).filter(
                PendingActionDB.id.in_(ids)
            ).delete(synchronize_session=False)
            db.commit()

    @pytest.fixture
    def draft_send(self, db):
        """A send instance with **no open request already against it**.

        One open request per subject is enforced by a partial unique index, so
        picking an instance that already has one makes every test in this class
        take the duplicate path and assert nothing it means to. The demo seed
        puts requests on several instances, which is exactly the situation a
        test must not be surprised by.
        """
        from app.approvals.db_models import PENDING, PendingActionDB
        from app.delivery.db_models import SendInstanceDB

        db.rollback()
        taken = {
            row.subject_id for row in db.query(PendingActionDB).filter(
                PendingActionDB.action_key == "send.fire_send_instance",
                PendingActionDB.status == PENDING,
            ).all()
        }
        instance = db.query(SendInstanceDB).filter(
            SendInstanceDB.brand_id == auth.ensure_default_brand(db).id,
            SendInstanceDB.id.notin_(taken or {-1}),
        ).order_by(SendInstanceDB.id).first()
        if instance is None:
            pytest.skip("every send instance already has a request waiting")
        return instance

    def test_an_unflagged_integration_gets_a_held_request(self, db, draft_send):
        from app.auth.permissions import SENDS_EXECUTE, VIEW

        before = [r.id for r in self._pending_rows(db)]
        try:
            with machine([VIEW, SENDS_EXECUTE]) as headers:
                response = client.post(
                    f"/delivery/send-instances/{draft_send.id}/send", headers=headers,
                )
                assert response.status_code == 202, response.text
                body = response.json()
                assert body["status"] == "pending_approval"
                assert body["review"].startswith("/ui/approvals/")
                # ADR-142 §4: pending actions expire.
                assert body["expires_at"]

                held = [r for r in self._pending_rows(db) if r.id not in before]
                assert len(held) == 1
                assert held[0].brand_id is not None, (
                    "a brand-less held request is invisible in every inbox"
                )
                assert held[0].requested_by_id is not None
        finally:
            self._cleanup(db)

    def test_an_integration_without_the_grant_mints_nothing(self, db, draft_send):
        """**The escalation test.**

        No `sends.execute` grant at all. Before the reorder this hit the
        unattended-send flag first and would, as a queue, have produced a
        pending send for a human to approve — access the integration was never
        given, arriving through the approval surface.
        """
        from app.auth.permissions import VIEW

        before = [r.id for r in self._pending_rows(db)]
        try:
            with machine([VIEW]) as headers:
                response = client.post(
                    f"/delivery/send-instances/{draft_send.id}/send", headers=headers,
                )
                assert response.status_code == 403, response.text
                assert "sends.execute" in response.json()["detail"]
                assert [r.id for r in self._pending_rows(db)] == before, (
                    "a caller with no grant created a pending send"
                )
        finally:
            self._cleanup(db)

    def test_a_brand_scoped_send_without_the_header_mints_nothing(
        self, db, draft_send
    ):
        """The brand moved above the flag for this: a held request with no
        brand would be invisible in every inbox."""
        from app.auth.permissions import SENDS_EXECUTE, VIEW

        before = [r.id for r in self._pending_rows(db)]
        try:
            with machine([VIEW, SENDS_EXECUTE]) as headers:
                headers.pop("X-Brand")
                response = client.post(
                    f"/delivery/send-instances/{draft_send.id}/send", headers=headers,
                )
                assert response.status_code == 400
                assert [r.id for r in self._pending_rows(db)] == before
        finally:
            self._cleanup(db)

    def test_a_retry_returns_the_same_held_request(self, db, draft_send):
        """An orchestrator that retries must not see an error — the request is
        pending, and saying so keeps the retry idempotent."""
        from app.auth.permissions import SENDS_EXECUTE, VIEW

        before = [r.id for r in self._pending_rows(db)]
        try:
            with machine([VIEW, SENDS_EXECUTE]) as headers:
                first = client.post(
                    f"/delivery/send-instances/{draft_send.id}/send", headers=headers,
                )
                second = client.post(
                    f"/delivery/send-instances/{draft_send.id}/send", headers=headers,
                )
                assert second.status_code == 202
                assert (second.json()["pending_action_id"]
                        == first.json()["pending_action_id"])
                assert len([r for r in self._pending_rows(db)
                            if r.id not in before]) == 1
        finally:
            self._cleanup(db)

    def test_a_flagged_integration_sends_without_being_held(self, db, draft_send):
        """The flag is what changes it, and it must create NO pending row —
        a send that both happens and waits would be the worst of both."""
        from app.auth.db_models import IntegrationDB
        from app.auth.permissions import SENDS_EXECUTE, VIEW
        from app.auth import integrations as ints

        before = [r.id for r in self._pending_rows(db)]
        try:
            with machine([VIEW, SENDS_EXECUTE]) as headers:
                key_id = headers["Authorization"].split()[1].split(".")[0]
                integration = db.query(IntegrationDB).join(
                    IntegrationCredentialDB,
                    IntegrationCredentialDB.integration_id == IntegrationDB.id,
                ).filter(IntegrationCredentialDB.key_id == key_id).first()
                ints.set_unattended_sending(db, integration.id, True)

                response = client.post(
                    f"/delivery/send-instances/{draft_send.id}/send", headers=headers,
                )
                assert response.status_code != 202, (
                    "a flagged integration must not be held"
                )
                assert [r.id for r in self._pending_rows(db)] == before
        finally:
            self._cleanup(db)

    def test_a_route_with_no_approvable_action_is_refused_not_queued(
        self, db, draft_send, monkeypatch
    ):
        """Fail-closed by omission.

        `APPROVABLE_ROUTES` is what grants a route a queue. A route missing from
        it must go back to being refused outright — the behaviour every send had
        before the approval surface existed — rather than reaching the handler
        with nothing to build a request from.

        The mapping is removed for the duration, because every send route in the
        app is currently mapped and there is otherwise no way to reach this
        branch. `delitem` mutates the dict the dependency imported, which is the
        same object.
        """
        from app.auth.permissions import SENDS_EXECUTE, VIEW
        from app.auth.policy import APPROVABLE_ROUTES

        monkeypatch.delitem(
            APPROVABLE_ROUTES, "/delivery/send-instances/{send_instance_id}/send",
        )
        before = [r.id for r in self._pending_rows(db)]
        try:
            with machine([VIEW, SENDS_EXECUTE]) as headers:
                response = client.post(
                    f"/delivery/send-instances/{draft_send.id}/send", headers=headers,
                )
                assert response.status_code == 403, response.text
                assert "cannot be held" in response.json()["detail"]
                assert [r.id for r in self._pending_rows(db)] == before
        finally:
            self._cleanup(db)

    def test_there_is_no_way_to_approve_over_the_api(self, db):
        """A machine that can approve its own held request has defeated the
        mechanism. The approve route lives only on the UI plane."""
        from app.auth.permissions import SENDS_EXECUTE, VIEW

        with machine([VIEW, SENDS_EXECUTE]) as headers:
            for path in ("/ui/approvals/1/approve", "/approvals/1/approve"):
                response = client.post(path, headers=headers)
                assert response.status_code in (401, 403, 404, 405), (
                    f"{path} answered {response.status_code}"
                )


class TestPlanningIsNotFiring:
    """What the ADR-166 point 2 split bought, checked from the machine side.

    This class used to assert that an unflagged integration was REFUSED a send.
    That was true for one day. The approval surface now holds it instead, which
    `TestAHeldSendIsQueuedNotRefused` covers — so the two tests that asserted a
    403 are gone rather than adjusted, because their subject changed rather
    than their expected value.
    """

    def test_planning_is_not_affected_by_the_unattended_flag(self, db):
        """The flag gates firing, not preparing. `sends.plan` reaches nobody,
        so it has nothing to be held for."""
        from app.auth.permissions import SENDS_PLAN, VIEW

        with machine([VIEW, SENDS_PLAN]) as headers:
            response = client.post(
                "/delivery/send-instances", headers=headers, json={},
            )
            assert response.status_code not in (202, 403), response.status_code
