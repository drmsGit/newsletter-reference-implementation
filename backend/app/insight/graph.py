"""The category graph's figures, for one brand (task-57, ADR-150).

Moved out of `frontend/router.py`, which only lays the graph out now: the
figures are what the SPA will need, and the Jinja UI the SPA is meant to
replace (task-50) was the only place they could be computed.

**Everything is scoped to one brand, together.** ADR-150's addendum of
2026-09-15 forbade scoping some figures and not others, because two
populations side by side on one canvas recreate the "every category works the
same" blend in a subtler form. So:

  - content counts and co-occurrence edges count only this brand's content
    records;
  - selection counts count only resolutions of this brand's content;
  - signal impact (on nodes and on edges) sums only **this brand's audience**:
    people whose latest *marketing* consent for this brand is opted in on any
    registered channel (decided 2026-10-02).

**Point 8 is untouched.** A person keeps one affinity profile, shared across
brands; nothing here derives a brand per contribution. What is scoped is which
people are summed — "a query, not a column", in the addendum's words.
"""
from itertools import combinations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.campaigns.db_models import DecisionResolutionDB
from app.channels.registry import list_channels
from app.content.db_models import (
    CategoryDB, CategoryRelationDB, ContentCategoryAssignmentDB, ContentRecordDB,
)
from app.insight.db_models import EngagementEventDB
from app.recipients.consent import is_consenting_filter
from app.recipients.db_models import RecipientDB, SignalContributionDB

_NO_IMPACT = {"update_count": 0, "total_delta": 0, "avg_delta": 0, "event_count": 0}


def brand_audience(brand_id: int):
    """Recipient ids in this brand's audience, as a subquery.

    Opted in for marketing on at least one registered channel. Kept as SQL so
    the graph stays a fixed number of queries whatever the recipient count.
    """
    channels = [manifest.name for manifest in list_channels()]
    return select(RecipientDB.id).where(
        or_(*(is_consenting_filter(brand_id, channel=channel) for channel in channels))
    )


def category_graph(db: Session, *, brand_id: int) -> dict:
    """Categories, their per-category figures and the graph's edges, for one brand.

    The categories and their relations are the shared vocabulary (ADR-150's
    addendum: one taxonomy for every brand), so every category appears; what
    its numbers count is this brand's.
    """
    categories = (
        db.query(CategoryDB).order_by(CategoryDB.type.asc(), CategoryDB.name.asc()).all()
    )
    brand_content = select(ContentRecordDB.id).where(ContentRecordDB.brand_id == brand_id)
    audience = brand_audience(brand_id)

    selections = dict(
        db.query(ContentCategoryAssignmentDB.category_id, func.count(DecisionResolutionDB.id))
        .join(
            DecisionResolutionDB,
            DecisionResolutionDB.content_record_id == ContentCategoryAssignmentDB.content_id,
        )
        .filter(ContentCategoryAssignmentDB.content_id.in_(brand_content))
        .group_by(ContentCategoryAssignmentDB.category_id)
        .all()
    )
    content_counts = dict(
        db.query(
            ContentCategoryAssignmentDB.category_id,
            func.count(func.distinct(ContentCategoryAssignmentDB.content_id)),
        )
        .filter(ContentCategoryAssignmentDB.content_id.in_(brand_content))
        .group_by(ContentCategoryAssignmentDB.category_id)
        .all()
    )
    impact = {
        category_id: {
            "update_count": update_count,
            "total_delta": round(float(total_delta), 2),
            "avg_delta": round(float(avg_delta), 2),
            "event_count": event_count,
        }
        for category_id, update_count, total_delta, avg_delta, event_count in (
            db.query(
                SignalContributionDB.category_id,
                func.count(SignalContributionDB.id),
                func.coalesce(func.sum(SignalContributionDB.base_weight), 0),
                func.coalesce(func.avg(SignalContributionDB.base_weight), 0),
                func.count(func.distinct(SignalContributionDB.event_id)),
            )
            .filter(SignalContributionDB.recipient_id.in_(audience))
            .group_by(SignalContributionDB.category_id)
            .all()
        )
    }
    parent_counts = dict(
        db.query(CategoryRelationDB.child_category_id, func.count(CategoryRelationDB.id))
        .group_by(CategoryRelationDB.child_category_id)
        .all()
    )
    child_counts = dict(
        db.query(CategoryRelationDB.parent_category_id, func.count(CategoryRelationDB.id))
        .group_by(CategoryRelationDB.parent_category_id)
        .all()
    )

    content_to_categories: dict[int, set[int]] = {}
    for assignment in (
        db.query(ContentCategoryAssignmentDB)
        .filter(ContentCategoryAssignmentDB.content_id.in_(brand_content))
        .all()
    ):
        content_to_categories.setdefault(assignment.content_id, set()).add(assignment.category_id)

    # Relations are shared vocabulary, so every relation is an edge in every
    # brand; co-occurrence is this brand's content only.
    edges: dict[tuple[int, int], dict] = {}
    for relation in db.query(CategoryRelationDB).all():
        key = tuple(sorted([relation.parent_category_id, relation.child_category_id]))
        edges[key] = {
            "source": relation.parent_category_id,
            "target": relation.child_category_id,
            "type": "relation",
            "cooccurrence_count": 0,
            "event_count": 0,
            "total_delta": 0,
            "strength": 1,
        }
    for category_ids in content_to_categories.values():
        for key in combinations(sorted(category_ids), 2):
            if key not in edges:
                edges[key] = {
                    "source": key[0],
                    "target": key[1],
                    "type": "cooccurrence",
                    "cooccurrence_count": 0,
                    "event_count": 0,
                    "total_delta": 0,
                    "strength": 0,
                }
            edges[key]["cooccurrence_count"] += 1
            edges[key]["strength"] += 1

    # Edge impact: this brand's audience reacting to this brand's content.
    # A content id from another brand is absent from `content_to_categories`
    # and so contributes nothing, which is the second half of the same scope.
    edge_event_ids: dict[tuple[int, int], set[int]] = {key: set() for key in edges}
    for contribution, event in (
        db.query(SignalContributionDB, EngagementEventDB)
        .join(EngagementEventDB, SignalContributionDB.event_id == EngagementEventDB.id)
        .filter(SignalContributionDB.recipient_id.in_(audience))
        .all()
    ):
        content_id = (event.event_data or {}).get("content_record_id")
        for key in combinations(sorted(content_to_categories.get(content_id, set())), 2):
            if key in edges:
                edges[key]["total_delta"] += float(contribution.base_weight)
                edge_event_ids[key].add(event.id)
    for key, event_ids in edge_event_ids.items():
        edges[key]["event_count"] = len(event_ids)
        edges[key]["total_delta"] = round(edges[key]["total_delta"], 2)

    return {
        "categories": categories,
        "metrics": {
            category.id: {
                "selected_count": selections.get(category.id, 0),
                "content_count": content_counts.get(category.id, 0),
                **impact.get(category.id, _NO_IMPACT),
                "parent_count": parent_counts.get(category.id, 0),
                "child_count": child_counts.get(category.id, 0),
            }
            for category in categories
        },
        "edges": list(edges.values()),
    }
