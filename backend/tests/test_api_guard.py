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

    def test_a_session_cookie_does_not_authenticate_the_machine_plane(self, db):
        """The narrowing that makes CSRF a non-question here.

        An Admin's browser session is a perfectly good credential for /ui and
        is deliberately not one for the JSON API: there is no ambient
        credential on this plane for a cross-site request to carry.
        """
        user = auth.create_user(
            db, email=f"apitest-{uuid.uuid4().hex[:8]}@example.invalid",
            role_key="admin",
        )
        token = auth.create_session(db, user)
        try:
            cookied = TestClient(app, raise_server_exceptions=False)
            cookied.cookies.set(auth.SESSION_COOKIE, token)
            assert cookied.post(
                "/content/", json=_content_payload()
            ).status_code == 401
        finally:
            db.execute(text("DELETE FROM auth_sessions WHERE user_id = :u"), {"u": user.id})
            db.execute(text("DELETE FROM role_assignments WHERE user_id = :u"), {"u": user.id})
            db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
            db.commit()


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


class TestAMachineSendNeedsApproval:
    """ADR-166 point 5, enforced rather than asserted.

    The ADR says a machine-triggered send lands in ADR-142 §4's approval
    surface unless the integration is flagged otherwise. That surface is not
    built, so there is nowhere for it to land — and storing the flag, showing
    it in the admin screen and letting the send through anyway would ship
    something that looks like a control and is not.
    """

    def test_an_unflagged_integration_cannot_fire_a_send(self, db):
        from app.auth.permissions import SENDS_EXECUTE, VIEW

        with machine([VIEW, SENDS_EXECUTE]) as headers:
            response = client.post(
                "/delivery/send-instances/1/send", headers=headers,
            )
            assert response.status_code == 403
            assert "without approval" in response.json()["detail"]

    def test_the_flag_is_what_changes_it(self, db):
        from app.auth.db_models import IntegrationDB
        from app.auth.permissions import SENDS_EXECUTE, VIEW

        with machine([VIEW, SENDS_EXECUTE]) as headers:
            key_id = headers["Authorization"].split()[1].split(".")[0]
            integration = db.query(IntegrationDB).join(
                IntegrationCredentialDB,
                IntegrationCredentialDB.integration_id == IntegrationDB.id,
            ).filter(IntegrationCredentialDB.key_id == key_id).first()
            ints.set_unattended_sending(db, integration.id, True)

            response = client.post(
                "/delivery/send-instances/1/send", headers=headers,
            )
            # Past the guard now: whatever happens next is the send path's
            # business, and a missing send instance is not an authorisation
            # answer.
            assert response.status_code != 403 or (
                "without approval" not in response.json().get("detail", "")
            )

    def test_planning_is_not_affected(self, db):
        """The flag gates firing, not preparing. `sends.plan` reaches nobody."""
        from app.auth.permissions import SENDS_PLAN, VIEW

        with machine([VIEW, SENDS_PLAN]) as headers:
            response = client.post(
                "/delivery/send-instances", headers=headers, json={},
            )
            assert response.status_code != 403
