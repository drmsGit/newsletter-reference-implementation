---
type: code-concern
concern: brand
topic:
  - architecture
  - brand
  - tenancy
created: 2026-09-18
modified: 2026-09-18
---

# brand

> Part of [[MOC - System Overview]]. **A cross-cutting concern, not a module** — there is no `backend/app/brand/`. Architecture rationale: [[ADR-150 — Tenancy and Access Model]], with addenda to [[ADR-013 — Content Reference Instead of Content Copy]] and [[ADR-163 — Per-Channel Consent and Addressability]].

## Purpose

**Brands are a scope, not a hierarchy — and multi-brand is the ordinary case**
(ADR-150 point 2). A switcher in the top nav selects the working context; no
nested org machinery, no per-brand duplication of settings, strategies or
taxonomy. "Brands behave like categories."

`brand_id` is **not a tenant discriminator** and the two must not be conflated
(point 1): one installation serves one company, separation between *companies* is
a deployment boundary. Where GDPR forces brand separation the answer is two
installations, "and we ship no alternative" (point 3).

The counterpart promise (point 4): a company that means "logo and palette" never
sees the switcher. One default brand always exists and the column is filled with
it from the first migration — **a company treating brands as a skin pays a
default value in a column**. The test suite names this as the single most
important property (`test_brand_scoping.py:146`, `TestTheSingleBrandCompanyPaysNothing`).

## Where it lives
- **The table**: `BrandDB` — `backend/app/auth/db_models.py:24`. Lives in [[auth]] because tenancy and access are one boundary. `key` is permanent; `ensure_default_brand` (`auth/service.py:338`) is the most-called function in the codebase.
- **The working brand, human plane**: middleware at `backend/main.py:309-311` sets `request.state.current_brand`. `resolve_session_brand` (`auth/service.py:261`) reads `auth_sessions.brand_id` but **revalidates it against the user's grants every request** — the column is a cache of a choice, never an authority. Read side: `working_brand_id(request, db)` — `frontend/router.py:65`.
- **The working brand, machine plane**: `X-Brand` (`auth/dependencies.py:221`), parsed by `_declared_brand` (`:276`). ADR-166 point 8 — "the header is declared, not trusted."
- **The shared guard**: `_permitted` — `auth/dependencies.py:81-107`.
- **Migrations**: `migrate_0007_brand_scoping.sql` (the four resource columns + sessions + the index swap) and `migrate_0008_consent_brand.sql`.

## What carries a brand
| Table | Column | Nullability |
|---|---|---|
| `content_records` | `content/db_models.py:14` | NOT NULL |
| `campaigns` | `campaigns/db_models.py:11` | NOT NULL |
| `audience_groups` | `audience/db_models.py:14` | NOT NULL |
| `send_instances` | `delivery/db_models.py:17` | NOT NULL — **the arbiter** when the two derivable paths disagree |
| `consent_events` | `recipients/db_models.py:57` | NOT NULL |
| `role_assignments` | `auth/db_models.py:105` | NOT NULL |
| `integration_grants` | `auth/db_models.py:298` | NOT NULL |
| `auth_sessions` | `auth/db_models.py:187` | nullable — the working context |
| `audit_events` | `audit/db_models.py:62` | nullable, **no FK** |

Variants, modules and decision slots have **no brand of their own** — they inherit through the campaign. `ux_audience_groups_brand_name_lower` replaced the globally-unique name index, so two brands may each own a "VIPs".

**The sending brand is always derived, never taken from the session** — `brand_for_snapshot` ([[delivery]] `service.py:82`), `resolve_audience` reading the *group's* brand ([[audience]] `service.py:455`), `_brand_of_execution` ([[providers]] `service.py:27`), `sending_brand_id` ([[decision]] `strategies/base.py:132`). All of them **raise rather than guess**.

