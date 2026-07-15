from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from itertools import combinations
from urllib.parse import quote
import math

from app.database import get_db

import json

from app.content.db_models import ContentRecordDB, ContentVersionDB, CategoryDB, ContentCategoryAssignmentDB, CategoryRelationDB
from app.content.service import create_content, update_content_record, assign_category_to_content, create_content_version, delete_category_assignment, delete_category_relation
from app.content.service import create_category, create_category_relation
from app.content.service import delete_content_record, delete_category, ContentRecordHasHistoryError, HasRelationsError
from app.campaigns.db_models import CampaignDB, DecisionResolutionDB, VariantDB, ModuleInstanceDB, DecisionSlotDB
from app.campaigns.service import create_campaign, create_variant_for_campaign, create_module_for_variant, create_decision_slot_for_variant, update_decision_slot, update_variant, delete_module, move_module
from app.rendering.service import UnpublishedContentError
from app.snapshots.service import create_snapshot_for_variant
from app.delivery.service import create_send_instance, send_send_instance
from app.recipients.db_models import RecipientDB, RecipientPreferenceDB, PreferenceUpdateLogDB
from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB
from app.audience import service as audience_service
from app.decision.strategies.registry import list_strategies
from app.email_modules.registry import list_manifests, get_manifest
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

templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
):
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "title": "Architecture Dashboard",
            "content_count": db.query(ContentRecordDB).count(),
            "campaign_count": db.query(CampaignDB).count(),
            "recipient_count": db.query(RecipientDB).count(),
            "snapshot_count": db.query(SnapshotDB).count(),
            "delivery_count": db.query(DeliveryExecutionDB).count(),
            "event_count": db.query(EngagementEventDB).count(),
        },
    )


