from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import working_brand
from app.pagination import Page, PageParams, page_of_list, page_params
from app.database import get_db
from app.insight.graph import category_graph
from app.insight.models import (
    BrandOverview,
    CategoryDetail,
    CategoryGraph,
    CategoryGraphEdge,
    CategoryGraphNode,
    EngagementEvent,
    EngagementEventCreate,
    PreferenceUpdateResult,
)
from app.insight.service import (
    create_engagement_event,
    list_events_for_delivery_execution,
    apply_event_to_signals,
)


router = APIRouter(prefix="/insight", tags=["insight"])


@router.post("/events", response_model=EngagementEvent)
def create_event(
    payload: EngagementEventCreate,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    try:
        return create_engagement_event(
            db=db,
            delivery_execution_id=payload.delivery_execution_id,
            event_type=payload.event_type,
            provider=payload.provider,
            provider_event_id=payload.provider_event_id,
            event_data=payload.event_data,
            occurred_at=payload.occurred_at,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Engagement event already recorded for provider={payload.provider!r}, provider_event_id={payload.provider_event_id!r}",
        )


@router.get("/delivery-executions/{delivery_execution_id}/events", response_model=Page[EngagementEvent])
def get_events_for_delivery_execution(
    delivery_execution_id: int,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    from app.insight.service import page_events_for_delivery_execution

    return page_events_for_delivery_execution(db, delivery_execution_id, params, brand_id=brand_id)


@router.post("/events/{event_id}/apply-signals", response_model=PreferenceUpdateResult)
def apply_signals_from_event(
    event_id: int,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    try:
        return apply_event_to_signals(
            db=db,
            event_id=event_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

@router.get(
    "/category-graph",
    response_model=CategoryGraph,
    summary="The category graph's figures for the working brand",
    description=(
        "Every category (the taxonomy is shared, so all appear) with this "
        "brand's figures, and the graph's edges. **Every figure is scoped to "
        "the working brand together** (ADR-150): counts are this brand's "
        "content and resolutions; signal impact sums this brand's audience — "
        "people whose latest marketing consent for it is opted in on any "
        "channel. Layout is the client's."
    ),
)
def get_category_graph(
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    figures = category_graph(db, brand_id=brand_id)
    return CategoryGraph(
        brand_id=brand_id,
        nodes=[
            CategoryGraphNode(
                id=category.id, name=category.name, type=category.type,
                **figures["metrics"][category.id],
            )
            for category in figures["categories"]
        ],
        edges=[CategoryGraphEdge(**edge) for edge in figures["edges"]],
    )


@router.get("/overview", response_model=BrandOverview,
            summary="The dashboard's counts for the working brand")
def get_overview(db: Session = Depends(get_db), brand_id: int = Depends(working_brand)):
    from app.insight.service import brand_overview

    return brand_overview(db, brand_id=brand_id)


@router.get(
    "/categories/{category_id}",
    response_model=CategoryDetail,
    summary="One category for the working brand: its content, audience and impact",
    description=(
        "Parents and children (with relation ids), this brand's content in the "
        "category, the top 50 of this brand's audience by decayed signal, and "
        "the impact over that audience (ADR-150). 404 for an unknown category."
    ),
)
def get_category_detail(
    category_id: int, db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
):
    from app.insight.graph import category_detail

    detail = category_detail(db, category_id, brand_id=brand_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Category {category_id} not found")
    return detail
