import logging
import os
import re
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# What a shell-style variable name may contain. Anything else — a stray space, a
# zero-width character picked up from a paste — makes the name silently not the
# name you meant, which is invisible in every editor.
VALID_ENV_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _load_local_env() -> None:
    """Load backend/.env (gitignored) into the environment for local secrets
    like RESEND_API_KEY — so credentials never live in code or the DB. A real
    environment variable always wins. No dependency; see .env.example for the
    expected keys.

    Three rules exist because the failure mode of this function is *silence*:
    a key that is present but not loaded looks exactly like a bug in whatever
    needed it, and the search starts in the wrong place.

      - An empty value is ignored, never stored. The first occurrence of a key
        wins, so a leftover `KEY=` line would otherwise quietly shadow the real
        one further down the file.
      - A name that isn't a plain variable name is reported, with its invisible
        characters escaped — the one failure you cannot see by looking.
      - What was loaded is logged by *name* (never value), so startup states
        what it picked up instead of leaving you to infer it.

    A real environment variable still wins over the file — but an *empty* one
    does not, because an empty value is not a real value. That distinction
    matters under `uvicorn --reload`: the reloader's parent process holds the
    environment its children inherit, so a blank value read once at startup
    would otherwise be pinned there for the life of the parent, and no edit to
    this file could dislodge it without a full restart.
    """
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return

    loaded: list[str] = []
    empty: list[str] = []
    malformed: list[str] = []
    shadowed: list[str] = []

    for line in env_path.read_text().splitlines():
        line = line.lstrip("﻿").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if not VALID_ENV_KEY.match(key):
            malformed.append(repr(key))
            continue
        if not value:
            empty.append(key)
            continue
        # A non-empty variable already in the environment wins. An empty one is
        # treated as absent and replaced from the file.
        if os.environ.get(key):
            shadowed.append(key)
            continue

        os.environ[key] = value
        loaded.append(key)

    if loaded:
        logger.info(".env loaded: %s", ", ".join(sorted(loaded)))
    if shadowed:
        logger.info(
            ".env not applied (already set in the environment): %s",
            ", ".join(sorted(shadowed)),
        )
    if empty:
        logger.warning(".env ignored (no value): %s", ", ".join(sorted(empty)))
    if malformed:
        logger.warning(
            ".env ignored (not a valid variable name — note the escapes): %s",
            ", ".join(sorted(malformed)),
        )


_load_local_env()

from app.database import Base, engine, SessionLocal
from app.content.db_models import ContentRecordDB, CategoryDB, ContentCategoryAssignmentDB, ContentVersionDB
from app.content.router import router as content_router
from app.content.service import create_demo_content_if_empty

from app.campaigns.db_models import CampaignDB, VariantDB, ModuleInstanceDB, DecisionSlotDB, DecisionResolutionDB
from app.campaigns.router import router as campaigns_router

from app.rendering.router import router as rendering_router

from app.snapshots.db_models import SnapshotDB
from app.snapshots.router import router as snapshots_router

from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.delivery.router import router as delivery_router

from app.insight.db_models import EngagementEventDB
from app.insight.router import router as insight_router

from app.decision.router import router as decision_router

from app.recipients.db_models import (
    AddressabilityDB,
    ConsentEventDB,
    ConsentSyncLogDB,
    RecipientDB,
    SignalContributionDB,
)
from app.recipients.router import router as recipients_router

from app.providers.db_models import ProviderEventQuarantineDB
from app.ai.db_models import AIPromptDB, AIRunDB
from app.providers.router import router as provider_router

from app.modules.router import router as modules_router
from app.approvals.router import router as approvals_router
from app.auth.integrations_router import router as integrations_router
from app.settings.router import router as settings_router
from app.auth.router import context_router

from app.overrides.db_models import ContentOverrideDB
from app.overrides.router import router as overrides_router

from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB
from app.audience.router import router as audience_router

# Imported for metadata registration so create_all() knows the table —
# the audit log has no router of its own in this slice.
from app.audit.db_models import AuditEventDB  # noqa: F401
# Same reason, and the same absence of a router in this slice: the approvals
# spine ships wired to nothing, so `create_all` needs the import to know the
# table exists (ADR-142 §4).
from app.approvals.db_models import PendingActionDB  # noqa: F401
from app.approvals.service import pending_count as pending_approval_count
from app.settings.db_models import AppConfigDB

