import logging
import os
import re
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
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

from app.recipients.db_models import RecipientDB, SignalContributionDB, ConsentSyncLogDB
from app.recipients.router import router as recipients_router

from app.providers.db_models import ProviderEventQuarantineDB
from app.ai.db_models import AIPromptDB, AIRunDB
from app.providers.router import router as provider_router

from app.email_modules.router import router as email_modules_router

from app.overrides.db_models import ContentOverrideDB
from app.overrides.router import router as overrides_router

from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB
from app.audience.router import router as audience_router

from app.settings.db_models import AppConfigDB

from app.auth.db_models import (
    BrandDB, LoginCodeDB, RoleAssignmentDB, RoleDB, RolePermissionDB, SessionDB, UserDB,
)
from app.auth.dependencies import (
    NotAuthenticated, NotAuthorised, auth_enforced, enforce_policy,
)
from app.auth.router import router as auth_router
from app.auth.service import (
    SESSION_COOKIE, bootstrap as bootstrap_auth, current_user_summary,
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
recipients) → **compose** (campaigns, email-modules) → **personalize** (decision,
overrides) → **audience** → **render** (rendering, snapshots) → **deliver**
(delivery, provider) → **learn** (insight). The **frontend** section at the end is
the server-rendered HTML admin UI (post/redirect/get), not a JSON API — it is
documented as a route index in `docs/architecture/Code/frontend.md`.
""".strip()

# Ordered by architecture layer; `frontend` (the /ui HTML routes) is deliberately
# last so the JSON API reads as one block above it.
TAGS_METADATA = [
    {"name": "content", "description": "Content catalog: reusable records, the category taxonomy, and content versions. Source of truth for *what can be said*."},
    {"name": "recipients", "description": "Local projection of CRM contacts + marketing consent + the signal-contribution log. Not a CRM."},
    {"name": "campaigns", "description": "Composition: campaigns, variants, module instances, decision slots, and the decision-resolution audit. Structure, not content."},
    {"name": "email-modules", "description": "The file-based email-module template registry (drop-a-file plugins). Read-only over `storage/email_modules/`."},
    {"name": "decision", "description": "The personalization engine: resolve a decision slot to content via pluggable strategies."},
    {"name": "overrides", "description": "Manager field-level edits on a module, logged against the system's original pick (trust loop)."},
    {"name": "audience", "description": "Audience groups from live rule blocks + manual pins, resolved consent-gated. (Prefix `/api/audience-groups`.)"},
    {"name": "rendering", "description": "Turn a variant's module stack into final, CSS-inlined HTML. Reads decisions, never executes them."},
    {"name": "snapshots", "description": "Freeze the render state (context + HTML) for reproducible, auditable sends. A snapshot ≠ a send."},
    {"name": "delivery", "description": "Plan and fire sends: send instances + per-recipient delivery executions, through a swappable provider."},
    {"name": "provider", "description": "Inbound feedback boundary: normalize + correlate provider webhooks (opens/clicks/bounces) to deliveries."},
    {"name": "insight", "description": "The learning loop: engagement → per-category signal contributions (decay-on-read)."},
    {"name": "frontend", "description": "Server-rendered HTML admin UI (post/redirect/get) — **not a JSON API**. Documented as a route index in `docs/architecture/Code/frontend.md`."},
]

app = FastAPI(
    title="Newsletter Reference Architecture API",
    version="0.1.0",
    description=API_DESCRIPTION,
    openapi_tags=TAGS_METADATA,
)


templates = Jinja2Templates(directory="app/templates")

Base.metadata.create_all(bind=engine)


with SessionLocal() as db:
    create_demo_content_if_empty(db)
    # Seed the default brand, the three preset roles and — while the user table
    # is empty — an initial Admin from INITIAL_ADMIN_EMAIL. Without that last
    # step nobody could ever sign in (ADR-151).
    bootstrap_auth(db)
    from app.auth.dependencies import auth_enforced

    if not auth_enforced(db):
        logger.warning(
            "auth: access control is NOT enforced — sessions and roles work, but no "
            "route refuses anyone. Turn it on at /ui/users once sign-in is verified."
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


app.include_router(auth_router)

# One guard over the whole UI, deriving the required permission from the route
# via app/auth/policy.py: reads need `view`, writes are looked up in the policy
# table, and a write with no policy entry is refused. Applied here rather than
# inside app/frontend so that module stays ignorant of authentication, and so
# the decision is visible in one place instead of 57 route decorators.
#
# Sign-in itself lives in auth_router, above, whose login routes are
# deliberately open and whose /ui/users routes carry their own explicit guard.
#
# The JSON API routers below are NOT guarded. That is machine authentication, a
# separately scoped concern and a Mode B prerequisite (ADR-142) — see
# docs/backlog.md. A human session cookie would be the wrong mechanism.
app.include_router(
    frontend_router,
    dependencies=[Depends(enforce_policy)],
)
app.include_router(content_router)
app.include_router(campaigns_router)
app.include_router(rendering_router)
app.include_router(snapshots_router)
app.include_router(delivery_router)
app.include_router(insight_router)
app.include_router(decision_router)
app.include_router(recipients_router)
app.include_router(provider_router)
app.include_router(email_modules_router)
app.include_router(overrides_router)
app.include_router(audience_router)


@app.get("/")
def root():
    return {"message": "Newsletter Reference Architecture API"}