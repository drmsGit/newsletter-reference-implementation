import logging
import os
from pathlib import Path

from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)


def _load_local_env() -> None:
    """Load backend/.env (gitignored) into the environment for local secrets
    like RESEND_API_KEY — so credentials never live in code or the DB. A real
    environment variable always wins (setdefault). No dependency; see
    .env.example for the expected keys."""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


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
from app.providers.router import router as provider_router

from app.email_modules.router import router as email_modules_router

from app.overrides.db_models import ContentOverrideDB
from app.overrides.router import router as overrides_router

from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB
from app.audience.router import router as audience_router

from app.settings.db_models import AppConfigDB

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


Base.metadata.create_all(bind=engine)


with SessionLocal() as db:
    create_demo_content_if_empty(db)


app.include_router(frontend_router)
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