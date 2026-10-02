"""Where are my campaigns — the monitoring read model (task-216).

Manager Workflow interview Q3.1 moved monitoring out of the campaign list and
Q5.4 kept it apart from deliveries: **monitoring is campaign-level** and
answers *where are my campaigns*, including ones that have sent nothing, while
deliveries answers *what did this send do*. A screen answers one question.

**Derived, never stored.** `CampaignDB.status` is set at creation and nothing
in the send lifecycle moves it, and the honest answer is not to start: a
variant is what gets snapshotted, planned and sent (ADR-160 point 4), so a
campaign's state is a summary of its variants' facts. Storing it would be a
second answer free to drift from the first — the reason ADR-163 computes
consent from events.

**"In flight" means approved but not finished** (decided 2026-10-02): any
variant with a snapshot that no send has used yet, or a send that is planned,
scheduled or sending.
"""

from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.campaigns.db_models import CampaignDB, VariantDB
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.snapshots.db_models import SnapshotDB

#: A variant's stages, furthest along first. A variant takes the first one its
#: facts support, so a waiting snapshot outranks last week's finished send —
#: the weekly newsletter is in flight again the moment it is snapshotted.
STAGES = ("sending", "scheduled", "planned", "snapshotted", "sent", "composing")
IN_FLIGHT_STAGES = {"sending", "scheduled", "planned", "snapshotted"}

#: Send statuses that end a send. Anything else is treated as still underway,
#: so a status this module has not heard of shows a campaign in flight rather
#: than hiding it as finished.
FINISHED = {"sent", "partial_failed", "failed", "no_recipients"}
FAILED = {"failed", "partial_failed"}
_ACTIVE_STAGE = {"sending": "sending", "scheduled": "scheduled"}

_STATE_ORDER = {"in_flight": 0, "in_preparation": 1, "sent": 2}


def _variant_stage(sends: list[SendInstanceDB], waiting_snapshot: bool) -> str:
    stages = set()
    for send in sends:
        if send.status in FINISHED:
            stages.add("sent")
        else:
            # `draft` is a planned send; an unknown status is treated as one.
            stages.add(_ACTIVE_STAGE.get(send.status, "planned"))
    if waiting_snapshot:
        stages.add("snapshotted")
    return next((s for s in STAGES if s in stages), "composing")


def campaign_monitoring(db: Session, *, brand_id: int) -> list[dict]:
    """Every campaign in the brand with its derived state, in flight first.

    One query per table, assembled here — not one per campaign, which is the
    shape task-213 records as the audience list's cost.
    """
    campaigns = db.query(CampaignDB).filter(CampaignDB.brand_id == brand_id).all()
    if not campaigns:
        return []
    campaign_ids = [c.id for c in campaigns]

    variants = (
        db.query(VariantDB)
        .filter(VariantDB.campaign_id.in_(campaign_ids))
        .order_by(VariantDB.id.asc())
        .all()
    )
    variant_ids = [v.id for v in variants]
    snapshots = (
        db.query(SnapshotDB).filter(SnapshotDB.variant_id.in_(variant_ids)).all()
        if variant_ids else []
    )
    snapshot_variant = {s.id: s.variant_id for s in snapshots}
    sends = (
        db.query(SendInstanceDB)
        .filter(SendInstanceDB.snapshot_id.in_(list(snapshot_variant)),
                SendInstanceDB.brand_id == brand_id)
        .all()
        if snapshot_variant else []
    )
    send_ids = [s.id for s in sends]
    last_sent = dict(
        db.query(DeliveryExecutionDB.send_instance_id, func.max(DeliveryExecutionDB.sent_at))
        .filter(DeliveryExecutionDB.send_instance_id.in_(send_ids))
        .group_by(DeliveryExecutionDB.send_instance_id)
        .all()
    ) if send_ids else {}

    sends_by_variant: dict[int, list[SendInstanceDB]] = defaultdict(list)
    used_snapshots = set()
    for send in sends:
        sends_by_variant[snapshot_variant[send.snapshot_id]].append(send)
        used_snapshots.add(send.snapshot_id)
    waiting = {s.variant_id for s in snapshots if s.id not in used_snapshots}
    variants_by_campaign: dict[int, list[VariantDB]] = defaultdict(list)
    for variant in variants:
        variants_by_campaign[variant.campaign_id].append(variant)

    rows = []
    for campaign in campaigns:
        variant_rows = []
        scheduled_at, sent_at = [], []
        for variant in variants_by_campaign[campaign.id]:
            variant_sends = sends_by_variant[variant.id]
            scheduled_at += [s.scheduled_at for s in variant_sends
                             if s.status == "scheduled" and s.scheduled_at]
            sent_at += [last_sent[s.id] for s in variant_sends if last_sent.get(s.id)]
            variant_rows.append({
                "id": variant.id,
                "name": variant.name,
                "channel": variant.channel,
                "stage": _variant_stage(variant_sends, variant.id in waiting),
                "has_failures": any(s.status in FAILED for s in variant_sends),
            })
        stages = {v["stage"] for v in variant_rows}
        if stages & IN_FLIGHT_STAGES:
            state = "in_flight"
        elif "sent" in stages:
            state = "sent"
        else:
            state = "in_preparation"
        rows.append({
            "id": campaign.id,
            "name": campaign.name,
            "state": state,
            "has_failures": any(v["has_failures"] for v in variant_rows),
            "next_scheduled_at": min(scheduled_at) if scheduled_at else None,
            "last_sent_at": max(sent_at) if sent_at else None,
            "updated_at": campaign.updated_at,
            "variants": variant_rows,
        })

    # Newest first within a state; then stable-sort by state, in flight first.
    rows.sort(key=lambda r: r["updated_at"], reverse=True)
    rows.sort(key=lambda r: _STATE_ORDER[r["state"]])
    return rows
