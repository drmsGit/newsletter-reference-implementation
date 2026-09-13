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
from app.auth.policy import UNMAPPED, required_permission
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
        if not has_permission(db, user, permission):
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

    if not has_permission(db, user, permission):
        raise NotAuthorised(permission)
    return user
