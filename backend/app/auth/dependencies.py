"""One dependency guards every route (ADR-150).

The reason access control did not need to touch business logic: authentication
is a request-scoped concern, so it lives in a FastAPI dependency and the
services underneath never learn that users exist. Adding a guard to a route is
one parameter.

**The decision is forced login** (2026-08-02): every UI page requires a signed-in
user, applied as a router-level dependency in `main.py` rather than 57 route
decorators. The lockout worry that argued against it is gone, because system
mail defaults to the mock provider and the sign-in code appears on screen
instead of depending on a mail path that might not work.

Enforcement remains a **setting rather than a constant**, and ships *off* so a
deployment turns it on once it has signed in successfully — recovering from a
misconfiguration needs a way back that is not "edit an environment variable on
the server". Startup says loudly which state it is in.
"""

import logging
import secrets

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.auth.db_models import UserDB
from app.auth.permissions import SENDS_EXECUTE, is_brand_scoped
from app.auth.policy import PROVIDER_SIGNED, UNMAPPED, required_permission
from app.auth.integrations import authenticate, record_auth_failure
from app.auth.service import (
    SESSION_COOKIE,
    csrf_token_for,
    has_permission,
    user_for_token,
)
from app.database import get_db
from app.settings.service import get_config

logger = logging.getLogger(__name__)

AUTH_ENFORCED_KEY = "auth_enforced"


class NotAuthenticated(Exception):
    """Raised when a guarded route is reached without a valid session."""


class NotAuthorised(Exception):
    """Raised when a valid session lacks the permission a route requires."""

    def __init__(self, permission: str):
        super().__init__(permission)
        self.permission = permission


def auth_enforced(db: Session) -> bool:
    """Whether access control is enforced. **Defaults to ON.**

    It shipped off until 2026-09-13, on the reasoning that a misconfigured
    deployment needed a way back and that the sign-in code was always readable
    because system mail defaults to the mock provider and printed it on screen.
    The gate-4b fix removed the on-screen code — it was the account-enumeration
    oracle — so that reasoning lapsed, and an unguarded default is the thing
    launch gate 4 exists to prevent.

    **Being locked out, and the way back.** With mock mail (the default) the
    code is written to the server log, so a developer is never locked out.
    With a real provider the code is emailed and deliberately not logged, so a
    broken mail path *would* lock everyone out — including the person who would
    fix it. The break-glass for that is `AUTH_DEV_SHOW_CODE=true`, which puts
    the code back in the log so an operator signs in **as themselves**, rather
    than a flag that switches access control off for everyone. Both need log
    access, so the bar is the same and the hole is much smaller.

    Cases that env var does NOT cover — a deactivated sole admin, a deleted
    admin role — need database access. That is stated rather than papered over.
    """
    return bool(get_config(db, AUTH_ENFORCED_KEY, True))


def _permitted(request: Request, db: Session, user: UserDB, permission: str) -> bool:
    """Check a permission, against the working brand when the permission is scoped.

    ADR-150's 2026-09-15 addendum: a permission is brand-scoped if the rows it
    guards carry a `brand_id`. A brand-scoped permission is checked against the
    brand this request is working in; a platform-level one is checked across
    every grant the user holds, which is what `permissions_for` does when given
    no brand.

    **A brand-scoped permission with no working brand is REFUSED, never checked
    without one.** `brand_id=None` means "any brand this user holds" — the
    union — so passing it through would be the fail-open direction: it would
    let an Admin on brand A act as one on brand B, which is the exact hole this
    addendum exists to close. No working brand means the user holds no grant at
    all, and holding no grant is not a reason to be allowed more.
    """
    if not is_brand_scoped(permission):
        return has_permission(db, user, permission)

    brand = getattr(request.state, "current_brand", None)
    if not brand:
        logger.warning(
            "auth: refused %s — brand-scoped, and this request has no working brand",
            permission,
        )
        return False
    return has_permission(db, user, permission, brand_id=brand["id"])


def current_user(request: Request, db: Session = Depends(get_db)) -> UserDB | None:
    """Resolve the session cookie, or None. Never raises — for optional use."""
    return user_for_token(db, request.cookies.get(SESSION_COOKIE))