from app.auth.db_models import (
    BrandDB, LoginCodeDB, RoleAssignmentDB, RoleDB, RolePermissionDB, SessionDB, UserDB,
)
from app.auth.dependencies import (
    AmbiguousPrincipal, ApiCsrfFailed, ApprovalRequired, BrandNotDeclared,
    MachineRefused,
    CsrfFailed, NotAuthenticated, NotAuthorised,
    auth_enforced, enforce_api_csrf, enforce_api_policy, enforce_csrf,
    enforce_policy,
)
from app.auth.router import router as auth_router
from app.auth.router import session_router
from app.auth.service import (
    SESSION_COOKIE, bootstrap as bootstrap_auth, csrf_token_for,
    brands_for_user,
    current_brand_summary,
    current_user_summary,
    user_for_token,
)

from app.frontend.router import router as frontend_router

# --- OpenAPI / Swagger metadata -------------------------------------------
# Swagger (/docs) is the *endpoint reference* tier of the docs (see
# docs/architecture/Code/MOC - System Overview.md). It is generated from the
# routes, so it can't drift. The prose below just frames it and orders/labels
# the tag sections by architecture layer; the module & flow pages carry the
# "how modules connect" tier, and docstrings carry function internals.
API_DESCRIPTION = """
Endpoint reference for the **Newsletter Blueprint** backend — a vendor-neutral
reference architecture for email marketing systems.

**This page documents HTTP routes only.** For how the ~14 modules connect, the
end-to-end flows, and the internal service functions, see the Obsidian docs in
`docs/architecture/Code/` (start at *MOC - System Overview*). Function internals
live in the code's docstrings.

Endpoints are grouped by module, following the data flow: **sources** (content,
recipients) → **compose** (campaigns, modules) → **personalize** (decision,
overrides) → **audience** → **render** (rendering, snapshots) → **deliver**
(delivery, provider) → **learn** (insight). The **frontend** section at the end is
the older server-rendered Jinja admin UI (post/redirect/get), not a JSON API — it
is documented as a route index in `docs/architecture/Code/frontend.md`. The React
manager client (the top-level `frontend/` directory) is a consumer of the JSON
API above, documented in `docs/architecture/Code/manager-client.md`.
""".strip()

# Ordered by architecture layer; `frontend` (the /ui HTML routes) is deliberately
# last so the JSON API reads as one block above it.
TAGS_METADATA = [
    {"name": "content", "description": "Content catalog: reusable records, the category taxonomy, and content versions. Source of truth for *what can be said*."},
    {"name": "recipients", "description": "Local projection of CRM contacts + marketing consent + the signal-contribution log. Not a CRM."},
    {"name": "campaigns", "description": "Composition: campaigns, variants, module instances, decision slots, and the decision-resolution audit. Structure, not content."},
    {"name": "modules", "description": "The file-based module template registry (drop-a-file plugins). Read-only over `storage/modules/<channel>/`. Serves every channel — it takes a `channel` parameter that merely defaults to email."},
    {"name": "decision", "description": "The personalization engine: resolve a decision slot to content via pluggable strategies."},
    {"name": "overrides", "description": "Manager field-level edits on a module, logged against the system's original pick (trust loop)."},
    {"name": "audience", "description": "Audience groups from live rule blocks + manual pins, resolved consent-gated. (Prefix `/api/audience-groups`.)"},
    {"name": "rendering", "description": "Turn a variant's module stack into final, CSS-inlined HTML. Reads decisions, never executes them."},
    {"name": "snapshots", "description": "Freeze the render state (context + HTML) for reproducible, auditable sends. A snapshot ≠ a send."},
    {"name": "delivery", "description": "Plan and fire sends: send instances + per-recipient delivery executions, through a swappable provider."},
    {"name": "provider", "description": "Inbound feedback boundary: normalize + correlate provider webhooks (opens/clicks/bounces) to deliveries."},
    {"name": "insight", "description": "The learning loop: engagement → per-category signal contributions (decay-on-read)."},
    {"name": "frontend", "description": "The older server-rendered Jinja admin UI (post/redirect/get) — **not a JSON API**, and not the React manager client (that one consumes the JSON API above; see `docs/architecture/Code/manager-client.md`). Route index in `docs/architecture/Code/frontend.md`."},
]

# --- API documentation exposure (ADR-184, tasks 31 and 232) -----------------
# `/openapi.json`, `/docs` and `/redoc` belong to the app, not to a router, so
# no JSON guard ever reached them: an anonymous caller got the whole route
# inventory of an API this file calls guarded. Who may see them is now a
# deployment setting, because a reference architecture wants its contract
# legible (ADR-002) and the typed client is generated from it (ADR-170 point
# 4), while a deployed instance probably wants /docs closed.
API_DOCS_MODES = ("public", "signed_in", "off")
API_DOCS = (os.environ.get("API_DOCS") or "public").strip()
if API_DOCS not in API_DOCS_MODES:
    # Refused rather than defaulted: a typo in a setting that closes the docs
    # must not silently leave them open.
    raise RuntimeError(
        f"API_DOCS={API_DOCS!r} is not one of {', '.join(API_DOCS_MODES)} (ADR-184)."
    )

