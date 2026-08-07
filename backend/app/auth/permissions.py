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