@router.get("/ui/recipients")
def recipients_list(
    request: Request,
    db: Session = Depends(get_db),
):
    recipients = (
        db.query(RecipientDB)
        .order_by(RecipientDB.id.asc())
        .all()
    )

    return templates.TemplateResponse(
        request,
        "recipients.html",
        {
            "title": "Recipients",
            "recipients": recipients,
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

    preferences = (
        db.query(
            RecipientPreferenceDB,
            CategoryDB.name,
        )
        .join(
            CategoryDB,
            RecipientPreferenceDB.category_id == CategoryDB.id,
        )
        .filter(
            RecipientPreferenceDB.recipient_id == recipient_id
        )
        .all()
    )

    preference_rows = [
        {
            "category_name": category_name,
            "score": pref.score,
            "source": pref.source,
        }
        for pref, category_name in preferences
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
                    PreferenceUpdateLogDB,
                    CategoryDB.name,
                )
                .join(
                    CategoryDB,
                    PreferenceUpdateLogDB.category_id == CategoryDB.id,
                )
                .filter(
                    PreferenceUpdateLogDB.event_id == event.id
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
                            "previous_score": update.previous_score,
                            "delta": update.delta,
                            "new_score": update.new_score,
                            "reason": update.reason,
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
            "recipient": recipient,
            "preferences": preference_rows,
            "decisions": decision_rows,
            "deliveries": delivery_rows,
        },
    )


@router.get("/ui/campaigns")
def campaigns_list(
    request: Request,
    db: Session = Depends(get_db),
):
    campaigns = (
        db.query(CampaignDB)
        .order_by(CampaignDB.created_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        request,
        "campaigns.html",
        {
            "title": "Campaigns",
            "campaigns": campaigns,
        },
    )


@router.get("/ui/campaigns/{campaign_id}")
def campaign_detail(
    campaign_id: int,
    request: Request,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    campaign = (
        db.query(CampaignDB)
        .filter(CampaignDB.id == campaign_id)
        .first()
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
            manifest = get_manifest(m.module_type)
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
            modules.append({
                "id": m.id,
                "position": m.position,
                "module_type": m.module_type,
                "content_record_id": m.content_record_id,
                "decision_slot_id": m.decision_slot_id,
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

        variant_rows.append(
            {
                "id": variant.id,
                "name": variant.name,
                "subject": variant.subject,
                "preheader": variant.preheader,
                "modules": modules,
                "override_module_choices": override_module_choices,
                "decision_slots": decision_slot_rows,
                "snapshots": snapshots,
            }
        )

    content_records = db.query(ContentRecordDB).order_by(ContentRecordDB.title.asc()).all()
    module_templates = list_manifests()
    strategies = sorted(s.name for s in list_strategies())

    return templates.TemplateResponse(
        request,
        "campaign_detail.html",
        {
            "title": f"Campaign {campaign_id}",
            "campaign": campaign,
            "variants": variant_rows,
            "content_records": content_records,
            "module_templates": module_templates,
            "strategies": strategies,
            "error": error,
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
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    campaign = create_campaign(db, name=name)
    return RedirectResponse(url=f"/ui/campaigns/{campaign.id}", status_code=303)


@router.post("/ui/campaigns/{campaign_id}/variants")
def variant_create(
    campaign_id: int,
    name: str = Form(...),
    subject: str = Form(""),
    preheader: str = Form(""),
    db: Session = Depends(get_db),
):
    create_variant_for_campaign(
        db,
        campaign_id=campaign_id,
        name=name,
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


@router.post("/ui/campaigns/{campaign_id}/variants/{variant_id}/modules")
def module_create(
    campaign_id: int,
    variant_id: int,
    module_type: str = Form(...),
    content_record_id: int | None = Form(None),
    decision_slot_id: int | None = Form(None),
    db: Session = Depends(get_db),
):
    try:
        create_module_for_variant(
            db,
            variant_id=variant_id,
            module_type=module_type,
            content_record_id=content_record_id or None,
            decision_slot_id=decision_slot_id or None,
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
    db: Session = Depends(get_db),
):
    send_instance = create_send_instance(db, snapshot_id=snapshot_id, name=name, provider="mock")
    return RedirectResponse(url=f"/ui/deliveries/send-instances/{send_instance.id}", status_code=303)


@router.post("/ui/decisions/slots/{slot_id}/edit")
def decision_slot_edit(
    slot_id: int,
    decision_strategy: str = Form(...),
    candidate_filter_json: str = Form("{}"),
    strategy_config_json: str = Form("{}"),
    db: Session = Depends(get_db),
):
    import json as _json
    try:
        candidate_filter = _json.loads(candidate_filter_json) or None
        strategy_config = _json.loads(strategy_config_json) or None
    except ValueError:
        return RedirectResponse(
            url=f"/ui/decisions/slots/{slot_id}?error={quote('Config/filter must be valid JSON')}",
            status_code=303,
        )
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
    send_send_instance(db, send_instance_id=send_instance_id)
    return RedirectResponse(url=f"/ui/deliveries/send-instances/{send_instance_id}", status_code=303)


@router.get("/ui/content")
def content_list(
    request: Request,
    db: Session = Depends(get_db),
):
    records = (
        db.query(ContentRecordDB)
        .order_by(ContentRecordDB.id.asc())
        .all()
    )

    return templates.TemplateResponse(
        request,
        "content.html",
        {
            "title": "Content",
            "records": records,
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
        .filter(ContentRecordDB.id == content_record_id)
        .first()
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
            PreferenceUpdateLogDB,
            CategoryDB.name,
            EngagementEventDB.event_data,
        )
        .join(
            CategoryDB,
            PreferenceUpdateLogDB.category_id == CategoryDB.id,
        )
        .join(
            EngagementEventDB,
            PreferenceUpdateLogDB.event_id == EngagementEventDB.id,
        )
        .order_by(
            PreferenceUpdateLogDB.created_at.desc()
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
                "previous_score": update.previous_score,
                "delta": update.delta,
                "new_score": update.new_score,
                "reason": update.reason,
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
        },
    )


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
    title: str = Form(...),
    description: str = Form(""),
    headline_medium: str = Form(...),
    body_medium: str = Form(""),
    button_label: str = Form(""),
    button_url: str = Form(""),
    image_url: str = Form(""),
    image_alt: str = Form(""),
    db: Session = Depends(get_db),
):
    record = create_content(
        db,
        title=title,
        description=description or None,
        content={
            "headline_medium": headline_medium,
            "body_medium": body_medium,
            "button_label": button_label,
            "button_url": button_url,
            "image_url": image_url,
            "image_alt": image_alt,
        },
    )
    return RedirectResponse(url=f"/ui/content/{record.id}", status_code=303)


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
    db: Session = Depends(get_db),
):
    update_content_record(
        db,
        content_record_id,
        title=title,
        description=description or None,
        content={
            "headline_medium": headline_medium,
            "body_medium": body_medium,
            "button_label": button_label,
            "button_url": button_url,
            "image_url": image_url,
            "image_alt": image_alt,
        },
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

    recipient_preferences = (
        db.query(
            RecipientDB.id,
            RecipientDB.external_id,
            RecipientPreferenceDB.score,
            RecipientPreferenceDB.source,
        )
        .join(
            RecipientPreferenceDB,
            RecipientPreferenceDB.recipient_id == RecipientDB.id,
        )
        .filter(
            RecipientPreferenceDB.category_id == category_id
        )
        .order_by(
            RecipientPreferenceDB.score.desc()
        )
        .limit(50)
        .all()
    )

    recipient_preference_rows = [
        {
            "recipient_id": recipient_id,
            "recipient_external_id": external_id,
            "score": score,
            "source": source,
        }
        for recipient_id, external_id, score, source in recipient_preferences
    ]

    impact = (
        db.query(
            func.count(PreferenceUpdateLogDB.id),
            func.coalesce(func.sum(PreferenceUpdateLogDB.delta), 0),
            func.coalesce(func.avg(PreferenceUpdateLogDB.delta), 0),
        )
        .filter(
            PreferenceUpdateLogDB.category_id == category_id
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
            DecisionSlotDB.id == decision_slot_id
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
            },
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
    db: Session = Depends(get_db),
):
    send_instances = (
        db.query(SendInstanceDB)
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
        },
    )


@router.get("/ui/deliveries/send-instances/{send_instance_id}")
def delivery_detail(
    send_instance_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    send_instance = (
        db.query(SendInstanceDB)
        .filter(SendInstanceDB.id == send_instance_id)
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
                    PreferenceUpdateLogDB,
                    CategoryDB.name,
                )
                .join(
                    CategoryDB,
                    PreferenceUpdateLogDB.category_id == CategoryDB.id,
                )
                .filter(
                    PreferenceUpdateLogDB.event_id == event.id
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
                            "previous_score": update.previous_score,
                            "delta": update.delta,
                            "new_score": update.new_score,
                            "reason": update.reason,
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

    return templates.TemplateResponse(
        request,
        "delivery_detail.html",
        {
            "title": f"Delivery {send_instance_id}",
            "send_instance": send_instance,
            "snapshot": snapshot,
            "executions": execution_rows,
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
            PreferenceUpdateLogDB.category_id,
            func.count(PreferenceUpdateLogDB.id),
            func.coalesce(func.sum(PreferenceUpdateLogDB.delta), 0),
            func.coalesce(func.avg(PreferenceUpdateLogDB.delta), 0),
            func.count(func.distinct(PreferenceUpdateLogDB.event_id)),
        )
        .group_by(PreferenceUpdateLogDB.category_id)
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
            PreferenceUpdateLogDB,
            EngagementEventDB,
        )
        .join(
            EngagementEventDB,
            PreferenceUpdateLogDB.event_id == EngagementEventDB.id,
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

            edge_map[key]["total_delta"] += float(update.delta)
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
    groups = audience_service.list_groups(db)
    rows = []
    for g in groups:
        count = db.query(AudienceGroupMemberDB).filter(AudienceGroupMemberDB.group_id == g.id).count()
        rows.append({"id": g.id, "name": g.name, "description": g.description,
                     "member_count": count, "created_at": g.created_at})
    return templates.TemplateResponse(request, "audience_groups.html",
                                      {"title": "Audience Groups", "groups": rows, "error": error})


@router.post("/ui/audience-groups")
def audience_groups_create(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    desc = description.strip() or None
    try:
        group = audience_service.create_group(db, name.strip(), desc)
    except ValueError as error:
        return RedirectResponse(f"/ui/audience-groups?error={quote(str(error))}", status_code=303)
    return RedirectResponse(f"/ui/audience-groups/{group.id}", status_code=303)


@router.get("/ui/audience-groups/{group_id}")
def audience_group_detail(group_id: int, request: Request, error: str | None = None, db: Session = Depends(get_db)):
    group = audience_service.get_group(db, group_id)
    if not group:
        return RedirectResponse("/ui/audience-groups", status_code=303)

    member_ids = audience_service.get_member_recipient_ids(db, group_id)
    raw_members = audience_service.list_members(db, group_id)

    members = []
    for m in raw_members:
        r = db.query(RecipientDB).filter(RecipientDB.id == m.recipient_id).first()
        if r:
            members.append({
                "recipient_id": r.id,
                "external_id": r.external_id,
                "email": r.email,
                "status": r.status,
                "added_at": m.added_at,
            })

    all_recipients = db.query(RecipientDB).order_by(RecipientDB.email.asc()).all()
    non_members = [r for r in all_recipients if r.id not in member_ids]

    languages = sorted({r.language for r in all_recipients if r.language})
    statuses = sorted({r.status for r in all_recipients if r.status})
    categories = db.query(CategoryDB).order_by(CategoryDB.name.asc()).all()

    return templates.TemplateResponse(request, "audience_group_detail.html", {
        "title": f"Group: {group.name}",
        "group": group,
        "members": members,
        "non_members": non_members,
        "languages": languages,
        "statuses": statuses,
        "categories": categories,
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
        language=language or None,
        status=status or None,
        preference_category_id=cat_id,
        min_preference_score=min_score,
        exclude_ids=member_ids,
    )
    return JSONResponse({"count": len(matches), "recipients": [
        {"id": r.id, "email": r.email, "external_id": r.external_id, "language": r.language, "status": r.status}
        for r in matches[:20]
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
        language=language or None,
        status=status or None,
        preference_category_id=cat_id,
        min_preference_score=min_score,
        exclude_ids=member_ids,
    )
    audience_service.bulk_add_members(db, group_id, [r.id for r in matches])
    return RedirectResponse(f"/ui/audience-groups/{group_id}", status_code=303)