# Try-it-out sends the browser's cookies, so a person signed in on this origin
# can exercise guarded routes; a machine key goes into Authorize (task-232).
SWAGGER_UI_PARAMETERS = {"withCredentials": True, "persistAuthorization": True}

app = FastAPI(
    title="Newsletter Reference Architecture API",
    version="0.1.0",
    description=API_DESCRIPTION,
    openapi_tags=TAGS_METADATA,
    # Built-in routes only when public; `signed_in` serves its own guarded
    # copies below, and `off` serves none.
    openapi_url="/openapi.json" if API_DOCS == "public" else None,
    docs_url="/docs" if API_DOCS == "public" else None,
    redoc_url="/redoc" if API_DOCS == "public" else None,
    swagger_ui_parameters=SWAGGER_UI_PARAMETERS,
)


def _openapi_with_security() -> dict:
    """The generated document, plus the authentication that actually exists.

    Without this the document said nothing about authentication, so Swagger had
    no Authorize control and every guarded route answered 401 from Try-it-out.
    Two ways in, as `enforce_api_policy` accepts them: a session cookie with
    the CSRF header for writes (ADR-168), or a machine key with its declared
    brand (ADR-166). Sign-in routes and provider webhooks need neither — the
    former are how a credential is obtained, the latter are signed by the
    provider — and are marked so.
    """
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi

    from app.auth.dependencies import BRAND_HEADER
    from app.auth.service import SESSION_COOKIE

    schema = get_openapi(
        title=app.title, version=app.version, description=app.description,
        routes=app.routes, tags=app.openapi_tags,
    )
    schema.setdefault("components", {})["securitySchemes"] = {
        "SessionCookie": {"type": "apiKey", "in": "cookie", "name": SESSION_COOKIE,
                          "description": "Sign in at /manager first; the browser sends it."},
        "CsrfToken": {"type": "apiKey", "in": "header", "name": "X-CSRF-Token",
                      "description": "Writes with a session. The value is in GET /auth/session."},
        "MachineKey": {"type": "http", "scheme": "bearer",
                       "description": "An integration key, `key_id.secret` (ADR-166)."},
        "Brand": {"type": "apiKey", "in": "header", "name": BRAND_HEADER,
                  "description": "The brand a machine key acts in (ADR-166 point 8)."},
    }
    schema["security"] = [{"SessionCookie": [], "CsrfToken": []}, {"MachineKey": [], "Brand": []}]
    public_paths = {route.path for route in session_router.routes}
    for path, operations in schema.get("paths", {}).items():
        if path in public_paths or path.startswith("/provider/webhooks/"):
            for operation in operations.values():
                if isinstance(operation, dict):
                    operation["security"] = []
    app.openapi_schema = schema
    return schema


app.openapi = _openapi_with_security


templates = Jinja2Templates(directory="app/templates")

# ADR-181. Asked BEFORE create_all, because afterwards every database has
# tables: an empty one is being built from the models and is at head by
# construction; one that already holds tables has a history only its ledger
# knows. Importing the module registers the ledger table for create_all too.
from app import schema_migrations

_built_from_nothing = not schema_migrations.application_tables_exist(engine)

Base.metadata.create_all(bind=engine)


