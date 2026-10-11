"""How a campaign went — the campaign page's results section (task-58, ADR-196).

**The one KPI view, and deliberately small.** The user's framing on
2026-09-18: "we are no analytics platform, you get what you need and an easy
way to export everything" — and on 2026-10-11 the export became the
adopter's own IT task, documented rather than built. What is left is this:
one row per variant that has sent, and a campaign line on top. Comparing
campaigns, series or audience groups is the analytics tool's job.

**Computed on read, never stored**, like monitoring (task-216): the figures
are the delivery rows and events as they are now. When retention pruning
arrives (task-136, task-85) it has to keep these figures before it removes the
rows they come from — ADR-196 says so; nothing here can.

**Counted per delivery, not per person.** A person on two sends of one
variant is two recipients, two possible clickers. "Unique" means distinct
deliveries with at least one such event.

**Every click rate is over sent**, per variant and for the campaign (pooled,
not a mean of the variants' rates), so email and push compare like for like:
push has no delivered events. Delivered is a figure of its own for email.

**Opens are not a figure** until task-353 decides whether they stay.
"""
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.campaigns.db_models import CampaignDB, VariantDB
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.insight.db_models import EngagementEventDB
from app.recipients.db_models import ConsentEventDB
from app.snapshots.db_models import SnapshotDB

#: Send statuses of a send that has gone out (or is going out). A draft or a
#: scheduled send has results of nobody yet.
WENT_OUT = ("sending", "sent", "partial_failed", "failed", "no_recipients")

#: From this moment a consent event records the delivery it came through
#: (migrate_0048). Unsubscribes made before it cannot be placed on a send, so a
#: send older than this may have more than it shows. Midnight after the
#: migration: conservative by up to a day, never generous.
UNSUBSCRIBES_COUNTED_SINCE = datetime(2026, 10, 12, tzinfo=timezone.utc)

#: Channels whose provider reports a delivery. Push has none.
DELIVERY_REPORTED = {"email"}

#: Execution statuses counted as failed. "uncertain" is in it, as in the
#: stored `failed_count` (ADR-196 point 3).
FAILED = ("failed", "uncertain")

_COUNTS = ("recipients", "sent", "failed", "excluded", "bounced", "complaints",
           "clicks_total", "unique_clickers", "unsubscribes")


def _rate(clickers: int, sent: int) -> float | None:
    return clickers / sent if sent else None


def _empty() -> dict:
    return {**{key: 0 for key in _COUNTS}, "delivered": 0, "excluded_by_stage": {}}


def campaign_results(db: Session, campaign_id: int, *, brand_id: int) -> dict | None:
    """The campaign's figures, or None when it is not the brand's."""
    campaign = (db.query(CampaignDB)
                .filter(CampaignDB.id == campaign_id, CampaignDB.brand_id == brand_id).first())
    if campaign is None:
        return None
    variants = (db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id)
                .order_by(VariantDB.id).all())
    sends = (db.query(SendInstanceDB.id, SnapshotDB.variant_id, SendInstanceDB.created_at)
             .join(SnapshotDB, SnapshotDB.id == SendInstanceDB.snapshot_id)
             .filter(SnapshotDB.variant_id.in_([v.id for v in variants]),
                     SendInstanceDB.brand_id == brand_id,
                     SendInstanceDB.status.in_(WENT_OUT))
             .all())
    variant_of_send = {send_id: variant_id for send_id, variant_id, _ in sends}
    partial = any(created_at < UNSUBSCRIBES_COUNTED_SINCE for _, _, created_at in sends)
    figures: dict[int, dict] = defaultdict(_empty)

    if variant_of_send:
        send_ids = list(variant_of_send)
        # Executions by status, and the exclusion stage — the part of
        # `exclusion_reason` before the first colon, as the deliveries screen
        # counts it (`send_instance_detail`).
        for send_id, status, reason, count in (
                db.query(DeliveryExecutionDB.send_instance_id, DeliveryExecutionDB.status,
                         DeliveryExecutionDB.exclusion_reason, func.count())
                .filter(DeliveryExecutionDB.send_instance_id.in_(send_ids))
                .group_by(DeliveryExecutionDB.send_instance_id, DeliveryExecutionDB.status,
                          DeliveryExecutionDB.exclusion_reason)):
            row = figures[variant_of_send[send_id]]
            row["recipients"] += count
            if status == "sent":
                row["sent"] += count
            elif status in FAILED:
                row["failed"] += count
            elif status == "excluded":
                row["excluded"] += count
                if reason:
                    stage = reason.split(":", 1)[0].strip()
                    row["excluded_by_stage"][stage] = row["excluded_by_stage"].get(stage, 0) + count

        # Events: distinct deliveries per type, and every click.
        for send_id, event_type, deliveries, events in (
                db.query(DeliveryExecutionDB.send_instance_id, EngagementEventDB.event_type,
                         func.count(distinct(EngagementEventDB.delivery_execution_id)), func.count())
                .join(EngagementEventDB, EngagementEventDB.delivery_execution_id == DeliveryExecutionDB.id)
                .filter(DeliveryExecutionDB.send_instance_id.in_(send_ids),
                        EngagementEventDB.event_type.in_(("delivered", "bounce", "complaint", "click")))
                .group_by(DeliveryExecutionDB.send_instance_id, EngagementEventDB.event_type)):
            row = figures[variant_of_send[send_id]]
            if event_type == "delivered":
                row["delivered"] += deliveries
            elif event_type == "bounce":
                row["bounced"] += deliveries
            elif event_type == "complaint":
                row["complaints"] += deliveries
            else:
                row["unique_clickers"] += deliveries
                row["clicks_total"] += events

        # Unsubscribes: distinct deliveries an unsubscribe came through, so an
        # "everything" opt-out (one row per brand and channel) counts once.
        for send_id, deliveries in (
                db.query(DeliveryExecutionDB.send_instance_id,
                         func.count(distinct(ConsentEventDB.delivery_execution_id)))
                .join(ConsentEventDB, ConsentEventDB.delivery_execution_id == DeliveryExecutionDB.id)
                .filter(DeliveryExecutionDB.send_instance_id.in_(send_ids),
                        ConsentEventDB.source == "unsubscribe")
                .group_by(DeliveryExecutionDB.send_instance_id)):
            figures[variant_of_send[send_id]]["unsubscribes"] += deliveries

    rows = []
    for variant in variants:
        if variant.id not in set(variant_of_send.values()):
            continue
        row = figures[variant.id]
        rows.append({
            "id": variant.id, "name": variant.name, "channel": variant.channel, **row,
            "delivered": row["delivered"] if variant.channel in DELIVERY_REPORTED else None,
            "click_rate": _rate(row["unique_clickers"], row["sent"]),
        })

    line = None
    if rows:
        line = {key: sum(r[key] for r in rows) for key in _COUNTS}
        stages: dict[str, int] = {}
        for r in rows:
            for stage, count in r["excluded_by_stage"].items():
                stages[stage] = stages.get(stage, 0) + count
        reported = [r["delivered"] for r in rows if r["delivered"] is not None]
        line.update(excluded_by_stage=stages, delivered=sum(reported) if reported else None,
                    click_rate=_rate(line["unique_clickers"], line["sent"]))
    return {"campaign": line, "variants": rows, "unsubscribes_partial": partial,
            "unsubscribes_counted_since": UNSUBSCRIBES_COUNTED_SINCE}