## What is deliberately NOT brand-scoped
- **The category vocabulary.** `categories` and `category_relations` carry no `brand_id` — "Beach means the same thing in every brand." Assignments hang off `content_records`, which *does*, so which content is Beach is already per-brand **transitively, with no column of its own**. Duplication as the general answer was rejected: "a synced copy is a copy that drifts."
- **Recipients** — "`recipient.brand` is the sending brand, not an attribute of the person" (point 9).
- **Signal contributions** — signals are shared at person level (point 8). The 2026-09-15 addendum confirms no column is needed: *"what is scoped is which people are summed, and that is a query, not a column."*
- **Settings / `app_config`**, **users, roles, integrations** (`users.manage` per brand "would be theatre"), **`ai.run`** (what is protected is spend, one company-wide pot), **`view`** ("the brand filter does the work").
- **Module templates and `brand.css`** — files on disk, already shared. Note the **naming collision**: that "brand" is theming, unrelated to `BrandDB`.

`migrate_0007_brand_scoping.sql:23-25` states the exclusion set outright: "`recipients`, `signal_contributions`, `categories` and `app_config` get NOTHING."

## Duplication — the one place a copy is made
ADR-013's 2026-09-16 addendum: **reference wherever referencing is expressible, copy only where the boundary makes it inexpressible.** `ContentRecordDB.brand_id` is NOT NULL, so a brand-B campaign has no way to point at a brand-A record — copying there is *forced, not preferred*. The cost is booked in ADR-013's own terms: "a typo fixed in brand A stays wrong in brand B."

`campaigns/duplication.py` — *"the rule that decides everything is the boundary, not the act."* `content_modes_for(source, target)` returns `[KEEP, LAYOUT]` within a brand and `[COPY, LAYOUT]` across one: **not a preference list — the excluded one in each case cannot be built.** Refusals live in the service, not merely hidden in the UI. Not carried: resolutions, snapshots, sends, versions, overrides; status forced to draft. A cross-brand copy gets **no `content_versions`**, so it previews and cannot be sent until someone publishes it.

**Provenance lives in the [[audit]] log, not a `copied_from_id` column** — so the answer cannot go stale when the source is renamed or deleted.

## Consent and brand
ADR-163's addendum widened the cell to `(recipient, brand, channel, purpose)`. The gap it closed: `is_consenting_filter()` took only channel and purpose, so *a campaign scoped to brand B still reached every consenting recipient* — the authoring side was scoped and the send side was not.

**Consent to brand A says nothing about brand B.** A newly created brand starts with **zero reachable recipients** until consent is captured for it. That is correct — it is the point — and "it will still surprise whoever creates their second brand."

`brand_id` is a **required positional on every consent function** (`recipients/consent.py`), with no default anywhere: "a consent row whose brand was assumed is a consent record nobody gave." An assertion naming no brand is **refused, not defaulted**. `consent_history` is the one deliberate exception — it **spans brands by default**, because hiding the other brand's events would present a partial record as a whole one.

## Brand-scoped permissions
**A permission is brand-scoped if the rows it guards carry a `brand_id`** — said about the permission, not about the Admin role, because roles are rows a company may rename or delete.

`permissions_for(db, principal, brand_id)` (`auth/service.py:819`) applies `RoleAssignmentDB.brand_id == brand_id`; with `brand_id=None` it returns the **union across every grant**, which is the platform-level answer. So a Manager on brand A + Viewer on brand B working in B holds `{view}` only; working in A holds the Manager set; platform-level keys resolve against the union either way.

**Several roles on one brand stay legal and resolve to the union** — permissions are grants only, with no DENY, so two roles cannot contradict each other. The access list computes the union **only** for brands carrying more than one role, so the ordinary case costs no extra query.