with SessionLocal() as db:
    # First, before anything writes: refuse to run against a database that is
    # behind its models. On 2026-09-20 a missed column rename started cleanly
    # and returned a 500 on sign-in; this stops at boot and names the file.
    schema_migrations.assert_no_pending_migrations(
        db, built_from_nothing=_built_from_nothing,
    )

    # Seed the default brand, the three preset roles and — while the user table
    # is empty — an initial Admin from INITIAL_ADMIN_EMAIL. Without that last
    # step nobody could ever sign in (ADR-151).
    #
    # MUST run before create_demo_content_if_empty: `ensure_default_brand` lives
    # in here, and content now carries a NOT NULL brand (ADR-150 point 2). The
    # other order was harmless until 2026-09-15 and would now be a crash on
    # first boot against an empty database — the one case nobody tests twice.
    bootstrap_auth(db)
    create_demo_content_if_empty(db)

    # ADR-162 point 5's startup assertion. A manifest whose declared channel
    # contradicts the directory it sits in would otherwise surface as a manager
    # being offered a module the renderer cannot take — so discovery is forced
    # here, where a misfiling stops the process, rather than at whichever
    # request happens to touch the registry first.
    from app.channels.registry import list_channels
    from app.modules.registry import assert_manifests_load, list_manifests

    assert_manifests_load()

    # task-20: a channel whose manifest does not parse is skipped — unless
    # variants already use it, where skipping turns one typo into a failure on
    # every request that touches those variants.
    from app.campaigns.db_models import VariantDB
    from app.channels.registry import assert_used_channels_load

    assert_used_channels_load({c for (c,) in db.query(VariantDB.channel).distinct()})
    logger.info(
        "channels: %s",
        ", ".join(
            f"{c.name} ({len(list_manifests(c.name))} modules, "
            f"max {c.max_modules if c.max_modules is not None else 'unbounded'})"
            for c in list_channels()
        ) or "none registered",
    )

    from app.auth.dependencies import auth_enforced
    from app.auth.service import cookie_secure

    if not cookie_secure():
        logger.warning(
            "auth: AUTH_COOKIE_INSECURE is set — the session cookie has NO Secure "
            "flag, so any plain-HTTP request transmits the session token in clear. "
            "This exists for browsers that refuse a Secure cookie on "
            "http://localhost. Never set it on a reachable host."
        )

    if not auth_enforced(db):
        logger.warning(
            "auth: access control is NOT enforced — sessions and roles work, but no "
            "route refuses anyone. This is no longer the default; someone turned it "
            "off at /ui/users. Turn it back on there."
        )
    else:
        from app.auth.service import dev_code_visible, system_mail_provider

        if dev_code_visible():
            logger.info(
                "auth: access control is enforced. Sign-in codes are written to THIS "
                "log (system mail provider is '%s'), so read your code from here.",
                system_mail_provider(),
            )
        else:
            logger.info(
                "auth: access control is enforced and sign-in codes are emailed via "
                "'%s'. If mail breaks, nobody can sign in — recover by setting "
                "AUTH_DEV_SHOW_CODE=true, which logs the code here so you can sign "
                "in as yourself.",
                system_mail_provider(),
            )


@app.middleware("http")
async def attach_current_user(request: Request, call_next):
    """Make the signed-in user available to every template, including
    unguarded ones.

    Without this the base layout cannot render a sign-out control, and a user
    whose role cannot reach `/ui/users` has no way to sign out at all — which
    is exactly what happened: a Viewer had to use the browser back button.
    """
    db = SessionLocal()
    try:
        request.state.current_user = current_user_summary(
            db, request.cookies.get(SESSION_COOKIE)
        )
        # The layout needs this too: with enforcement off nobody signs in, so
        # hiding the navigation from anonymous visitors would hide it from
        # everybody and leave the app unusable.
        request.state.auth_enforced = auth_enforced(db)
        # Every form needs this; deriving it here means no route has to
        # remember to put it in its template context.
        request.state.csrf_token = csrf_token_for(request.cookies.get(SESSION_COOKIE))
        # The working brand (ADR-150 point 2), for the same reason as the two
        # above: there are 21 TemplateResponse sites and no shared context
        # helper, so threading it through per-route dicts would be 21 chances
        # to forget. A plain dict, never the ORM object — this session closes
        # immediately below and a committed instance expires on first attribute
        # access in the template.
        request.state.current_brand = current_brand_summary(
            db, request.cookies.get(SESSION_COOKIE)
        )
        # Only paid for when the switcher will actually render. A single-brand
        # company never reaches this query at all.
        request.state.brand_options = (
            [
                {"id": b.id, "name": b.name}
                for b in brands_for_user(
                    db, user_for_token(db, request.cookies.get(SESSION_COOKIE))
                )
            ]
            if request.state.current_brand and request.state.current_brand["switchable"]
            else []
        )
        # The approvals badge (ADR-142 §4). Computed here for the reason the
        # three above are: the base layout needs it on every page, and there is
        # no shared context helper to hang it off. One indexed COUNT against the
        # working brand — never a load-and-filter — and it reads `expires_at`
        # rather than `status`, so a request whose deadline has passed stops
        # being counted the moment it passes, with or without a sweep.
        request.state.pending_approvals = pending_approval_count(
            db,
            request.state.current_brand["id"] if request.state.current_brand else None,
        )
    finally:
        db.close()
    return await call_next(request)


def _wants_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "")


@app.exception_handler(NotAuthenticated)
def _not_authenticated(request: Request, exc: NotAuthenticated):
    """Send a browser to sign-in, remembering where it was going.

    Branches on what the client asked for, not on the URL: an earlier version
    tested for a `/ui/` prefix and handed the dashboard at `/` a raw JSON 401,
    that being the one UI route without the prefix.
    """
    if not _wants_html(request):
        return JSONResponse({"detail": "Authentication required"}, status_code=401)

    target = request.url.path
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(
        url=f"/ui/login?next={quote(target, safe='')}", status_code=303
    )


