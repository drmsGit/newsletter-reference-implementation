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
    # The JSON twin (gap C1, 2026-09-20). Same reasoning: switching is
    # navigation, not a capability — `set_session_brand` refuses any brand the
    # user holds no grant on, so `view` is the honest requirement.
    ("/auth/session/brand", VIEW),

    # --- narrow cases that live inside broader prefixes ---------------------
    # Spends real money, so it is gated on AI rather than on owning the campaign.
    ("/ui/campaigns/{campaign_id}/variants/{variant_id}/suggest-subject", AI_RUN),
    # The JSON twin, and it needs its own line for the same reason: the broad
    # `/campaigns` entry below would resolve it to `campaigns.manage`, which is
    # "may restructure a campaign" and not "may spend money on the model".
    #
    # This is the second time that shape has been caught. `/delivery/process-due`
    # resolved to `sends.plan` through the broad `/delivery/` prefix on
    # 2026-09-19, hours after the ordering hazard was logged. Order is semantics
    # in this table and nothing enforces it — a narrow entry that drifts below
    # its prefix is silently downgraded, and the test below pins this pair.
    ("/campaigns/variants/{variant_id}/suggest-subject", AI_RUN),
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
    # The JSON twin, and it needs its own line **above** the broad `/delivery`
    # entry, which would price it as `sends.plan` — "may prepare a send" rather
    # than "may put mail in front of a person". A test send reaches a real
    # inbox through a real provider; that it goes to one address the operator
    # typed rather than to an audience makes it smaller, not different.
    #
    # **Third time.** `/delivery/process-due` resolved to `sends.plan` on
    # 2026-09-19 and `/campaigns/…/suggest-subject` to `campaigns.manage` on
    # 2026-09-20, both through a broad prefix sitting above a narrow route.
    # `test_every_route_that_mails_a_person_is_priced_as_such` now asserts the
    # set exactly, so a fourth is an edit somebody has to justify rather than
    # a silent downgrade.
    ("/delivery/send-test", SENDS_EXECUTE),

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
    # The real gate is `approvals.service.may_decide`, which both planes call —
    # it moved out of `app/frontend/router.py` on 2026-09-20 when the JSON
    # plane needed the same answer. It has its own test. Same shape as the
    # /ui/users and /ui/roles entries below: an entry that documents rather
    # than enforces, said out loud.
    ("/ui/approvals", VIEW),
    # The JSON twin, and the same reasoning applies to it unchanged.
    #
    # **What this entry does NOT express is that a machine may not approve at
    # all.** That is `require_person` on the two decision routes, because it is
    # not a permission question — a credential holding every grant there is is
    # still refused. Putting it in this table would say the opposite: that
    # some permission could unlock it.
    ("/approvals", VIEW),

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


#: **Which of the twelve JSON routers own brand-scoped rows** (ADR-172).
#:
#: Not enforcement — nothing reads this at request time. It is the answer to
#: the hazard [[ADR-168]]'s `### Negative` names: "a guard added to eleven of
#: twelve routers fails identically and reports identically: a gate that reads
#: as closed over a plane that is open." A rollout across twelve routers has
#: exactly that shape while it is in progress, and the only thing that
#: distinguishes "not done yet" from "decided not to" is a list that names
#: every router, including the ones the rule does not apply to and why.
#:
#: Here rather than in `main.py` for this file's own stated reason: the policy
#: has to be legible in one place, and a classification hiding in the wiring is
#: one nobody auditing access control would find.
#:
#: The values are deliberately prose rather than an enum. "Partial" is the
#: interesting state and an enum would flatten *why* — which is the only part
#: worth reading.
BRAND_OWNED: dict[str, str] = {
    "/campaigns": (
        "yes — `campaigns.brand_id`. Variants, modules, decision slots and "
        "resolutions carry none and are reached by joining back to it."
    ),
    "/content": (
        "partial — `content_records.brand_id`, but `/categories` and "
        "`/category-relations` are the global vocabulary ADR-150's 2026-09-15 "
        "addendum settles as unbranded. Content is per-brand; what a category "
        "MEANS is not."
    ),
    "/api/audience-groups": (
        "yes — `audience_groups.brand_id`. Members and rule blocks join back "
        "to it. Note the group's brand gates consent at resolution time, not "
        "the caller's (ADR-163's addendum)."
    ),
    "/delivery": (
        "yes — `send_instances.brand_id`, NOT NULL since migration 0007. The "
        "predicate lives INSIDE `send_send_instance`'s `FOR UPDATE`, because "
        "checking it separately is a check-then-act window on the one query "
        "where that matters most."
    ),
    "/snapshots": (
        "yes — transitively, `snapshot -> variant -> campaign`. No column."
    ),
    "/rendering": (
        "yes — `variant -> campaign`. The service takes the brand optionally "
        "and the route passes `Depends(working_brand)`, so the request path "
        "cannot forget while the send path does not re-derive what it holds."
    ),
    "/overrides": (
        "yes — the longest chain in the codebase, `override -> module -> "
        "variant -> campaign`. Scoped by subquery rather than join, because "
        "both lookups take `FOR UPDATE` and a join would lock campaign rows."
    ),
    "/decision": (
        "partial — `/slots/{id}/execute` is brand-owned via the slot's "
        "variant; `/strategies` lists a code-level registry and is not. What "
        "strategies EXIST is a property of the deployment, not of a brand."
    ),
    "/insight": (
        "partial — reading a delivery execution's events is brand-owned via "
        "its send instance. Writing events feeds signal contributions, which "
        "carry no brand by ADR-150 point 8, because a recipient does not "
        "either (point 9)."
    ),
    "/recipients": (
        "partial, and the unresolved one. Recipients carry no brand (ADR-150 "
        "point 9), so most of this router is genuinely platform-level. But "
        "`POST /{external_id}/consent` writes `consent_events.brand_id` and "
        "takes that brand FROM THE REQUEST BODY, while `recipients.consent` is "
        "platform-level and so is checked against no brand at all. That is the "
        "shape ADR-166 point 8 refuses. Logged in `docs/backlog.md`; the fix "
        "is a decision about whether consent capture is a brand-scoped act, "
        "not an edit."
    ),
    "/provider": (
        "no — provider configuration and signed callbacks. A webhook arrives "
        "from a vendor with no notion of brands, and is exempt from the guard "
        "entirely via `PROVIDER_SIGNED`."
    ),
    "/approvals": (
        "yes — `pending_actions.brand_id`, set to the brand the request was "
        "authorised in. The inbox filters on it and `may_decide` checks the "
        "action's permission against the ROW's brand, not the reader's, which "
        "is what stays correct if an inbox ever spans more than one."
    ),
    "/auth": (
        "no, and it is the interesting 'no'. These two routes are ABOUT brands "
        "— `GET /auth/session` reports the working one and `POST "
        "/auth/session/brand` changes it — but the rows they touch are "
        "sessions and role assignments, which are platform-level. The brand "
        "here is the session's working CONTEXT, which is the thing ADR-172 "
        "point 1 separated from authorisation. A route that sets the context "
        "cannot itself be scoped by it."
    ),
    "/modules": (
        "no — module manifests read from disk. They describe what the "
        "deployment can compose, which is the same for every brand."
    ),
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
