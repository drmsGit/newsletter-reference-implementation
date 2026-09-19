from fastapi import APIRouter, Depends, Query, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from itertools import combinations
from urllib.parse import quote
from datetime import datetime
import logging
import math
import os

logger = logging.getLogger(__name__)

from app.database import get_db
from app.auth.service import (
    SESSION_COOKIE, brands_for_user, brands_with_permission, has_permission,
    list_brands, safe_next, set_session_brand, user_for_token,
)
from app.auth.dependencies import require_permission
from app.auth.permissions import (
    CAMPAIGNS_MANAGE, CONTENT_MANAGE, INTEGRATIONS_MANAGE,
)
from app.channels.registry import DEFAULT_CHANNEL, get_channel, max_modules_for
from app.delivery.providers.factory import providers_for_channel
from app.settings.service import available_channels, channel_available
from app.audit import service as audit
from app.campaigns import duplication
from app.recipients.consent import consent_grid, consent_history, resolve_emails
from app.recipients.service import to_recipient, to_recipients

import json

from app.content.db_models import ContentRecordDB, ContentVersionDB, CategoryDB, ContentCategoryAssignmentDB, CategoryRelationDB
from app.content.service import create_content, get_content_record, update_content_record, set_content_status, assign_category_to_content, create_content_version, delete_category_assignment, delete_category_relation
from app.content.service import create_category, create_category_relation
from app.content.service import delete_content_record, delete_category, ContentRecordHasHistoryError, HasRelationsError
from app.campaigns.db_models import CampaignDB, DecisionResolutionDB, VariantDB, ModuleInstanceDB, DecisionSlotDB
from app.campaigns.service import create_campaign, create_variant_for_campaign, create_module_for_variant, create_decision_slot_for_variant, update_decision_slot, update_variant, update_module, delete_module, move_module
from app.rendering.service import UnpublishedContentError, envelope_fields_for_variant, render_variant_html
from app.snapshots.service import create_snapshot_for_variant
from app.delivery.service import create_send_instance, prepare_send_from_audience, process_due_scheduled_sends, send_send_instance
from app.delivery.providers.factory import get_provider
from app.recipients.db_models import RecipientDB, SignalContributionDB
from app.insight.signals import operational_signals_for_recipient, operational_signals_for_category
from app.settings.service import get_signal_weights, get_half_lives, get_max_send_recipients, set_config, SIGNAL_WEIGHTS, HALF_LIFE_DAYS_KEY, MAX_SEND_RECIPIENTS_KEY
from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB
from app.audience import service as audience_service
from app.decision.strategies.registry import list_strategies
from app.modules.registry import envelope_module_type, get_manifest, list_manifests
from app.overrides.service import (
    create_content_override,
    get_active_content_override,
    list_content_overrides,
    reset_content_override,
)
from app.overrides.models import ContentOverrideCreate
from app.snapshots.db_models import SnapshotDB
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.insight.db_models import EngagementEventDB

router = APIRouter(tags=["frontend"])


def working_brand_id(request: Request, db: Session) -> int:
    """The brand this request is acting in (ADR-150 point 2).

    Reads the value the middleware already resolved onto `request.state`, so
    this is a dict lookup rather than a query on the hot path.

    **Falls back to the default brand when there is no working context.** That
    happens in exactly two situations, both legitimate: access control is
    switched off, so nobody is signed in; or the signed-in user holds no role
    grant at all. Falling back keeps the app usable in the first case, and in
    the second the user cannot reach a write route anyway — `enforce_policy`
    refuses them before this is called.
    """
    brand = getattr(request.state, "current_brand", None)
    if brand:
        return brand["id"]
    from app.auth.service import ensure_default_brand

    return ensure_default_brand(db).id


#: Where a brand switch lands when you were looking at one specific row.
#:
#: **The switch was never the problem; the landing was.** `safe_next` sends you
#: back to the page you were on, and that page is a row belonging to the brand
#: you just left — so the correct answer is a red banner telling you the record
#: does not exist, which reads as an accusation for an action that was entirely
#: reasonable. The section is what you were doing; the id was only where you
#: happened to be.
#:
#: A table rather than "strip the last numeric segment", for the same reason
#: `WRITE_POLICY` is a table: the nested routes do not follow the pattern —
#: `/ui/decisions/slots/{id}` would strip to `/ui/decisions/slots`, which is not
#: a page. First match wins, so narrower prefixes sit above broader ones.
#:
#: **Deliberately excludes recipients and categories.** Recipients carry no
#: brand (ADR-150 point 9) and categories are global, so the row you are looking
#: at survives the switch. What changes is the consent shown against it, which
#: is exactly what somebody switching brand on a recipient wants to see.
SWITCH_LANDINGS: tuple[tuple[str, str], ...] = (
    ("/ui/decisions/slots/", "/ui/decisions"),
    ("/ui/deliveries/send-instances/", "/ui/deliveries"),
    ("/ui/audience-groups/", "/ui/audience-groups"),
    ("/ui/campaigns/", "/ui/campaigns"),
    ("/ui/content/", "/ui/content"),
)


def landing_after_switch(path: str) -> str:
    """The collection to land on, or `path` unchanged if it is not a row."""
    for prefix, collection in SWITCH_LANDINGS:
        if path.startswith(prefix):
            return collection
    return path


@router.post("/ui/brand")
def switch_brand(
    request: Request,
    brand_id: int = Form(...),
    next: str = Form(""),
    db: Session = Depends(get_db),
):
    """Change the working brand (ADR-150 point 2's switcher).

    Not a permission — any signed-in user may switch to a brand they already
    hold a grant on, and `set_session_brand` refuses anything else. Its
    `WRITE_POLICY` entry is therefore `view`, which every role implies.

    **Answers identically whether the switch was accepted or refused.** A
    distinct response would tell a signed-in user which brands exist beyond
    their own grants, which is the enumeration shape ADR-151 point 2 closes on
    the login form, arriving in a different place.
    """
    set_session_brand(db, request.cookies.get(SESSION_COOKIE), brand_id)
    # Rewritten unconditionally, not only when the switch was accepted. A
    # refused switch leaves you in the brand you were already in, so landing on
    # that brand's list is harmless — and branching here would make the response
    # differ by outcome, which is the one property this route's docstring
    # promises it does not do.
    return RedirectResponse(url=landing_after_switch(safe_next(next)), status_code=303)


templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
):
    dashboard_brand_id = working_brand_id(request, db)

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "title": "Architecture Dashboard",
            # Active only — a deactivated record still exists and still renders
            # where it is already used, but it is not part of the catalogue a
            # manager can compose with, so counting it here overstates the number.
            # Scoped to the working brand, all of them together. A dashboard
            # mixing scopes is the subtler version of the problem brand
            # scoping exists to solve: "0 campaigns, 7 snapshots" invites the
            # reader to average two different populations in their head.
            "content_count": (
                db.query(ContentRecordDB)
                .filter(
                    ContentRecordDB.status == "active",
                    ContentRecordDB.brand_id == dashboard_brand_id,
                )
                .count()
            ),
            "campaign_count": (
                db.query(CampaignDB)
                .filter(CampaignDB.brand_id == dashboard_brand_id)
                .count()
            ),
            # Recipients are company-wide by ADR-150 point 9 — brand is the
            # SENDING context, not an attribute of the person — so this one is
            # deliberately unscoped rather than overlooked.
            "recipient_count": db.query(RecipientDB).count(),
            "snapshot_count": (
                db.query(SnapshotDB)
                .join(VariantDB, VariantDB.id == SnapshotDB.variant_id)
                .join(CampaignDB, CampaignDB.id == VariantDB.campaign_id)
                .filter(CampaignDB.brand_id == dashboard_brand_id)
                .count()
            ),
            "delivery_count": (
                db.query(DeliveryExecutionDB)
                .join(SendInstanceDB, SendInstanceDB.id == DeliveryExecutionDB.send_instance_id)
                .filter(SendInstanceDB.brand_id == dashboard_brand_id)
                .count()
            ),
            "event_count": (
                db.query(EngagementEventDB)
                .join(DeliveryExecutionDB, DeliveryExecutionDB.id == EngagementEventDB.delivery_execution_id)
                .join(SendInstanceDB, SendInstanceDB.id == DeliveryExecutionDB.send_instance_id)
                .filter(SendInstanceDB.brand_id == dashboard_brand_id)
                .count()
            ),
        },
    )


@router.get("/ui/settings")
def settings_page(request: Request, saved: bool = False, db: Session = Depends(get_db)):
    """Parametric config an admin/BI person can retune without touching code
    (ADR-132's "tunable weights/half-lives"). The decay *model* and scoring
    logic stay in code — only these values are editable here."""
    weights = get_signal_weights(db)
    half_lives = get_half_lives(db)
    # Show them together, one row per contribution type.
    types = sorted(set(weights) | set(half_lives))
    signal_rows = [
        {
            "type": t,
            "weight": weights.get(t, 0.0),
            "half_life": half_lives.get(t, None),
        }
        for t in types
    ]
    # AI budget + the manager-owned prompt (ADR-140/144).
    from app.ai.service import (
        get_published_prompt, list_prompt_versions, spend_to_date, tokens_used,
    )
    from app.ai.tasks.registry import list_tasks
    from app.ai.adapters.claude import DEFAULT_MODEL as CLAUDE_DEFAULT_MODEL
    from app.ai.adapters.factory import AVAILABLE_AI_PROVIDERS
    from app.settings.service import get_ai_provider_name, get_ai_spend_cap

    ai_cap = get_ai_spend_cap(db)
    ai_used = tokens_used(db)
    ai_spend = spend_to_date(db)
    # One entry per discovered task rather than the single task this page used
    # to import by name. A second task now appears here by existing — no
    # import, no context keys, no duplicated card.
    from app.settings.service import get_task_model, governed_models

    ai_tasks = []
    for meta in list_tasks():
        published = get_published_prompt(db, meta.key)
        ai_tasks.append({
            "meta": meta,
            "body": published.body if published else meta.default_prompt,
            "version": published.version if published else None,
            "versions": list_prompt_versions(db, meta.key),
            # None means "the deployment default", which is a real answer and
            # not a missing one (ADR-144 §2).
            "model": get_task_model(db, meta.key),
        })

    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "title": "Settings",
            "signal_rows": signal_rows,
            "max_send_recipients": get_max_send_recipients(db),
            "saved": saved,
            "ai_provider": get_ai_provider_name(db),
            "ai_providers": AVAILABLE_AI_PROVIDERS,
            "ai_key_present": bool(os.environ.get("ANTHROPIC_API_KEY")),
            # Which model id will actually be called — the adapter's default
            # unless the environment overrides it. Worth showing: "claude" names
            # the adapter, not the model, and the audit records the model.
            "ai_model": os.environ.get("ANTHROPIC_MODEL") or CLAUDE_DEFAULT_MODEL,
            "ai_model_from_env": bool(os.environ.get("ANTHROPIC_MODEL")),
            "ai_cap": ai_cap,
            "ai_tokens_used": ai_used,
            "ai_spend": ai_spend,
            "ai_tokens_remaining": max(0, ai_cap["hard_stop_tokens"] - ai_used),
            "ai_used_pct": min(100, round(ai_used / max(1, ai_cap["hard_stop_tokens"]) * 100)),
            "ai_over_warn": ai_used >= ai_cap["warn_tokens"],
            "ai_tasks": ai_tasks,
            "ai_governed_models": governed_models(),
        },
    )


@router.post("/ui/settings/ai")
async def settings_save_ai(request: Request, db: Session = Depends(get_db)):
    """Persist the AI token budget. Blank/invalid values keep the code defaults."""
    from app.settings.service import AI_SPEND_CAP_KEY, get_ai_spend_cap

    form = await request.form()
    current = get_ai_spend_cap(db)
    values = dict(current)
    for field, key in (("ai_warn_tokens", "warn_tokens"),
                       ("ai_hard_stop_tokens", "hard_stop_tokens")):
        raw = (form.get(field) or "").strip()
        if not raw:
            continue
        try:
            num = int(raw)
        except ValueError:
            continue
        if num > 0:
            values[key] = num

    # Reference figure only, so 0/blank is meaningful here — it clears the
    # denominator from the money readout rather than being rejected as invalid.
    raw_budget = (form.get("ai_budget_usd") or "").strip().replace(",", ".")
    try:
        values["budget_usd"] = max(0.0, float(raw_budget))
    except ValueError:
        pass

    set_config(db, AI_SPEND_CAP_KEY, values)
    return RedirectResponse(url="/ui/settings?saved=true", status_code=303)


@router.post("/ui/settings/ai-provider")
async def settings_save_ai_provider(request: Request, db: Session = Depends(get_db)):
    """Choose which model the AI layer calls.

    Validated against the factory's governed list, so an unknown name can never
    be stored — every later run would otherwise fail on a value saved once
    (ADR-140: enablement is a governed choice, not free text).
    """
    from app.ai.adapters.factory import AVAILABLE_AI_PROVIDERS
    from app.settings.service import AI_PROVIDER_KEY

    form = await request.form()
    name = (form.get("ai_provider") or "").strip()
    if name in AVAILABLE_AI_PROVIDERS:
        set_config(db, AI_PROVIDER_KEY, name)
    return RedirectResponse(url="/ui/settings?saved=true", status_code=303)


@router.post("/ui/settings/ai-prompt")
async def settings_publish_ai_prompt(request: Request, db: Session = Depends(get_db)):
    """Publish a new prompt version (never mutates an existing one — ADR-140 §3)."""
    from app.ai.service import publish_prompt

    form = await request.form()
    task_key = (form.get("task_key") or "").strip()
    body = (form.get("body") or "").strip()
    if task_key and body:
        publish_prompt(db, task_key, body)
    return RedirectResponse(url="/ui/settings?saved=true", status_code=303)


@router.post("/ui/settings/ai-task-model")
async def settings_set_task_model(request: Request, db: Session = Depends(get_db)):
    """Point one task at a model, or clear it back to the deployment default.

    Separate from publishing a prompt on purpose. ADR-140 §3 makes a prompt
    version immutable and audited; a model choice is a setting that can be
    changed back. **Whether changing the model should mint a new prompt version
    is an open question** the backlog records — the same prompt on a different
    model is arguably a different thing — and it is not decided here.
    """
    from app.settings.service import set_task_model

    form = await request.form()
    task_key = (form.get("task_key") or "").strip()
    model = (form.get("model") or "").strip()
    if task_key:
        # An empty selection clears it; `set_task_model` also refuses anything
        # outside the governed list rather than storing it.
        set_task_model(db, task_key, model or None)
    return RedirectResponse(url="/ui/settings?saved=true", status_code=303)


@router.post("/ui/settings")
async def settings_save(request: Request, db: Session = Depends(get_db)):
    """Persist weight / half-life overrides. Only keys that parse as numbers are
    stored; blank fields fall back to the code defaults."""
    form = await request.form()
    weights: dict[str, float] = {}
    half_lives: dict[str, float] = {}
    for field, value in form.items():
        value = (value or "").strip()
        if not value:
            continue
        try:
            num = float(value)
        except ValueError:
            continue
        if field.startswith("weight__"):
            weights[field[len("weight__"):]] = num
        elif field.startswith("halflife__"):
            half_lives[field[len("halflife__"):]] = num
    set_config(db, SIGNAL_WEIGHTS, weights)
    set_config(db, HALF_LIFE_DAYS_KEY, half_lives)

    # Recipient cap: a single scalar setting, stored only when it parses as a
    # positive int (blank/invalid leaves the code default in place).
    raw_cap = (form.get("max_send_recipients") or "").strip()
    if raw_cap:
        try:
            cap = int(raw_cap)
            if cap > 0:
                set_config(db, MAX_SEND_RECIPIENTS_KEY, cap)
        except ValueError:
            pass

    return RedirectResponse(url="/ui/settings?saved=true", status_code=303)


def _send_test_context(db):
    variants = (
        db.query(VariantDB.id, VariantDB.name, CampaignDB.name)
        .join(CampaignDB, VariantDB.campaign_id == CampaignDB.id)
        .order_by(VariantDB.id.asc())
        .all()
    )
    recipient_rows = db.query(RecipientDB.id).order_by(RecipientDB.id.asc()).limit(200).all()
    recipient_ids = [rid for (rid,) in recipient_rows]
    recipient_addresses = resolve_emails(db, recipient_ids)
    return {
        "variant_choices": [{"id": vid, "label": f"#{vid} {cname} — {vname}"} for vid, vname, cname in variants],
        "recipient_choices": [
            {"id": rid, "email": recipient_addresses.get(rid, "")}
            for rid in recipient_ids
        ],
    }


@router.get("/ui/send-test")
def send_test_page(request: Request, db: Session = Depends(get_db)):
    ctx = {"title": "Send test email", "result": None, **_send_test_context(db)}
    return templates.TemplateResponse(request, "send_test.html", ctx)