@app.exception_handler(CsrfFailed)
def _csrf_failed(request: Request, exc: CsrfFailed):
    """A refused form is a 403 with an explanation, not a blank failure.

    The realistic cause in this codebase is not an attack but a form added
    without the hidden field, so the message says that outright — a developer
    hitting this should not have to go looking for what "403" meant.
    """
    detail = (
        "This form was refused because its security token was missing or stale. "
        "Reload the page and try again. If you are developing: every state-"
        "changing form needs the hidden csrf_token field."
    )
    if not _wants_html(request):
        return JSONResponse({"detail": detail}, status_code=403)
    return templates.TemplateResponse(
        request, "forbidden.html",
        {"title": "Form refused", "permission": "a valid CSRF token"},
        status_code=403,
    )


@app.exception_handler(AmbiguousPrincipal)
def _ambiguous_principal(request: Request, exc: AmbiguousPrincipal):
    return JSONResponse(
        {"detail": (
            "This request carried both a machine credential and a session "
            "cookie. Send one. Preferring either would make the audit trail "
            "name a principal you cannot predict from reading the request."
        )},
        status_code=400,
    )


@app.exception_handler(ApiCsrfFailed)
def _api_csrf_failed(request: Request, exc: ApiCsrfFailed):
    return JSONResponse(
        {"detail": (
            "This request was refused because its CSRF token was missing or "
            "stale. A session-authenticated write to the JSON API must send "
            "the X-CSRF-Token header. A machine credential needs no token."
        )},
        status_code=403,
    )


@app.exception_handler(ApprovalRequired)
def _approval_required(request: Request, exc: ApprovalRequired):
    """Hold the action and tell the caller where it went (ADR-142 §4).

    "An autonomous flow calls an action, receives 'pending approval', and
    **finishes**." So this answers **202 Accepted** with the id of the held
    request and a link into the inbox — not 403, and not a long-running
    response the caller has to keep open.

    **The row is created here, with a session of its own.** The dependency that
    raised may have left its session in a rollback state, and a dependency with
    a side effect is harder to reason about than one that only refuses.
    """
    if exc.action_key is None:
        # No entry in APPROVABLE_ROUTES, so there is nothing to queue into.
        # Fail closed — this is the behaviour every send had before the
        # approval surface existed, kept deliberately rather than letting an
        # unmapped route through.
        return JSONResponse(
            {"detail": (
                "This integration is not permitted to send without approval, "
                "and this route has no approvable action mapped to it, so the "
                "request cannot be held for review. Enable unattended sending "
                "for this integration, or add the route to APPROVABLE_ROUTES."
            )},
            status_code=403,
        )

    from app.approvals import service as approvals
    from app.approvals.actions.registry import get_action, get_action_module
    from app.approvals.db_models import OPEN, PendingActionDB
    from app.audit.service import ACTOR_INTEGRATION

    meta = get_action(exc.action_key)
    module = get_action_module(exc.action_key)
    # By convention the subject is the path parameter named after the action's
    # declared subject type — `send_instance` → `send_instance_id`. Stated as a
    # convention rather than inferred loosely, so an action whose subject is not
    # in its path says so by declaring none.
    subject_id = exc.payload.get(f"{meta.subject_type}_id") if meta else None

    db = SessionLocal()
    try:
        # **The subject must be in the caller's brand, or nothing is held**
        # (task-9, ADR-142 addendum of 2026-09-29, second). The guard that
        # raised this cannot know what the path parameter names, so a caller in
        # brand A naming brand B's send used to get a held request anyway — and
        # its subject id occupied B's slot in the one-open-request index, which
        # has no brand in its key, so B's own request was answered with A's row.
        if meta is not None and meta.subject_type and subject_id is not None:
            if module is None or not callable(getattr(module, "subject_in_brand", None)):
                # Fail closed, like the unmapped route above: an action that
                # names a subject but cannot say whose it is must not be held.
                return JSONResponse(
                    {"detail": (
                        f"'{exc.action_key}' names a {meta.subject_type} but "
                        "cannot confirm it belongs to the declared brand, so "
                        "the request cannot be held for review."
                    )},
                    status_code=403,
                )
            if not module.subject_in_brand(db, subject_id, brand_id=exc.brand_id):
                # Word for word what the unattended path answers for a foreign
                # or missing send (`send_send_instance` → 409), so the two
                # paths cannot be compared to learn that the id exists in
                # another brand.
                noun = "".join(part.capitalize() for part in meta.subject_type.split("_"))
                return JSONResponse(
                    {"detail": f"{noun} {subject_id} not found"}, status_code=409,
                )

        summary = ""
        if module is not None and hasattr(module, "summarise") and subject_id:
            try:
                # The brand the request is being raised in, so a summary
                # frozen onto the row cannot quote another brand's record
                # (ADR-172 point 6).
                summary = module.summarise(db, subject_id, brand_id=exc.brand_id)
            except Exception:  # pragma: no cover - a summary must not block
                logger.warning("could not summarise %s", exc.action_key, exc_info=True)
        try:
            held = approvals.request_approval(
                db, exc.action_key,
                payload=exc.payload,
                summary=summary or (meta.label if meta else exc.action_key),
                requested_by_type=ACTOR_INTEGRATION,
                requested_by_id=exc.integration_id,
                brand_id=exc.brand_id,
                subject_id=subject_id,
            )
        except approvals.SubjectRequired as refusal:
            # Fail closed, like the unmapped route above: a request that cannot
            # be kept one of a kind is not held (task-15).
            return JSONResponse(
                {"detail": f"This request cannot be held for review: {refusal}"},
                status_code=403,
            )
        except approvals.DuplicateRequest:
            # An orchestrator that retries a held call should get the same
            # answer, not an error: the request IS pending, and saying so keeps
            # the retry idempotent instead of making it look like a failure.
            held = db.query(PendingActionDB).filter(
                PendingActionDB.action_key == exc.action_key,
                PendingActionDB.subject_type == (meta.subject_type if meta else None),
                PendingActionDB.subject_id == subject_id,
                PendingActionDB.status.in_(OPEN),
                # Never answer one brand with another brand's request. Without
                # this, brand B retrying its own send was handed brand A's
                # pending_action_id (task-9).
                PendingActionDB.brand_id == exc.brand_id,
            ).first()
            if held is None:
                # The slot is taken by a request from another brand — possible
                # only for rows created before the subject check above existed.
                # Said without an id, because the id is not this caller's.
                return JSONResponse(
                    {"detail": (
                        "A request for this is already held and cannot be "
                        "reused from here. It lapses at its deadline."
                    )},
                    status_code=409,
                )
        return JSONResponse(
            {
                "status": "pending_approval",
                "pending_action_id": held.id,
                "expires_at": held.expires_at.isoformat() if held.expires_at else None,
                "review": f"/ui/approvals/{held.id}",
                "detail": (
                    "This integration may not send without approval, so the "
                    "send is held. A person with the right permission approves "
                    "it in the app — there is deliberately no way to approve "
                    "over the API."
                ),
            },
            status_code=202,
        )
    finally:
        db.close()