def require_permission(permission: str):
    """Dependency factory: this route needs this named permission.

    For routes guarded individually. Most of the UI is covered by
    `enforce_policy` instead, which derives the permission from the route.

    While enforcement is off the check is skipped, but a signed-in user is
    still resolved — so the UI can show who you are, and the audit trail
    (ADR-153) has an actor to attribute to, before the switch is flipped.
    """

    def guard(request: Request, db: Session = Depends(get_db)) -> UserDB | None:
        user = user_for_token(db, request.cookies.get(SESSION_COOKIE))
        if not auth_enforced(db):
            return user
        if user is None:
            raise NotAuthenticated()
        if not _permitted(request, db, user, permission):
            raise NotAuthorised(permission)
        return user

    return guard


CSRF_FIELD = "csrf_token"
_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class CsrfFailed(Exception):
    """Raised when a state-changing form arrives without a valid CSRF token."""


async def enforce_csrf(request: Request) -> None:
    """Reject a state-changing request whose CSRF token is missing or wrong.

    Applied once over the UI router, the same way `enforce_policy` is — a
    per-route decorator across 60-odd forms is a list someone eventually
    forgets to add to, and the failure would be silent.

    **Fails closed**: a form that omits the field is refused, so a new form
    added without one breaks loudly in development rather than shipping
    unguarded. That is the same property `enforce_policy` gives an unclassified
    write route.

    Skipped when there is no session, because the token is derived from one:
    an anonymous POST is the sign-in form itself, which has no session to
    protect and is rate-limited separately. Nothing a signed-out visitor can
    submit changes state on someone else's behalf.
    """
    if request.method not in _UNSAFE_METHODS:
        return

    session_token = request.cookies.get(SESSION_COOKIE)
    if not session_token:
        return

    form = await request.form()
    submitted = (form.get(CSRF_FIELD) or "").strip()
    expected = csrf_token_for(session_token)
    if not submitted or not secrets.compare_digest(submitted, expected):
        logger.warning(
            "csrf: refused %s %s — token %s",
            request.method,
            request.url.path,
            "missing" if not submitted else "mismatched",
        )
        raise CsrfFailed()


def enforce_policy(request: Request, db: Session = Depends(get_db)) -> UserDB | None:
    """Derive the required permission from the route and check it.

    Applied once over the whole UI router. Reads need `view`; writes are looked
    up in the policy table, and a write nobody classified is **refused** — so a
    new endpoint added without a policy entry fails closed and loudly, instead
    of silently shipping unguarded.

    A user holding several roles gets the **union** of their permissions: if any
    one role grants it, access is allowed. That is not a rule implemented here,
    it falls out of the model — permissions are grants only, with no DENY, so
    two roles cannot contradict each other and there is nothing to resolve.
    """
    user = user_for_token(db, request.cookies.get(SESSION_COOKIE))
    if not auth_enforced(db):
        return user
    if user is None:
        raise NotAuthenticated()

    route = request.scope.get("route")
    template = getattr(route, "path", None) or request.url.path
    permission = required_permission(request.method, template)

    if permission == UNMAPPED:
        logger.warning(
            "auth: refused %s %s — no policy entry. Add one in app/auth/policy.py.",
            request.method, template,
        )
        raise NotAuthorised(permission)

    if not _permitted(request, db, user, permission):
        raise NotAuthorised(permission)
    return user


# --- the machine plane (ADR-166) --------------------------------------------

BRAND_HEADER = "X-Brand"


class ApprovalRequired(Exception):
    """A machine tried to fire a send it is not flagged to fire unattended.

    ADR-166 point 5 says such a send "lands in ADR-142 §4's approval surface —
    the same pending-action mechanism, the same inbox, the same history".
    **That surface is not built.** The shared approval inbox is an open item,
    so there is nowhere for the send to land.

    Refusing is the only honest reading of "defaults to requiring approval"
    while that is true. The alternative — storing the flag, showing it in the
    UI and letting the send through anyway — ships something that looks like a
    control and is not, which is worse than shipping no flag at all. When the
    approval surface exists this becomes a queue instead of a refusal, and the
    default does not have to change.
    """


