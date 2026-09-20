"""The permission vocabulary, and the three roles ADR-150 §5 ships as a preset.

The split matters: **permission keys are code, role composition is data.**
A permission names a code path, so inventing one requires writing the code it
guards. Which role holds which permission is a row, so a company can add
`campaign-approver` or drop Viewer entirely without touching Python — the same
convention-based-extension posture as the decision strategies and email module
templates.

Deliberately small. ADR-150 §5: we are not modelling the average company's org
chart, because companies mostly run everything as admin or arrive with a scheme
of their own, and copying an imagined average serves neither.
"""

# --- the vocabulary --------------------------------------------------------
VIEW = "view"                              # read-only access to the app
CAMPAIGNS_MANAGE = "campaigns.manage"      # campaigns, variants, modules
CONTENT_MANAGE = "content.manage"          # content records, categories
AUDIENCES_MANAGE = "audiences.manage"      # groups, rule blocks, pins
SENDS_EXECUTE = "sends.execute"            # plan and trigger a real send
AI_RUN = "ai.run"                          # spend tokens on an AI task
SETTINGS_MANAGE = "settings.manage"        # tunable config, budgets, prompts
USERS_MANAGE = "users.manage"              # invite, assign roles, deactivate
CREDENTIALS_MANAGE = "credentials.manage"  # provider and model credentials

# ADR-166 point 2 / ADR-150 point 5: nine keys became sixteen, because nine
# were too coarse for their own worked example — *n8n may trigger a send; a
# website form may only pin a recipient*. Pinning used to sit under
# `audiences.manage`, so granting a public form the right to add one recipient
# would also have granted it the right to restructure the audience.
#
# **The splits serve humans too**, which is why they live in the shared
# vocabulary rather than in a machine-only scope list: "may pin, may not
# restructure" and "may prepare a send, may not fire it" are both ordinary
# descriptions of a junior marketer.
AUDIENCES_PIN = "audiences.pin"            # add/remove one member, not the rules
SENDS_PLAN = "sends.plan"                  # prepare a send without dispatching
RECIPIENTS_MANAGE = "recipients.manage"    # create and edit recipients
RECIPIENTS_CONSENT = "recipients.consent"  # write a consent record
INSIGHT_WRITE = "insight.write"            # write engagement events
OVERRIDES_MANAGE = "overrides.manage"      # override a system content pick
INTEGRATIONS_MANAGE = "integrations.manage"  # issue/rotate/revoke machine keys

ALL_PERMISSIONS: dict[str, str] = {
    VIEW: "See dashboards, campaigns, signals and delivery history",
    CAMPAIGNS_MANAGE: "Create and edit campaigns, variants and modules",
    CONTENT_MANAGE: "Create and edit content records and categories",
    AUDIENCES_MANAGE: "Create and edit audience groups and rules",
    SENDS_EXECUTE: "Plan and trigger sends, including real ones",
    AI_RUN: "Run AI tasks, which spends against the token budget",
    SETTINGS_MANAGE: "Change tunable settings, budgets and AI prompts",
    USERS_MANAGE: "Invite users, assign roles, deactivate accounts",
    CREDENTIALS_MANAGE: "Set provider and model credentials (write-only)",
    AUDIENCES_PIN: "Add and remove individual audience members",
    SENDS_PLAN: "Prepare a send — snapshot and send instance — without firing it",
    RECIPIENTS_MANAGE: "Create and edit recipients",
    RECIPIENTS_CONSENT: "Record a consent decision for a recipient",
    INSIGHT_WRITE: "Write engagement events into the signal layer",
    OVERRIDES_MANAGE: "Override a system content pick, and reset one",
    INTEGRATIONS_MANAGE: "Issue, rotate and revoke machine credentials",
}

# `recipients.consent` is separate from `recipients.manage` deliberately
# (ADR-150 point 5): an integration that imports contact records must not
# thereby be able to assert consent for them. Consent is ADR-142 §7's hard
# floor and the record a UWG §7 complaint is answered with, so the ability to
# write one is its own grant and never a side effect of importing a contact.