@router.post("/ui/send-test")
def send_test_submit(
    request: Request,
    to: str = Form(...),
    subject: str = Form("Test from the newsletter reference build"),
    provider: str = Form("resend"),
    variant_id: str = Form(""),
    recipient_id: str = Form(""),
    db: Session = Depends(get_db),
):
    """Trigger a real send through the configured provider — renders a variant
    (if chosen) so a genuine personalized newsletter goes out, else a simple
    test body. Shows the provider's result (message id or error) inline."""
    render_note = None
    if variant_id.strip():
        try:
            # This page sends an EMAIL, so it renders through the email path on
            # purpose — and that path now refuses a variant of another channel
            # rather than returning an empty document. Before, a push variant
            # rendered as a 252-character empty shell, which was mailed to a
            # real address and reported as a success: the handler below never
            # fired because nothing raised.
            html = render_variant_html(
                db,
                int(variant_id),
                recipient_id=int(recipient_id) if recipient_id.strip() else None,
                mode="preview",
            )
        except Exception as error:  # never block the send on a render hiccup
            render_note = f"Could not render variant ({error}); sent a plain test body instead."
            html = f"<h1>{subject}</h1><p>Test email from the newsletter reference build.</p>"
    else:
        html = f"<h1>{subject}</h1><p>Test email from the newsletter reference build.</p>"

    try:
        from app.rendering.renderers.base import RenderedArtifact

        send_result = get_provider(provider).send(
            to.strip(), RenderedArtifact.email(html=html, subject=subject)
        )
        result = {
            "success": send_result.success,
            "provider_message_id": send_result.provider_message_id,
            "message": send_result.message,
            "to": to.strip(),
            "provider": provider,
            "render_note": render_note,
        }
    except ValueError as error:  # unknown provider
        result = {"success": False, "message": str(error), "to": to.strip(), "provider": provider, "render_note": render_note}

    ctx = {"title": "Send test email", "result": result, **_send_test_context(db)}
    return templates.TemplateResponse(request, "send_test.html", ctx)


