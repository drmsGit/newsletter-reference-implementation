"""A content record's figures (task-359; ADR-196 addendum 2026-10-16).

The campaign results' definitions (`app/campaigns/results.py`), per record:
**counted per delivery, not per person**, all time, computed on read.

- `deliveries`: sent deliveries that carried the record — as a module of
  their frozen frame, or as one of this recipient's slot picks
  (`carried_content`, the rule click attribution uses); `picked`: of those,
  how many through a slot pick.
- `clicks`: clicks on its links (a click names its record through
  `event_data.content_record_id`, ADR-182); `unique_clickers`: deliveries
  with at least one.
- `click_share`: its clicks over **all** clicks in the deliveries that
  carried it — the user's measure (2026-10-16): when it is in an email, does
  it pull the clicks? A rate over deliveries reads very low and is the
  campaign section's job. None while those deliveries have no clicks.

No opens (ADR-196). Every sent delivery of the brand is read on each call:
right for a reference installation; one with millions of deliveries would
store these figures instead.
"""
from collections import defaultdict

from sqlalchemy.orm import Session

from app.campaigns.db_models import CampaignDB, VariantDB
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.delivery.service import carried_content
from app.insight.db_models import EngagementEventDB
from app.snapshots.db_models import SnapshotDB

_FIGURES = ("deliveries", "picked", "clicks", "unique_clickers", "clicks_in_deliveries")


def _empty() -> dict:
    return dict.fromkeys(_FIGURES, 0)


def _finish(row: dict) -> dict:
    return {**row, "click_share": row["clicks"] / row["clicks_in_deliveries"] if row["clicks_in_deliveries"] else None}


def content_figures(db: Session, brand_id: int, content_ids=None, *, by_campaign: bool = False):
    """{content id: figures} for the brand's sent deliveries; with
    `by_campaign`, also {content id: {campaign id: figures}} and the campaigns'
    names. `content_ids` limits the result, not the reading."""
    rows = (db.query(DeliveryExecutionDB.id, DeliveryExecutionDB.delivery_record, SnapshotDB.id,
                     VariantDB.campaign_id)
            .join(SendInstanceDB, SendInstanceDB.id == DeliveryExecutionDB.send_instance_id)
            .join(SnapshotDB, SnapshotDB.id == SendInstanceDB.snapshot_id)
            .join(VariantDB, VariantDB.id == SnapshotDB.variant_id)
            .filter(SendInstanceDB.brand_id == brand_id, DeliveryExecutionDB.status == "sent")
            .all())
    wanted = set(content_ids) if content_ids is not None else None
    frames = {sid: ctx for sid, ctx in db.query(SnapshotDB.id, SnapshotDB.render_context)
              .filter(SnapshotDB.id.in_({r[2] for r in rows}))} if rows else {}

    carried: dict[int, tuple[set, set, int]] = {}
    for execution_id, record, snapshot_id, campaign_id in rows:
        placed, picked = carried_content(frames.get(snapshot_id) or {}, record or {})
        if wanted is not None:
            placed, picked = placed & wanted, picked & wanted
        if placed or picked:
            carried[execution_id] = (placed, picked, campaign_id)

    clicks_by_execution: dict[int, int] = defaultdict(int)
    named: dict[tuple[int, int], int] = defaultdict(int)
    if carried:
        for execution_id, data in (db.query(EngagementEventDB.delivery_execution_id, EngagementEventDB.event_data)
                                   .filter(EngagementEventDB.delivery_execution_id.in_(list(carried)),
                                           EngagementEventDB.event_type == "click")):
            clicks_by_execution[execution_id] += 1
            content_id = (data or {}).get("content_record_id")
            if isinstance(content_id, int):
                named[(execution_id, content_id)] += 1

    overall: dict[int, dict] = defaultdict(_empty)
    campaigns: dict[int, dict[int, dict]] = defaultdict(lambda: defaultdict(_empty))
    for execution_id, (placed, picked, campaign_id) in carried.items():
        for content_id in placed | picked:
            clicks = named.get((execution_id, content_id), 0)
            targets = [overall[content_id]] + ([campaigns[content_id][campaign_id]] if by_campaign else [])
            for row in targets:
                row["deliveries"] += 1
                row["picked"] += content_id in picked and content_id not in placed
                row["clicks"] += clicks
                row["unique_clickers"] += bool(clicks)
                row["clicks_in_deliveries"] += clicks_by_execution.get(execution_id, 0)

    result = {content_id: _finish(row) for content_id, row in overall.items()}
    if not by_campaign:
        return result
    names = dict(db.query(CampaignDB.id, CampaignDB.name).filter(CampaignDB.id.in_(
        {c for per in campaigns.values() for c in per}))) if campaigns else {}
    per_campaign = {content_id: {campaign_id: _finish(row) for campaign_id, row in per.items()}
                    for content_id, per in campaigns.items()}
    return result, per_campaign, names