# --- scope: which permissions are checked against a brand -------------------
# ADR-150, addendum 2026-09-15. **Scope is a property of the permission, not of
# the role**: a permission is brand-scoped if the rows it guards carry a
# `brand_id`, and platform-level otherwise.
#
# Saying it about the Admin role instead would hardcode a role name, and roles
# are rows a company may rename or delete. Said about permissions it falls out
# of the schema: recipients carry no brand (ADR-150 point 9) and signal
# contributions carry none (point 8), so anything guarding them is
# platform-level without anyone deciding it.
#
# The sharpest case is `users.manage`, which is platform-level for a reason
# worth remembering: scoping it per brand would be theatre, because an Admin on
# brand A can grant themselves Admin on brand B in two clicks. A control the
# controlled party can lift is not a control.
#
# `ai.run` is the one entry that breaks the rule's own logic — an AI task
# writes rows that DO carry a brand. What is actually protected is spend, and
# the budget is one company-wide pot. The standard package does not assume how
# a company would split or roll over a budget between brands.
BRAND_SCOPED: frozenset[str] = frozenset({
    CONTENT_MANAGE,
    CAMPAIGNS_MANAGE,
    AUDIENCES_MANAGE,
    SENDS_EXECUTE,
    # Built 2026-09-18; these were pre-classified here before their guards
    # existed, and now name real code paths in `policy.py`.
    AUDIENCES_PIN,
    SENDS_PLAN,
    OVERRIDES_MANAGE,
    # Moved here 2026-09-20 (ADR-150's addendum of that date). It was filed
    # platform-level because "recipients carry no brand" — true, and not the
    # question. The rows this permission guards are **consent events**, and
    # `consent_events.brand_id` became NOT NULL the same day the rule was
    # written. Eight and eight, not seven and nine.
    RECIPIENTS_CONSENT,
})

# Platform-level by omission, and each for a reason from ADR-150 point 5:
# recipients carry no brand (point 9) and neither do signal contributions
# (point 8), so `recipients.manage` and `insight.write` have no brand to be
# checked against. **`recipients.consent` used to be on this list and is not
# any more** — it guards consent events rather than recipients, and those have
# carried a brand since ADR-163's 2026-09-15 addendum. The justification was
# correct about recipients and wrong about which rows the permission guards. `integrations.manage` joins
# `users.manage` for the same reason that one is platform-level — scoping the
# power to mint credentials per brand would be theatre, since a holder could
# mint a credential granted on any brand they can already reach.


def is_brand_scoped(permission: str) -> bool:
    """Whether this permission is checked against the working brand.

    Unknown permissions answer False, which is deliberate but NOT a licence to
    fail open: an unmapped write route never reaches a permission check at all,
    it is refused as `UNMAPPED` by `policy.required_permission`. So the only
    callers here are permissions somebody classified.
    """
    return permission in BRAND_SCOPED


# --- the shipped preset ----------------------------------------------------
ADMIN = "admin"
MANAGER = "manager"
VIEWER = "viewer"

BUILTIN_ROLES: dict[str, dict] = {
    ADMIN: {
        "name": "Admin",
        "description": "Full access, including users, credentials and settings.",
        "permissions": sorted(ALL_PERMISSIONS),
    },
    MANAGER: {
        "name": "Manager",
        "description": "The marketer's daily surface: content, campaigns, audiences, sends, AI.",
        # Note what a Manager cannot do: touch credentials or users. That line
        # is the one ADR-152's write-only credential rule leans on.
        "permissions": [
            VIEW, CAMPAIGNS_MANAGE, CONTENT_MANAGE,
            AUDIENCES_MANAGE, SENDS_EXECUTE, AI_RUN,
            # Added with the 2026-09-18 split. A Manager could already pin, plan
            # a send and override a pick — those acts were reachable under
            # `audiences.manage`, `sends.execute` and `campaigns.manage`
            # respectively. Naming them explicitly keeps the role's capability
            # exactly where it was; omitting them would have been a silent
            # downgrade dressed as a refactor.
            AUDIENCES_PIN, SENDS_PLAN, OVERRIDES_MANAGE,
        ],
        # Still not a Manager's: `recipients.manage`, `recipients.consent` and
        # `insight.write` guard no UI surface — recipients originate in the
        # source system (ADR-167) and engagement arrives from providers and
        # integrations, so these exist for machine callers. `integrations.manage`
        # is Admin's by ADR-166 point 4.
    },
    VIEWER: {
        "name": "Viewer",
        "description": "Read-only.",
        "permissions": [VIEW],
    },
}

# Every role implies VIEW — a role that can edit but not read is not a case
# worth modelling, and forgetting VIEW on a custom role would be a confusing
# way to lock someone out.
IMPLIED = {VIEW}