@app.exception_handler(MachineRefused)
def _machine_refused(request: Request, exc: MachineRefused):
    """403, and it says which kind of refusal it is.

    Not a permission problem — the credential may hold every grant there is and
    still be refused — so the message must not send an operator off to widen a
    grant that is already correct.
    """
    return JSONResponse(
        {"detail": (
            "A machine credential may request approval and may not grant it "
            "(ADR-166 point 5). Approving requires a signed-in person; sign in "
            "and decide it in the app."
        )},
        status_code=403,
    )


@app.exception_handler(BrandNotDeclared)
def _brand_not_declared(request: Request, exc: BrandNotDeclared):
    """Say which of the two refusals this is (ADR-166 point 8's mitigation).

    Without this the caller sees the same 403 they would get for lacking the
    permission, and "the integration that worked yesterday and stopped because
    somebody scoped it to a second brand" reads as "permissions broke".
    """
    return JSONResponse(
        {"detail": (
            "This action is brand-scoped. Send the brand you are acting in as "
            "an X-Brand header carrying the brand id. The header selects which "
            "grant is checked — it grants nothing on its own."
        )},
        status_code=400,
    )


@app.exception_handler(NotAuthorised)
def _not_authorised(request: Request, exc: NotAuthorised):
    """A browser gets a page it can navigate away from, not a dead end.

    The JSON body left a signed-in user with no navigation and no way back —
    effectively logged out of a system they were still authenticated to.
    """
    detail = f"This account lacks the '{exc.permission}' permission"
    if not _wants_html(request):
        return JSONResponse({"detail": detail}, status_code=403)
    return templates.TemplateResponse(
        request, "forbidden.html",
        {"title": "Not allowed", "permission": exc.permission},
        status_code=403,
    )


# CSRF over the auth router too. It carries explicit `require_permission`
# guards on thirteen user- and role-administration forms and had NO CSRF until
# 2026-09-18, because `enforce_csrf` was wired onto the frontend router alone —
# so the most privileged forms in the system were the only unprotected ones,
# while launch gate 4 recorded "CSRF on all 62 forms". The sign-in routes below
# it are unaffected: `enforce_csrf` skips a request with no session cookie,
# which is what an anonymous sign-in POST is.
app.include_router(auth_router, dependencies=[Depends(enforce_csrf)])

