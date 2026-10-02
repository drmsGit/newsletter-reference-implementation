"""The Jinja UI is frozen: it gets no new routes (task-50, ADR-170).

[[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]] gives the
server-rendered UI a deletion date, and task-50 asked for it to be frozen for
new features the day the migration audit was done. Nothing enforced that, so
the freeze held only as long as everyone remembered it — and every route added
here is one more rule the SPA migration has to find and move.

**What this pins:** the exact `(method, path)` set of every route under `/ui`
and everything defined in `app/frontend/router.py`, across whichever router
declares it (`app/auth/router.py` serves `/ui/login`, `/ui/users`, `/ui/roles`).

  - A route that is not in `FROZEN` fails: build it on the JSON API instead,
    which is where the SPA will look for it.
  - A route in `FROZEN` that no longer exists fails too, so the list shrinks
    as the Jinja UI is retired and can never quietly re-admit a path.

**What it does not catch,** by the choice made on 2026-10-02: logic added
inside a route that already exists. That stays a review question.

If a new Jinja route is genuinely needed — a fix that cannot wait for the SPA —
add it here in the same commit and say why in the message. The edit is meant
to be visible, not impossible.
"""
from fastapi.routing import APIRoute

from main import app

FROZEN = {
    ("GET", "/"),
    ("GET", "/ui/approvals"),
    ("GET", "/ui/approvals/{pending_id}"),
    ("GET", "/ui/audience-groups"),
    ("GET", "/ui/audience-groups/{group_id}"),
    ("GET", "/ui/audience-groups/{group_id}/criteria-preview"),
    ("GET", "/ui/campaigns"),
    ("GET", "/ui/campaigns/{campaign_id}"),
    ("GET", "/ui/campaigns/{campaign_id}/duplicate"),
    ("GET", "/ui/campaigns/{campaign_id}/variants/{variant_id}/suggestions"),
    ("GET", "/ui/categories"),
    ("GET", "/ui/categories/{category_id}"),
    ("GET", "/ui/content"),
    ("GET", "/ui/content/{content_record_id}"),
    ("GET", "/ui/decisions"),
    ("GET", "/ui/decisions/slots/{decision_slot_id}"),
    ("GET", "/ui/deliveries"),
    ("GET", "/ui/deliveries/send-instances/{send_instance_id}"),
    ("GET", "/ui/graph"),
    ("GET", "/ui/integrations"),
    ("GET", "/ui/login"),
    ("GET", "/ui/login/verify"),
    ("GET", "/ui/recipients"),
    ("GET", "/ui/recipients/{recipient_id}"),
    ("GET", "/ui/roles"),
    ("GET", "/ui/send-test"),
    ("GET", "/ui/settings"),
    ("GET", "/ui/users"),
    ("POST", "/ui/approvals/process-expired"),
    ("POST", "/ui/approvals/{pending_id}/approve"),
    ("POST", "/ui/approvals/{pending_id}/reject"),
    ("POST", "/ui/audience-groups"),
    ("POST", "/ui/audience-groups/{group_id}/blocks"),
    ("POST", "/ui/audience-groups/{group_id}/blocks/{block_id}/delete"),
    ("POST", "/ui/audience-groups/{group_id}/blocks/{block_id}/edit"),
    ("POST", "/ui/audience-groups/{group_id}/bulk-add"),
    ("POST", "/ui/audience-groups/{group_id}/delete"),
    ("POST", "/ui/audience-groups/{group_id}/edit"),
    ("POST", "/ui/audience-groups/{group_id}/members"),
    ("POST", "/ui/audience-groups/{group_id}/members/{recipient_id}/remove"),
    ("POST", "/ui/audience-groups/{group_id}/recalculate"),
    ("POST", "/ui/brand"),
    ("POST", "/ui/brands"),
    ("POST", "/ui/brands/{brand_id}/delete"),
    ("POST", "/ui/brands/{brand_id}/rename"),
    ("POST", "/ui/campaigns"),
    ("POST", "/ui/campaigns/{campaign_id}/duplicate"),
    ("POST", "/ui/campaigns/{campaign_id}/overrides/{override_id}/reset"),
    ("POST", "/ui/campaigns/{campaign_id}/snapshots/{snapshot_id}/send-instances"),
    ("POST", "/ui/campaigns/{campaign_id}/suggest-audience"),
    ("POST", "/ui/campaigns/{campaign_id}/variants"),
    ("POST", "/ui/campaigns/{campaign_id}/variants/{variant_id}/apply-subject"),
    ("POST", "/ui/campaigns/{campaign_id}/variants/{variant_id}/decision-slots"),
    ("POST", "/ui/campaigns/{campaign_id}/variants/{variant_id}/edit"),
    ("POST", "/ui/campaigns/{campaign_id}/variants/{variant_id}/modules"),
    ("POST", "/ui/campaigns/{campaign_id}/variants/{variant_id}/modules/{module_id}/delete"),
    ("POST", "/ui/campaigns/{campaign_id}/variants/{variant_id}/modules/{module_id}/edit"),
    ("POST", "/ui/campaigns/{campaign_id}/variants/{variant_id}/modules/{module_id}/move"),
    ("POST", "/ui/campaigns/{campaign_id}/variants/{variant_id}/overrides"),
    ("POST", "/ui/campaigns/{campaign_id}/variants/{variant_id}/snapshots"),
    ("POST", "/ui/campaigns/{campaign_id}/variants/{variant_id}/suggest-subject"),
    ("POST", "/ui/categories"),
    ("POST", "/ui/categories/relations"),
    ("POST", "/ui/categories/{category_id}/delete"),
    ("POST", "/ui/categories/{category_id}/relations/{relation_id}/delete"),
    ("POST", "/ui/content"),
    ("POST", "/ui/content/{content_record_id}/assign-category"),
    ("POST", "/ui/content/{content_record_id}/categories/{assignment_id}/delete"),
    ("POST", "/ui/content/{content_record_id}/delete"),
    ("POST", "/ui/content/{content_record_id}/duplicate"),
    ("POST", "/ui/content/{content_record_id}/edit"),
    ("POST", "/ui/content/{content_record_id}/publish-version"),
    ("POST", "/ui/content/{content_record_id}/set-status"),
    ("POST", "/ui/decisions/slots/{slot_id}/edit"),
    ("POST", "/ui/deliveries/process-due"),
    ("POST", "/ui/integrations"),
    ("POST", "/ui/integrations/{integration_id}/deactivate"),
    ("POST", "/ui/integrations/{integration_id}/grants"),
    ("POST", "/ui/integrations/{integration_id}/grants/remove"),
    ("POST", "/ui/integrations/{integration_id}/keys"),
    ("POST", "/ui/integrations/{integration_id}/keys/{credential_id}/revoke"),
    ("POST", "/ui/integrations/{integration_id}/unattended"),
    ("POST", "/ui/login"),
    ("POST", "/ui/login/verify"),
    ("POST", "/ui/logout"),
    ("POST", "/ui/roles"),
    ("POST", "/ui/roles/{role_id}/delete"),
    ("POST", "/ui/roles/{role_id}/permissions"),
    ("POST", "/ui/send-instances/{send_instance_id}/send"),
    ("POST", "/ui/send-test"),
    ("POST", "/ui/settings"),
    ("POST", "/ui/settings/ai"),
    ("POST", "/ui/settings/ai-prompt"),
    ("POST", "/ui/settings/ai-provider"),
    ("POST", "/ui/settings/ai-task-approval"),
    ("POST", "/ui/settings/ai-task-model"),
    ("POST", "/ui/users"),
    ("POST", "/ui/users/assignments/{assignment_id}/remove"),
    ("POST", "/ui/users/enforcement"),
    ("POST", "/ui/users/{user_id}/active"),
    ("POST", "/ui/users/{user_id}/roles"),
}


