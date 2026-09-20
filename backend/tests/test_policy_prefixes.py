"""The policy table matches by prefix, and a prefix can cut into a segment.

`app/auth/policy.py` resolves a route's required permission by walking
`WRITE_POLICY` and taking the first entry the route template starts with. That
is a **string** `startswith`, not a path-segment comparison, so `/app` matches
`/approvals` and `/ui/brand` matches `/ui/brands`.

**This failure is invisible by construction.** The route still works, the caller
is still authorised, and the permission asked for is simply the wrong one. Only
reading the table in the right order reveals it, and this repository has caught
it by reading three times:

  * `/delivery/process-due` resolved to `sends.plan` (2026-09-19)
  * `/campaigns/.../suggest-subject` resolved to `campaigns.manage` (2026-09-20)
  * `/delivery/send-test` would have resolved to `sends.plan` (2026-09-20)

`test_api_guard.py` pins the send routes specifically, which catches those three
and nothing else. This file asserts the **shape** instead, so the fourth is an
edit somebody has to justify rather than a defect somebody has to notice.

Written 2026-09-20, prompted by mounting the React client. `/app` was the
obvious URL for it and is a `startswith` prefix of `/approvals` -- so a single
line added to this table would have repriced every approvals route, including
approve and reject. The client is mounted at `/manager` instead, and this test
is why the next such choice does not depend on somebody remembering.
"""

from main import app
from app.auth.policy import WRITE_POLICY


def _cuts_into(prefix: str, template: str) -> bool:
    """True when `prefix` matches `template` part-way through a path segment.

    `/ui/` against `/ui/content` is fine -- the prefix ends at a boundary.
    `/ui/brand` against `/ui/brands` is not: it matches four characters into
    the segment, so it claims a route that is not below it.
    """
    if prefix == template or not template.startswith(prefix):
        return False
    if prefix.endswith("/"):
        return False
    return not template[len(prefix) :].startswith("/")


def _first_match(prefixes, template):
    """The entry `required_permission` would pick: first match wins."""
    for prefix in prefixes:
        if template.startswith(prefix):
            return prefix
    return None


class TestNoPolicyPrefixCutsIntoASegment:
    """**Order-aware, because ordering is how this table expresses precedence.**

    The narrow-above-broad idiom is used throughout and is correct: `/delivery/
    send-test` sits above `/delivery/` on purpose. So a mid-segment prefix is
    only a defect when it actually *wins* -- which is what these assert, rather
    than flagging every pair that could be reordered into a defect.
    """

    def test_no_earlier_entry_cuts_into_a_later_one(self):
        prefixes = [entry[0] for entry in WRITE_POLICY]

        bad = [
            (earlier, later)
            for i, earlier in enumerate(prefixes)
            for later in prefixes[i + 1 :]
            if _cuts_into(earlier, later)
        ]

        assert not bad, (
            f"these WRITE_POLICY entries are matched part-way through a path "
            f"segment by an entry listed ABOVE them: {bad}. The earlier one "
            "wins, so the later one never applies and its routes are priced "
            "with the wrong permission. Move the narrower entry up, or give "
            "the broader one a trailing slash."
        )

    def test_every_route_resolves_to_an_entry_that_ends_at_a_boundary(self):
        """The half that catches a new mount path.

        An entry can cut into a route template that has no entry of its own, so
        the table-versus-table check above sees nothing. This resolves each
        registered route the way the guard does and checks what actually won.
        """
        prefixes = [entry[0] for entry in WRITE_POLICY]
        templates = sorted(
            {route.path for route in app.routes if getattr(route, "path", "/") != "/"}
        )

        bad = [
            (template, winner)
            for template in templates
            if (winner := _first_match(prefixes, template)) and _cuts_into(winner, template)
        ]

        assert not bad, (
            f"these routes resolve to a WRITE_POLICY entry that matches them "
            f"part-way through a path segment: {bad}. The route works and the "
            "permission asked for is the wrong one, which is the failure this "
            "file exists to make loud."
        )


class TestTheCheckItselfCatchesTheCaseItWasWrittenFor:
    """**Mutation-proofing.** A test that cannot fail is worse than no test,
    because it reports a property nobody is checking. These assert the predicate
    reacts to the exact shapes that produced the real defects."""

    def test_it_catches_app_against_approvals(self):
        assert _cuts_into("/app", "/approvals/{pending_id}/approve")

    def test_it_catches_the_known_brand_collision(self):
        # `("/ui/brand", VIEW)` is in the table and `/ui/brands` is safe today
        # only because brand CRUD lives in `auth_router`, which carries no
        # policy guard. If those routes ever move, this shape is waiting.
        assert _cuts_into("/ui/brand", "/ui/brands")

    def test_it_allows_a_prefix_that_ends_at_a_boundary(self):
        assert not _cuts_into("/delivery/", "/delivery/send-test")
        assert not _cuts_into("/campaigns", "/campaigns/{campaign_id}")
