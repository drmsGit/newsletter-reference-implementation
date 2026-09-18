"""Which permission each route requires — one readable table, not 57 decorators.

Two properties this shape buys that per-route decorators do not:

  **The policy is legible.** Somebody auditing "who can trigger a send" reads
  one table instead of grepping every router. For a reference architecture
  that has to be explainable, that matters more than the microscopic
  convenience of a decorator.

  **Unmapped writes are denied.** The failure mode of per-route guards is the
  route somebody forgot, and it fails *open* — the new endpoint silently has no
  protection. Here a write nobody classified is refused, so forgetting is loud
  and safe rather than quiet and dangerous.

Matching is on the **route template** FastAPI resolved (`/ui/campaigns/{id}/…`),
not the request URL. Path parameters are therefore literal text, so an id can
never be mistaken for a path segment and the table needs no regular
expressions.

Order is specificity: first match wins, so the narrow cases sit above the broad
ones they live inside.
"""

from app.auth.permissions import (
    AI_RUN, AUDIENCES_MANAGE, AUDIENCES_PIN, CAMPAIGNS_MANAGE, CONTENT_MANAGE,
    OVERRIDES_MANAGE, SENDS_EXECUTE, SENDS_PLAN, SETTINGS_MANAGE, USERS_MANAGE,
    VIEW,
)

WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Returned when a write route matches nothing. Not a real permission — no role
# can hold it — so the effect is a refusal that names itself in the log.
UNMAPPED = "unmapped.write"

WRITE_POLICY: tuple[tuple[str, str], ...] = (
    # --- the working context -------------------------------------------------
    # Switching brand is not a capability, it is navigation: the route refuses
    # any brand the user holds no grant on, so `view` (implied by every role)
    # is the honest requirement rather than inventing a permission for it.
    ("/ui/brand", VIEW),

    # --- narrow cases that live inside broader prefixes ---------------------
    # Spends real money, so it is gated on AI rather than on owning the campaign.
    ("/ui/campaigns/{campaign_id}/variants/{variant_id}/suggest-subject", AI_RUN),
    # Creates an audience group; it is filed under campaigns only by URL.
    ("/ui/campaigns/{campaign_id}/suggest-audience", AUDIENCES_MANAGE),
    # Overriding a system pick is its own act, not a campaign edit (ADR-166
    # point 2). These sat under `campaigns.manage`, which also means "restructure
    # the composition" — and the override layer (ADR-040/041) exists precisely to
    # keep correcting a pick distinct from rebuilding the thing it sits in.
    ("/ui/campaigns/{campaign_id}/variants/{variant_id}/overrides", OVERRIDES_MANAGE),
    ("/ui/campaigns/{campaign_id}/overrides", OVERRIDES_MANAGE),

    # --- sending: preparing is not firing -----------------------------------
    # ADR-166 point 2 splits `sends.execute`. The line is "does a person receive
    # something because of this request": snapshotting and creating a send
    # instance do not reach anybody, and dispatching does. Both entries below
    # are ordered narrow-above-broad, so the one route that actually sends is
    # matched before the prefix that covers preparing it.
    ("/ui/campaigns/{campaign_id}/snapshots/", SENDS_PLAN),
    ("/ui/send-instances/{send_instance_id}/send", SENDS_EXECUTE),
    ("/ui/send-instances/", SENDS_PLAN),
    ("/ui/deliveries/process-due", SENDS_EXECUTE),
    ("/ui/send-test", SENDS_EXECUTE),

    # --- editorial and audience --------------------------------------------
    # Adding or removing one member is `audiences.pin`; changing the rules that
    # decide membership is `audiences.manage`. ADR-166 point 2's worked example
    # is exactly this: a website form may pin a recipient and must not be able
    # to restructure the audience it pins into.
    ("/ui/audience-groups/{group_id}/members", AUDIENCES_PIN),
    ("/ui/audience-groups", AUDIENCES_MANAGE),
    ("/ui/content", CONTENT_MANAGE),
    ("/ui/categories", CONTENT_MANAGE),
    ("/ui/campaigns", CAMPAIGNS_MANAGE),
    ("/ui/decisions/", CAMPAIGNS_MANAGE),

    # --- administration ------------------------------------------------------
    # /ui/users and /ui/roles live in auth_router and carry their own explicit
    # guards, so these entries are documentation rather than enforcement — the
    # table is meant to be readable as *the* policy, and omitting them would
    # make it look as though nothing protects them.
    ("/ui/settings", SETTINGS_MANAGE),
    ("/ui/users", USERS_MANAGE),
    ("/ui/roles", USERS_MANAGE),
)


def required_permission(method: str, route_template: str) -> str:
    """The permission this request needs.

    Reads are `view`; writes consult the table; an unclassified write is
    refused. Returning a sentinel rather than None keeps the caller from having
    to decide what "no policy" means — there is only one safe answer.
    """
    if (method or "").upper() not in WRITE_METHODS:
        return VIEW

    for prefix, permission in WRITE_POLICY:
        if (route_template or "").startswith(prefix):
            return permission

    return UNMAPPED