@router.get("/ui/recipients")
def recipients_list(
    request: Request,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    records = (
        db.query(RecipientDB)
        .order_by(RecipientDB.id.asc())
        .all()
    )
    # Projected rather than passed raw: the address is no longer an attribute
    # on the ORM row (ADR-163 point 2), so a template reading `.email` off one
    # would silently render nothing. to_recipients resolves addresses and
    # consent for the whole page in two queries.
    recipients = to_recipients(db, records, working_brand_id(request, db))

    return templates.TemplateResponse(
        request,
        "recipients.html",
        {
            "title": "Recipients",
            "recipients": recipients,
            "error": error,
        },
    )


@router.get("/ui/recipients/{recipient_id}")
def recipient_detail(
    recipient_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    recipient = (
        db.query(RecipientDB)
        .filter(RecipientDB.id == recipient_id)
        .first()
    )

    # Not a brand case — recipients carry no brand (ADR-150 point 9), so this
    # row is either there or it is not. It crashed all the same: `to_recipient`
    # is handed the record below and a typo'd id reached it as None. Found by
    # probing every detail-by-id route with a nonexistent id while fixing the
    # campaign one, rather than waiting for somebody to mistype a URL.
    if recipient is None:
        return RedirectResponse(
            url="/ui/recipients?error=" + quote("That recipient does not exist."),
            status_code=303,
        )

    # Preferences are now computed operational signals (decay-on-read, ADR-132),
    # not stored rows.
    signals = operational_signals_for_recipient(db, recipient_id)
    category_names = dict(
        db.query(CategoryDB.id, CategoryDB.name)
        .filter(CategoryDB.id.in_(signals.keys()))
        .all()
    ) if signals else {}
    preference_rows = [
        {
            "category_name": category_names.get(category_id, f"#{category_id}"),
            "score": round(score, 1),
            "source": "signal",
        }
        for category_id, score in sorted(signals.items(), key=lambda kv: kv[1], reverse=True)
    ]

    decisions = (
        db.query(
            DecisionResolutionDB,
            ContentRecordDB.title,
            ContentVersionDB.version_number,
        )
        .join(
            ContentRecordDB,
            DecisionResolutionDB.content_record_id == ContentRecordDB.id,
        )
        .outerjoin(
            ContentVersionDB,
            DecisionResolutionDB.content_version_id == ContentVersionDB.id,
        )
        .filter(
            DecisionResolutionDB.recipient_id == recipient_id
        )
        .order_by(
            DecisionResolutionDB.created_at.desc()
        )
        .limit(20)
        .all()
    )

    decision_rows = [
        {
            "id": decision.id,
            "decision_slot_id": decision.decision_slot_id,
            "content_title": content_title,
            "content_version": version_number,
            "score": decision.score,
            "reason": decision.reason,
            "created_at": decision.created_at,
        }
        for decision, content_title, version_number in decisions
    ]

    deliveries = (
        db.query(
            DeliveryExecutionDB,
            SendInstanceDB.name,
        )
        .join(
            SendInstanceDB,
            DeliveryExecutionDB.send_instance_id == SendInstanceDB.id,
        )
        .filter(
            DeliveryExecutionDB.recipient_id == recipient.id
        )
        .order_by(
            DeliveryExecutionDB.created_at.desc()
        )
        .limit(20)
        .all()
    )

    delivery_rows = []

    for delivery, send_instance_name in deliveries:
        delivery_events = (
            db.query(EngagementEventDB)
            .filter(
                EngagementEventDB.delivery_execution_id == delivery.id
            )
            .order_by(
                EngagementEventDB.created_at.desc()
            )
            .all()
        )

        event_rows = []

        for event in delivery_events:
            preference_updates = (
                db.query(
                    SignalContributionDB,
                    CategoryDB.name,
                )
                .join(
                    CategoryDB,
                    SignalContributionDB.category_id == CategoryDB.id,
                )
                .filter(
                    SignalContributionDB.event_id == event.id
                )
                .all()
            )

            event_rows.append(
                {
                    "id": event.id,
                    "event_type": event.event_type,
                    "provider_event_id": event.provider_event_id,
                    "created_at": event.created_at,
                    "preference_updates": [
                        {
                            "category_name": category_name,
                            "previous_score": None,
                            "delta": update.base_weight,
                            "new_score": None,
                            "reason": update.contribution_type,
                        }
                        for update, category_name in preference_updates
                    ],
                }
            )

        delivery_rows.append(
            {
                "id": delivery.id,
                "send_instance_name": send_instance_name,
                "status": delivery.status,
                "provider": delivery.provider,
                "provider_message_id": delivery.provider_message_id,
                "created_at": delivery.created_at,
                "events": event_rows,
            }
        )


    return templates.TemplateResponse(
        request,
        "recipient_detail.html",
        {
            "title": f"Recipient {recipient_id}",
            # Projected for the same reason as the list view — a raw ORM row
            # has no address attribute since ADR-163 point 2.
            "recipient": to_recipient(db, recipient, working_brand_id(request, db)),
            # The (channel × purpose) grid for the working brand, and the
            # append-only log across every brand. The flat `consent_status` on
            # `recipient` is the (email, marketing) cell of this grid — it is
            # kept because the API exposes it, but it is one cell of several
            # and reading it as "the" consent status is what made the read side
            # email-shaped.
            "consent_grid": consent_grid(
                db, recipient.id, working_brand_id(request, db),
                [c.name for c in available_channels(db)],
            ),
            "consent_history": consent_history(db, recipient.id),
            # Consent is to a sender, so the log names the brand each event
            # belongs to — otherwise a recipient opted in to one brand and out
            # of another reads as self-contradictory.
            "brand_names": {b.id: b.name for b in list_brands(db)},
            "preferences": preference_rows,
            "decisions": decision_rows,
            "deliveries": delivery_rows,
        },
    )


@router.get("/ui/campaigns")
def campaigns_list(
    request: Request,
    notice: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    campaigns = (
        db.query(CampaignDB)
        .filter(CampaignDB.brand_id == working_brand_id(request, db))
        .order_by(CampaignDB.created_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        request,
        "campaigns.html",
        {
            "title": "Campaigns",
            "campaigns": campaigns,
            # ADR-160 point 8: a disabled channel "disappears from the
            # variant-creation UI". This is that list, and it is the same one
            # the server-side refusal checks against.
            "channels": available_channels(db),
            "notice": notice,
            "error": error,
        },
    )


#: The push module's authoring fields, as names. Declared in the manifest, not
#: here — `test_channels.py` asserts the two agree, because FastAPI needs the
#: form parameters spelled out below and a hand-written list next to a manifest
#: is exactly where drift lives.
PUSH_CONTENT_FIELDS = ("push_title", "push_body", "push_image_url", "push_link")


def _channel_authoring_sections(db: Session) -> list[dict]:
    """Extra authoring fields a content record needs, per available channel.

    **Channel fields are separate and required, never derived from the email
    ones** — ADR-160 point 3. Deriving a 40-character push title from a
    60-character headline at render time is the rendering-time transformation
    point 1 rejects: a notification is not a shortened email.

    **This returns fields, never a readiness verdict, and that is deliberate.**
    Whether a record may be used at all is gated by the manager activating it
    and freezing a version — a "ready" badge beside a draft asserts a status
    nobody granted. And `required` belongs to a *module's* manifest variable,
    not to the record: a record with no headline cannot fill `single_stack`
    and fills `cta` perfectly well, so readiness is meaningless until a module
    is named. ADR-161 point 7's catalogue-readiness rider is a candidate filter
    for decision slots, where a module IS in scope. It is not a record badge,
    and an earlier version of this page made it one.

    Email is deliberately absent: its fields are the form's hand-written
    section, with labels and placeholders a manifest does not carry. That
    asymmetry is real and recorded in the backlog — the fully manifest-driven
    authoring form is a bigger change than adding one channel.
    """
    sections = []
    for channel in available_channels(db):
        if channel.name == "email":
            continue
        fields = []
        for manifest in list_manifests(channel.name):
            if not manifest.cms:
                continue
            for var in manifest.variables:
                fields.append({
                    "name": var.name,
                    "label": var.label or var.name,
                    "required": var.required,
                })
        if fields:
            sections.append({"channel": channel.name, "label": channel.label,
                             "fields": fields})
    return sections


def _push_preview(db: Session, variant) -> dict | None:
    """The rendered fields of a push variant, or None for any other channel.

    Never raises: a preview that breaks a page is worse than a missing
    preview, and an unconfigured variant (no module yet) is an ordinary state
    rather than an error.
    """
    if variant.channel != "push":
        return None
    try:
        from app.rendering.service import render_variant

        artifact = render_variant(db, variant.id, mode="preview")
        return artifact.fields or None
    except Exception as error:  # noqa: BLE001 — see the docstring
        logger.warning("push preview failed for variant %s: %s", variant.id, error)
        return None


@router.get("/ui/campaigns/{campaign_id}")
def campaign_detail(
    campaign_id: int,
    request: Request,
    error: str | None = None,
    ai_run: int | None = None,
    db: Session = Depends(get_db),
):
    campaign = (
        db.query(CampaignDB)
        .filter(
            CampaignDB.id == campaign_id,
            # Scoped here too, not only in the list. A hard filter that filters
            # only lists is not a hard filter — another brand's campaign would
            # still open by URL, and a guessable integer id is not a secret.
            CampaignDB.brand_id == working_brand_id(request, db),
        )
        .first()
    )

    # The same absence `content_detail` was taught to answer on 2026-09-15, in
    # the route that was missed. Before the brand filter above, `campaign` could
    # not be None — the id came from a list the caller had just been shown — so
    # scoping made absence reachable for the first time and nothing was added to
    # meet it. `campaign_detail.html` reads `{{ campaign.name }}` unguarded, so
    # switching brand while viewing a campaign produced an internal error.
    #
    # Answering exactly as a deleted campaign does is also the point: another
    # brand's campaign must be indistinguishable from one that does not exist.
    if campaign is None:
        return RedirectResponse(
            url="/ui/campaigns?error=" + quote("That campaign does not exist in this brand."),
            status_code=303,
        )

    variants = (
        db.query(VariantDB)
        .filter(VariantDB.campaign_id == campaign_id)
        .order_by(VariantDB.id.asc())
        .all()
    )

    variant_rows = []

    for variant in variants:
        module_records = (
            db.query(ModuleInstanceDB)
            .filter(ModuleInstanceDB.variant_id == variant.id)
            .order_by(ModuleInstanceDB.position.asc())
            .all()
        )

        modules = []
        override_module_choices = []
        for m in module_records:
            manifest = get_manifest(variant.channel, m.module_type)
            # Overrideable = the module resolves content (a content record or a
            # decision slot) and has a manifest so its fields are known. Not tied
            # to the cms flag — a hero/cta referencing a content record qualifies.
            resolves_content = m.content_record_id is not None or m.decision_slot_id is not None
            overrideable = bool(manifest and resolves_content)
            active = get_active_content_override(db, m.id) if overrideable else None
            if active is not None:
                active_override = {
                    "id": active.id,
                    "summary": "fields: " + ", ".join((active.field_overrides or {}).keys()),
                }
            else:
                active_override = None
            is_envelope = bool(manifest and any(v.envelope for v in manifest.variables))
            # Envelope modules are storage, not composition. Showing one as a
            # row in the module table — `{"subject": …}` sitting under the
            # variant's own Subject field — would be the two-places confusion
            # ADR-162 point 1 exists to remove, in the UI instead of the model.
            #
            # **Note what this does NOT yet unlock.** ADR-162 point 1 argues
            # that moving these fields into a module means "a personalised
            # subject line comes free" through the override layer. It does not,
            # yet: `overrideable` below requires a module that *resolves
            # content* — a content record or a decision slot — and an envelope
            # module has neither, so it never reaches the override picker.
            # Verified by rendering the page, not assumed. Closing that gap is
            # an override-layer change (the `resolves_content` rule), logged
            # rather than smuggled in here.
            if not is_envelope:
                modules.append({
                    "id": m.id,
                    "position": m.position,
                    "module_type": m.module_type,
                    "content_record_id": m.content_record_id,
                    "decision_slot_id": m.decision_slot_id,
                    "module_data_json": json.dumps(m.module_data) if m.module_data else "",
                    "overrideable": overrideable,
                    "active_override": active_override,
                })
            if overrideable:
                override_module_choices.append({
                    "id": m.id,
                    "label": f"#{m.id} {m.module_type} (pos {m.position})",
                    "variables": [v.name for v in manifest.variables],
                })

        decision_slots = (
            db.query(DecisionSlotDB)
            .filter(DecisionSlotDB.variant_id == variant.id)
            .order_by(DecisionSlotDB.id.asc())
            .all()
        )
        
        decision_slot_rows = []

        for slot in decision_slots:
            resolution_count = (
                db.query(DecisionResolutionDB)
                .filter(
                    DecisionResolutionDB.decision_slot_id == slot.id
                )
                .count()
            )
            unique_content_count = (
                db.query(
                    DecisionResolutionDB.content_record_id
                )
                .filter(
                    DecisionResolutionDB.decision_slot_id == slot.id
                )
                .distinct()
                .count()
            )
            top_content = (
                db.query(
                    ContentRecordDB.title,
                    func.count(
                        DecisionResolutionDB.id
                    ).label("resolution_count"),
                )
                .join(
                    ContentRecordDB,
                    DecisionResolutionDB.content_record_id
                    == ContentRecordDB.id,
                )
                .filter(
                    DecisionResolutionDB.decision_slot_id == slot.id
                )
                .group_by(
                    ContentRecordDB.title
                )
                .order_by(
                    desc("resolution_count")
                )
                .limit(5)
                .all()
            )
            latest_resolutions = (
                db.query(
                    DecisionResolutionDB,
                    ContentRecordDB.title,
                )
                .join(
                    ContentRecordDB,
                    DecisionResolutionDB.content_record_id
                    == ContentRecordDB.id,
                )
                .filter(
                    DecisionResolutionDB.decision_slot_id == slot.id
                )
                .order_by(
                    DecisionResolutionDB.created_at.desc()
                )
                .limit(10)
                .all()
            )
            decision_slot_rows.append(
                {
                    "id": slot.id,
                    "name": slot.name,
                    "decision_type": slot.decision_type,
                    "decision_strategy": slot.decision_strategy,
                    "resolution_count": resolution_count,
                    "unique_content_count": unique_content_count,
                    "top_content": top_content,
                    "latest_resolutions": latest_resolutions,
                }
            )

        snapshot_records = (
            db.query(SnapshotDB)
            .filter(SnapshotDB.variant_id == variant.id)
            .order_by(SnapshotDB.created_at.desc())
            .all()
        )

        snapshots = [
            {
                "id": snapshot.id,
                "recipient_id": snapshot.recipient_id,
                # A push artifact lives in the row, not on disk (2026-09-17),
                # so "Open HTML" would link to a handler that correctly answers
                # nothing. The template needs to know which it is.
                "is_inline": snapshot.html_storage_type == "inline",
                "artifact_fields": (snapshot.render_context or {}).get("artifact", {}).get("fields"),
                "html_size": snapshot.html_size,
                "created_at": snapshot.created_at,
                "render_context": snapshot.render_context,
                "render_context_pretty": json.dumps(
                    snapshot.render_context or {},
                    indent=2,
                    ensure_ascii=False,
                ),
            }
            for snapshot in snapshot_records
        ]

        variant_envelope = envelope_fields_for_variant(db, variant.id, variant.channel)
        variant_rows.append(
            {
                "id": variant.id,
                "name": variant.name,
                "channel": variant.channel,
                # Per variant, not per page. ADR-161 point 7: a channel is "an
                # attribute on the variant plus **which manifests it accepts**".
                # Page-level, an email composer was offered the push module the
                # moment a second channel existed — which is the leak that made
                # the directory restructure part of this work rather than a
                # later tidy-up.
                # Envelope modules are excluded: they are authored through the
                # variant's own subject/preheader fields (ADR-162 point 1), so
                # offering one in the add-module picker would be a second way to
                # create the same thing — and a manager who used it would get a
                # duplicate the envelope writer then silently ignores.
                "module_templates": [
                    m for m in list_manifests(variant.channel)
                    if not any(v.envelope for v in m.variables)
                ],
                # Cardinality, read from the channel manifest rather than known
                # here. A full variant is offered no add-module form at all —
                # but the service refuses it regardless, because a form that is
                # not rendered is not a control.
                "module_limit": max_modules_for(variant.channel),
                # Whether this channel HAS envelope copy at all, asked of the
                # manifests rather than tested against "email" (ADR-162 pt 1).
                # A push has no subject line, so every surface that offers,
                # displays or generates one is meaningless in front of it.
                "has_envelope": envelope_module_type(variant.channel) is not None,
                # What the notification will actually say. A push has no HTML
                # to open in a new tab, so the only way to see one before
                # sending is to render it here. Preview mode, so unpublished
                # content still shows — `mode="send"` is what refuses it, and
                # that refusal belongs at snapshot time, not on a page load.
                "push_preview": _push_preview(db, variant),
                "can_add_module": (
                    max_modules_for(variant.channel) is None
                    or len(modules) < max_modules_for(variant.channel)
                ),
                "channel_label": (
                    get_channel(variant.channel).label
                    if get_channel(variant.channel) else variant.channel
                ),
                # From the envelope module (ADR-162 point 1), not the row —
                # the columns stopped being written when the write path moved,
                # so reading them here would show the value as it was at
                # migration time and never update.
                "subject": variant_envelope.get("subject"),
                "preheader": variant_envelope.get("preheader"),
                "modules": modules,
                "override_module_choices": override_module_choices,
                "decision_slots": decision_slot_rows,
                "snapshots": snapshots,
            }
        )

    # Only active records are offered in the module content picker — a deactivated
    # record stays renderable where it is already used, but must not be newly
    # selected (same rule the decision strategies apply to their candidate pool).
    content_records = (
        db.query(ContentRecordDB)
        .filter(
            ContentRecordDB.status == "active",
            # The CAMPAIGN's brand, not the viewer's. Without this a manager
            # could bind brand A's content to brand B's campaign straight from
            # the picker — the situation duplication exists to replace — and
            # nothing downstream would object, because only the decision
            # strategies enforce brand on content. The audience picker a few
            # lines below was scoped for exactly this reason; this was missed.
            ContentRecordDB.brand_id == campaign.brand_id,
        )
        .order_by(ContentRecordDB.title.asc())
        .all()
    )
    strategies = sorted(s.name for s in list_strategies())

    # Audience choices for the prepare-send form, each with its live resolved
    # (consent-gated) recipient count so a manager sees the reach before planning.
    #
    # **Per channel, because the count is.** Consent is keyed per channel
    # (ADR-163 point 1), so one group resolves to different people for an email
    # variant and a push variant. Computed once per distinct channel on this
    # campaign rather than once per variant — a campaign has a handful of
    # variants and at most a handful of channels, and `resolve_audience` is not
    # free. Before this the form showed one email-gated number against every
    # variant, so planning a push from a group reading "40 recipients" could
    # reach three, with the difference only appearing as exclusions afterwards.
    audience_choices_by_channel: dict[str, list[dict]] = {}
    # Scoped: these feed a picker on the campaign page, and a suggested group
    # is NAMED after the campaign that produced it ("Demo Campaign 1 —
    # suggested audience"). Unfiltered, the picker leaked another brand's
    # campaign names even though the campaign itself was correctly refused —
    # the page said no and the dropdown beside it said everything.
    groups = audience_service.list_groups(db, brand_id=working_brand_id(request, db))
    for channel in {row["channel"] for row in variant_rows} or {DEFAULT_CHANNEL}:
        audience_choices_by_channel[channel] = [
            {
                "id": group.id,
                "name": group.name,
                "count": len(
                    audience_service.resolve_audience(db, group.id, channel=channel)
                ),
            }
            for group in groups
        ]
    for row in variant_rows:
        row["audience_choices"] = audience_choices_by_channel.get(row["channel"], [])
        # From the adapters' own `channels` declaration, so the picker cannot
        # offer something `get_provider` will refuse (ADR-161 point 1).
        row["providers"] = providers_for_channel(row["channel"])

    default_from = os.environ.get("RESEND_FROM", "onboarding@resend.dev")

    # Read back an AI run from the redirect, if one just happened. The persisted
    # run row is the source of truth for what was offered (ADR-140 §3), so no
    # session state is needed and a refresh shows the same suggestions.
    ai_suggestions: list[dict] = []
    ai_suggestions_variant_id = None
    ai_error = None
    ai_raw_reply = None
    ai_run_tokens = 0
    ai_notices: list[str] = []
    if ai_run is not None:
        from app.ai.db_models import AIRunDB
        from app.ai.tasks import subject_preheader as subject_task

        row = db.query(AIRunDB).filter(AIRunDB.id == ai_run).first()
        if row is not None:
            ai_suggestions_variant_id = row.target_id
            ai_run_tokens = (row.input_tokens or 0) + (row.output_tokens or 0)
            if row.status == "ok":
                ai_suggestions = subject_task.parse_options(row.output_text or "")
                # A successful run can still carry a message — a `max_tokens`
                # stop is recorded there — and it is the manager, not only the
                # audit trail, who needs to know before applying an option.
                ai_notices = subject_task.option_notices(ai_suggestions, row.message)
                if not ai_suggestions:
                    # **Show what it actually said.** This used to report only
                    # "the model replied, but not in the requested format" and
                    # drop `output_text` on the floor — which threw away the
                    # most useful reply the task has produced: asked for subject
                    # lines on an empty variant, the model explained that
                    # writing any would mean inventing specifics, and declined.
                    # That was a better answer than the format allowed for, and
                    # the manager never saw it.
                    ai_error = (
                        "No options could be read from the reply. The model said:"
                    )
                    ai_raw_reply = (row.output_text or "").strip()
            else:
                ai_error = row.message or "The suggestion could not be generated."

    return templates.TemplateResponse(
        request,
        "campaign_detail.html",
        {
            "title": f"Campaign {campaign_id}",
            "campaign": campaign,
            "variants": variant_rows,
            "channels": available_channels(db),
            # Which channels carry envelope copy, so the add-variant form can
            # show or hide the subject box as the channel is picked without the
            # template knowing that email is the one with a subject.
            "envelope_channels": [
                c.name for c in available_channels(db)
                if envelope_module_type(c.name) is not None
            ],
            "content_records": content_records,
            "strategies": strategies,
            # Kept for the page-level default; each variant carries its own.
            "audience_choices": audience_choices_by_channel.get(DEFAULT_CHANNEL, []),
            "default_from": default_from,
            "error": error,
            "ai_suggestions": ai_suggestions,
            "ai_suggestions_variant_id": ai_suggestions_variant_id,
            "ai_error": ai_error,
            "ai_raw_reply": ai_raw_reply,
            "ai_notices": ai_notices,
            "ai_run_tokens": ai_run_tokens,
        },
    )


@router.post("/ui/content/{content_record_id}/categories/{assignment_id}/delete")
def content_category_delete(
    content_record_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
):
    delete_category_assignment(db, assignment_id)
    return RedirectResponse(url=f"/ui/content/{content_record_id}", status_code=303)


@router.post("/ui/campaigns")
def campaign_create(
    request: Request,
    name: str = Form(...),
    channel: str = Form(...),
    db: Session = Depends(get_db),
):
    """Creating a campaign also creates its first variant, so it also picks a
    channel — the invariant that a campaign always has a variant makes that
    unavoidable. The channel belongs to the variant, never to the campaign
    (ADR-160 point 4); this form is simply the first place one is chosen."""
    # ADR-160 point 8: a channel this deployment has not turned on is "refused
    # server-side if requested directly", not merely absent from the dropdown.
    if not channel_available(db, channel):
        return RedirectResponse(
            url="/ui/campaigns?error=" + quote("That channel is not available."),
            status_code=303,
        )
    campaign = create_campaign(
        db, name=name, brand_id=working_brand_id(request, db), channel=channel
    )
    return RedirectResponse(url=f"/ui/campaigns/{campaign.id}", status_code=303)


def _duplication_targets(db: Session, request: Request, permission: str):
    """Brands this request may duplicate *into*.

    Not `brands_for_user`: the target brand is chosen by the form, and the
    policy table checks `campaigns.manage` against the **working** brand only.
    Without this, a Manager on brand A could create a campaign in brand B by
    picking it from a dropdown — the check would pass, because it never looked
    at the destination.
    """
    if not getattr(request.state, "auth_enforced", True):
        # Nobody is signed in, so there are no grants to read. Same reasoning
        # as `working_brand_id` falling back to the default brand rather than
        # refusing: with enforcement off, refusing would make the app unusable.
        return list_brands(db)
    user = user_for_token(db, request.cookies.get(SESSION_COOKIE))
    if user is None:
        return []
    return brands_with_permission(db, user, permission)


def _may_in_brand(db: Session, request: Request, permission: str, brand_id: int) -> bool:
    if not getattr(request.state, "auth_enforced", True):
        return True
    user = user_for_token(db, request.cookies.get(SESSION_COOKIE))
    if user is None:
        return False
    return has_permission(db, user, permission, brand_id=brand_id)


@router.get("/ui/campaigns/{campaign_id}/duplicate")
def campaign_duplicate_form(
    campaign_id: int,
    request: Request,
    target_brand_id: int | None = None,
    name: str = "",
    variant_id: list[int] = Query(default=[]),
    error: str | None = None,
    db: Session = Depends(get_db),
):
    """The wizard. Two steps, and the second one's options depend on the first.

    Two steps rather than one button, deliberately: a one-click copy produces a
    campaign that looks complete and is wrong in ways the manager cannot see —
    its content has no published version so it will refuse to send, its decision
    slots would resolve against a catalogue that may be empty, and its URLs
    still point at the brand it came from. Splitting the act is what makes those
    three sayable before they are discovered.
    """
    source_brand_id = working_brand_id(request, db)
    campaign = (
        db.query(CampaignDB)
        .filter(CampaignDB.id == campaign_id, CampaignDB.brand_id == source_brand_id)
        .first()
    )
    if campaign is None:
        return RedirectResponse(
            url="/ui/campaigns?error=" + quote("That campaign does not exist in this brand."),
            status_code=303,
        )

    targets = _duplication_targets(db, request, CAMPAIGNS_MANAGE)
    target = next((b for b in targets if b.id == target_brand_id), None)

    modes = []
    if target is not None:
        for mode in duplication.content_modes_for(source_brand_id, target.id):
            # Copying content writes content rows into the *target* brand, so
            # it needs the target's content permission, not the working one.
            if mode == duplication.COPY and not _may_in_brand(
                db, request, CONTENT_MANAGE, target.id
            ):
                continue
            modes.append(mode)

    return templates.TemplateResponse(
        request,
        "campaign_duplicate.html",
        {
            "title": f"Duplicate “{campaign.name}”",
            "campaign": campaign,
            # The whole campaign's assets, for the picker in step 1.
            "summary": duplication.summarise_source(db, campaign.id),
            # Only the chosen ones, for step 2's content count — summarising
            # the whole campaign while copying two of its four variants would
            # advertise records this copy never creates.
            "selected_summary": duplication.summarise_source(
                db, campaign.id, variant_id or None
            ),
            "selected_variant_ids": variant_id,
            "brands": targets,
            "target": target,
            "crossing": target is not None and target.id != source_brand_id,
            "modes": modes,
            "suggested_name": name or f"{campaign.name} (copy)",
            "error": error,
        },
    )


@router.post("/ui/campaigns/{campaign_id}/duplicate")
def campaign_duplicate(
    campaign_id: int,
    request: Request,
    name: str = Form(...),
    target_brand_id: int = Form(...),
    content_mode: str = Form(...),
    variant_id: list[int] = Form(default=[]),
    db: Session = Depends(get_db),
):
    source_brand_id = working_brand_id(request, db)
    campaign = (
        db.query(CampaignDB)
        .filter(CampaignDB.id == campaign_id, CampaignDB.brand_id == source_brand_id)
        .first()
    )
    if campaign is None:
        return RedirectResponse(
            url="/ui/campaigns?error=" + quote("That campaign does not exist in this brand."),
            status_code=303,
        )

    back = f"/ui/campaigns/{campaign_id}/duplicate?target_brand_id={target_brand_id}&name={quote(name)}"

    targets = _duplication_targets(db, request, CAMPAIGNS_MANAGE)
    target = next((b for b in targets if b.id == target_brand_id), None)
    if target is None:
        # Answers the same whether the brand does not exist or the user simply
        # holds no grant on it — the difference would tell a signed-in user
        # which brands exist beyond their own, exactly as `set_session_brand`
        # refuses to.
        return RedirectResponse(
            url=back + "&error=" + quote("You cannot create campaigns in that brand."),
            status_code=303,
        )
    if content_mode == duplication.COPY and not _may_in_brand(
        db, request, CONTENT_MANAGE, target.id
    ):
        return RedirectResponse(
            url=back + "&error=" + quote(
                "Copying content creates records in the target brand, and you cannot "
                "edit content there. Take the layout only."
            ),
            status_code=303,
        )

    try:
        report = duplication.duplicate_campaign(
            db,
            campaign_id=campaign.id,
            target_brand_id=target.id,
            name=name,
            content_mode=content_mode,
            # Empty means "all", which is what the wizard did before there was
            # anything to choose — the service refuses an explicitly empty
            # list, which is a different thing from not choosing.
            variant_ids=variant_id or None,
        )
    except duplication.DuplicationRefused as error:
        return RedirectResponse(url=back + "&error=" + quote(str(error)), status_code=303)

    audit.record_from_request(
        request,
        db,
        audit.CAMPAIGN_DUPLICATED,
        subject_type="campaign",
        subject_id=report.campaign_id,
        # The entry belongs to the brand the copy now lives in; the brand it
        # came from is in the detail, so the log reads correctly from either end.
        brand_id=report.target_brand_id,
        detail=report.as_detail(),
    )

    if not report.crossed_brands:
        return RedirectResponse(url=f"/ui/campaigns/{report.campaign_id}", status_code=303)

    # The copy is in another brand, so it cannot appear in this list and
    # following it would 404 behind the brand filter. Say where it went.
    notice = (
        f"Duplicated into {target.name}. Switch to that brand to open it."
        if not report.content_records_copied
        else (
            f"Duplicated into {target.name}, with "
            f"{len(report.content_records_copied)} content record(s) copied across. "
            "They have no published version yet, so the copy cannot be sent until "
            "someone publishes them. Switch to that brand to open it."
        )
    )
    return RedirectResponse(url="/ui/campaigns?notice=" + quote(notice), status_code=303)


@router.post("/ui/campaigns/{campaign_id}/variants")
def variant_create(
    campaign_id: int,
    name: str = Form(...),
    channel: str = Form(...),
    subject: str = Form(""),
    preheader: str = Form(""),
    db: Session = Depends(get_db),
):
    """The "what channel?" question. Asked once, here, and never again —
    ADR-160 point 5 fixes it at creation."""
    if not channel_available(db, channel):
        return RedirectResponse(
            url=f"/ui/campaigns/{campaign_id}?error=" + quote("That channel is not available."),
            status_code=303,
        )
    # Passed through as given. The channel check that used to live here is
    # gone, not forgotten: ADR-162 point 1 landed, so envelope copy is written
    # by `set_envelope_fields`, which finds the module a channel *declares* for
    # it — and push declares none, so a subject posted to a push variant has
    # nowhere to go and is discarded by the model rather than by a guard. A
    # redundant check that reads as load-bearing is worse than no check.
    create_variant_for_campaign(
        db,
        campaign_id=campaign_id,
        name=name,
        channel=channel,
        subject=subject.strip() or None,
        preheader=preheader.strip() or None,
    )
    return RedirectResponse(url=f"/ui/campaigns/{campaign_id}", status_code=303)


@router.post("/ui/campaigns/{campaign_id}/variants/{variant_id}/edit")
def variant_edit(
    campaign_id: int,
    variant_id: int,
    name: str = Form(...),
    subject: str = Form(""),
    preheader: str = Form(""),
    db: Session = Depends(get_db),
):
    update_variant(
        db,
        variant_id=variant_id,
        name=name,
        subject=subject.strip() or None,
        preheader=preheader.strip() or None,
    )
    return RedirectResponse(url=f"/ui/campaigns/{campaign_id}", status_code=303)


@router.post("/ui/campaigns/{campaign_id}/variants/{variant_id}/suggest-subject")
def variant_suggest_subject(
    campaign_id: int,
    variant_id: int,
    db: Session = Depends(get_db),
):
    """Run the Mode A subject/preheader task (ADR-141 §3).

    Nothing is written to the variant here — AI output is a proposal until a
    human picks one. The run id travels in the query string so the suggestions
    survive the redirect without server-side session state; the persisted run
    row is what the next GET reads back.
    """
    from app.ai.tasks import subject_preheader as subject_task

    # Refused for a channel with no envelope, not merely hidden. The button is
    # gated in the template, but a hand-crafted POST never sees a template —
    # and this one spends tokens against the budget (ADR-144 §5) to generate
    # copy that has nowhere to be stored, since `set_envelope_fields` writes
    # only into the module a channel declares.
    variant = db.query(VariantDB).filter(VariantDB.id == variant_id).first()
    if variant is None or envelope_module_type(variant.channel) is None:
        return RedirectResponse(
            url=f"/ui/campaigns/{campaign_id}?error=" + quote(
                "That channel has no subject line, so there is nothing to suggest."
            ),
            status_code=303,
        )

    try:
        _, run = subject_task.suggest(db, variant_id)
    except subject_task.NothingToWorkFrom as refusal:
        # Refused before the call, so no tokens were spent and no run row was
        # written. The manager is told what to fix rather than being handed the
        # model's (correct, and paid-for) version of the same sentence.
        return RedirectResponse(
            url=f"/ui/campaigns/{campaign_id}?error=" + quote(str(refusal), safe=""),
            status_code=303,
        )
    if run is None:
        return RedirectResponse(url=f"/ui/campaigns/{campaign_id}", status_code=303)
    return RedirectResponse(
        url=f"/ui/campaigns/{campaign_id}?ai_run={run.run_id}",
        status_code=303,
    )


@router.post("/ui/campaigns/{campaign_id}/variants/{variant_id}/apply-subject")
def variant_apply_subject(
    campaign_id: int,
    variant_id: int,
    subject: str = Form(""),
    preheader: str = Form(""),
    db: Session = Depends(get_db),
):
    """Apply a chosen suggestion — the human decision that turns it into content."""
    variant = db.query(VariantDB).filter(VariantDB.id == variant_id).first()
    if variant is not None:
        update_variant(
            db,
            variant_id=variant_id,
            name=variant.name,
            subject=subject.strip() or None,
            preheader=preheader.strip() or None,
        )
    return RedirectResponse(url=f"/ui/campaigns/{campaign_id}", status_code=303)


@router.post("/ui/campaigns/{campaign_id}/variants/{variant_id}/modules")
def module_create(
    campaign_id: int,
    variant_id: int,
    module_type: str = Form(...),
    content_record_id: int | None = Form(None),
    decision_slot_id: int | None = Form(None),
    module_data_json: str = Form(""),
    db: Session = Depends(get_db),
):
    # Static modules (hero, cta, …) take their template variables from
    # module_data. Without this the fields render empty. Parse the optional
    # JSON here, same pattern as field_overrides_json on the override form.
    module_data = None
    if module_data_json.strip():
        try:
            module_data = json.loads(module_data_json)
        except ValueError:
            return RedirectResponse(
                url=f"/ui/campaigns/{campaign_id}?error={quote('Module fields must be valid JSON')}",
                status_code=303,
            )
    try:
        create_module_for_variant(
            db,
            variant_id=variant_id,
            module_type=module_type,
            content_record_id=content_record_id or None,
            decision_slot_id=decision_slot_id or None,
            module_data=module_data,
        )
    except ValueError as error:
        return RedirectResponse(
            url=f"/ui/campaigns/{campaign_id}?error={quote(str(error))}",
            status_code=303,
        )
    return RedirectResponse(url=f"/ui/campaigns/{campaign_id}", status_code=303)


@router.post("/ui/campaigns/{campaign_id}/variants/{variant_id}/modules/{module_id}/edit")
def module_edit(
    campaign_id: int,
    variant_id: int,
    module_id: int,
    module_type: str = Form(...),
    content_record_id: int | None = Form(None),
    decision_slot_id: int | None = Form(None),
    module_data_json: str = Form(""),
    db: Session = Depends(get_db),
):
    module_data = None
    if module_data_json.strip():
        try:
            module_data = json.loads(module_data_json)
        except ValueError:
            return RedirectResponse(
                url=f"/ui/campaigns/{campaign_id}?error={quote('Module fields must be valid JSON')}",
                status_code=303,
            )
    try:
        update_module(
            db,
            module_id=module_id,
            module_type=module_type,
            content_record_id=content_record_id or None,
            decision_slot_id=decision_slot_id or None,
            module_data=module_data,
        )
    except ValueError as error:
        return RedirectResponse(
            url=f"/ui/campaigns/{campaign_id}?error={quote(str(error))}",
            status_code=303,
        )
    return RedirectResponse(url=f"/ui/campaigns/{campaign_id}", status_code=303)


@router.post("/ui/campaigns/{campaign_id}/variants/{variant_id}/modules/{module_id}/delete")
def module_delete(campaign_id: int, variant_id: int, module_id: int, db: Session = Depends(get_db)):
    delete_module(db, module_id)
    return RedirectResponse(url=f"/ui/campaigns/{campaign_id}", status_code=303)


@router.post("/ui/campaigns/{campaign_id}/variants/{variant_id}/modules/{module_id}/move")
def module_move(
    campaign_id: int,
    variant_id: int,
    module_id: int,
    direction: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        move_module(db, module_id, direction)
    except ValueError:
        pass
    return RedirectResponse(url=f"/ui/campaigns/{campaign_id}", status_code=303)


@router.post("/ui/campaigns/{campaign_id}/variants/{variant_id}/decision-slots")
def decision_slot_create(
    campaign_id: int,
    variant_id: int,
    name: str = Form(...),
    decision_strategy: str = Form("top_score"),
    db: Session = Depends(get_db),
):
    create_decision_slot_for_variant(
        db,
        variant_id=variant_id,
        name=name,
        decision_strategy=decision_strategy,
    )
    return RedirectResponse(url=f"/ui/campaigns/{campaign_id}", status_code=303)


@router.post("/ui/campaigns/{campaign_id}/variants/{variant_id}/overrides")
def content_override_create(
    campaign_id: int,
    variant_id: int,
    module_instance_id: int = Form(...),
    field_overrides_json: str = Form(""),
    reason: str = Form(""),
    db: Session = Depends(get_db),
):
    field_overrides = None
    if field_overrides_json.strip():
        try:
            field_overrides = json.loads(field_overrides_json)
        except ValueError:
            return RedirectResponse(
                url=f"/ui/campaigns/{campaign_id}?error={quote('field_overrides must be valid JSON')}",
                status_code=303,
            )
    try:
        create_content_override(
            db,
            ContentOverrideCreate(
                module_instance_id=module_instance_id,
                field_overrides=field_overrides,
                overridden_by="manager@example.com",
                reason=reason.strip() or None,
            ),
        )
    except ValueError as error:
        return RedirectResponse(
            url=f"/ui/campaigns/{campaign_id}?error={quote(str(error))}",
            status_code=303,
        )
    return RedirectResponse(url=f"/ui/campaigns/{campaign_id}", status_code=303)


@router.post("/ui/campaigns/{campaign_id}/overrides/{override_id}/reset")
def content_override_reset(
    campaign_id: int,
    override_id: int,
    db: Session = Depends(get_db),
):
    reset_content_override(db, override_id)
    return RedirectResponse(url=f"/ui/campaigns/{campaign_id}", status_code=303)


@router.post("/ui/campaigns/{campaign_id}/variants/{variant_id}/snapshots")
def snapshot_create(
    campaign_id: int,
    variant_id: int,
    db: Session = Depends(get_db),
):
    try:
        create_snapshot_for_variant(db, variant_id=variant_id)
    except UnpublishedContentError as exc:
        return RedirectResponse(
            url=f"/ui/campaigns/{campaign_id}?error={quote(str(exc))}",
            status_code=303,
        )
    return RedirectResponse(url=f"/ui/campaigns/{campaign_id}", status_code=303)


@router.post("/ui/campaigns/{campaign_id}/snapshots/{snapshot_id}/send-instances")
def send_instance_create(
    campaign_id: int,
    snapshot_id: int,
    name: str = Form(...),
    audience_group_id: str = Form(""),
    provider: str = Form("mock"),
    from_address: str = Form(""),
    audience_resolution_mode: str = Form("freeze"),
    send_timing: str = Form("now"),
    scheduled_at: str = Form(""),
    db: Session = Depends(get_db),
):
    """Plan a delivery: pick an audience → provider / from address → resolution
    mode → timing. Materializes the send instance and one execution per resolved
    recipient. Lands on the delivery page (draft, or scheduled if a time is set)."""
    if not audience_group_id.strip():
        return RedirectResponse(
            url=f"/ui/campaigns/{campaign_id}?error={quote('Select an audience to plan a send.')}",
            status_code=303,
        )

    scheduled = None
    if send_timing == "schedule":
        if not scheduled_at.strip():
            return RedirectResponse(
                url=f"/ui/campaigns/{campaign_id}?error={quote('Pick a date/time to schedule the send.')}",
                status_code=303,
            )
        try:
            # datetime-local gives "YYYY-MM-DDTHH:MM"; stored naive, compared
            # DB-side in process_due_scheduled_sends.
            scheduled = datetime.fromisoformat(scheduled_at)
        except ValueError:
            return RedirectResponse(
                url=f"/ui/campaigns/{campaign_id}?error={quote('Invalid schedule date/time.')}",
                status_code=303,
            )

    try:
        send_instance = prepare_send_from_audience(
            db,
            snapshot_id=snapshot_id,
            name=name,
            audience_group_id=int(audience_group_id),
            provider=provider,
            from_address=from_address.strip() or None,
            audience_resolution_mode=audience_resolution_mode,
            scheduled_at=scheduled,
        )
    except ValueError as error:
        return RedirectResponse(
            url=f"/ui/campaigns/{campaign_id}?error={quote(str(error))}",
            status_code=303,
        )
    return RedirectResponse(url=f"/ui/deliveries/send-instances/{send_instance.id}", status_code=303)


@router.post("/ui/decisions/slots/{slot_id}/edit")
def decision_slot_edit(
    slot_id: int,
    decision_strategy: str = Form(...),
    candidate_filter_json: str = Form("{}"),
    strategy_config_json: str = Form("{}"),
    category_ids: list[str] = Form(default=[]),
    db: Session = Depends(get_db),
):
    import json as _json
    try:
        candidate_filter = _json.loads(candidate_filter_json) or {}
        strategy_config = _json.loads(strategy_config_json) or None
    except ValueError:
        return RedirectResponse(
            url=f"/ui/decisions/slots/{slot_id}?error={quote('Config/filter must be valid JSON')}",
            status_code=303,
        )

    # The category picker (a name-based multi-select) is the friendly way to set
    # candidate_filter.category_ids — it wins over whatever's in the raw JSON for
    # that one key, so a manager never hand-types category IDs. Empty selection =
    # remove the key = "consider every category" (the strategies' documented
    # empty-means-all semantics). Other candidate_filter keys stay in the JSON.
    selected = [int(c) for c in category_ids if str(c).strip()]
    if selected:
        candidate_filter["category_ids"] = selected
    else:
        candidate_filter.pop("category_ids", None)
    candidate_filter = candidate_filter or None
    try:
        update_decision_slot(db, slot_id, decision_strategy, candidate_filter, strategy_config)
    except ValueError as error:
        # The config/filter didn't match the chosen strategy's declared shape —
        # surface it now instead of letting it crash later at resolution time.
        return RedirectResponse(
            url=f"/ui/decisions/slots/{slot_id}?error={quote(str(error))}",
            status_code=303,
        )
    return RedirectResponse(url=f"/ui/decisions/slots/{slot_id}", status_code=303)


@router.post("/ui/send-instances/{send_instance_id}/send")
def send_instance_trigger(
    send_instance_id: int,
    db: Session = Depends(get_db),
):
    try:
        send_send_instance(db, send_instance_id=send_instance_id)
    except ValueError as error:
        # e.g. re-resolved "rerun" audience exceeds the send cap, or already sent.
        return RedirectResponse(
            url=f"/ui/deliveries/send-instances/{send_instance_id}?error={quote(str(error))}",
            status_code=303,
        )
    return RedirectResponse(url=f"/ui/deliveries/send-instances/{send_instance_id}", status_code=303)


@router.post("/ui/deliveries/process-due")
def deliveries_process_due(db: Session = Depends(get_db)):
    """Fire all scheduled sends that are due now. In the POC this is a manual
    button; in a real deployment a cron/worker/automation platform calls this
    same operation on an interval (the architecture exposes the seam, doesn't
    bake in a scheduler)."""
    triggered = process_due_scheduled_sends(db)
    msg = f"Triggered {len(triggered)} due scheduled send(s)." if triggered else "No scheduled sends were due."
    return RedirectResponse(url=f"/ui/deliveries?notice={quote(msg)}", status_code=303)


@router.get("/ui/content")
def content_list(
    request: Request,
    show_inactive: bool = False,
    notice: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    brand_id = working_brand_id(request, db)
    query = db.query(ContentRecordDB).filter(ContentRecordDB.brand_id == brand_id)
    if not show_inactive:
        query = query.filter(ContentRecordDB.status == "active")
    records = query.order_by(ContentRecordDB.id.asc()).all()

    inactive_count = (
        db.query(ContentRecordDB)
        .filter(ContentRecordDB.brand_id == brand_id)
        .filter(ContentRecordDB.status != "active")
        .count()
    )

    return templates.TemplateResponse(
        request,
        "content.html",
        {
            "title": "Content",
            "records": records,
            "show_inactive": show_inactive,
            "inactive_count": inactive_count,
            "channel_sections": _channel_authoring_sections(db),
            # `content_detail` has redirected here with ?error= since brand
            # scoping landed, but the route never accepted the parameter and
            # the template never rendered it — so "that record does not exist
            # in this brand" was silently dropped for anyone who hit it.
            "notice": notice,
            "error": error,
        },
    )


@router.get("/ui/content/{content_record_id}")
def content_detail(
    content_record_id: int,
    request: Request,
    error: str | None = None,
    confirm_delete: bool = False,
    db: Session = Depends(get_db),
):
    record = (
        db.query(ContentRecordDB)
        .filter(
            ContentRecordDB.id == content_record_id,
            ContentRecordDB.brand_id == working_brand_id(request, db),
        )
        .first()
    )

    # Until the brand filter above, `record` could not be None on this route —
    # the id came from a list the caller had just been shown. Scoping it made
    # absence reachable for the first time, and `content_detail.html` reads
    # `record.content.headline_medium` unguarded, so the page raised a 500
    # instead of saying no. Answering exactly as a deleted record does is also
    # the point: another brand's content must be indistinguishable from content
    # that does not exist.
    if record is None:
        return RedirectResponse(
            url="/ui/content?error=" + quote("That content record does not exist in this brand."),
            status_code=303,
        )

    categories = (
        db.query(
            ContentCategoryAssignmentDB.id,
            CategoryDB.name,
            CategoryDB.type,
            ContentCategoryAssignmentDB.score,
        )
        .join(
            ContentCategoryAssignmentDB,
            ContentCategoryAssignmentDB.category_id == CategoryDB.id,
        )
        .filter(
            ContentCategoryAssignmentDB.content_id == content_record_id
        )
        .all()
    )

    category_rows = [
        {
            "assignment_id": assignment_id,
            "name": name,
            "type": category_type,
            "score": score,
        }
        for assignment_id, name, category_type, score in categories
    ]

    versions = (
        db.query(ContentVersionDB)
        .filter(ContentVersionDB.content_record_id == content_record_id)
        .order_by(ContentVersionDB.version_number.desc())
        .all()
    )

    version_rows = [
        {
            "version_number": version.version_number,
            "created_by": version.created_by,
            "created_at": version.created_at,
            "headline": (
                (version.content or {}).get("headline_medium")
                or (version.content or {}).get("headline_short")
                or (version.content or {}).get("headline")
            ),
            "text": (
                (version.content or {}).get("body_medium")
                or (version.content or {}).get("text_medium")
                or (version.content or {}).get("text_short")
                or (version.content or {}).get("text")
            ),
            "button_label": (version.content or {}).get("button_label"),
        }
        for version in versions
    ]

    decision_usage = (
        db.query(DecisionResolutionDB)
        .filter(
            DecisionResolutionDB.content_record_id == content_record_id
        )
        .order_by(
            DecisionResolutionDB.created_at.desc()
        )
        .limit(20)
        .all()
    )

    signals = (
        db.query(
            SignalContributionDB,
            CategoryDB.name,
            EngagementEventDB.event_data,
        )
        .join(
            CategoryDB,
            SignalContributionDB.category_id == CategoryDB.id,
        )
        .join(
            EngagementEventDB,
            SignalContributionDB.event_id == EngagementEventDB.id,
        )
        .order_by(
            SignalContributionDB.created_at.desc()
        )
        .limit(100)
        .all()
    )

    signal_rows = []

    for update, category_name, event_data in signals:
        event_content_record_id = (event_data or {}).get("content_record_id")

        if event_content_record_id != content_record_id:
            continue

        signal_rows.append(
            {
                "recipient_id": update.recipient_id,
                "category_name": category_name,
                "previous_score": None,
                "delta": update.base_weight,
                "new_score": None,
                "reason": update.contribution_type,
                "created_at": update.created_at,
            }
        )

    all_categories = db.query(CategoryDB).order_by(CategoryDB.name.asc()).all()

    return templates.TemplateResponse(
        request,
        "content_detail.html",
        {
            "title": f"Content {content_record_id}",
            "record": record,
            "categories": category_rows,
            "versions": version_rows,
            "decision_usage": decision_usage,
            "preference_signals": signal_rows,
            "all_categories": all_categories,
            "error": error,
            "confirm_delete": confirm_delete,
            # Which brands this record may be copied into — the target's own
            # content permission, not the working brand's, because the copy is
            # written there.
            "duplicate_targets": _duplication_targets(db, request, CONTENT_MANAGE),
            "channel_sections": _channel_authoring_sections(db),
        },
    )


@router.post("/ui/content/{content_record_id}/set-status")
def content_set_status(
    content_record_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        set_content_status(db, content_record_id, status)
    except ValueError as error:
        return RedirectResponse(
            url=f"/ui/content/{content_record_id}?error={quote(str(error))}",
            status_code=303,
        )
    return RedirectResponse(url=f"/ui/content/{content_record_id}", status_code=303)


@router.post("/ui/content/{content_record_id}/delete")
def content_delete(
    content_record_id: int,
    force: bool = Form(False),
    db: Session = Depends(get_db),
):
    try:
        delete_content_record(db, content_record_id, force=force)
    except ContentRecordHasHistoryError as error:
        return RedirectResponse(
            url=f"/ui/content/{content_record_id}?error={quote(str(error))}",
            status_code=303,
        )
    except HasRelationsError as error:
        return RedirectResponse(
            url=f"/ui/content/{content_record_id}?error={quote(str(error))}&confirm_delete=true",
            status_code=303,
        )
    return RedirectResponse(url="/ui/content", status_code=303)


@router.post("/ui/content")
def content_create(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    headline_medium: str = Form(...),
    body_medium: str = Form(""),
    button_label: str = Form(""),
    button_url: str = Form(""),
    image_url: str = Form(""),
    image_alt: str = Form(""),
    push_title: str = Form(""),
    push_body: str = Form(""),
    push_image_url: str = Form(""),
    push_link: str = Form(""),
    db: Session = Depends(get_db),
):
    content = {
        "headline_medium": headline_medium,
        "body_medium": body_medium,
        "button_label": button_label,
        "button_url": button_url,
        "image_url": image_url,
        "image_alt": image_alt,
    }
    # Only stored when actually written. An empty push_title is the difference
    # between "not prepared for push" and "prepared with nothing in it", and
    # ADR-161 point 7's rider makes catalogue readiness exactly "push fields
    # not empty" — so writing empty strings would make every record look
    # push-ready.
    for name, value in (
        ("push_title", push_title), ("push_body", push_body),
        ("push_image_url", push_image_url), ("push_link", push_link),
    ):
        if value.strip():
            content[name] = value.strip()

    record = create_content(
        db,
        title=title,
        brand_id=working_brand_id(request, db),
        description=description or None,
        content=content,
    )
    return RedirectResponse(url=f"/ui/content/{record.id}", status_code=303)


@router.post("/ui/content/{content_record_id}/duplicate")
def content_duplicate(
    content_record_id: int,
    request: Request,
    target_brand_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """One record, one step — no wizard.

    The campaign wizard is deliberate because duplicating a campaign multiplies:
    one click can produce a dozen content records and a composition that cannot
    send. A single record does neither, so gating it the same way would be
    ceremony without a risk behind it.
    """
    record = (
        db.query(ContentRecordDB)
        .filter(
            ContentRecordDB.id == content_record_id,
            ContentRecordDB.brand_id == working_brand_id(request, db),
        )
        .first()
    )
    if record is None:
        return RedirectResponse(
            url="/ui/content?error=" + quote("That content record does not exist in this brand."),
            status_code=303,
        )

    targets = _duplication_targets(db, request, CONTENT_MANAGE)
    target = next((b for b in targets if b.id == target_brand_id), None)
    if target is None:
        return RedirectResponse(
            url="/ui/content?error=" + quote("You cannot create content in that brand."),
            status_code=303,
        )

    try:
        copy = duplication.duplicate_content_record(
            db, content_id=record.id, target_brand_id=target.id
        )
    except duplication.DuplicationRefused as error:
        return RedirectResponse(
            url="/ui/content?error=" + quote(str(error)), status_code=303
        )

    audit.record_from_request(
        request,
        db,
        audit.CONTENT_DUPLICATED,
        subject_type="content_record",
        subject_id=copy.id,
        brand_id=target.id,
        detail={
            "source_content_id": record.id,
            "source_brand_id": record.brand_id,
            "target_brand_id": target.id,
        },
    )

    if target.id == record.brand_id:
        return RedirectResponse(url=f"/ui/content/{copy.id}", status_code=303)

    return RedirectResponse(
        url="/ui/content?notice=" + quote(
            f"Copied “{copy.title}” into {target.name}. It has no published version "
            "yet, so a campaign using it cannot be sent until someone publishes it."
        ),
        status_code=303,
    )


@router.post("/ui/content/{content_record_id}/edit")
def content_edit(
    content_record_id: int,
    title: str = Form(...),
    description: str = Form(""),
    headline_medium: str = Form(...),
    body_medium: str = Form(""),
    button_label: str = Form(""),
    button_url: str = Form(""),
    image_url: str = Form(""),
    image_alt: str = Form(""),
    push_title: str = Form(""),
    push_body: str = Form(""),
    push_image_url: str = Form(""),
    push_link: str = Form(""),
    # **Which channel sections this form actually rendered.** The route cannot
    # work it out for itself: an absent field and a cleared one are
    # indistinguishable, because FastAPI coerces an empty form value to None
    # for a `str | None` parameter — so `Form(None)` looks like it draws that
    # line and does not. Checked against 0.136/pydantic 2.13 rather than
    # assumed, after a test caught it.
    #
    # Without this the merge below could not tell "push is switched off, so
    # this form never asked" from "the author emptied the push title", and it
    # would erase push copy on every edit made while push was off.
    channel_sections_present: list[str] = Form([]),
    db: Session = Depends(get_db),
):
    # **Merged onto what is there, not replacing it.** This route used to
    # rebuild `content` from scratch, so any key the form did not carry was
    # silently dropped — harmless while the form knew every field, and a
    # data-loss bug the moment a channel's fields are conditionally rendered:
    # editing a record while push is switched off would erase its push copy.
    existing = get_content_record(db, content_record_id)
    content = dict((existing.content if existing else None) or {})
    content.update({
        "headline_medium": headline_medium,
        "body_medium": body_medium,
        "button_label": button_label,
        "button_url": button_url,
        "image_url": image_url,
        "image_alt": image_alt,
    })
    if "push" in channel_sections_present:
        for name, value in (
            ("push_title", push_title), ("push_body", push_body),
            ("push_image_url", push_image_url), ("push_link", push_link),
        ):
            if value.strip():
                content[name] = value.strip()
            else:
                # Asked and left empty means the author cleared it. Removed
                # rather than stored as "" — ADR-161 point 7's rider makes
                # catalogue readiness "push fields not empty", so a blank
                # string would leave the record looking push-ready.
                content.pop(name, None)

    update_content_record(
        db,
        content_record_id,
        title=title,
        description=description or None,
        content=content,
    )
    return RedirectResponse(url=f"/ui/content/{content_record_id}", status_code=303)


@router.post("/ui/content/{content_record_id}/publish-version")
def content_publish_version(
    content_record_id: int,
    created_by: str = Form(""),
    db: Session = Depends(get_db),
):
    create_content_version(
        db,
        content_record_id=content_record_id,
        created_by=created_by or None,
    )
    return RedirectResponse(url=f"/ui/content/{content_record_id}", status_code=303)


@router.post("/ui/content/{content_record_id}/assign-category")
def content_assign_category(
    content_record_id: int,
    category_id: int = Form(...),
    score: int = Form(10),
    db: Session = Depends(get_db),
):
    try:
        assign_category_to_content(db, content_id=content_record_id, category_id=category_id, score=score)
    except ValueError as error:
        return RedirectResponse(
            url=f"/ui/content/{content_record_id}?error={quote(str(error))}",
            status_code=303,
        )
    return RedirectResponse(url=f"/ui/content/{content_record_id}", status_code=303)


@router.get("/ui/categories")
def categories_list(
    request: Request,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    categories = (
        db.query(CategoryDB)
        .order_by(CategoryDB.type.asc(), CategoryDB.name.asc())
        .all()
    )

    category_rows = []

    for category in categories:
        parent_count = (
            db.query(func.count(CategoryRelationDB.id))
            .filter(CategoryRelationDB.child_category_id == category.id)
            .scalar()
        )

        child_count = (
            db.query(func.count(CategoryRelationDB.id))
            .filter(CategoryRelationDB.parent_category_id == category.id)
            .scalar()
        )

        category_rows.append(
            {
                "id": category.id,
                "name": category.name,
                "type": category.type,
                "parent_count": parent_count,
                "child_count": child_count,
            }
        )

    return templates.TemplateResponse(
        request,
        "categories.html",
        {
            "title": "Categories",
            "categories": category_rows,
            "all_categories": categories,
            "error": error,
        },
    )


@router.get("/ui/categories/{category_id}")
def category_detail(
    category_id: int,
    request: Request,
    error: str | None = None,
    confirm_delete: bool = False,
    db: Session = Depends(get_db),
):
    category = (
        db.query(CategoryDB)
        .filter(CategoryDB.id == category_id)
        .first()
    )

    parent_categories = (
        db.query(CategoryDB, CategoryRelationDB.id.label("relation_id"))
        .join(
            CategoryRelationDB,
            CategoryRelationDB.parent_category_id == CategoryDB.id,
        )
        .filter(
            CategoryRelationDB.child_category_id == category_id
        )
        .order_by(CategoryDB.name.asc())
        .all()
    )

    child_categories = (
        db.query(CategoryDB, CategoryRelationDB.id.label("relation_id"))
        .join(
            CategoryRelationDB,
            CategoryRelationDB.child_category_id == CategoryDB.id,
        )
        .filter(
            CategoryRelationDB.parent_category_id == category_id
        )
        .order_by(CategoryDB.name.asc())
        .all()
    )

    assigned_content = (
        db.query(
            ContentRecordDB.id,
            ContentRecordDB.title,
            ContentCategoryAssignmentDB.score,
        )
        .join(
            ContentCategoryAssignmentDB,
            ContentCategoryAssignmentDB.content_id == ContentRecordDB.id,
        )
        .filter(
            ContentCategoryAssignmentDB.category_id == category_id
        )
        .order_by(
            ContentCategoryAssignmentDB.score.desc()
        )
        .all()
    )

    assigned_content_rows = [
        {
            "content_id": content_id,
            "title": title,
            "score": score,
        }
        for content_id, title, score in assigned_content
    ]

    # Recipients ranked by their operational signal for this category
    # (decay-on-read, ADR-132), not a stored preference score.
    category_signals = operational_signals_for_category(db, category_id)
    if category_signals:
        recip_lookup = dict(
            db.query(RecipientDB.id, RecipientDB.external_id)
            .filter(RecipientDB.id.in_(category_signals.keys()))
            .all()
        )
        recipient_preference_rows = sorted(
            [
                {
                    "recipient_id": rid,
                    "recipient_external_id": recip_lookup.get(rid),
                    "score": round(score, 1),
                    "source": "signal",
                }
                for rid, score in category_signals.items()
            ],
            key=lambda r: r["score"],
            reverse=True,
        )[:50]
    else:
        recipient_preference_rows = []

    impact = (
        db.query(
            func.count(SignalContributionDB.id),
            func.coalesce(func.sum(SignalContributionDB.base_weight), 0),
            func.coalesce(func.avg(SignalContributionDB.base_weight), 0),
        )
        .filter(
            SignalContributionDB.category_id == category_id
        )
        .first()
    )

    impact_summary = {
        "update_count": impact[0],
        "total_delta": round(float(impact[1]), 2),
        "avg_delta": round(float(impact[2]), 2),
    }

    all_categories = db.query(CategoryDB).order_by(CategoryDB.name.asc()).all()

    return templates.TemplateResponse(
        request,
        "category_detail.html",
        {
            "title": f"Category {category_id}",
            "category": category,
            "parent_categories": parent_categories,
            "child_categories": child_categories,
            "assigned_content": assigned_content_rows,
            "recipient_preferences": recipient_preference_rows,
            "impact_summary": impact_summary,
            "all_categories": all_categories,
            "error": error,
            "confirm_delete": confirm_delete,
        },
    )


@router.post("/ui/categories/{category_id}/delete")
def category_delete(
    category_id: int,
    force: bool = Form(False),
    db: Session = Depends(get_db),
):
    try:
        delete_category(db, category_id, force=force)
    except HasRelationsError as error:
        return RedirectResponse(
            url=f"/ui/categories/{category_id}?error={quote(str(error))}&confirm_delete=true",
            status_code=303,
        )
    return RedirectResponse(url="/ui/categories", status_code=303)


@router.post("/ui/categories")
def category_create(
    name: str = Form(...),
    type: str = Form("main"),
    db: Session = Depends(get_db),
):
    create_category(db, name=name, type=type)
    return RedirectResponse(url="/ui/categories", status_code=303)


@router.post("/ui/categories/relations")
def category_relation_create(
    parent_category_id: int = Form(...),
    child_category_id: int = Form(...),
    db: Session = Depends(get_db),
):
    try:
        create_category_relation(db, parent_category_id=parent_category_id, child_category_id=child_category_id)
    except ValueError as error:
        return RedirectResponse(url=f"/ui/categories?error={quote(str(error))}", status_code=303)
    return RedirectResponse(url="/ui/categories", status_code=303)


@router.post("/ui/categories/{category_id}/relations/{relation_id}/delete")
def category_relation_delete(
    category_id: int,
    relation_id: int,
    db: Session = Depends(get_db),
):
    delete_category_relation(db, relation_id)
    return RedirectResponse(url=f"/ui/categories/{category_id}", status_code=303)


@router.get("/ui/decisions")
def decisions_list(
    request: Request,
    db: Session = Depends(get_db),
):
    slots = (
        db.query(
            DecisionSlotDB,
            VariantDB.id.label("variant_id"),
            VariantDB.name.label("variant_name"),
            CampaignDB.id.label("campaign_id"),
            CampaignDB.name.label("campaign_name"),
            func.count(DecisionResolutionDB.id).label("resolution_count"),
            func.count(func.distinct(DecisionResolutionDB.content_record_id)).label("unique_content_count"),
            func.max(DecisionResolutionDB.created_at).label("last_resolution_at"),
        )
        .join(
            VariantDB,
            DecisionSlotDB.variant_id == VariantDB.id,
        )
        .join(
            CampaignDB,
            VariantDB.campaign_id == CampaignDB.id,
        )
        # A decision slot has no brand of its own — it inherits one through the
        # variant's campaign, which is the only place the brand is recorded.
        .filter(CampaignDB.brand_id == working_brand_id(request, db))
        .outerjoin(
            DecisionResolutionDB,
            DecisionResolutionDB.decision_slot_id == DecisionSlotDB.id,
        )
        .group_by(
            DecisionSlotDB.id,
            VariantDB.id,
            VariantDB.name,
            CampaignDB.id,
            CampaignDB.name,
        )
        .order_by(
            CampaignDB.id.asc(),
            VariantDB.id.asc(),
            DecisionSlotDB.id.asc(),
        )
        .all()
    )

    slot_rows = [
        {
            "id": slot.id,
            "name": slot.name,
            "decision_type": slot.decision_type,
            "decision_strategy": slot.decision_strategy,
            "variant_id": variant_id,
            "variant_name": variant_name,
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "resolution_count": resolution_count,
            "unique_content_count": unique_content_count,
            "last_resolution_at": last_resolution_at,
        }
        for (
            slot,
            variant_id,
            variant_name,
            campaign_id,
            campaign_name,
            resolution_count,
            unique_content_count,
            last_resolution_at,
        ) in slots
    ]

    return templates.TemplateResponse(
        request,
        "decisions.html",
        {
            "title": "Decisions",
            "slots": slot_rows,
        },
    )


@router.get("/ui/decisions/slots/{decision_slot_id}")
def decision_slot_detail(
    decision_slot_id: int,
    request: Request,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    slot_context = (
        db.query(
            DecisionSlotDB,
            VariantDB.id.label("variant_id"),
            VariantDB.name.label("variant_name"),
            CampaignDB.id.label("campaign_id"),
            CampaignDB.name.label("campaign_name"),
        )
        .join(
            VariantDB,
            DecisionSlotDB.variant_id == VariantDB.id,
        )
        .join(
            CampaignDB,
            VariantDB.campaign_id == CampaignDB.id,
        )
        .filter(
            DecisionSlotDB.id == decision_slot_id,
            CampaignDB.brand_id == working_brand_id(request, db),
        )
        .first()
    )

    if not slot_context:
        return templates.TemplateResponse(
            request,
            "decision_slot_detail.html",
            {
                "title": f"Decision Slot {decision_slot_id}",
                "slot": None,
            },
        )

    slot, variant_id, variant_name, campaign_id, campaign_name = slot_context

    summary = (
        db.query(
            func.count(DecisionResolutionDB.id),
            func.count(func.distinct(DecisionResolutionDB.recipient_id)),
            func.count(func.distinct(DecisionResolutionDB.content_record_id)),
            func.coalesce(func.avg(DecisionResolutionDB.score), 0),
            func.coalesce(func.min(DecisionResolutionDB.score), 0),
            func.coalesce(func.max(DecisionResolutionDB.score), 0),
            func.max(DecisionResolutionDB.created_at),
        )
        .filter(
            DecisionResolutionDB.decision_slot_id == decision_slot_id
        )
        .first()
    )

    resolution_summary = {
        "resolution_count": summary[0],
        "unique_recipient_count": summary[1],
        "unique_content_count": summary[2],
        "avg_score": round(float(summary[3]), 2),
        "min_score": round(float(summary[4]), 2),
        "max_score": round(float(summary[5]), 2),
        "last_resolution_at": summary[6],
    }

    top_content = (
        db.query(
            ContentRecordDB.id,
            ContentRecordDB.title,
            ContentVersionDB.version_number,
            func.count(DecisionResolutionDB.id).label("selection_count"),
        )
        .join(
            ContentRecordDB,
            DecisionResolutionDB.content_record_id == ContentRecordDB.id,
        )
        .outerjoin(
            ContentVersionDB,
            DecisionResolutionDB.content_version_id == ContentVersionDB.id,
        )
        .filter(
            DecisionResolutionDB.decision_slot_id == decision_slot_id
        )
        .group_by(
            ContentRecordDB.id,
            ContentRecordDB.title,
            ContentVersionDB.version_number,
        )
        .order_by(
            desc("selection_count")
        )
        .limit(20)
        .all()
    )

    total_resolutions = resolution_summary["resolution_count"] or 0

    top_content_rows = [
        {
            "content_id": content_id,
            "title": title,
            "version_number": version_number,
            "selection_count": selection_count,
            "share": round((selection_count / total_resolutions) * 100, 2)
            if total_resolutions
            else 0,
        }
        for content_id, title, version_number, selection_count in top_content
    ]

    latest_resolutions = (
        db.query(
            DecisionResolutionDB,
            ContentRecordDB.title,
            ContentVersionDB.version_number,
        )
        .join(
            ContentRecordDB,
            DecisionResolutionDB.content_record_id == ContentRecordDB.id,
        )
        .outerjoin(
            ContentVersionDB,
            DecisionResolutionDB.content_version_id == ContentVersionDB.id,
        )
        .filter(
            DecisionResolutionDB.decision_slot_id == decision_slot_id
        )
        .order_by(
            DecisionResolutionDB.created_at.desc()
        )
        .limit(50)
        .all()
    )

    latest_resolution_rows = [
        {
            "id": resolution.id,
            "recipient_id": resolution.recipient_id,
            "content_record_id": resolution.content_record_id,
            "content_title": content_title,
            "content_version": version_number,
            "score": resolution.score,
            "reason": resolution.reason,
            "created_at": resolution.created_at,
        }
        for resolution, content_title, version_number in latest_resolutions
    ]

    reason_summary = (
        db.query(
            DecisionResolutionDB.reason,
            func.count(DecisionResolutionDB.id).label("count"),
        )
        .filter(
            DecisionResolutionDB.decision_slot_id == decision_slot_id
        )
        .group_by(
            DecisionResolutionDB.reason
        )
        .order_by(
            desc("count")
        )
        .limit(20)
        .all()
    )

    reason_summary_rows = [
        {
            "reason": reason,
            "count": count,
        }
        for reason, count in reason_summary
    ]

    strategy_metas = list_strategies()
    supported_strategies = sorted(s.name for s in strategy_metas)

    # Declared config/filter shape per strategy, so the edit form can show
    # which keys are valid (structure is locked to the chosen strategy).
    strategy_manifests = {
        meta.name: {
            "candidate_filter_fields": [
                {"name": f.name, "type": f.type, "default": f.default, "description": f.description}
                for f in meta.candidate_filter_fields
            ],
            "config_fields": [
                {"name": f.name, "type": f.type, "default": f.default, "description": f.description}
                for f in meta.config_fields
            ],
        }
        for meta in strategy_metas
    }

    candidate_filter_pretty = json.dumps(
        slot.candidate_filter or {},
        indent=2,
        ensure_ascii=False,
    )

    strategy_config_pretty = json.dumps(
        slot.strategy_config or {},
        indent=2,
        ensure_ascii=False,
    )

    return templates.TemplateResponse(
        request,
        "decision_slot_detail.html",
        {
            "title": f"Decision Slot {decision_slot_id}",
            "slot": {
                "id": slot.id,
                "name": slot.name,
                "decision_type": slot.decision_type,
                "decision_strategy": slot.decision_strategy,
                "variant_id": variant_id,
                "variant_name": variant_name,
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "candidate_filter": slot.candidate_filter,
                "candidate_filter_pretty": candidate_filter_pretty,
                "strategy_config": slot.strategy_config,
                "strategy_config_pretty": strategy_config_pretty,
                "supported_strategies": supported_strategies,
                "selected_category_ids": (slot.candidate_filter or {}).get("category_ids") or [],
            },
            "all_categories": db.query(CategoryDB).order_by(CategoryDB.name.asc()).all(),
            "strategy_manifests": strategy_manifests,
            "error": error,
            "summary": resolution_summary,
            "reason_summary": reason_summary_rows,
            "top_content": top_content_rows,
            "latest_resolutions": latest_resolution_rows,
        },
    )


@router.get("/ui/deliveries")
def deliveries_list(
    request: Request,
    notice: str | None = None,
    db: Session = Depends(get_db),
):
    send_instances = (
        db.query(SendInstanceDB)
        # send_instances.brand_id is the sending brand and the arbiter of
        # record — the send went out as this brand whatever its snapshot chain
        # says — so this filters on the column rather than walking to campaign.
        .filter(SendInstanceDB.brand_id == working_brand_id(request, db))
        .order_by(SendInstanceDB.created_at.desc())
        .all()
    )

    rows = []

    for send_instance in send_instances:
        snapshot = (
            db.query(SnapshotDB)
            .filter(SnapshotDB.id == send_instance.snapshot_id)
            .first()
        )

        variant = None
        campaign = None

        if snapshot:
            variant = (
                db.query(VariantDB)
                .filter(VariantDB.id == snapshot.variant_id)
                .first()
            )

            if variant:
                campaign = (
                    db.query(CampaignDB)
                    .filter(CampaignDB.id == variant.campaign_id)
                    .first()
                )

        execution_count = (
            db.query(DeliveryExecutionDB)
            .filter(DeliveryExecutionDB.send_instance_id == send_instance.id)
            .count()
        )

        sent_count = (
            db.query(DeliveryExecutionDB)
            .filter(
                DeliveryExecutionDB.send_instance_id == send_instance.id,
                DeliveryExecutionDB.status == "sent",
            )
            .count()
        )

        event_count = (
            db.query(EngagementEventDB)
            .join(
                DeliveryExecutionDB,
                EngagementEventDB.delivery_execution_id == DeliveryExecutionDB.id,
            )
            .filter(
                DeliveryExecutionDB.send_instance_id == send_instance.id
            )
            .count()
        )

        rows.append(
            {
                "id": send_instance.id,
                "name": send_instance.name,
                "status": send_instance.status,
                "provider": send_instance.provider,
                "scheduled_at": send_instance.scheduled_at,
                "created_at": send_instance.created_at,
                "snapshot_id": send_instance.snapshot_id,
                "campaign_id": campaign.id if campaign else None,
                "campaign_name": campaign.name if campaign else None,
                "variant_id": variant.id if variant else None,
                "variant_name": variant.name if variant else None,
                "recipient_id": snapshot.recipient_id if snapshot else None,
                "execution_count": execution_count,
                "sent_count": sent_count,
                "event_count": event_count,
            }
        )

    return templates.TemplateResponse(
        request,
        "deliveries.html",
        {
            "title": "Deliveries",
            "send_instances": rows,
            "notice": notice,
            "scheduled_count": sum(1 for r in rows if r["status"] == "scheduled"),
        },
    )


@router.get("/ui/deliveries/send-instances/{send_instance_id}")
def delivery_detail(
    send_instance_id: int,
    request: Request,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    send_instance = (
        db.query(SendInstanceDB)
        .filter(
            SendInstanceDB.id == send_instance_id,
            SendInstanceDB.brand_id == working_brand_id(request, db),
        )
        .first()
    )

    if send_instance is None:
        return templates.TemplateResponse(
            request,
            "delivery_detail.html",
            {
                "title": f"Delivery {send_instance_id}",
                "send_instance": None,
            },
        )

    snapshot = (
        db.query(SnapshotDB)
        .filter(SnapshotDB.id == send_instance.snapshot_id)
        .first()
    )

    executions = (
        db.query(DeliveryExecutionDB)
        .filter(DeliveryExecutionDB.send_instance_id == send_instance_id)
        .order_by(DeliveryExecutionDB.created_at.desc())
        .all()
    )

    execution_rows = []

    for execution in executions:
        recipient = (
            db.query(RecipientDB)
            .filter(RecipientDB.id == execution.recipient_id)
            .first()
        )

        events = (
            db.query(EngagementEventDB)
            .filter(EngagementEventDB.delivery_execution_id == execution.id)
            .order_by(EngagementEventDB.created_at.desc())
            .all()
        )

        event_rows = []

        for event in events:
            preference_updates = (
                db.query(
                    SignalContributionDB,
                    CategoryDB.name,
                )
                .join(
                    CategoryDB,
                    SignalContributionDB.category_id == CategoryDB.id,
                )
                .filter(
                    SignalContributionDB.event_id == event.id
                )
                .all()
            )

            event_rows.append(
                {
                    "id": event.id,
                    "event_type": event.event_type,
                    "provider": event.provider,
                    "provider_event_id": event.provider_event_id,
                    "event_data_pretty": json.dumps(
                        event.event_data or {},
                        indent=2,
                        ensure_ascii=False,
                    ),
                    "occurred_at": event.occurred_at,
                    "created_at": event.created_at,
                    "preference_updates": [
                        {
                            "category_name": category_name,
                            "previous_score": None,
                            "delta": update.base_weight,
                            "new_score": None,
                            "reason": update.contribution_type,
                        }
                        for update, category_name in preference_updates
                    ],
                }
            )

        execution_rows.append(
            {
                "id": execution.id,
                "recipient_external_id": recipient.external_id if recipient else None,
                "recipient_id": execution.recipient_id,
                "status": execution.status,
                "provider": execution.provider,
                "provider_message_id": execution.provider_message_id,
                "created_at": execution.created_at,
                "updated_at": execution.updated_at,
                "events": event_rows,
            }
        )

    audience_group = None
    if send_instance.audience_group_id:
        audience_group = (
            db.query(AudienceGroupDB)
            .filter(AudienceGroupDB.id == send_instance.audience_group_id)
            .first()
        )

    return templates.TemplateResponse(
        request,
        "delivery_detail.html",
        {
            "title": f"Delivery {send_instance_id}",
            "send_instance": send_instance,
            "snapshot": snapshot,
            "executions": execution_rows,
            "audience_group": audience_group,
            "recipient_count": len(execution_rows),
            "error": error,
        },
    )


@router.get("/ui/graph")
def category_graph(
    request: Request,
    db: Session = Depends(get_db),
):
    categories = (
        db.query(CategoryDB)
        .order_by(CategoryDB.type.asc(), CategoryDB.name.asc())
        .all()
    )

    category_lookup = {
        category.id: category
        for category in categories
    }

    # ---------------------------------------------------------
    # Node metrics
    # ---------------------------------------------------------

    selection_rows = (
        db.query(
            ContentCategoryAssignmentDB.category_id,
            func.count(DecisionResolutionDB.id),
        )
        .join(
            DecisionResolutionDB,
            DecisionResolutionDB.content_record_id
            == ContentCategoryAssignmentDB.content_id,
        )
        .group_by(ContentCategoryAssignmentDB.category_id)
        .all()
    )

    selections_by_category = {
        category_id: count
        for category_id, count in selection_rows
    }

    content_rows = (
        db.query(
            ContentCategoryAssignmentDB.category_id,
            func.count(func.distinct(ContentCategoryAssignmentDB.content_id)),
        )
        .group_by(ContentCategoryAssignmentDB.category_id)
        .all()
    )

    content_count_by_category = {
        category_id: count
        for category_id, count in content_rows
    }

    impact_rows = (
        db.query(
            SignalContributionDB.category_id,
            func.count(SignalContributionDB.id),
            func.coalesce(func.sum(SignalContributionDB.base_weight), 0),
            func.coalesce(func.avg(SignalContributionDB.base_weight), 0),
            func.count(func.distinct(SignalContributionDB.event_id)),
        )
        .group_by(SignalContributionDB.category_id)
        .all()
    )

    impact_by_category = {
        category_id: {
            "update_count": update_count,
            "total_delta": round(float(total_delta), 2),
            "avg_delta": round(float(avg_delta), 2),
            "event_count": event_count,
        }
        for (
            category_id,
            update_count,
            total_delta,
            avg_delta,
            event_count,
        ) in impact_rows
    }

    parent_count_rows = (
        db.query(
            CategoryRelationDB.child_category_id,
            func.count(CategoryRelationDB.id),
        )
        .group_by(CategoryRelationDB.child_category_id)
        .all()
    )

    parent_count_by_category = {
        category_id: count
        for category_id, count in parent_count_rows
    }

    child_count_rows = (
        db.query(
            CategoryRelationDB.parent_category_id,
            func.count(CategoryRelationDB.id),
        )
        .group_by(CategoryRelationDB.parent_category_id)
        .all()
    )

    child_count_by_category = {
        category_id: count
        for category_id, count in child_count_rows
    }

    # ---------------------------------------------------------
    # Content-category map for co-occurrence and combination impact
    # ---------------------------------------------------------

    assignments = db.query(ContentCategoryAssignmentDB).all()

    content_to_categories = {}

    for assignment in assignments:
        content_to_categories.setdefault(
            assignment.content_id,
            set(),
        ).add(assignment.category_id)

    # ---------------------------------------------------------
    # Edge metrics: category relations
    # ---------------------------------------------------------

    edge_map = {}

    relations = db.query(CategoryRelationDB).all()

    for relation in relations:
        key = tuple(
            sorted(
                [
                    relation.parent_category_id,
                    relation.child_category_id,
                ]
            )
        )

        edge_map[key] = {
            "source": relation.parent_category_id,
            "target": relation.child_category_id,
            "type": "relation",
            "cooccurrence_count": 0,
            "event_count": 0,
            "total_delta": 0,
            "strength": 1,
        }

    # ---------------------------------------------------------
    # Edge metrics: category co-occurrence on content
    # ---------------------------------------------------------

    for category_ids in content_to_categories.values():
        for source_id, target_id in combinations(
            sorted(category_ids),
            2,
        ):
            key = (source_id, target_id)

            if key not in edge_map:
                edge_map[key] = {
                    "source": source_id,
                    "target": target_id,
                    "type": "cooccurrence",
                    "cooccurrence_count": 0,
                    "event_count": 0,
                    "total_delta": 0,
                    "strength": 0,
                }

            edge_map[key]["cooccurrence_count"] += 1
            edge_map[key]["strength"] += 1

    # ---------------------------------------------------------
    # Edge impact: preference updates by content/category pair
    # ---------------------------------------------------------

    update_events = (
        db.query(
            SignalContributionDB,
            EngagementEventDB,
        )
        .join(
            EngagementEventDB,
            SignalContributionDB.event_id == EngagementEventDB.id,
        )
        .all()
    )

    edge_event_ids = {
        key: set()
        for key in edge_map.keys()
    }

    for update, event in update_events:
        event_data = event.event_data or {}
        content_id = event_data.get("content_record_id")

        if not content_id:
            continue

        category_ids = content_to_categories.get(content_id, set())

        for source_id, target_id in combinations(
            sorted(category_ids),
            2,
        ):
            key = (source_id, target_id)

            if key not in edge_map:
                continue

            edge_map[key]["total_delta"] += float(update.base_weight)
            edge_event_ids[key].add(event.id)

    for key, event_ids in edge_event_ids.items():
        edge_map[key]["event_count"] = len(event_ids)
        edge_map[key]["total_delta"] = round(
            edge_map[key]["total_delta"],
            2,
        )

    # ---------------------------------------------------------
    # Layout
    # ---------------------------------------------------------

    width = 900
    height = 620
    center_x = width / 2
    center_y = height / 2

    main_categories = [
        category
        for category in categories
        if category.type == "main"
    ]

    sub_categories = [
        category
        for category in categories
        if category.type != "main"
    ]

    positions = {}

    for index, category in enumerate(main_categories):
        angle = 2 * math.pi * index / max(len(main_categories), 1)

        positions[category.id] = {
            "x": center_x + math.cos(angle) * 150,
            "y": center_y + math.sin(angle) * 150,
        }

    for index, category in enumerate(sub_categories):
        angle = 2 * math.pi * index / max(len(sub_categories), 1)

        positions[category.id] = {
            "x": center_x + math.cos(angle) * 260,
            "y": center_y + math.sin(angle) * 230,
        }

    nodes = []

    for category in categories:
        impact = impact_by_category.get(
            category.id,
            {
                "update_count": 0,
                "total_delta": 0,
                "avg_delta": 0,
                "event_count": 0,
            },
        )

        selected_count = selections_by_category.get(category.id, 0)
        total_delta = impact["total_delta"]
        avg_delta = impact["avg_delta"]

        radius = 16 + min(
            34,
            (selected_count * 4) + abs(total_delta) * 0.4,
        )

        if avg_delta > 0:
            color = "#198754"
        elif avg_delta < 0:
            color = "#dc3545"
        else:
            color = "#6c757d"

        nodes.append(
            {
                "id": category.id,
                "name": category.name,
                "type": category.type,
                "x": round(positions[category.id]["x"], 2),
                "y": round(positions[category.id]["y"], 2),
                "radius": round(radius, 2),
                "color": color,
                "selected_count": selected_count,
                "content_count": content_count_by_category.get(category.id, 0),
                "update_count": impact["update_count"],
                "event_count": impact["event_count"],
                "total_delta": total_delta,
                "avg_delta": avg_delta,
                "parent_count": parent_count_by_category.get(category.id, 0),
                "child_count": child_count_by_category.get(category.id, 0),
            }
        )

    node_lookup = {
        node["id"]: node
        for node in nodes
    }

    edges = []

    for edge in edge_map.values():
        source = node_lookup.get(edge["source"])
        target = node_lookup.get(edge["target"])

        if not source or not target:
            continue

        thickness = 1 + min(
            8,
            edge["strength"] + abs(edge["total_delta"]) * 0.2,
        )

        edges.append(
            {
                "source": edge["source"],
                "target": edge["target"],
                "source_name": category_lookup[edge["source"]].name,
                "target_name": category_lookup[edge["target"]].name,
                "x1": source["x"],
                "y1": source["y"],
                "x2": target["x"],
                "y2": target["y"],
                "type": edge["type"],
                "cooccurrence_count": edge["cooccurrence_count"],
                "event_count": edge["event_count"],
                "total_delta": edge["total_delta"],
                "strength": edge["strength"],
                "thickness": round(thickness, 2),
            }
        )

    top_nodes = sorted(
        nodes,
        key=lambda item: item["total_delta"],
        reverse=True,
    )

    top_edges = sorted(
        edges,
        key=lambda item: (
            item["total_delta"],
            item["cooccurrence_count"],
        ),
        reverse=True,
    )

    return templates.TemplateResponse(
        request,
        "graph.html",
        {
            "title": "Category Graph",
            "width": width,
            "height": height,
            "nodes": nodes,
            "edges": edges,
            "top_nodes": top_nodes[:10],
            "top_edges": top_edges[:10],
            "total_categories": len(nodes),
            "total_edges": len(edges),
            "total_selections": sum(
                node["selected_count"]
                for node in nodes
            ),
            "total_events": sum(
                node["event_count"]
                for node in nodes
            ),
            "total_delta": round(
                sum(
                    node["total_delta"]
                    for node in nodes
                ),
                2,
            ),
        },
    )

# ── Audience Groups ──────────────────────────────────────────────────────────

@router.get("/ui/audience-groups")
def audience_groups_list(request: Request, error: str | None = None, db: Session = Depends(get_db)):
    groups = audience_service.list_groups(db, brand_id=working_brand_id(request, db))
    rows = []
    for g in groups:
        # "Recipients" = the live resolved audience (rule blocks ∪ pins − excludes,
        # consent-gated), not just manual pins — a suggested/rule-only group has
        # 0 pins but real recipients. "pinned" is kept as a secondary detail.
        pinned = db.query(AudienceGroupMemberDB).filter(AudienceGroupMemberDB.group_id == g.id).count()
        rows.append({"id": g.id, "name": g.name, "description": g.description,
                     "recipient_count": len(audience_service.resolve_audience(db, g.id)),
                     "pinned_count": pinned, "created_at": g.created_at})
    campaigns = (
        db.query(CampaignDB)
        .filter(CampaignDB.brand_id == working_brand_id(request, db))
        .order_by(CampaignDB.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(request, "audience_groups.html",
                                      {"title": "Audience Groups", "groups": rows,
                                       "campaigns": campaigns, "error": error})


@router.post("/ui/audience-groups")
def audience_groups_create(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    desc = description.strip() or None
    try:
        group = audience_service.create_group(
            db, name.strip(), brand_id=working_brand_id(request, db), description=desc,
        )
    except ValueError as error:
        return RedirectResponse(f"/ui/audience-groups?error={quote(str(error))}", status_code=303)
    return RedirectResponse(f"/ui/audience-groups/{group.id}", status_code=303)


@router.get("/ui/audience-groups/{group_id}")
def audience_group_detail(group_id: int, request: Request, error: str | None = None, db: Session = Depends(get_db)):
    group = audience_service.get_group(db, group_id)
    if group and group.brand_id != working_brand_id(request, db):
        group = None  # another brand's group: indistinguishable from absent
    if not group:
        return RedirectResponse("/ui/audience-groups", status_code=303)

    member_ids = audience_service.get_member_recipient_ids(db, group_id)
    raw_members = audience_service.list_members(db, group_id)

    members = []
    member_addresses = resolve_emails(db, [m.recipient_id for m in raw_members])
    for m in raw_members:
        r = db.query(RecipientDB).filter(RecipientDB.id == m.recipient_id).first()
        if r:
            members.append({
                "recipient_id": r.id,
                "external_id": r.external_id,
                "email": member_addresses.get(r.id, ""),
                "status": r.status,
                "added_at": m.added_at,
            })

    # Sorted by resolved address rather than in SQL: the address is a row on
    # another table now (ADR-163 point 2), and this list is short enough that
    # ordering it in Python is cheaper than joining for a display concern.
    all_recipients = db.query(RecipientDB).order_by(RecipientDB.id.asc()).all()
    all_addresses = resolve_emails(db, [r.id for r in all_recipients])
    all_recipients.sort(key=lambda r: all_addresses.get(r.id, ""))
    non_members = [
        {"id": r.id, "email": all_addresses.get(r.id, ""), "external_id": r.external_id,
         "language": r.language, "status": r.status}
        for r in all_recipients if r.id not in member_ids
    ]

    languages = sorted({r.language for r in all_recipients if r.language})
    statuses = sorted({r.status for r in all_recipients if r.status})
    categories = db.query(CategoryDB).order_by(CategoryDB.name.asc()).all()
    category_names = {c.id: c.name for c in categories}

    # Rule blocks (live) shown on top, each with its own count so a manager sees
    # the impact of every include/exclude before sending.
    blocks = []
    for b in audience_service.list_blocks(db, group_id):
        crit = b.criteria or {}
        parts = []
        if crit.get("category_id"):
            parts.append(f"interested in {category_names.get(crit['category_id'], 'category ' + str(crit['category_id']))}")
        if crit.get("min_score") not in (None, ""):
            parts.append(f"signal ≥ {crit['min_score']}")
        if crit.get("language"):
            parts.append(f"language {crit['language']}")
        if crit.get("status"):
            parts.append(f"status {crit['status']}")
        blocks.append({
            "id": b.id,
            "kind": b.kind,
            "label": b.label,
            "source": b.source,
            "criteria": crit,
            "summary": ", ".join(parts) if parts else "everyone (no criteria)",
            "count": audience_service.count_for_criteria(db, crit, group.brand_id),
        })

    resolved = audience_service.resolve_audience(db, group_id)
    resolved_addresses = resolve_emails(db, [r.id for r in resolved[:20]])

    # Source campaign (if this group was seeded by "Suggest audience") — enables
    # the Recalculate button and a link back to the campaign.
    source_campaign = None
    if group.source_campaign_id:
        source_campaign = db.query(CampaignDB).filter(CampaignDB.id == group.source_campaign_id).first()

    return templates.TemplateResponse(request, "audience_group_detail.html", {
        "title": f"Group: {group.name}",
        "group": group,
        "members": members,
        "non_members": non_members,
        "languages": languages,
        "statuses": statuses,
        "categories": categories,
        "blocks": blocks,
        "resolved_count": len(resolved),
        "resolved_preview": [
            {"id": r.id, "email": resolved_addresses.get(r.id, ""),
             "external_id": r.external_id, "language": r.language, "status": r.status}
            for r in resolved[:20]
        ],
        "source_campaign": source_campaign,
        "error": error,
    })


@router.post("/ui/audience-groups/{group_id}/edit")
def audience_group_edit(
    group_id: int,
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    desc = description.strip() or None
    try:
        audience_service.update_group(db, group_id, name.strip(), desc)
    except ValueError as error:
        return RedirectResponse(f"/ui/audience-groups/{group_id}?error={quote(str(error))}", status_code=303)
    return RedirectResponse(f"/ui/audience-groups/{group_id}", status_code=303)


@router.post("/ui/audience-groups/{group_id}/delete")
def audience_group_delete(group_id: int, db: Session = Depends(get_db)):
    audience_service.delete_group(db, group_id)
    return RedirectResponse("/ui/audience-groups", status_code=303)


@router.post("/ui/audience-groups/{group_id}/members")
def audience_group_add_member(
    group_id: int,
    recipient_id: int = Form(...),
    db: Session = Depends(get_db),
):
    audience_service.add_member(db, group_id, recipient_id)
    return RedirectResponse(f"/ui/audience-groups/{group_id}", status_code=303)


@router.post("/ui/audience-groups/{group_id}/members/{recipient_id}/remove")
def audience_group_remove_member(group_id: int, recipient_id: int, db: Session = Depends(get_db)):
    audience_service.remove_member(db, group_id, recipient_id)
    return RedirectResponse(f"/ui/audience-groups/{group_id}", status_code=303)


@router.get("/ui/audience-groups/{group_id}/criteria-preview")
def audience_group_criteria_preview(
    group_id: int,
    request: Request,
    language: str = "",
    status: str = "",
    preference_category_id: str = "",
    min_preference_score: str = "",
    db: Session = Depends(get_db),
):
    from fastapi.responses import JSONResponse
    member_ids = audience_service.get_member_recipient_ids(db, group_id)
    cat_id = int(preference_category_id) if preference_category_id else None
    min_score = float(min_preference_score) if min_preference_score else None
    matches = audience_service.find_by_criteria(
        db,
        # The group's brand, not the viewer's: a preview must count the same
        # people the resolve will, or it advertises reach the send refuses.
        audience_service.get_group(db, group_id).brand_id,
        language=language or None,
        status=status or None,
        preference_category_id=cat_id,
        min_preference_score=min_score,
        exclude_ids=member_ids,
    )
    preview = matches[:20]
    preview_addresses = resolve_emails(db, [r.id for r in preview])
    return JSONResponse({"count": len(matches), "recipients": [
        {"id": r.id, "email": preview_addresses.get(r.id, ""), "external_id": r.external_id,
         "language": r.language, "status": r.status}
        for r in preview
    ]})


@router.post("/ui/audience-groups/{group_id}/bulk-add")
def audience_group_bulk_add(
    group_id: int,
    language: str = Form(""),
    status: str = Form(""),
    preference_category_id: str = Form(""),
    min_preference_score: str = Form(""),
    db: Session = Depends(get_db),
):
    member_ids = audience_service.get_member_recipient_ids(db, group_id)
    cat_id = int(preference_category_id) if preference_category_id else None
    min_score = float(min_preference_score) if min_preference_score else None
    matches = audience_service.find_by_criteria(
        db,
        # The group's brand, not the viewer's: a preview must count the same
        # people the resolve will, or it advertises reach the send refuses.
        audience_service.get_group(db, group_id).brand_id,
        language=language or None,
        status=status or None,
        preference_category_id=cat_id,
        min_preference_score=min_score,
        exclude_ids=member_ids,
    )
    audience_service.bulk_add_members(db, group_id, [r.id for r in matches])
    return RedirectResponse(f"/ui/audience-groups/{group_id}", status_code=303)


# ── Audience rule blocks (live include/exclude criteria) ──────────────────

def _block_criteria_from_form(category_id: str, min_score: str, language: str, status: str) -> dict:
    criteria: dict = {}
    if category_id.strip():
        criteria["category_id"] = int(category_id)
    if min_score.strip():
        criteria["min_score"] = float(min_score)
    if language.strip():
        criteria["language"] = language.strip()
    if status.strip():
        criteria["status"] = status.strip()
    return criteria


@router.post("/ui/audience-groups/{group_id}/blocks")
def audience_block_add(
    group_id: int,
    kind: str = Form("include"),
    label: str = Form(""),
    category_id: str = Form(""),
    min_score: str = Form(""),
    language: str = Form(""),
    status: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        audience_service.add_block(
            db,
            group_id=group_id,
            kind=kind,
            criteria=_block_criteria_from_form(category_id, min_score, language, status),
            label=label.strip() or None,
            source="manual",
        )
    except ValueError as error:
        return RedirectResponse(f"/ui/audience-groups/{group_id}?error={quote(str(error))}", status_code=303)
    return RedirectResponse(f"/ui/audience-groups/{group_id}", status_code=303)


@router.post("/ui/audience-groups/{group_id}/blocks/{block_id}/edit")
def audience_block_edit(
    group_id: int,
    block_id: int,
    kind: str = Form("include"),
    label: str = Form(""),
    category_id: str = Form(""),
    min_score: str = Form(""),
    language: str = Form(""),
    status: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        audience_service.update_block(
            db,
            block_id=block_id,
            kind=kind,
            criteria=_block_criteria_from_form(category_id, min_score, language, status),
            label=label.strip() or None,
        )
    except ValueError as error:
        return RedirectResponse(f"/ui/audience-groups/{group_id}?error={quote(str(error))}", status_code=303)
    return RedirectResponse(f"/ui/audience-groups/{group_id}", status_code=303)


@router.post("/ui/audience-groups/{group_id}/blocks/{block_id}/delete")
def audience_block_delete(group_id: int, block_id: int, db: Session = Depends(get_db)):
    audience_service.delete_block(db, block_id)
    return RedirectResponse(f"/ui/audience-groups/{group_id}", status_code=303)


@router.post("/ui/campaigns/{campaign_id}/suggest-audience")
def campaign_suggest_audience(campaign_id: int, db: Session = Depends(get_db)):
    """Use case 1: turn the campaign's content categories into a live, editable
    suggested audience (include blocks, one per top category), then drop the
    manager on the group so they can tighten/extend/delete it."""
    campaign = db.query(CampaignDB).filter(CampaignDB.id == campaign_id).first()
    if campaign is None:
        return RedirectResponse("/ui/campaigns", status_code=303)
    try:
        group = audience_service.create_suggested_group_for_campaign(db, campaign_id, campaign.name)
    except ValueError as error:
        return RedirectResponse(f"/ui/campaigns/{campaign_id}?error={quote(str(error))}", status_code=303)
    return RedirectResponse(f"/ui/audience-groups/{group.id}", status_code=303)


@router.post("/ui/audience-groups/{group_id}/recalculate")
def audience_group_recalculate(group_id: int, db: Session = Depends(get_db)):
    """Re-derive the suggested blocks from the source campaign's current content
    (after its slots/content changed). Manual blocks and pins are preserved."""
    result = audience_service.recalculate_suggested_blocks(db, group_id)
    if result is None:
        return RedirectResponse(
            f"/ui/audience-groups/{group_id}?error={quote('This group is not linked to a campaign, so there is nothing to recalculate.')}",
            status_code=303,
        )
    return RedirectResponse(f"/ui/audience-groups/{group_id}", status_code=303)


# --- integrations: machine callers and their keys (ADR-166) -----------------
#
# These live in the frontend router rather than `auth_router` so they inherit
# both `enforce_csrf` and `enforce_policy` from the one place those are wired.
# `auth_router` carries explicit permission guards and no CSRF, which is a gap
# in its own right; this feature does not extend it.
#
# Gated by `integrations.manage` through the policy table's `/ui/integrations`
# prefix. ADR-166 point 4 makes that its own permission rather than a fold into
# `credentials.manage` — that key is for credentials the platform HOLDS, and
# these are credentials it ISSUES, a line ADR-152 drew itself.

# **The GET needs its own guard**, and this is the trap the policy table sets
# for a read-only admin surface: `required_permission` answers `view` for every
# GET, so the `/ui/integrations` entry covers the writes and leaves the page
# itself readable by anyone who can sign in. The users and roles screens carry
# explicit guards for exactly this reason; the entry in the table made this one
# *look* covered, which is worse than an obvious omission. Caught by a test
# asserting a Manager is refused, not by reading the table.

def _integration_rows(db: Session):
    from app.auth.db_models import (
        IntegrationCredentialDB, IntegrationDB, IntegrationGrantDB,
    )

    rows = []
    for integration in db.query(IntegrationDB).order_by(IntegrationDB.id).all():
        credentials = db.query(IntegrationCredentialDB).filter(
            IntegrationCredentialDB.integration_id == integration.id
        ).order_by(IntegrationCredentialDB.id).all()
        grants = db.query(IntegrationGrantDB).filter(
            IntegrationGrantDB.integration_id == integration.id
        ).order_by(IntegrationGrantDB.permission).all()
        rows.append({
            "integration": integration,
            "credentials": credentials,
            "grants": grants,
            "live_keys": sum(1 for c in credentials if c.revoked_at is None),
        })
    return rows


def _integrations_context(request: Request, db: Session, **extra):
    from app.auth.permissions import ALL_PERMISSIONS

    context = {
        "rows": _integration_rows(db),
        "all_permissions": sorted(ALL_PERMISSIONS.items()),
        "brands": list_brands(db),
        "issued": None,
        "issued_for": None,
    }
    context.update(extra)
    return context


@router.get("/ui/integrations")
def integrations_page(
    request: Request,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(INTEGRATIONS_MANAGE)),
):
    """The review surface ADR-166's Notes called "the obvious shape of an
    answer" to the credential-outlives-its-issuer gap.

    It is not a mitigation and the ADR is careful not to claim it is: a
    credential still survives the deactivation of whoever created it. What this
    gives is the thing ADR-151 §5 relies on for people — somewhere to *look*.
    Each integration, what it may do, how many live keys it has, when each was
    last used, and whether it may send without approval.
    """
    return templates.TemplateResponse(
        request, "integrations.html", _integrations_context(request, db),
    )


@router.post("/ui/integrations")
def integration_create(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    from app.auth import integrations as ints

    user = user_for_token(db, request.cookies.get(SESSION_COOKIE))
    ints.create_integration(
        db, name=name, description=description,
        created_by_user_id=user.id if user else None,
    )
    return RedirectResponse(url="/ui/integrations", status_code=303)


@router.post("/ui/integrations/{integration_id}/keys")
def integration_issue_key(
    request: Request,
    integration_id: int,
    label: str = Form(""),
    db: Session = Depends(get_db),
):
    """Issue a key and show the secret **once**, in this response.

    Deliberately not a redirect. ADR-166 point 3 keeps the secret out of "a URL,
    a query string or a path segment", because a referrer header, an access log
    or an intermediary will capture any of them — and the redirect that would
    otherwise be the idiomatic answer here is exactly how a secret ends up in a
    query string. Rendering it directly means it exists in one response body and
    nowhere else.
    """
    from app.auth import integrations as ints

    issued = ints.issue_credential(db, integration_id, label=label)
    extra = {}
    if issued is not None:
        credential, secret = issued
        extra = {
            "issued": f"{credential.key_id}.{secret}",
            "issued_for": integration_id,
        }
    return templates.TemplateResponse(
        request, "integrations.html", _integrations_context(request, db, **extra),
    )


@router.post("/ui/integrations/{integration_id}/keys/{credential_id}/revoke")
def integration_revoke_key(
    integration_id: int, credential_id: int, db: Session = Depends(get_db),
):
    from app.auth import integrations as ints

    ints.revoke_credential(db, credential_id)
    return RedirectResponse(url="/ui/integrations", status_code=303)


@router.post("/ui/integrations/{integration_id}/grants")
def integration_grant(
    integration_id: int,
    permission: str = Form(...),
    brand_id: int = Form(...),
    db: Session = Depends(get_db),
):
    from app.auth import integrations as ints

    ints.grant(db, integration_id, permission, brand_id)
    return RedirectResponse(url="/ui/integrations", status_code=303)


@router.post("/ui/integrations/{integration_id}/grants/remove")
def integration_revoke_grant(
    integration_id: int,
    permission: str = Form(...),
    brand_id: int = Form(...),
    db: Session = Depends(get_db),
):
    from app.auth import integrations as ints

    ints.revoke_grant(db, integration_id, permission, brand_id)
    return RedirectResponse(url="/ui/integrations", status_code=303)


@router.post("/ui/integrations/{integration_id}/unattended")
def integration_set_unattended(
    integration_id: int, allowed: str = Form(""), db: Session = Depends(get_db),
):
    """ADR-166 point 5: switching this off is the control, so it is logged.

    "The integration where someone switched it off is by construction the one
    with the least oversight. Logging the change is the whole control."
    """
    from app.auth import integrations as ints

    ints.set_unattended_sending(db, integration_id, allowed == "1")
    return RedirectResponse(url="/ui/integrations", status_code=303)


@router.post("/ui/integrations/{integration_id}/deactivate")
def integration_deactivate(integration_id: int, db: Session = Depends(get_db)):
    from app.auth import integrations as ints

    ints.deactivate_integration(db, integration_id)
    return RedirectResponse(url="/ui/integrations", status_code=303)


# --- the approval inbox (ADR-142 §4) ---------------------------------------
#
# **Who may see it, and who may act.** Seeing that a send is waiting is
# operational visibility, not a secret, so the list needs only `view` — which is
# how the policy table's `/ui/approvals` entry reads. Acting is a different
# question, and it is answered **per row**, against the permission the action
# itself declares: `approve_permission`. The table matches on a route template
# and cannot express "the permission depends on which row you clicked", so the
# real gate lives in the route and has its own test.
#
# That is a weaker-looking arrangement than a table entry and a stronger one in
# practice, because two actions in one inbox can require different permissions —
# a machine send needs `sends.execute`, applying an AI suggestion will need
# `campaigns.manage`. A single route-level permission would have to be the union
# of every action's, which is the widest grant rather than the right one.

def _approval_rows(request: Request, db: Session, status: str):
    """Inbox rows, each paired with its action declaration.

    An action whose module has been removed still renders — its request happened
    and its history is real — but it cannot be approved, because
    `get_action_module` returns nothing and `approve()` refuses. A row that
    disappears because somebody deleted a file would be worse than one that
    reads "no longer available".
    """
    from app.approvals import service as approvals
    from app.approvals.actions.registry import get_action

    rows = []
    for row in approvals.list_for_brand(db, working_brand_id(request, db), status):
        meta = get_action(row.action_key)
        rows.append({
            "row": row,
            "meta": meta,
            "status": approvals.effective_status(row),
            "can_decide": bool(meta) and _may_decide(request, db, meta, row),
        })
    return rows


def _may_decide(request: Request, db: Session, meta, row) -> bool:
    """Whether this user may approve or reject this particular request.

    Brand-scoped permissions are checked against the request's own brand rather
    than the working one. They are the same today — the inbox is filtered by
    working brand — but reading the row's brand is what stays correct if the
    inbox ever shows more than one.
    """
    user = user_for_token(db, request.cookies.get(SESSION_COOKIE))
    if user is None:
        # Access control switched off. `enforce_policy` already let the request
        # through, so refusing here would break a deployment that has not turned
        # enforcement on — and there is no principal to check anything against.
        from app.auth.dependencies import auth_enforced

        return not auth_enforced(db)
    from app.auth.permissions import is_brand_scoped

    if is_brand_scoped(meta.approve_permission):
        return has_permission(
            db, user, meta.approve_permission, brand_id=row.brand_id,
        )
    return has_permission(db, user, meta.approve_permission)


@router.get("/ui/approvals")
def approvals_list(
    request: Request,
    status: str = "pending",
    notice: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    """One screen, filtered — pending by default.

    Not two screens. ADR-142 §4 requires that "approved, rejected *and* expired
    requests stay inspectable", so the history is mandatory rather than a later
    nicety, and a filter is the cheapest honest way to carry it.
    """
    if status not in ("pending", "decided", "all"):
        status = "pending"
    from app.approvals import service as approvals

    return templates.TemplateResponse(request, "approvals.html", {
        "rows": _approval_rows(request, db, status),
        "status": status,
        "due_count": approvals.due_count(db),
        "notice": notice,
        "error": error,
    })


@router.post("/ui/approvals/process-expired")
def approvals_process_expired(db: Session = Depends(get_db)):
    """Retire every request past its deadline (ADR-142 §4).

    **Bookkeeping, not enforcement.** `approve()` already refuses an expired
    request by reading `expires_at`, so nothing here is load-bearing: a
    deployment where this button is never pressed is safe, its inbox merely
    shows a status column lagging behind the clock. Pressing it makes the
    column agree, and writes the `approval.expired` entry that ADR-142 §4's
    "approved, rejected *and* expired requests stay inspectable" asks for.

    A manual button in the POC, exactly like "Run due scheduled sends" beside
    it — a real deployment points cron or its orchestrator at this same
    operation on an interval. The architecture exposes the seam rather than
    baking in a scheduler (ADR-094), which is also why there is no background
    thread: this codebase has no process model for one.

    **Not brand-scoped**, and neither is the sweep it triggers. A deadline is a
    time rather than a brand, the outcome is identical in every brand already,
    and the operation is idempotent — it can only retire things that are
    already dead.

    Needs only `view`, by the `/ui/approvals` entry in the policy table. Same
    reasoning as `("/ui/brand", VIEW)`: refusing to let a Viewer press a button
    that changes nothing they could not already see would be theatre.
    """
    from app.approvals import service as approvals

    expired = approvals.expire_due_pending_actions(db)
    message = (
        f"Retired {len(expired)} request(s) whose deadline had passed."
        if expired else "Nothing had expired."
    )
    return RedirectResponse(
        url=f"/ui/approvals?status=all&notice={quote(message, safe='')}",
        status_code=303,
    )


@router.get("/ui/approvals/{pending_id}")
def approval_detail(
    request: Request, pending_id: int, db: Session = Depends(get_db),
):
    """The review screen — and the one place the frozen/live split is visible.

    It shows `describe()` run **now**, beside the `summary` frozen when the
    request was made, beside the audit trail. A reviewer needs current reality
    to decide; a reader of history needs what was said at the time; and the
    difference between them is often the reason to say no.
    """
    from app.approvals import service as approvals
    from app.approvals.actions.registry import get_action, get_action_module
    from app.approvals.db_models import PendingActionDB
    from app.audit.service import events_for_subject

    row = db.query(PendingActionDB).filter(
        PendingActionDB.id == pending_id,
        # Brand isolation, the same rule as every other detail page: a request
        # belonging to another brand does not exist from here.
        PendingActionDB.brand_id == working_brand_id(request, db),
    ).first()
    if row is None:
        return templates.TemplateResponse(
            request, "approvals.html",
            {"rows": [], "status": "pending",
             "error": f"Request {pending_id} does not exist in this brand."},
            status_code=404,
        )

    meta = get_action(row.action_key)
    module = get_action_module(row.action_key)
    description = None
    describe_error = None
    if module is not None and hasattr(module, "describe"):
        try:
            description = module.describe(db, row.payload or {})
        except Exception as failure:
            # A description that raises must not hide the request. The reviewer
            # still needs to see that something is waiting and still needs to be
            # able to reject it.
            describe_error = str(failure)
            logger.warning(
                "approval %s: describe() failed", pending_id, exc_info=True,
            )

    return templates.TemplateResponse(request, "approval_detail.html", {
        "row": row,
        "meta": meta,
        "status": approvals.effective_status(row),
        "description": description,
        "describe_error": describe_error,
        "can_decide": bool(meta) and _may_decide(request, db, meta, row),
        "history": events_for_subject(db, approvals.SUBJECT, row.id),
    })


def _decide(request: Request, db: Session, pending_id: int):
    """Shared preamble: find the row in this brand and check the row's own rule."""
    from app.approvals.actions.registry import get_action
    from app.approvals.db_models import PendingActionDB

    row = db.query(PendingActionDB).filter(
        PendingActionDB.id == pending_id,
        PendingActionDB.brand_id == working_brand_id(request, db),
    ).first()
    if row is None:
        return None, None, "That request does not exist in this brand."
    meta = get_action(row.action_key)
    if meta is None:
        return row, None, (
            f"'{row.action_key}' is no longer a registered action, so it cannot "
            "be approved. Reject it, or restore the action module."
        )
    if not _may_decide(request, db, meta, row):
        return row, meta, (
            f"You need the '{meta.approve_permission}' permission to decide this."
        )
    return row, meta, None


@router.post("/ui/approvals/{pending_id}/approve")
def approval_approve(
    request: Request,
    pending_id: int,
    reason: str = Form(""),
    choice_index: int | None = Form(None),
    db: Session = Depends(get_db),
):
    from app.approvals import service as approvals
    from app.audit.service import ACTOR_USER

    row, meta, refusal = _decide(request, db, pending_id)
    if refusal:
        return RedirectResponse(
            url=f"/ui/approvals?error={quote(refusal, safe='')}", status_code=303,
        )

    user = user_for_token(db, request.cookies.get(SESSION_COOKIE))
    choice = None
    if choice_index is not None:
        # ADR-141 §4's "pick-one for options": N options are ONE request, and
        # the index says which one the human chose.
        choice = {"index": choice_index}
    result = approvals.approve(
        db, pending_id,
        approver_type=ACTOR_USER, approver_id=user.id if user else None,
        choice=choice, reason=reason.strip() or None,
    )
    key = "notice" if result.ok else "error"
    message = result.message or ("Approved and executed." if result.ok else "Refused.")
    return RedirectResponse(
        url=f"/ui/approvals?{key}={quote(message, safe='')}", status_code=303,
    )


@router.post("/ui/approvals/{pending_id}/reject")
def approval_reject(
    request: Request,
    pending_id: int,
    reason: str = Form(""),
    db: Session = Depends(get_db),
):
    from app.approvals import service as approvals
    from app.audit.service import ACTOR_USER

    row, meta, refusal = _decide(request, db, pending_id)
    if refusal:
        return RedirectResponse(
            url=f"/ui/approvals?error={quote(refusal, safe='')}", status_code=303,
        )

    user = user_for_token(db, request.cookies.get(SESSION_COOKIE))
    approvals.reject(
        db, pending_id,
        approver_type=ACTOR_USER, approver_id=user.id if user else None,
        reason=reason.strip() or None,
    )
    return RedirectResponse(
        url="/ui/approvals?notice=" + quote("Rejected.", safe=""), status_code=303,
    )
