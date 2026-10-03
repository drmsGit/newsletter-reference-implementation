"""ADR-185: lists that grow with data are paged in one envelope (task-88).

Two kinds of test. The mechanism's own (the total counts the whole filtered
set; pages neither overlap nor skip). And a guard over the routes the app
actually registers: every GET list route is CLASSIFIED — paged, or fixed by
code or configuration (point 1) — so a new list route cannot arrive without
someone deciding which it is, and a paged one cannot half-adopt (its own
parameters, or a plain list).
"""
import typing

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.pagination import MAX_LIMIT, Page, PageParams, page_of_list, page_of_query
from main import app

#: Lists whose length grows with use (ADR-185 point 1).
PAGED = {
    "/approvals/",
    "/delivery/send-instances",
    "/campaigns/",
    "/content/",
    "/api/audience-groups/",
    "/campaigns/monitoring",
}

#: Lists fixed by code or configuration, or bounded by one parent record
#: small by construction — returned whole (ADR-185 point 1).
FIXED = {
    "/content/categories",
    "/content/categories/{category_id}/children",
    "/content/categories/{category_id}/parents",
    "/content/category-relations",
    "/content/fields",
    "/content/{content_id}/assignments",
    "/content/{content_id}/categories",
    "/content/{content_id}/duplicate-targets",
    "/content/{content_record_id}/versions",
    "/decision/strategies",
    "/modules",
    "/integrations",
    "/campaigns/{campaign_id}/variants",
    "/campaigns/variants/{variant_id}/modules",
    "/campaigns/variants/{variant_id}/decision-slots",
    "/campaigns/variants/{variant_id}/suggestions",
    "/api/audience-groups/{group_id}/blocks",
    "/snapshots/variants/{variant_id}",
    "/recipients/{recipient_id}/preferences",
    "/delivery/snapshots/{snapshot_id}/send-instances",
}

#: Lists that grow with use and are adopted in the next step of task-88.
#: **This set must be empty when task-88 closes.**
NOT_YET = {
    "/recipients/",
    "/api/audience-groups/{group_id}/members",
    "/campaigns/decision-slots",
    "/campaigns/decision-slots/{decision_slot_id}/resolutions",
    "/delivery/send-instances/{send_instance_id}/executions",
    "/insight/delivery-executions/{delivery_execution_id}/events",
    "/overrides/",
    "/provider/quarantine",
    "/recipients/consent/sync-log",
    "/recipients/consent/drift",
}


def _get_routes():
    for route in app.routes:
        if isinstance(route, APIRoute) and "GET" in route.methods and route.include_in_schema:
            yield route


def _is_page(model) -> bool:
    return isinstance(model, type) and issubclass(model, Page)


def test_every_list_route_is_classified():
    lists = {r.path for r in _get_routes()
             if typing.get_origin(r.response_model) is list or _is_page(r.response_model)}
    unclassified = lists - PAGED - FIXED - NOT_YET
    assert not unclassified, (
        f"classify these under ADR-185 point 1 (paged if they grow with use): {sorted(unclassified)}"
    )
    assert not (PAGED & FIXED), "a route cannot be both"


def test_every_paged_route_uses_the_one_envelope_and_the_shared_parameters():
    routes = {r.path: r for r in _get_routes()}
    for path in PAGED:
        route = routes[path]
        assert _is_page(route.response_model), f"{path} does not return the envelope"
        params = {p.name for p in route.dependant.query_params}
        sub = {p.name for d in route.dependant.dependencies for p in d.query_params}
        assert {"limit", "offset"} <= params | sub, f"{path} has no shared paging parameters"


def test_no_fixed_route_returns_the_envelope():
    routes = {r.path: r for r in _get_routes()}
    for path in FIXED & set(routes):
        assert not _is_page(routes[path].response_model), f"{path} is fixed but paged"


# --- the mechanism ----------------------------------------------------------

def test_a_page_of_a_list_says_its_total():
    page = page_of_list(range(7), PageParams(limit=3, offset=3))
    assert (page.items, page.total, page.limit, page.offset) == ([3, 4, 5], 7, 3, 3)
    assert page_of_list(range(7), PageParams(limit=3, offset=9)).items == []


def test_a_page_of_a_query_counts_the_filtered_set_and_pages_do_not_overlap():
    """Against a real table: the campaigns the suite's seed created."""
    from app.campaigns.db_models import CampaignDB
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        query = db.query(CampaignDB).filter(CampaignDB.name.like("Demo Campaign%"))
        expected = query.count()
        assert expected >= 3, "the seed's campaigns are missing"
        order = (CampaignDB.created_at.desc(), CampaignDB.id.desc())
        first = page_of_query(query, PageParams(limit=2, offset=0), *order)
        rest = page_of_query(query, PageParams(limit=MAX_LIMIT, offset=2), *order)
        assert first.total == rest.total == expected, "the total ignored the filter"
        ids = [c.id for c in first.items] + [c.id for c in rest.items]
        assert len(ids) == len(set(ids)) == expected, "pages overlapped or skipped"
    finally:
        db.close()


@pytest.mark.parametrize("path", sorted(PAGED))
def test_over_json_each_paged_route_answers_with_the_envelope(path):
    from app.auth.permissions import VIEW
    from tests.machine import machine

    client = TestClient(app, raise_server_exceptions=False)
    with machine([VIEW]) as headers:
        response = client.get(path, params={"limit": 1}, headers=headers)
        too_many = client.get(path, params={"limit": MAX_LIMIT + 1}, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"items", "total", "limit", "offset"}
    assert body["limit"] == 1 and len(body["items"]) <= 1 and body["total"] >= len(body["items"])
    assert too_many.status_code == 422, "the page size has a ceiling"
