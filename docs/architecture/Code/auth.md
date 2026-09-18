---
type: code-module
module: auth
topic:
  - architecture
  - auth
  - security
created: 2026-09-18
modified: 2026-09-18
---

# auth

> Part of [[MOC - System Overview]]. Architecture rationale: [[ADR-150 — Tenancy and Access Model]], [[ADR-151 — Authentication and Sessions]], [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]].

## Purpose

The auth module owns **one boundary: who is calling, and may they do this here.**
It holds the tenancy scope (brands), the access model (users × roles × brands),
passwordless sign-in and sessions, machine principals and their credentials, the
permission vocabulary, the route→permission policy table, and the FastAPI
dependencies that enforce all of it. Everything downstream — [[content]],
[[campaigns]], [[delivery]], [[insight]] — is deliberately ignorant that users
exist. The architectural promise it keeps is that **people and machines are
evaluated by the same policy table and the same permission resolver**: ADR-166
point 1 refuses a parallel authorization system, and `permissions_for`
(`service.py:819`) is the single point where that promise is kept or broken.

## Key files
- `backend/app/auth/service.py` (1089) — brand resolution/switching, bootstrap, system mail, rate limiting, code issue/verify, session lifecycle, `permissions_for`/`has_permission`, user and role administration
- `backend/app/auth/router.py` (432) — server-rendered sign-in/out, the users & access list, the role × permission grid, brand CRUD, the enforcement toggle
- `backend/app/auth/dependencies.py` (361) — the five guards, the five auth exceptions, brand-scope resolution, `Authorization: Bearer` parsing
- `backend/app/auth/db_models.py` (339) — all 12 tables
- `backend/app/auth/integrations.py` (273) — machine principals: integrations, credentials, grants, `authenticate()`, aggregated failure recording. **No authorization decisions.**
- `backend/app/auth/permissions.py` (164) — the 16-key vocabulary, `BRAND_SCOPED`, the three preset roles as data
- `backend/app/auth/policy.py` (162) — the single `WRITE_POLICY` route→permission table (UI half + JSON API half) and `required_permission()`

## Public surface
**The five guards** (`auth/dependencies.py`), all wired in `backend/main.py`:

| Guard | Line | Wired at | Does |
|---|---|---|---|
| `enforce_policy` | `:184` | `main.py:445`, whole frontend router | Derives the permission from the resolved route template; refuses `UNMAPPED` |
| `enforce_csrf` | `:147` | `main.py:430`, `:445` | Rejects a state-changing form with a missing/wrong token |
| `enforce_api_policy` | `:289` | `main.py:470`, 12 JSON routers | The machine plane. Bearer credential only, **no cookies** |
| `require_permission(perm)` | `:115` | per-route | Explicit guard for routes outside the table's reach |
| `current_user` | `:110` | optional | Resolves the cookie or None; never raises |

**Permission resolution** — the two functions both planes share: `Principal = UserDB | IntegrationDB` (`service.py:816`), `permissions_for(db, principal, brand_id=None)` (`:819`), `has_permission(...)` (`:869`).