def _jinja_routes() -> set[tuple[str, str]]:
    return {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        and (route.path.startswith("/ui") or route.endpoint.__module__ == "app.frontend.router")
        for method in route.methods
    }


def test_no_route_was_added_to_the_jinja_ui():
    added = sorted(_jinja_routes() - FROZEN)
    assert not added, (
        f"New Jinja route(s): {added}. The server-rendered UI is frozen "
        "(ADR-170, task-50): build this on the JSON API, where the SPA will "
        "look for it. If it truly cannot wait, add it to FROZEN in the same "
        "commit and say why."
    )


def test_every_frozen_route_still_exists():
    gone = sorted(FROZEN - _jinja_routes())
    assert not gone, (
        f"Retired Jinja route(s) still listed: {gone}. Remove them from FROZEN "
        "so the list only shrinks — a stale entry would let the path come back "
        "unnoticed."
    )


def test_the_guard_sees_both_routers():
    """Without this, a refactor that renamed the module or moved the prefix
    would empty `_jinja_routes()` on both sides and every test would pass."""
    modules = {
        route.endpoint.__module__
        for route in app.routes
        if isinstance(route, APIRoute) and (route.path.startswith("/ui"))
    }
    assert {"app.frontend.router", "app.auth.router"} <= modules, modules