# The JSON session surface (ADR-168), on its own router with the HEADER-borne
# CSRF guard rather than the form one. Without this pair the manager client has
# no way to *obtain* the session cookie ADR-168 decided it authenticates with,
# which made that record unusable in practice until 2026-09-19.
app.include_router(session_router, dependencies=[Depends(enforce_api_csrf)])

# One guard over the whole UI, deriving the required permission from the route
# via app/auth/policy.py: reads need `view`, writes are looked up in the policy
# table, and a write with no policy entry is refused. Applied here rather than
# inside app/frontend so that module stays ignorant of authentication, and so
# the decision is visible in one place instead of 57 route decorators.
#
# Sign-in itself lives in auth_router, above, whose login routes are
# deliberately open and whose /ui/users routes carry their own explicit guard.
#
app.include_router(
    frontend_router,
    # CSRF first: a forged request should be refused before its permissions are
    # even considered, and before any handler runs.
    dependencies=[Depends(enforce_csrf), Depends(enforce_policy)],
)

# The JSON API — the machine plane, guarded since 2026-09-18 (ADR-166, launch
# gate 3). Until then these routers were included with no guard at all while
# the UI above them was locked, which ADR-166's Context calls worse than either
# state alone "because it looks protected": 69 routes, 36 of them
# state-changing, including one that fires real mail and one that writes the
# consent record a UWG §7 complaint is answered with.
#
# `enforce_api_policy` accepts **either** a platform-issued integration
# credential or a person's session cookie (ADR-168), never both at once. The
# narrowing that stood here from 2026-09-18 to 2026-09-19 — machine credentials
# only — was what left the React manager client unable to authenticate at all.
#
# **`enforce_api_csrf` is on EVERY router in this list, and that is the line to
# be careful about.** ADR-168's own Negative section names it: `enforce_csrf`
# was once wired onto the frontend router alone, which left the thirteen most
# privileged forms in the system unprotected while LAUNCH-GATES recorded gate 4
# as "CSRF on all 62 forms". A guard on eleven of twelve routers fails
# identically and reports identically. It is one line and it is the line that
# matters.
#
# It is a *header*-borne token rather than the form-borne one, because
# `enforce_csrf` reads the request as a form — against a JSON body that yields
# an empty FormData rather than an error, so reusing it would refuse every JSON
# write while doing nothing at all on a bearer request.
#
# `POST /provider/webhooks/resend` is inside `provider_router` and is exempt by
# policy rather than by wiring: the table maps it to PROVIDER_SIGNED and the
# guard stands aside so the route's own Svix check runs (ADR-166 point 6). The
# exemption is legible in `app/auth/policy.py` — where somebody auditing the
# policy would actually look — instead of hiding here.
# **Which of these own brand-scoped rows is recorded in `app/auth/policy.py`'s
# `BRAND_OWNED`**, not here — the classification is policy, and this is wiring.
# A test asserts the two agree, so a thirteenth router cannot arrive unclassified
# and leave the boundary looking uniform while it is not (ADR-172 point 7).
_api = [Depends(enforce_api_csrf), Depends(enforce_api_policy)]
app.include_router(content_router, dependencies=_api)
app.include_router(campaigns_router, dependencies=_api)
app.include_router(rendering_router, dependencies=_api)
app.include_router(snapshots_router, dependencies=_api)
app.include_router(delivery_router, dependencies=_api)
app.include_router(insight_router, dependencies=_api)
app.include_router(decision_router, dependencies=_api)
app.include_router(recipients_router, dependencies=_api)
app.include_router(provider_router, dependencies=_api)
app.include_router(modules_router, dependencies=_api)
app.include_router(overrides_router, dependencies=_api)
app.include_router(audience_router, dependencies=_api)
# **Thirteenth, and the only one with a route a machine may not reach.**
# `require_person` sits on approve and reject rather than on the router: the
# inbox is readable by anything that may read, and it is granting that ADR-166
# point 5 reserves for people.
app.include_router(approvals_router, dependencies=_api)
# The session's own context — who is signed in and which brand they work in.
# **Guarded, unlike the three `session_router` routes**, which are PUBLIC_AUTH
# because you cannot require a session in order to obtain one. These read and
# change a session that already exists.
app.include_router(context_router, dependencies=_api)
# Person-only administration (ADR-166 addendum 2026-10-02): `require_person_with`
# sits on the router, so every route, including the GETs, refuses a machine.
app.include_router(integrations_router, dependencies=_api)
# Reads are `view`; writes are people only and `settings.manage` (ADR-150's
# addendum of 2026-10-02), with `ai.run` too for prompts and models.
app.include_router(settings_router, dependencies=_api)


