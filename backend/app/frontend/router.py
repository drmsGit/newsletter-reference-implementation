from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import get_db

import json

from app.content.db_models import ContentRecordDB, ContentVersionDB, CategoryDB, ContentCategoryAssignmentDB, CategoryRelationDB
from app.campaigns.db_models import CampaignDB, DecisionResolutionDB, VariantDB, ModuleInstanceDB, DecisionSlotDB
from app.recipients.db_models import RecipientDB, RecipientPreferenceDB, PreferenceUpdateLogDB
from app.decision.strategies.registry import STRATEGIES
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
            DeliveryExecutionDB.recipient_id == recipient.external_id
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
        modules = (
            db.query(ModuleInstanceDB)
            .filter(ModuleInstanceDB.variant_id == variant.id)
            .order_by(ModuleInstanceDB.position.asc())
            .all()
        )

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

        snapshots = (
            db.query(SnapshotDB)
            .filter(SnapshotDB.variant_id == variant.id)
            .order_by(SnapshotDB.created_at.desc())
            .all()
        )

        variant_rows.append(
            {
                "id": variant.id,
                "name": variant.name,
                "modules": modules,
                "decision_slots": decision_slot_rows,
                "snapshots": snapshots,
            }
        )

    return templates.TemplateResponse(
        request,
        "campaign_detail.html",
        {
            "title": f"Campaign {campaign_id}",
            "campaign": campaign,
            "variants": variant_rows,
        },
    )


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
    db: Session = Depends(get_db),
):
    record = (
        db.query(ContentRecordDB)
        .filter(ContentRecordDB.id == content_record_id)
        .first()
    )

    categories = (
        db.query(
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
            "name": name,
            "type": category_type,
            "score": score,
        }
        for name, category_type, score in categories
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
                (version.content or {}).get("text_medium")
                or (version.content or {}).get("text_short")
                or (version.content or {}).get("text")
            ),
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
        },
    )


@router.get("/ui/categories")
def categories_list(
    request: Request,
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
        },
    )


@router.get("/ui/categories/{category_id}")
def category_detail(
    category_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    category = (
        db.query(CategoryDB)
        .filter(CategoryDB.id == category_id)
        .first()
    )

    parent_categories = (
        db.query(CategoryDB)
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
        db.query(CategoryDB)
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
        },
    )


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

    supported_strategies = sorted(STRATEGIES.keys())

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
            "summary": resolution_summary,
            "reason_summary": reason_summary_rows,
            "top_content": top_content_rows,
            "latest_resolutions": latest_resolution_rows,
        },
    )