"""Tests for the route→permission policy (ADR-150).

The most valuable test here is the last one: every write route in the UI must
have a policy entry. Without it, adding an endpoint and forgetting the policy
is caught at runtime by a refusal — safe, but discovered by a confused user.
With it, it is caught in CI.
"""
import re
from pathlib import Path

from app.auth.permissions import (
    AI_RUN, AUDIENCES_MANAGE, CAMPAIGNS_MANAGE, CONTENT_MANAGE,
    SENDS_EXECUTE, SETTINGS_MANAGE, USERS_MANAGE, VIEW,
)
from app.auth.policy import UNMAPPED, required_permission


class TestReads:

    def test_reads_need_only_view(self):
        assert required_permission("GET", "/ui/settings") == VIEW
        assert required_permission("GET", "/ui/campaigns/{campaign_id}") == VIEW
        assert required_permission("HEAD", "/ui/content") == VIEW


class TestWrites:

    def test_editorial_and_audience_writes(self):
        assert required_permission("POST", "/ui/content") == CONTENT_MANAGE
        assert required_permission("POST", "/ui/categories/relations") == CONTENT_MANAGE
        assert required_permission("POST", "/ui/audience-groups") == AUDIENCES_MANAGE
        assert required_permission("POST", "/ui/campaigns") == CAMPAIGNS_MANAGE

    def test_administration_writes(self):
        assert required_permission("POST", "/ui/settings/ai") == SETTINGS_MANAGE
        assert required_permission("POST", "/ui/users") == USERS_MANAGE

    def test_anything_that_reaches_real_people_needs_sends_execute(self):
        for route in (
            "/ui/send-test",
            "/ui/deliveries/process-due",
            "/ui/send-instances/{send_instance_id}/send",
            "/ui/campaigns/{campaign_id}/snapshots/{snapshot_id}/send-instances",
        ):
            assert required_permission("POST", route) == SENDS_EXECUTE, route


class TestSpecificityOrdering:
    """The narrow cases must win over the broad prefixes they sit inside."""

    def test_suggest_subject_is_an_ai_action_not_a_campaign_edit(self):
        # It spends real money, so owning the campaign is not enough.
        route = "/ui/campaigns/{campaign_id}/variants/{variant_id}/suggest-subject"
        assert required_permission("POST", route) == AI_RUN

    def test_planning_a_send_is_a_send_action(self):
        route = "/ui/campaigns/{campaign_id}/snapshots/{snapshot_id}/send-instances"
        assert required_permission("POST", route) == SENDS_EXECUTE

    def test_suggest_audience_is_an_audience_action(self):
        # Filed under /ui/campaigns by URL only — it creates an audience group.
        route = "/ui/campaigns/{campaign_id}/suggest-audience"
        assert required_permission("POST", route) == AUDIENCES_MANAGE

    def test_ordinary_campaign_writes_still_fall_through_to_campaigns(self):
        route = "/ui/campaigns/{campaign_id}/variants/{variant_id}/modules"
        assert required_permission("POST", route) == CAMPAIGNS_MANAGE


class TestFailsClosed:

    def test_an_unclassified_write_is_refused(self):
        # The whole point: forgetting a policy entry must deny, not allow.
        assert required_permission("POST", "/ui/something-brand-new") == UNMAPPED
        assert required_permission("DELETE", "/ui/nope") == UNMAPPED

    def test_unmapped_is_not_a_real_permission(self):
        # No role can hold it, so the sentinel cannot accidentally grant.
        from app.auth.permissions import ALL_PERMISSIONS
        assert UNMAPPED not in ALL_PERMISSIONS

    def test_every_ui_write_route_has_a_policy_entry(self):
        """Catch an unguarded new endpoint in CI, not in production."""
        src = Path("app/frontend/router.py").read_text()
        routes = sorted(set(
            re.findall(r'@router\.(post|put|patch|delete)\("([^"]+)"', src)
        ))
        assert routes, "no write routes found — has the router moved?"

        unmapped = [
            f"{method.upper()} {path}"
            for method, path in routes
            if required_permission(method, path) == UNMAPPED
        ]
        assert not unmapped, (
            "write routes with no entry in app/auth/policy.py:\n  "
            + "\n  ".join(unmapped)
        )
