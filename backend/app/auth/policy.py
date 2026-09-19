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
    INSIGHT_WRITE, INTEGRATIONS_MANAGE, OVERRIDES_MANAGE,
    RECIPIENTS_CONSENT, RECIPIENTS_MANAGE,
    SENDS_EXECUTE, SENDS_PLAN, SETTINGS_MANAGE, USERS_MANAGE, VIEW,
)

WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Returned when a write route matches nothing. Not a real permission — no role
# can hold it — so the effect is a refusal that names itself in the log.
UNMAPPED = "unmapped.write"

# Returned for a route authenticated by a PROVIDER SIGNATURE rather than by a
# credential this platform issued (ADR-166 point 6). Also not a permission: no
# principal can hold it, and the guard reads it as "not mine to judge" and
# stands aside so the route's own signature check runs.
#
# **Two inbound mechanisms coexist deliberately.** Platform-issued credentials
# authenticate systems the adopter controls; signature verification
# authenticates send providers, who cannot hold a credential this platform
# issued and will not be asked to. Neither is a degraded version of the other.
#
# Listing the exemption here rather than skipping the guard at the wiring is
# the point: the table is meant to read as *the* policy, and an exemption that
# lives in `main.py` is an exemption nobody auditing this file would find.
PROVIDER_SIGNED = "provider.signed"

# Returned for a route that is deliberately UNAUTHENTICATED because it is how
# authentication begins. You cannot require a session in order to obtain one.
#
# A second sentinel rather than reusing `PROVIDER_SIGNED`, because the two are
# exempt for unrelated reasons and a single list would say they are the same
# kind of thing: one is a caller this platform cannot issue a credential to,
# the other is the door every credential comes through. A test asserts each
# list exactly, so widening either is an edit somebody has to justify —
# which is what caught this being conflated in the first place.
PUBLIC_AUTH = "auth.public"

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
    # **The approval inbox is guarded twice, and the weaker guard is here.**
    # Seeing that a send is waiting is operational visibility rather than a
    # secret, so the screen itself needs only `view`. Deciding is answered per
    # row, against the permission the ACTION declares — this table matches on a
    # route template and has no way to express "it depends which row you
    # clicked".
    #
    # That is deliberate rather than a shortfall: two actions in one inbox
    # legitimately need different permissions (a machine send wants
    # `sends.execute`; applying an AI suggestion will want `campaigns.manage`),
    # so a single route-level entry would have to be the *union* of every
    # action's requirement — the widest grant rather than the right one.
    #
    # The real gate is `_may_decide` in `app/frontend/router.py`, and it has its
    # own test. Same shape as the /ui/users and /ui/roles entries below: an
    # entry that documents rather than enforces, said out loud.
    ("/ui/approvals", VIEW),

    # Issuing a machine credential is its own grant, not a fold into
    # `credentials.manage` — ADR-152 scopes that key to credentials the
    # platform HOLDS, and these are ones it ISSUES (ADR-166 point 4).
    ("/ui/integrations", INTEGRATIONS_MANAGE),
    ("/ui/settings", SETTINGS_MANAGE),
    ("/ui/users", USERS_MANAGE),
    ("/ui/roles", USERS_MANAGE),

    # === the JSON API (ADR-166) ===========================================
    # Until 2026-09-18 these 36 write routes had no guard at all, while the UI
    # above them was locked — the state ADR-166's Context calls worse than
    # either alone, "because it looks protected".
    #
    # Same rule as the UI half: first match wins, narrow above broad, and an
    # unlisted write is refused. Nothing here is a new capability; each entry
    # names the permission the equivalent UI act already required.

    # **The JSON session surface is public, like the sign-in form it mirrors —
    # you cannot require a session in order to obtain one.** This entry is
    # DOCUMENTATION rather than enforcement, the same way the /ui/users and
    # /ui/roles entries below are: `session_router` is wired with the CSRF
    # guard alone and never reaches `required_permission`. It is written here
    # because this table is meant to read as *the* policy, and a public
    # authentication surface that appears nowhere in it would look like an
    # omission rather than a decision. Those routes defend themselves the way
    # the form routes do — a throttle before the lookup, one unconditional
    # answer, and a code burned on use (ADR-151 §2).
    ("/auth/session", PUBLIC_AUTH),

    # A provider signs its own callbacks. Above /provider so it wins.
    ("/provider/webhooks/", PROVIDER_SIGNED),
    # ADR-150 point 5: gated by `insight.write` rather than an `events.ingest`
    # key of its own, because ingesting a provider event and posting an insight
    # event both end in an engagement row feeding the signal layer. One key
    # names the capability that matters rather than two naming the doors.
    ("/provider/events", INSIGHT_WRITE),
    ("/insight/", INSIGHT_WRITE),

    # Recipients. `recipients.consent` sits above `recipients.manage` so that
    # an integration which only imports contact records cannot also assert
    # consent for them (ADR-150 point 5, ADR-142 §7's hard floor).
    ("/recipients/{external_id}/consent", RECIPIENTS_CONSENT),
    ("/recipients/", RECIPIENTS_MANAGE),

    # Sending: preparing is not firing, the same split as the UI half.
    ("/delivery/send-instances/{send_instance_id}/send", SENDS_EXECUTE),
    # Fires every scheduled send that is due, so people receive mail because
    # of it. **Added above the broad prefix on 2026-09-19 after landing below
    # it** — `/delivery/process-due` matched `("/delivery/", SENDS_PLAN)` and
    # was silently downgraded to the permission that only PREPARES a send.
    # That is the exact hazard the 2026-09-18 review logged about this table:
    # order is semantics and nothing enforces it. Found by printing the
    # resolved permission rather than by a failing test, which is the point of
    # the logged item.
    ("/delivery/process-due", SENDS_EXECUTE),
    ("/delivery/", SENDS_PLAN),
    ("/snapshots/", SENDS_PLAN),

    # Audience: pinning one member is not restructuring the group.
    ("/api/audience-groups/{group_id}/members", AUDIENCES_PIN),
    ("/api/audience-groups", AUDIENCES_MANAGE),

    ("/overrides/", OVERRIDES_MANAGE),
    ("/content/", CONTENT_MANAGE),
    ("/campaigns/", CAMPAIGNS_MANAGE),
    ("/decision/", CAMPAIGNS_MANAGE),
)


#: Which held action a refused route turns into (ADR-166 point 5, ADR-142 §4).
#:
#: Here rather than in `main.py` for this file's own stated reason: the policy
#: has to be legible in one place, and "what happens when this route is refused
#: for approval" is part of the policy. A mapping hiding in the wiring is one
#: nobody auditing access control would find.
#:
#: **Fail-closed by omission.** A route with no entry cannot be queued, so it is
#: refused outright — the behaviour every send had before the approval surface
#: existed. Adding a route here is what grants it a queue.
APPROVABLE_ROUTES: dict[str, str] = {
    "/delivery/send-instances/{send_instance_id}/send": "send.fire_send_instance",
}


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
