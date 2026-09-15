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
}

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
    # Classified now so the split lands correctly when these keys are built.
    # They are in ADR-150 point 5's sixteen-key vocabulary but not yet in
    # ALL_PERMISSIONS, because a key names a code path and those guards do not
    # exist: "audiences.pin", "sends.plan", "overrides.manage".
    "audiences.pin",
    "sends.plan",
    "overrides.manage",
})


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
        ],
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