## Invariants & decisions
- **The default brand cannot be deleted**, and `delete_brand` refuses any brand still holding content, campaigns, groups, sends or role assignments — naming what blocks it.
- **A brand-scoped permission with no working brand fails closed** — holding no grant "is not a reason to be allowed more."
- **`BrandNotDeclared` is its own exception, not a `NotAuthorised`** — ADR-166's Negative section names the confusion, and it is explicitly *not* a fallback to "the one brand this integration holds" ("that would work right up until it holds two"). The `may_send_unattended` check runs **before** it: "you may not do this at all" outranks "you did not say where."
- **Another brand's row is indistinguishable from a row that does not exist** — campaigns, content and audience groups all redirect identically. A brand switch from a detail page lands on the section's *collection*, never a stale id.
- **A refused brand switch answers identically to an accepted one** — a distinct response would disclose which brands exist.
- **An unknown brand is not "any brand"** — `sending_brand_id` returning None must not silently widen the candidate set.
- **`brand_id=None` on list functions means *every* brand and is not the caller's default** — the identical docstring appears three times ([[content]], [[campaigns]], [[audience]]), for platform-wide counts, migrations and tests.
- **Migrations assert their preconditions rather than assume them** — `migrate_0007` refuses above one brand with rows unassigned, because "the correct brand per row is unknowable and guessing it would invent evidence." `migrate_0008` asserts a timestamp fact instead, because 0007's guard would now refuse.
- **Bootstrap ordering**: content seeding requires the default brand, so `bootstrap_auth` must run first — the reverse order was harmless until 2026-09-15 and is now a first-boot crash.

## ⚠️ Change-impact — what leaks if a filter is dropped
Nothing structural stops these: the column is on the table, the filter is in the query.

| Path | Leaks |
|---|---|
| `list_content_records` / `list_campaigns` / `list_groups` without `brand_id` | every brand's rows — **the default is `None`, which means "all"** |
| the five detail-by-id routes | another brand's row by URL (unscoped until 2026-09-15) |
| the module content picker (`frontend/router.py:1082`) | binding brand-A content to a brand-B campaign — the defect ADR-013's addendum records |
| decision candidate sets | brand A's content resolved into brand B's send |
| **the three consent gates** | **the compliance failure** — a brand-B send reaching brand-A's subscribers |
| dashboard counts | a dashboard mixing scopes |
| the suggested-audience picker | another brand's campaign *name*, via groups named after it |

Also: anything calling `has_permission` **must decide** whether to pass a brand — passing None is the fail-open direction. A new permission key needs classifying in `BRAND_SCOPED` *and* a `WRITE_POLICY` entry. A new brand-carrying table must be added to `delete_brand`'s blocking counts. A new detail route needs a `SWITCH_LANDINGS` entry. **The target brand of a cross-brand write is not covered by the working-brand check** — use `brands_with_permission`.

## Known gaps
1. **The twelve JSON routers create rows in the default brand regardless of `X-Brand`.** `content/router.py:151`, `campaigns/router.py:57`, `audience/router.py:27` call `ensure_default_brand(db).id` under a comment marked PROVISIONAL. Since `enforce_api_policy` now guards all twelve, the permission is checked against the **declared** brand while the row lands in the **default** brand. The comment's premise ("this router is unauthenticated") is stale as of 2026-09-18. `recipients/router.py:73,124` already takes `payload.brand_id` — the pattern the other three have not adopted. **This is the sharpest live inconsistency in the boundary.**
2. **[[audit]]'s read paths are not brand-filtered** though the rows carry `brand_id`. No ADR decides whether they should.
3. **`/ui/graph` has no brand filter at all.** ADR-150's addendum says it is blocked on the consent work and must not be half-shipped. **Consent has now shipped, so the stated blocker is cleared and the work is not done.**
4. **No unsubscribe page exists**, so ADR-163's opt-out-scope decision governs a surface with nowhere to live.
5. **Per-brand affinity is an open question** (ADR-150 `:188`) — the later addendum argues it needs no column but records the tension rather than closing point 8.
6. **Per-brand AI budgets are direction, not a build commitment**; **point 10's configurable brand filter on decision strategies is demonstrated, not built**.
7. **Stale records**: `docs/backlog.md:35` still says brand-scoped roles are "modelled but not enforced" (no longer true, and it carries a DECIDED note that was never closed); ADR-150's implementation-status paragraphs at `:120`, `:132-139`, `:164` are superseded by code but not marked so; `HANDOFF.md:3` says step 1 built while `:305`/`:311` record steps 2 and 3. **Cite the code, not those paragraphs.**