class BrandNotDeclared(Exception):
    """Raised when a brand-scoped write arrives with no `X-Brand` header.

    Its own exception, rather than a NotAuthorised, because ADR-166 point 8's
    `### Negative` names the confusion this exists to prevent: "a caller that
    omits the header is refused for having no working brand, which from outside
    is indistinguishable from being refused for lacking the permission", and
    the mitigation is "an error that says which of the two happened".

    Explicitly **not** a fallback to "the one brand this integration holds".
    That would work right up until it holds two, and would then fail by
    silently acting on the wrong brand rather than by refusing.
    """


def _machine_credential(request: Request) -> tuple[str, str] | None:
    """Pull `Authorization: Bearer <key_id>.<secret>` apart, or None.

    **Key and secret in one standard header.** ADR-166 point 1 wants the two
    halves distinguishable so a request that fails to authenticate can still be
    attributed and counted; splitting on the first dot gives that without a
    second header to forget. `Authorization` rather than a custom name because
    proxies, log scrubbers and client libraries already know to redact it —
    ADR-166 point 3 bans the credential from anywhere a log or a referrer can
    capture it, and the well-known header is the one most tooling protects.
    """
    scheme, _, value = (request.headers.get("authorization") or "").partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None
    key_id, _, secret = value.strip().partition(".")
    if not key_id or not secret:
        return None
    return key_id, secret


def _declared_brand(request: Request) -> int | None:
    raw = (request.headers.get(BRAND_HEADER) or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        # A malformed value is the same as none: it selects no grant, and
        # guessing what was meant is how a header becomes a second identifier
        # scheme nobody documented.
        return None


def enforce_api_policy(request: Request, db: Session = Depends(get_db)):
    """One guard over the JSON API — the machine plane (ADR-166).

    **Only machine credentials are accepted here; a session cookie is not.**
    That is a deliberate narrowing and it buys the CSRF question outright:
    there is no ambient credential on this plane, so a cross-site request
    carries nothing to abuse. It also keeps `enforce_csrf` — which reads the
    request as a form — away from JSON bodies. A developer who wants to call
    the API issues themselves an integration key, which is attributable and
    revocable in a way a browser session is not.

    Everything else is shared with the human path on purpose: the same policy
    table decides which permission a route needs, and the same
    `permissions_for` answers whether the caller holds it. ADR-166 point 1
    refuses a parallel authorization system, and this is where that promise is
    either kept or quietly broken.
    """
    route = request.scope.get("route")
    template = getattr(route, "path", None) or request.url.path
    permission = required_permission(request.method, template)

    # A provider signs its own callbacks (ADR-166 point 6). Checked before
    # enforcement, because this door is not ours to open or close: the route
    # verifies a signature whether or not access control is switched on, and
    # ADR-106 makes that feedback path mandatory for a production provider.
    if permission == PROVIDER_SIGNED:
        return None

    if not auth_enforced(db):
        return None

    credential = _machine_credential(request)
    if credential is None:
        raise NotAuthenticated()

    key_id, secret = credential
    integration = authenticate(db, key_id, secret)
    if integration is None:
        record_auth_failure(db, key_id, request.client.host if request.client else None)
        raise NotAuthenticated()

    if permission == UNMAPPED:
        logger.warning(
            "api: refused %s %s — no policy entry. Add one in app/auth/policy.py.",
            request.method, template,
        )
        raise NotAuthorised(permission)

    # ADR-166 point 5, enforced rather than asserted. Checked before the brand,
    # because "you may not do this at all" outranks "you did not say where".
    if permission == SENDS_EXECUTE and not integration.may_send_unattended:
        logger.warning(
            "api: refused a send for integration %s — not flagged for "
            "unattended sending", integration.id,
        )
        raise ApprovalRequired()

    if is_brand_scoped(permission):
        brand_id = _declared_brand(request)
        if brand_id is None:
            logger.warning(
                "api: refused %s for integration %s — %s is brand-scoped and no "
                "%s header was sent",
                permission, integration.id, permission, BRAND_HEADER,
            )
            raise BrandNotDeclared()
        if not has_permission(db, integration, permission, brand_id=brand_id):
            raise NotAuthorised(permission)
        return integration

    if not has_permission(db, integration, permission):
        raise NotAuthorised(permission)
    return integration