**Brands**: `ensure_default_brand` (`service.py:338`, the module's most-called function), `brands_for_user` (`:218`), `brands_with_permission` (`:237`), `resolve_session_brand` (`:261`), `set_session_brand` (`:316`).

**Sessions**: `request_login_code` (`:670`), `verify_login_code` (`:718`), `user_for_token` (`:767`), `revoke_all_sessions` (`:804`), `csrf_token_for` (`:65`), `safe_next` (`:92`). `SESSION_ABSOLUTE_HOURS = 12`, `SESSION_IDLE_MINUTES = 60`, `CODE_TTL_MINUTES = 10`, `CODE_MAX_ATTEMPTS = 5`.

**Machine principals** (`auth/integrations.py`): `create_integration` (`:53`), `issue_credential` (`:148` — **the secret is the second tuple element and exists nowhere else**), `revoke_credential` (`:180`), `grant`/`revoke_grant` (`:112`/`:136`), `authenticate` (`:235`), `record_auth_failure` (`:201`).

**Routes**: 18, all server-rendered (`router.py`). Sign-in/verify/logout are open; everything else is `USERS_MANAGE`. Two auth-owned surfaces live **outside** this router on purpose — `POST /ui/brand` (the switcher) and the `/ui/integrations` family, both in [[frontend]], so they inherit `enforce_csrf` + `enforce_policy` from `main.py:445`, which `auth_router` does not get.

## Data model
*Twelve tables*, all via `create_all` at `main.py:213` — **there is no Alembic in this repo.**
- **`brands`** (`BrandDB`, `db_models.py:24`) — the tenancy scope, not a hierarchy. `key` is permanent. Exactly one row always exists and **cannot be deleted**. `brand_id` is NOT NULL on content records, campaigns, audience groups and send instances.
- **`users`** (`:41`) — **no password column, by design**. `is_external` is visibility only, grants nothing.
- **`roles`** (`:62`) / **`role_permissions`** (`:83`) — `is_customised` stops the startup re-sync reverting a hand-edited role.
- **`role_assignments`** (`:94`) — the `(user × role × brand)` grant, **all three NOT NULL**. One row per grant, so a person on two brands has two rows.
- **`login_codes`** (`:109`), **`login_code_requests`** (`:129` — the rate-limit counter, both identifiers hashed, pruned on write), **`auth_sessions`** (`:163` — carries the working `brand_id`).
- **`integrations`** (`:200`) — the caller and **the durable audit actor**, so history stays continuous across a credential rotation. **`integration_credentials`** (`:236`) — many per integration, so rotation is overlap-then-revoke. **`integration_grants`** (`:272`) — permissions held **directly, not through a role**; `brand_id` NOT NULL exactly as `role_assignments`. **`integration_auth_failures`** (`:302`) — one row per `(key_id, client, hour)` bucket with a counter.

## The permission vocabulary
Sixteen keys (`permissions.py:16-42`). **Brand-scoped (7)**: `content.manage`, `campaigns.manage`, `audiences.manage`, `sends.execute`, `audiences.pin`, `sends.plan`, `overrides.manage`. **Platform-level (9)**: `view`, `ai.run`, `settings.manage`, `users.manage`, `credentials.manage`, `recipients.manage`, `recipients.consent`, `insight.write`, `integrations.manage`.

The omissions are reasoned, not accidental (`permissions.py:101-107`): `ai.run` writes branded rows but what is protected is *spend*, and the budget is one company-wide pot; `users.manage` and `integrations.manage` scoped per brand would be **theatre** — an Admin on brand A can grant themselves Admin on brand B in two clicks; recipients and signals carry no brand at all.

**The 9→16 split** (`permissions.py:26-35`) came from ADR-166's own worked example: n8n may trigger a send, a website form may only pin a recipient. Pinning used to sit under `audiences.manage`, so granting a public form the right to add one recipient would also have granted it the right to restructure the audience. Crucially **the splits serve humans too** — "may pin, may not restructure" is an ordinary junior marketer — which is why they went into the shared vocabulary rather than a machine-only scope list, and why Manager explicitly gained the three new brand-scoped keys so the split was not a **silent downgrade dressed as a refactor** (`permissions.py:141-146`).

## Depends on →
- [[settings]] — `get_config`/`set_config` (the `auth_enforced` flag)
- [[audit]] — every administrative action
- [[delivery]] / [[rendering]] — **lazily, for one thing only**: emailing a sign-in code. This is the circular dependency called out at `service.py:14-16` — if system mail breaks, nobody can sign in, including whoever would fix it.

## Depended on by →
- `backend/main.py` — tables, all five guards, the router, `bootstrap`
- [[frontend]] — brand switching, the integrations admin UI, `has_permission`
- [[recipients]] — `enforce_api_policy` plus **the only payload-dependent permission check in the system** (`recipients/router.py:61`)
- [[audience]], [[campaigns]], [[content]] — `ensure_default_brand` only

**Only `main.py` imports the guards for wiring.** Every business module stays ignorant of authentication except the two that genuinely need it.

## Invariants & decisions
**Fail-closed**
- **An unmapped write route is refused, not allowed.** `policy.py:162` returns `UNMAPPED`, which no role can hold, so it is a refusal that names itself in the log. The whole table shape exists for this.
- **A brand-scoped permission with no working brand is refused, never checked without one** (`dependencies.py:97-107`). Passing `brand_id=None` would mean the *union* across all grants — letting an Admin on brand A act as one on brand B. That is the hole ADR-150's 2026-09-15 addendum closes.
- **`auth_enforced` defaults ON** (`dependencies.py:78`) since 2026-09-13. Break-glass is `AUTH_DEV_SHOW_CODE=true`, which puts the code in the *log* so an operator signs in **as themselves**, rather than a flag that disables access control for everyone.
- **`cookie_secure()` defaults True; `trust_proxy_headers()` defaults False** — believing `X-Forwarded-For` lets an attacker mint a fresh identity per request; not believing it merely makes the limit global. **`system_mail_provider()` defaults to mock** and is deliberately *not* inferred from a key being present — that inference once emailed a live message to a throwaway test address.
- **`may_send_unattended` defaults False**, and a machine send it cannot queue is **refused** (`dependencies.py:339-344`) — ADR-166 point 5. Shipping the flag while letting the send through would be a control that is not one.

**Enumeration-oracle rules** — break any of these and the login form leaks accounts
- **`POST /ui/login` returns one identical 303 for every outcome** (`router.py:62-109`) — known address, unknown, deactivated, sent, failed to send.
- **Throttling happens BEFORE the user lookup** (`router.py:80-90`) so the path cannot diverge at all; a limit applied after would be a *timing* oracle replacing the response one.
- **`request_login_code` returns the code only on the dev path.** `CodeDelivery` is a tri-state (`service.py:508-524`) specifically because collapsing "deliberately not attempted" and "attempted and failed" into `False` was a **P0**: a deployment with a broken mail provider handed a working sign-in code to anyone who typed an admin's address. **No HTTP path may render this value.**
- **Refused rate-limit requests are not recorded** (`service.py:616-621`) — counting them would let an attacker hold a victim's address over the limit indefinitely, turning a mail-volume control into a lockout weapon.
- **`authenticate` returns one `None` for every failure mode** (`integrations.py:237-241`) — unknown key, wrong secret, revoked credential, deactivated integration.
- **Brand switching answers identically whether accepted or refused** — a distinct response would tell a signed-in user which brands exist beyond their grants.

**Model**
- **Permissions are grants only; there is no DENY.** So the union across roles *is* the answer and there is nothing to resolve (`dependencies.py:192-195`). This falls out of the model rather than being implemented.
- **`view` is implied for every role and NOT for an integration** (`permissions.py:161-164` vs `service.py:846-853`). A deliberate asymmetry: implying it would hand every integration the recipient list — one of the four routes ADR-166's Context names as the reason the feature exists.
- **Permission keys are code; role composition is data** (`permissions.py:3-8`). Inventing a key requires writing the code it guards.
- **Scope is a property of the permission, not of the role** — saying it about Admin would hardcode a role name, and roles are deletable rows.
- **`resolve_session_brand` revalidates the stored `brand_id` against the grant table on every resolution** — the column is a cache of a choice, never an authority.
- **Deactivation revokes sessions immediately; role revocation does not** (`service.py:903` vs `:942`). Losing a role is a change of scope, not a reason to be thrown out mid-edit; deactivation is the whole offboarding control.
- **`POST /ui/logout` is deliberately unguarded** — a Viewer previously had no route to it, because the only control lived on a page their role was refused.
- **`safe_next` rejects anything but a same-site absolute path**, including `//host` and backslashes, closing an open-redirect on the login page.
- **The integration, not the credential, is the audit actor** — a credential-as-actor model cannot answer "who triggered this send" a year later. **`created_by_user_id` is NOT an ownership link**; deactivating that user revokes nothing, a cost booked in ADR-166's Negative section rather than mitigated.
- **Failed machine auth is aggregated per `(key, client, hour)`, never one row per attempt** — a row-per-attempt table hands an unauthenticated attacker a write primitive.
- **sha256, not bcrypt, for credential secrets** (`integrations.py:39-47`) — slow KDFs exist for low-entropy human input, and there is no dictionary of 32 random bytes.

## ⚠️ Change-impact — if you touch this, also check…
- **Adding any write route anywhere → add a `WRITE_POLICY` entry**, or it is refused at runtime with a log line naming `policy.py`. Intentional and loud, but it means every new endpoint in every module is a change to this file.
- **`WRITE_POLICY` order is load-bearing.** First match wins on a plain `startswith`; inserting a broad prefix above a narrow one silently downgrades the narrow route. Six live specificity pairs depend on this.
- **Prefix collision:** `("/ui/brand", VIEW)` at `policy.py:57` is a prefix of `/ui/brands`. Today the brand CRUD routes live in `auth_router`, which is not wrapped in `enforce_policy` and relies on explicit `require_permission(USERS_MANAGE)`. **Move them into the frontend router and they would match `/ui/brand` and silently drop from `users.manage` to `view`.**
- **GET routes on admin surfaces need an explicit guard** — `required_permission` answers `VIEW` for every read, so a `/ui/x` table entry covers only the writes. Applies to `/ui/users`, `/ui/roles`, `/ui/integrations`. This was caught by a test asserting a Manager is refused, not by reading the table.
- **`auth_router` has permission guards but no `enforce_policy`** — its entries in the policy table are **documentation, not enforcement**. Removing a `require_permission` there removes the only guard.
- **Adding a permission key** is five steps: constant, `ALL_PERMISSIONS`, brand-scope decision, role membership decision, `WRITE_POLICY`. The re-sync reaches non-customised roles automatically; **customised ones will not get it.**
- **Removing or renaming a key** orphans rows in `role_permissions` and `integration_grants`. Nothing sweeps them, and there is no migration tooling.
- **Changing a permission's brand-scope flips machine behaviour**: newly brand-scoped means every existing integration call without `X-Brand` starts failing with a 400.
- **Touching `hash_secret` invalidates every stored session, login code, credential secret and rate-limit counter at once.** `csrf_token_for` is domain-separated from it and must stay that way.
- **`enforce_csrf` reads `request.form()`** — deliberately absent from the JSON API; wiring it there would consume/mangle JSON bodies. It also skips requests with no session cookie: do not "tighten" that, it is what lets the anonymous sign-in POST work.
- **The machine plane accepts no cookies.** That narrowing buys the CSRF question outright — no ambient credential, nothing for a cross-site request to carry. Adding cookie acceptance reopens it.
- **`brands_with_permission` exists for destination-brand checks** (campaign duplication). Any new action naming a brand other than the working one must use it — **the policy table only ever checks the working brand.**
- **`delete_brand` hardcodes the five tables carrying `brand_id`** (`service.py:196-207`). A new brand-scoped table must be added, or deleting a brand fails at the foreign key instead of refusing cleanly.
- **Startup order is a first-boot crash risk**: `bootstrap_auth` must precede `create_demo_content_if_empty` (`main.py:216-224`). The other order crashed on 2026-09-15.
- **`ApprovalRequired` becomes a queue, not a refusal, once the ADR-142 §4 approval surface exists** (`dependencies.py:230-238`). The default need not change — but anyone building that surface must come here.
- **Six environment variables are read directly from `os.environ`**, not the settings table: `INITIAL_ADMIN_EMAIL`, `SYSTEM_MAIL_PROVIDER`, `SYSTEM_MAIL_FROM`, `AUTH_DEV_SHOW_CODE`, `AUTH_COOKIE_INSECURE`, `TRUST_PROXY_HEADERS`.
