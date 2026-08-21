---
name: cluster6-auth-settings
description: Cluster 6 sweep (auth + settings) — the constraint-gap streak ends here; residue is 3 loc; the real findings are two sign-in defects and a double session resolution
metadata:
  type: project
---

Swept 2026-08-21. Report written to session scratchpad (`cluster6-report.md`), not to
`docs/architecture/code-slimmer-report.md` — the human appends. See
[[cluster5-audience-decision]] for the preceding sweep and [[seams-do-not-flag]].

## Clean negatives — do not re-derive these

- **Zero unused imports** in `app/auth/` and `app/settings/` (AST-verified).
- **Zero orphaned config keys.** All six `app_config` keys have a live writer and a live
  reader: `signal_weights`, `half_life_days`, `max_send_recipients`, `ai_spend_cap`,
  `ai_provider` (all in `settings/service.py:15-19`) and `auth_enforced` (declared in
  `auth/dependencies.py:33`, not in settings — deliberate, auth owns its key).
- **Zero missing DB constraints or FK indexes.** The Cluster 3/4/5 streak ends here.
  `auth/db_models.py` indexes every FK and has both compound uniques. `app_config.key`
  is the PK. The gap runs the *other* way: `role_permissions.role_id` and
  `role_assignments.user_id` are redundant single-column indexes (leading columns of
  existing unique constraints).
- **Zero dead routes, orphaned columns, orphaned templates, or JSON/Pydantic drift**
  (neither module has a JSON router or a Pydantic model).
- **Guards are applied consistently.** `enforce_policy` once over `frontend_router`
  (`main.py:293`), `auth_router` included without it and carrying ten explicit
  `require_permission(USERS_MANAGE)` guards, login/logout deliberately open with written
  reasons. No inconsistency exists — checked all 43 frontend write routes.
- **Permission vocabulary is 8/9 consumed.** Only `credentials.manage` is unconsumed.

## The one deletion

`current_user` (`auth/dependencies.py:52-54`) has zero callers. 3 loc. Note the
counter-argument before deleting: it reads as an optional-auth seam example, and the
app's actual optional-auth mechanism is the `attach_current_user` middleware.

## Do not flag as dead in this cluster

`BrandDB` (one row, joined by `access_list`), `UserDB.is_external` (read by
`users.html`), `RoleDB.is_customised` (two refs, both load-bearing, tested),
`MANAGER`/`VIEWER` constants (they are `BUILTIN_ROLES` keys), `IMPLIED` (three call
sites), `DEFAULT_LANDING`, `credentials.manage` (ADR-150 line 54 + ADR-152 §4 hook —
declared-but-unimplemented, not residue), the `system_mail_provider()` mock default
(deliberate, has an incident behind it), `settings/` having no router (documented).

## Findings the human still has to triage

- **A1, the important one:** `deliver_code` returns `False` for *any* delivery failure,
  not just the dev path, so `request_login_code` (`service.py:310-311`) returns the code
  and `router.py:63-76` renders it on screen. Authentication bypass in production. Not in
  `docs/backlog.md`.
- **A2:** `router.py:79, 108` interpolate the email into a query string unquoted while
  quoting `next` on the same line — a `+` address can never sign in. Only bites once a
  real provider is configured, which is why review missed it.
- **A3:** the session is resolved twice per request (middleware `main.py:227` +
  `enforce_policy` `dependencies.py:94`), with two `UPDATE auth_sessions … COMMIT`s.
- **S3:** ADR-153's audit log does not exist anywhere in `app/`; auth docstrings
  reference it as though it does.
- **S4:** nothing ever deletes an `auth_sessions` or `login_codes` row. ADR-154 line 79
  says a prune mechanism is the architecture's obligation.

## Cluster 4 C1 — extra evidence found here

`app/templates/settings.html:61-62` says *"set `click` weight higher to make clicks count
more … Changes apply immediately"*. Half-lives do apply (`insight/signals.py:52-58`);
weights do not on the engagement path (`insight/service.py:92` reads the constant). Note
`record_contribution` (`signals.py:76-78`) *does* call `get_signal_weights`, which is why
the screen appears to work when tested by hand. `docs/backlog.md:206`'s Done entry
verified the half-life side only.

## Doc gaps noticed

There is no `docs/architecture/Code/auth.md` — the only module without a page, and it is
not in `MOC - System Overview.md`. `settings.md` is stale (2026-07-27): missing
`get_ai_provider_name`, `get_ai_spend_cap`, three config keys, and the `settings → ai`
module-level import at `settings/service.py:10`.
