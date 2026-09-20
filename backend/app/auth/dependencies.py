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
from app.auth.policy import (
    APPROVABLE_ROUTES, PROVIDER_SIGNED, UNMAPPED, required_permission,
)
from app.auth.integrations import authenticate, record_auth_failure
from app.auth.service import (
    SESSION_COOKIE,
    csrf_token_for,
    ensure_default_brand,
    has_permission,
    permissions_for,
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
    """A machine asked to fire a send it is not flagged to fire unattended.

    ADR-166 point 5: such a send "lands in ADR-142 §4's approval surface — the
    same pending-action mechanism, the same inbox, the same history".

    **It is a queue now, not a refusal.** Between 2026-09-18 and 2026-09-19
    this raised an outright 403, because the approval surface did not exist and
    storing the flag while letting the send through would have shipped
    something that looks like a control and is not. The surface exists, so the
    default described in point 5 finally means what it says.

    The exception carries what the handler needs to build the held request. It
    is raised inside a dependency, and a session that has raised there may be in
    a rollback state, so the row is created by the handler with a session of its
    own rather than here.
    """

    def __init__(
        self,
        *,
        action_key: str | None = None,
        payload: dict | None = None,
        integration_id: int | None = None,
        brand_id: int | None = None,
    ):
        super().__init__(action_key or "approval required")
        #: None when the route has no entry in `APPROVABLE_ROUTES`. There is
        #: then nothing to queue into, and the handler refuses outright — the
        #: pre-2026-09-19 behaviour, kept as the fail-closed case rather than
        #: quietly letting an unmapped send through.
        self.action_key = action_key
        self.payload = payload or {}
        self.integration_id = integration_id
        self.brand_id = brand_id


class AmbiguousPrincipal(Exception):
    """A request carried both a machine credential and a session cookie.

    ADR-168 point 4: refused outright rather than silently preferring one. The
    cost of preferring is not ambiguity in the guard — a guard can always pick —
    it is that the audit row then names a principal nobody can predict from
    reading the request. Refusing is the only answer that keeps "who acted"
    derivable from what was sent.
    """


class ApiCsrfFailed(Exception):
    """A cookie-authenticated JSON write arrived without a valid CSRF token."""


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


def _session_brand(request: Request) -> int | None:
    """A person's working brand, already resolved by the middleware.

    Read rather than recomputed: `attach_current_user` resolves it onto
    `request.state` for every request including these, so asking again would be
    a second query for an answer the request is already carrying.
    """
    brand = getattr(request.state, "current_brand", None)
    return brand["id"] if brand else None


def working_brand(request: Request) -> int:
    """The brand this request is working in (ADR-172 point 1).

    The consumer half of the guard above: `enforce_api_policy` resolves the
    brand once and writes it to `request.state.working_brand_id`, and a
    brand-owned route asks for it with `Depends(working_brand)`.

    **It raises rather than defaulting**, which is the whole point. The three
    routers that needed a brand before this existed each grew a private
    `_request_brand` helper falling back to `ensure_default_brand` — so a
    request that could not say which brand it meant wrote to the default one
    instead of being refused. ADR-172 point 3 forbids exactly that on this
    plane: a fallback "would work right up until it holds two, and would fail
    by silently acting on the wrong brand rather than by refusing".

    `working_brand_id` is `None` only when nothing resolved one — no session
    and no `X-Brand`. With enforcement off the guard sets it before returning,
    so this is reachable there too.
    """
    brand_id = getattr(request.state, "working_brand_id", None)
    if brand_id is None:
        raise BrandNotDeclared()
    return brand_id


class MachineRefused(Exception):
    """Raised when a bearer credential reaches a route only a person may use.

    Its own exception rather than a `NotAuthorised`, because it is not about
    permissions at all: the credential may hold every grant there is and still
    be refused here. Conflating the two would tell an operator to go and fix a
    permission that is already correct.
    """


def require_person(request: Request, db: Session = Depends(get_db)) -> None:
    """Refuse a machine credential on a route that only a person may use.

    **The one place this applies is approving** (ADR-166 point 5, as ADR-168's
    2026-09-19 addendum re-read it). A machine may *request* approval and may
    never grant it — an integration that can approve its own held request has
    defeated the mechanism it was held by.

    That property was previously kept by there being no route at all, which was
    true of the machine plane and became wrong for people when ADR-168 put them
    on it: it said the React client could not work an approval inbox. The
    property is the same; what enforces it is now a guard rather than an
    absence, which is also the sharper thing to test.

    Checked from the request rather than from whatever `enforce_api_policy`
    resolved, deliberately: this reads as "is there a bearer credential here",
    which is the actual question, and does not depend on the guard having run
    first or on a shape it might later stop writing.
    """
    if _machine_credential(request) is not None:
        logger.warning(
            "api: refused %s %s — a machine credential may not approve",
            request.method, request.url.path,
        )
        raise MachineRefused()


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
    """One guard over the JSON API, for **two kinds of principal** (ADR-168).

    A machine credential first — `Authorization: Bearer <key_id>.<secret>` —
    and failing that the `nra_session` cookie, resolved through
    `user_for_token`. The principal that comes out is the `UserDB |
    IntegrationDB` union `permissions_for` already dispatches on, so adding a
    second way to say *who* changes the credential reader and nothing below it.
    `policy.py` and `permissions_for` are untouched, which is ADR-166 point 1's
    promise kept in fact rather than in intent.

    **This docstring used to say the opposite, and celebrated it.** Between
    2026-09-18 and 2026-09-19 the plane took machine credentials only, on the
    reasoning that refusing cookies "buys the CSRF question outright" — no
    ambient credential, nothing for a cross-site request to abuse. That was
    true and it left the React manager client with no way to authenticate at
    all, which ADR-168 answers. The sentence is removed rather than softened:
    CSRF is now a control this codebase must get right and keep right, defended
    by `enforce_api_csrf` beside this guard, and a docstring that still read as
    reassurance would be the most expensive kind of stale comment.

    **Both credentials at once is refused** (point 4), not silently resolved.
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
        # **The working brand still has to exist here.** ADR-172 point 3
        # refuses a brand-owned operation that cannot resolve one, and nothing
        # below this line runs with enforcement off — so without this, every
        # brand-owned JSON route would refuse in the one posture that exists to
        # make a broken deployment fixable.
        #
        # This is point 3's own carve-out — "access control is switched off" is
        # one of the exactly two conditions it names as legitimate — applied
        # where it is legitimate, rather than `working_brand_id`'s fallback
        # lifted onto this plane wholesale. Decided 2026-09-19 alongside the
        # ADR, because it is adjacent to point 3 rather than part of it.
        #
        # It is the ONLY path on this plane that chooses a default brand, and
        # `test_the_auth_off_default_is_unreachable_with_enforcement_on` is
        # what keeps it that way.
        request.state.working_brand_id = (
            _declared_brand(request) or ensure_default_brand(db).id
        )
        return None

    credential = _machine_credential(request)
    session_token = request.cookies.get(SESSION_COOKIE)

    # ADR-168 point 4. Checked before either is resolved, so the refusal does
    # not depend on which one happened to be valid.
    if credential is not None and session_token:
        logger.warning(
            "api: refused %s %s — both a machine credential and a session "
            "cookie were sent", request.method, template,
        )
        raise AmbiguousPrincipal()

    principal = None
    if credential is not None:
        key_id, secret = credential
        principal = authenticate(db, key_id, secret)
        if principal is None:
            record_auth_failure(
                db, key_id, request.client.host if request.client else None,
            )
            raise NotAuthenticated()
    elif session_token:
        principal = user_for_token(db, session_token)

    if principal is None:
        raise NotAuthenticated()
    integration = principal  # the name the rest of this function already uses

    if permission == UNMAPPED:
        logger.warning(
            "api: refused %s %s — no policy entry. Add one in app/auth/policy.py.",
            request.method, template,
        )
        raise NotAuthorised(permission)

    # **Authorisation first, then the approval gate.** The order here was the
    # other way round until 2026-09-19, and it was correct for a refusal and
    # wrong for a queue.
    #
    # The comment that stood here read "you may not do this at all outranks you
    # did not say where", which argued for checking the unattended-send flag
    # before anything else. That reasoning does not survive the flag becoming a
    # queue: `ApprovalRequired` is not a "may not", it is a "not yet", and it
    # now HANDS OUT something — a held request a human is asked to approve.
    #
    # Left in the old order it would be privilege escalation through the queue:
    # an integration holding no `sends.execute` grant at all hit the flag check
    # before `has_permission`, so as a queue it could mint a pending send for a
    # person to approve. Harmless while both answers were 403; not harmless now.
    #
    # The brand moves up for the same reason. It was resolved after, so a queued
    # request would have carried `brand_id = NULL` and been invisible in every
    # brand's inbox — a send that looks accepted and that nobody can ever see.
    # **Context first, then authorisation — they are two questions.**
    #
    # Until 2026-09-19 they were one line: the brand was resolved only inside
    # `if is_brand_scoped(permission)`, so a request whose permission was
    # platform-level never resolved a brand at all. Every GET maps to `view`,
    # `view` is platform-level, and the result was that no read on this plane
    # had a working brand — which is why `GET /content/` returned every brand's
    # rows to anybody. ADR-172 point 1 separates them: the brand a request is
    # working in is established for EVERY request, and whether a permission is
    # checked against that brand stays the question it was.
    #
    # **Where it comes from depends on the principal**, and that asymmetry is
    # ADR-166 point 8's, not a new one: "a human's working brand comes from the
    # brand switcher and rides in the session; a machine has no session to carry
    # one, so it states one per request." The middleware has already resolved a
    # person's onto `request.state`, so the SPA sends no `X-Brand` and must not
    # be asked to.
    brand_id = _declared_brand(request) if credential else _session_brand(request)

    # **Resolved once and reused.** `permissions_for` narrowed to a brand is
    # both "what may this principal do here" and — by being non-empty — "does
    # it hold anything here at all". Asking once keeps the brand-scoped path at
    # the single query it has always been; only the platform-level path pays a
    # second, and only when a brand was declared.
    held_here = permissions_for(db, principal, brand_id) if brand_id is not None else set()

    # **ADR-172 point 2.** A brand-scoped permission implies this check —
    # `has_permission` against the declared brand fails without a grant there.
    # A platform-level one does not, because it is checked with no brand at
    # all: without this, a machine holding nothing but `view` could declare any
    # brand in `X-Brand` and read it, which replaces one leak with a more
    # convincing one. On reads the FILTER enforces the boundary rather than the
    # permission check, and this is the only thing standing between a declared
    # brand and the rows selected against it.
    if brand_id is not None and not held_here:
        logger.warning(
            "api: refused %s %s for principal %s — declared brand %s, holds no "
            "grant on it",
            request.method, template, getattr(principal, "id", None), brand_id,
        )
        raise NotAuthorised(permission)

    # **Its own attribute, not `current_brand`.** The middleware builds
    # `request.state.current_brand` as a presentation summary — it carries
    # `switchable`, and `base.html` reads it. Overwriting that with `{"id": ...}`
    # was survivable while it happened only on brand-scoped writes; under point
    # 1 it would happen on every request, turning a rare shape collision into a
    # universal one. The ADR's own split between context and authorisation,
    # applied to the state object rather than only to this function.
    request.state.working_brand_id = brand_id

    if is_brand_scoped(permission):
        if brand_id is None:
            logger.warning(
                "api: refused %s for principal %s — %s is brand-scoped and no "
                "working brand could be resolved",
                permission, getattr(principal, "id", None), permission,
            )
            raise BrandNotDeclared()
        if permission not in held_here:
            raise NotAuthorised(permission)
    elif not has_permission(db, principal, permission):
        raise NotAuthorised(permission)

    # ADR-166 point 5. Reached only by a caller that is authenticated,
    # authorised for this action on this brand, and has said which brand.
    # Only an integration can be held for approval — a person firing a send is
    # the approval. `may_send_unattended` does not exist on a user.
    if (
        credential
        and permission == SENDS_EXECUTE
        and not integration.may_send_unattended
    ):
        logger.info(
            "api: holding a send for integration %s — not flagged for "
            "unattended sending", integration.id,
        )
        raise ApprovalRequired(
            action_key=APPROVABLE_ROUTES.get(template),
            # Path parameters only. The JSON body has already been consumed by
            # the time a dependency runs, and re-reading it is its own problem.
            payload=dict(request.scope.get("path_params") or {}),
            integration_id=integration.id,
            brand_id=brand_id,
        )

    return integration


API_CSRF_HEADER = "X-CSRF-Token"


async def enforce_api_csrf(request: Request) -> None:
    """CSRF for the JSON plane, carried in a header (ADR-168 point 2).

    Compares `X-CSRF-Token` against `csrf_token_for(session_token)` with
    `secrets.compare_digest`. No storage, no column, no new secret to rotate:
    the token is derived from the session token rather than kept server-side,
    and is already domain-separated from `hash_secret` so it cannot collide
    with the session hash in `auth_sessions.token_hash`.

    **Skipped when there is no session cookie**, because a bearer-authenticated
    request carries no ambient credential — a cross-site page cannot make a
    browser attach an `Authorization` header it does not know. And
    `enforce_api_policy` refuses a request carrying both, so "has a cookie" and
    "is a machine" are mutually exclusive by the time this runs.

    **Why `enforce_csrf` could not be reused, in two independent ways.** It
    calls `await request.form()`, which against a JSON body returns an empty
    `FormData` rather than raising — so it would find no token and refuse every
    JSON write. And it returns early when there is no session cookie, so on a
    bearer-only request it is silently inert. A guard that refuses everything on
    one plane and does nothing on the other is not a guard that was reused; it
    is two bugs sharing a name.
    """
    if request.method not in _UNSAFE_METHODS:
        return

    session_token = request.cookies.get(SESSION_COOKIE)
    if not session_token:
        return

    submitted = (request.headers.get(API_CSRF_HEADER) or "").strip()
    expected = csrf_token_for(session_token)
    if not submitted or not secrets.compare_digest(submitted, expected):
        logger.warning(
            "api csrf: refused %s %s — token %s",
            request.method, request.url.path,
            "missing" if not submitted else "mismatched",
        )
        raise ApiCsrfFailed()