# --- the manager client (ADR-170 point 1, ADR-168 point 3) ------------------
#
# **This is what makes same-origin true in production rather than aspirational.**
# ADR-168 point 3 states that FastAPI serves the built SPA, which is what keeps
# the session cookie at `samesite="lax"` and `CORSMiddleware` out of this file.
# Vite proxies to this app in development; here the app serves Vite's output, so
# the browser sees one origin in both cases.
#
# **Mounted under `/manager`, not `/`, because the Jinja UI still owns the front
# door.** `frontend/router.py` registers a `dashboard` route at `/` and is
# registered first, so it wins whatever is written here -- taking `/` would mean
# moving the existing product's home page before the SPA has screens to replace
# it with. `/app` lets both run untouched, and the day `frontend/router.py` is
# deleted this prefix goes with it.
#
# Scoping under one prefix also removes a problem the root-level version had:
# a catch-all at `/` has to refuse every path the API owns, or an unknown API
# route quietly answers with HTML to a caller parsing JSON. Under one prefix
# that collision cannot arise.
#
# **The word is `manager`, and `/app` was rejected for two reasons.** It read
# ambiguously against `backend/app/`, which is this codebase's Python package
# and not a URL. And `/app` is a `startswith` prefix of `/approvals`, which
# matters because `policy.py` matches route templates with a bare `startswith`
# where order is semantics -- so a single `("/app", ...)` line added to
# `WRITE_POLICY` would silently reprice every approvals route. That shape has
# already produced three defects in this table; `test_policy_prefixes.py` now
# refuses the whole class.
SPA_MOUNT = "/manager"
SPA_DIR = Path(__file__).parent.parent / "frontend" / "dist"
SPA_INDEX = SPA_DIR / "index.html"

if SPA_INDEX.exists():
    app.mount(
        f"{SPA_MOUNT}/assets",
        StaticFiles(directory=SPA_DIR / "assets"),
        name="spa-assets",
    )


def _spa_index() -> FileResponse:
    """The built SPA's entry document.

    **A backend-only checkout must keep working.** `frontend/dist` is generated
    and not committed, so its absence is the ordinary state of a fresh clone,
    and somebody who has never run `npm install` should get a clear 404 here
    rather than a 500 about a missing directory.
    """
    if not SPA_INDEX.exists():
        raise HTTPException(
            status_code=404,
            detail="The manager client is not built. Run `npm install && npm run build` in frontend/.",
        )
    return FileResponse(SPA_INDEX)


@app.get(SPA_MOUNT, include_in_schema=False)
def spa_root():
    return _spa_index()


@app.get(SPA_MOUNT + "/{spa_path:path}", include_in_schema=False)
def spa_fallback(spa_path: str):
    """Serve the SPA's own index for a client-side route.

    The SPA owns paths like `/manager/sign-in` that exist only in the browser.
    Reloading one sends the browser here, and answering with the index lets
    React Router resolve it -- without this, a reload on any screen but the
    first is a 404.
    """
    return _spa_index()


# `signed_in`: the same three routes, behind the JSON guard like any other
# read — a session or machine key holding `view` (ADR-184 point 1).
if API_DOCS == "signed_in":
    from fastapi import APIRouter
    from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html

    docs_router = APIRouter(include_in_schema=False)

    @docs_router.get("/openapi.json")
    def openapi_signed_in():
        return app.openapi()

    @docs_router.get("/docs")
    def docs_signed_in():
        return get_swagger_ui_html(openapi_url="/openapi.json", title=app.title,
                                   swagger_ui_parameters=SWAGGER_UI_PARAMETERS)

    @docs_router.get("/redoc")
    def redoc_signed_in():
        return get_redoc_html(openapi_url="/openapi.json", title=app.title)

    app.include_router(docs_router, dependencies=_api)


# --- the schema describes the JSON plane only (task-244) ---------------------
#
# The Jinja UI still serves every page and form post it did (frozen by
# `tests/test_jinja_freeze.py`), but it is not part of the contract ADR-002 and
# ADR-170 point 4 describe, and `frontend/src/api/schema.d.ts` is generated
# from this schema: on 2026-10-02 88 of its 198 paths were `/ui` routes the
# React client never calls. Hidden by what the route IS rather than by which
# router declared it, because the auth router serves `/ui/login`, `/ui/users`
# and `/ui/roles` itself — and the frontend router's dashboard is `GET /`.
# Done after every include, so a router added later is covered too.
#
# A JSON `GET /` that returned an API banner used to sit here. The frontend
# router's dashboard is registered first and always won, so it was never
# reachable — and the schema documented a response nobody could get.
_JINJA_ENDPOINTS = {route.endpoint for route in frontend_router.routes}
for _route in app.routes:
    if getattr(_route, "path", "").startswith("/ui") or getattr(_route, "endpoint", None) in _JINJA_ENDPOINTS:
        _route.include_in_schema = False
