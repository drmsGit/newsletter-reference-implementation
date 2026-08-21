# Code Slimmer Report

**Date:** 2026-08-21
**Scope:** All seven clusters. `backend/app/` is fully swept.
**Method:** Read-only sweep by the `code-slimmer` agent — nothing edited, nothing deleted
**Status:** Open, partially promoted. **Six items promoted to `docs/backlog.md` on 2026-08-21**
and ticked below — Cluster 6 A1/A2/A4 (auth), Cluster 4 C1 (inert signal-weight editor, which
also corrected a false Done claim in the backlog), Cluster 3 C1/C5 (missing DB constraints).
Everything else remains staged here by decision: the sweep found near-zero dead code across all
seven clusters, so remaining cleanup is deferred until before public beta rather than worked now.

> **Cluster 6, A1 — promoted 2026-08-21.** A failed provider delivery renders a live
> six-digit sign-in code into the browser of whoever requested it, for any address. Traced
> statically and re-verified against source on promotion, **not yet reproduced** — the check
> to run is in Cluster 6's Unverified list. **Now logged in `docs/backlog.md` as a P0
> security bug**; track it there.
> **Stage context:** this is a local POC with no real users, and the on-screen code is a dev
> affordance that will not exist in future — so this is a **must-fix before any exposure**,
> not a live risk today. See the Assessment section on deferred-by-decision items.

Sweep order is by cluster. `delivery/` + `providers/` were swept earlier and their
findings live in `docs/backlog.md` (external code review 2026-08-07). This file holds
sweeps that have **not** been promoted to the backlog — it is a staging area, not the
queue of record. Promote an item to `docs/backlog.md` when it is accepted for work;
strike it here when it is.

> **Line numbers drift.** Every reference below was accurate on 2026-08-21 against
> `backend/app/frontend/router.py` at 2,927 loc. Re-locate by symbol name, not by line,
> if the file has changed. (`docs/backlog.md` already has one ref that drifted ~740
> lines — see Housekeeping.)

---

# Cluster 1 — `frontend` + `templates`

**Swept:** 2026-08-21 · `backend/app/frontend/router.py` (2,927 loc) + `backend/app/templates/` (24 files)

## Headline

**The expected residue is not there.** Zero dead routes, zero orphaned templates, zero
unused context keys, zero unused local variables — verified mechanically across all 65
handlers and all 24 templates, not sampled. What this cluster actually carries is
**duplication and per-row queries**.

Method that produced the clean negative, worth repeating: an AST pass over
`TemplateResponse(...)` calls diffing context keys against template bodies, plus a second
pass turning each `@router` path into a regex (`{param}` → `[^"']*`) matched against all
templates at once. Two false-positive sources to watch: `**ctx` dict merges hide keys from
the AST, and Jinja `~` concatenation hides paths from literal greps.

---

## To do

Ranked by loc saved ÷ risk. Unchecked = not started.

### Free wins — zero risk

- [ ] **1. Two unused imports.** `backend/app/frontend/router.py:24` (`create_send_instance`)
      and `:36` (`list_content_overrides`). Each name appears exactly once in the file —
      the import itself. Both functions are genuinely used elsewhere
      (`app/delivery/router.py:70`, `app/overrides/router.py:32`), so the services stay;
      only the frontend's import is dead. Residue from when the plan-send and override UIs
      were built directly rather than via `prepare_send_from_audience` /
      `get_active_content_override`.
      *2 loc. Blast radius: none — removal fails loudly at import time if wrong.*

- [ ] **2. `import json as _json` shadowing the module-level `json`.**
      `backend/app/frontend/router.py:1100`, inside `decision_slot_edit`. `json` is already
      imported at `:13` and used at `:558`, `:873`, `:910`, `:983`. This one function
      re-imports it under an alias for two calls two lines later.
      *1 line + 2 renames. Blast radius: none.*

- [ ] **3. Sender-address default hardcoded twice.**
      `backend/app/frontend/router.py:711` reads
      `os.environ.get("RESEND_FROM", "onboarding@resend.dev")`, duplicating
      `backend/app/delivery/providers/resend.py:26-32`, which defines `DEFAULT_FROM` for
      exactly this. A provider-side change to the default leaves the UI showing a stale
      value with no error. Import the constant.
      *0 loc, one import. Cheapest correctness win in the list.*
      Also the only direct `os.environ` read in the router that has an owning module —
      see Open call B. (The three `ANTHROPIC_*` reads at `:118-123` are a different case:
      they deliberately report env presence to the settings screen.)

### Redundant DB queries

- [ ] **4. `deliveries_list` — N+1, six queries per row.**
      `backend/app/frontend/router.py:2003-2093`. Per send instance, in a Python loop: a
      `SnapshotDB` lookup, a `VariantDB` lookup, a `CampaignDB` lookup, an execution
      `.count()`, a sent-status `.count()`, and a joined engagement-event `.count()`.
      Unpaginated (`db.query(SendInstanceDB).all()`).
      **The fix already exists in this file:** `decisions_list` (`:1686-1725`) does the
      identical job — join up the campaign chain, aggregate counts — in one grouped query.
      This is inconsistency with an in-repo precedent, not a missing technique.
      *~30 loc. Queries: 1 + 6N → 2. Blast radius: one handler, one template
      (`deliveries.html` consumes a flat row dict a joined query can produce unchanged).*
      **Risk:** the joins must be `outerjoin`. A send instance whose snapshot was deleted
      currently renders with `campaign_name: None`; an inner join would silently drop the
      row. No test covers this handler.
      **This is not P2-04** (that is `delivery/service.py`'s per-recipient send loop) and
      not the pagination Feature at `docs/backlog.md:87` (limit/offset only, says nothing
      about per-row queries). Fresh finding.

- [ ] **5. `audience_groups_list` — full audience resolution per group.**
      `backend/app/frontend/router.py:2632-2647`. Per group: a `.count()` on
      `AudienceGroupMemberDB` **plus** `len(audience_service.resolve_audience(db, g.id))` —
      running the entire rule-block engine and consent gate to produce a list whose only
      use is `len()`. On a list page. Worse per row than #4, because the cost is a whole
      subsystem invocation rather than a count.
      *Belongs in `app/audience/service.py` as a count path, not in the router. Three call
      sites benefit (see #6).*
      **Risk:** a count-only query written independently **will** drift from the resolve
      path's semantics. The comment at `:2637-2639` is explicit that "recipients" means
      blocks ∪ pins − excludes, consent-gated. Safer form: one resolver with a `count_only`
      path inside the service, never a parallel query.

- [ ] **6. `resolve_audience(...)` called for its length in three places.**
      `backend/app/frontend/router.py:709`, `:2642`, `:2718`. Same `len(resolve_audience(...))`
      idiom; one of them (`:2718`) legitimately needs the list. Folds into #5.

- [ ] **7. `campaign_detail` — nested N+1, four queries per decision slot.**
      `backend/app/frontend/router.py:507-753`. Per variant: a modules query, then per
      module a `get_active_content_override(db, m.id)` query; then a slots query, then per
      slot `resolution_count`, `unique_content_count`, `top_content`, `latest_resolutions` —
      four queries; then a snapshots query. Plus the `audience_choices` loop at `:704-710`
      (same problem as #5).
      *~40 of 247 loc.*
      **Risk: highest of the query findings.** Largest handler after `category_graph`;
      `campaign_detail.html` is 542 lines and reads this structure deeply. Batch-fetching
      overrides and slot stats changes the shape of `variant_rows`. No test covers this
      page. **Do this after #4 and #5, using them as the pattern.**

### Duplication

- [ ] **8. Merge `module_create` / `module_edit`.**
      `backend/app/frontend/router.py:857-892` and `:896-929`. 37 and 36 lines,
      byte-identical except the service call (`create_module_for_variant` vs
      `update_module`) and the extra `module_id` param. Same optional-JSON parse, same two
      error redirects, same success redirect. The comment at `:868-870` even says "same
      pattern as field_overrides_json on the override form" — the author noticed the
      duplication and documented it instead of extracting it.
      *~30 loc. Blast radius: two handlers, one template form block. Low risk — both are
      POST/redirect with no return-value contract.*

- [ ] **9. One flash block in `base.html`.**
      `alert-danger` markup is hand-copied in 12 of 24 templates in four incompatible
      forms: `alert alert-danger role="alert"` (6×), without `role` (1×), with `py-2` (3×),
      and two that additionally inline a `confirm_delete` branch
      (`category_detail.html:16`, `content_detail.html:27`). There is **not one
      `{% include %}` in the entire template directory** — 24 files, all
      `{% extends "base.html" %}`, one macro total. A `{% block flash %}` removes the
      duplication and settles the four-way inconsistency at once.
      *~30 loc, 12 mechanical edits.*
      **Risk:** the two `confirm_delete` variants must **not** be flattened into the shared
      block — they carry a destructive-action confirmation.

- [ ] **10. Extract the redirect-error helper.**
      26 occurrences of `quote(` between `backend/app/frontend/router.py:876` and `:2924`,
      inside 21 `except ValueError as error:` blocks all doing the same four lines.
      Consistent in behaviour (all 72 redirects use `status_code=303`), inconsistent in
      form (some pass `url=` as a kwarg, some positionally). A single
      `_redirect_error(path, message)`, or a `ValueError` handler registered on the router,
      makes the post/redirect/get invariant enforceable rather than conventional.
      *~60 loc.*
      **Risk:** low individually, but 21 simultaneous edits across handlers with **no test
      coverage** is exactly how one typo'd redirect path hides. Do it one commit per
      feature area, not one sweep.

- [ ] **11. Consolidate decision-slot resolution stats — three implementations.**
      `backend/app/frontend/router.py:577-644` (per-slot, 4 separate queries, inside the
      N+1 above), `:1690-1725` (one grouped aggregate), `:1803-1818` (one single-row
      aggregate, seven metrics). Three answers to "how many resolutions, how many distinct
      content records, what was the last one" — three query shapes, three rounding
      conventions. If the definition of a resolution changes, three places must change and
      only two will.
      *~60 loc net if consolidated into one `decision/service.py` helper returning a stats
      dict. Blast radius: three handlers, three templates.*
      **Risk:** the three call sites want different field subsets, so a shared helper must
      return a superset or take a flag — mild over-generalization risk.
      See Open call B: this is the router computing decision-layer metrics.

---

## Two open calls — need a decision before anything is scoped

### A. Is AI-optional boot a real requirement?

There are **14 function-local imports** at `backend/app/frontend/router.py:94-100`, `:141`,
`:178-179`, `:191`, `:721-722`, `:825`, `:2789`.

The import-cycle hypothesis is **ruled out**: `app/ai/service.py` imports `settings`,
`campaigns`, `content` — never `frontend`, which is the dependency leaf per
`docs/architecture/Code/Module dependency map.md`. So nothing *forces* these to be local.

But they may be deliberate, to keep the AI package optional at import time — ADR-140
governs AI enablement as a choice.

**The question:** is the app meant to boot with `app/ai/` absent, or with `anthropic`
uninstalled? If no, hoist all 14 to module level (~6 loc net). If yes, they stay and should
carry a comment saying why, so the next sweep doesn't re-flag them.

**ANSWERED — Cluster 7, 2026-08-21: no, definitively.** There is no `anthropic` package to be
optional about (the Claude adapter is raw `httpx`), `main.py:121` imports `app.ai.db_models`
unconditionally, and `frontend/router.py:28` → `settings/service.py:10` → `ai.adapters.factory`
is an unbroken module-level chain, so the adapters are already loaded before any route runs.
**The 14 lazy imports protect nothing that is not already unprotected two lines above them.**
Resolution: hoist them — but fix the `httpx2` pin first; see Cluster 7's answer for why that
pin is a boot-blocker, not a delivery-only problem.

### B. Does the `frontend.md` presentation-only invariant have ADR force?

`docs/architecture/Code/frontend.md` states: *"Presentation only — every route delegates to
a service; no business logic here. If logic creeps in, it belongs in the owning module."*

Three findings sit against it — #3 (the only owned `os.environ` read in the router), #11
(the router computing decision-layer metrics three ways), and `category_graph` below. The
invariant already says where they go, so if it holds, those aren't judgment calls.

**The question:** is this a doc-only convention, or is it recorded in an ADR? **Unverified —
I have not checked whether an ADR covers it.** If none does, that gap is itself worth
knowing, and this may be a `📋 Needs ADR` item rather than a cleanup item.

---

## Noted, deliberately not ranked

**`category_graph`** — `backend/app/frontend/router.py:2233-2628`, 395 lines. The single
largest function. Loads three whole tables plus a full
`SignalContributionDB × EngagementEventDB` join into memory on every page view, then does
layout trigonometry and colour thresholds in the router. A clear violation of the
presentation-only invariant (Open call B).

Left off the ranked list because the only honest fix is "extract a graph service" — a
rewrite of the largest handler in the cluster. Per this project's rule, open forks get
noted and implemented in the final MVP package, not chased one at a time. **Noting it as an
option, not proposing it.**

---

## Housekeeping

- [ ] **Stale line reference in the backlog.** `docs/backlog.md:83` cites the
      `avg_delta < 0` display branch as `frontend/router.py:1765-1767`. It is now at
      `backend/app/frontend/router.py:2503-2504` — drifted ~740 lines, and will mislead
      whoever picks that item up.

---

## Leave alone — looks dead, is not

Checked exhaustively, not sampled. **Do not re-run reachability on this cluster.**

- **`forbidden.html`** — zero references inside `app/`; rendered from `backend/main.py:273`
  (the 403 handler). The only template not owned by a router in `app/`.
- **`POST /ui/audience-groups/{group_id}/blocks/{block_id}/edit`** (`:2872`) — the one route
  with no literal path in any template. Reached via the `block_form(action, ...)` macro in
  `audience_group_detail.html:146`, whose action is built with Jinja `~` concatenation. A
  literal-path grep misses it.
- **`GET /ui/audience-groups/{group_id}/criteria-preview`** (`:2779`) — no template action,
  no nav link. Called from a `fetch()` in `audience_group_detail.html:319`. The only
  JS-only route in the cluster.
- **`title` in every context dict** — never referenced by any page template; consumed by
  `base.html:5`. Not an unused context key.
- **`send_test.html` rendered without an explicit `title`** — false alarm; both call sites
  merge it via `**_send_test_context(db)` style dicts at `:254` and `:299`.
- **All 24 templates and all 65 routes.**

---

---

# Cluster 2 — `overrides` + `campaigns`

**Swept:** 2026-08-21 · `backend/app/overrides/` (372 loc) + `backend/app/campaigns/` (854 loc), both read in full
**Method:** every symbol, column and Pydantic field grepped across `backend/app/`, `backend/tests/`, `backend/scripts/` and `docs/`. `docs/backlog.md` cross-checked before every finding.

## Headline

**Almost no orphaned _code_ — but unlike Cluster 1, real orphaned _schema_.**

Every function in both modules is reachable, every route is registered and documented, and
the test suite carries **no residue of removed behaviour** (`tests/test_overrides.py` was
grepped for `pin`, `override_content_record`, `condition_category` and "Case 2" — zero hits;
it was rewritten cleanly during the 2026-07-15 rebuild).

What the two cut-backs left behind is at the **column** level. Three columns and one Pydantic
field lost their writers when record pins and "Case 2" were removed (`docs/backlog.md:212`,
Done 2026-07-15). Their only remaining writers are `scripts/*.sql` and
`scripts/seed_demo_data.py` — **seed SQL masks exactly this class of orphan from a naive
writer-grep.**

Second theme: **JSON-router / Pydantic drift** — two `campaigns` routes accept fields,
validate them, then throw them away before calling the service.

**The most consequential finding is not a deletion.** One orphaned column is the sole key of
a data-protection guard in another module, so that guard is currently inert for anything the
application creates.

**No N+1 exists in Cluster 2.** All `list_*` functions are single queries;
`create_module_for_variant` uses one `MAX(position)` aggregate; `move_module` is 2 queries +
3 flushes and cannot be reduced without breaking the temporary-slot dance it documents at
`campaigns/service.py:275-277`. That pattern lives in `frontend/router.py` (Cluster 1 #4-#7)
and `delivery/service.py` (P2-04), not here.

## To do

Ranked by loc saved ÷ risk. Unchecked = not started.

### Live bugs — additive fixes, zero risk

- [ ] **D1 (rank 1). `POST /campaigns/{campaign_id}/variants` silently discards `subject`
      and `preheader`.** `backend/app/campaigns/router.py:66-77` forwards only `name` and
      `status`. `VariantCreate` declares both fields (`campaigns/models.py:19-20`) and
      `create_variant_for_campaign` accepts both (`campaigns/service.py:91-92`). The **UI
      path is correct** — `frontend/router.py:783-789` passes them — so this is
      JSON-surface-only drift, which is why nobody has hit it.
      **Why it matters:** `docs/architecture/Code/campaigns.md` states `VariantDB.subject` is
      read by `send_send_instance` as the email subject, falling back to the send name. A
      machine-created variant therefore reproduces exactly the conflation
      `campaigns/db_models.py:27-31` says these fields were introduced to end.
      *+2 loc. Blast radius: one route. Risk: none — strictly additive, both default to
      `None`, no test covers this route.*

- [ ] **D2 (rank 2). `POST /campaigns/decision-slots/{id}/resolutions` silently discards
      `recipient_id` and `content_version_id`.** `backend/app/campaigns/router.py:176-191`.
      Both are declared (`campaigns/models.py:101,103`), both are accepted **and validated**
      by the service (`campaigns/service.py:404-405, 419-425`). A resolution posted for a
      specific recipient is stored as a non-personalized, NULL-recipient row.
      **Breaks two documented invariants:** `campaigns.md` says resolutions key off
      `recipients.id`, and that `providers` inbound reads `DecisionResolutionDB` to attribute
      engagement — so attribution breaks for any resolution created this way. Dropping
      `content_version_id` contradicts **ADR-062**.
      **Asymmetry:** the internal caller is correct (`decision/service.py:91-99` passes both).
      Only the public API is wrong.
      *+2 loc. Blast radius: one route. Risk: none as a fix — but see open question 6.*

### Free wins

- [ ] **S1 (rank 3). The content-XOR-slot rule is stated three times, two verbatim.**
      `backend/app/campaigns/service.py:164-168` and `:205-209` are byte-identical including
      the error message, plus the `CheckConstraint` at `campaigns/db_models.py:69-72`.
      `campaigns.md` calls the CHECK "load-bearing" and **ADR-083** governs it — a rule this
      load-bearing with two copies of its message means a future clarification lands in one
      and not the other.
      *~5 loc into one `_reject_content_and_slot(...)`. Risk: none. Cheapest item in the
      report. The DB CHECK stays — that is defence in depth, not a third duplicate.*

- [ ] **W1 (rank 4). Comment the ADR-041 carve-out and the cycle-breaking import.**
      See "Cross-module tension" below. Zero code change; it stops the next sweep re-raising
      a decision that was already made.
      *0 loc. Risk: none.*

- [ ] **R2 (rank 5). Delete the unreachable `send_instance_id` filter branch.**
      `backend/app/overrides/service.py:153-154`. `ContentOverrideDB.send_instance_id`
      (`overrides/db_models.py:60`) is never set by any code path in `backend/app/` — seed SQL
      only. So `list_content_overrides(send_instance_id=...)` and `GET /overrides/?send_instance_id=`
      filter on a column that is uniformly NULL for application-created rows. The branch can
      execute; it can only ever return zero rows.
      **Keep the column and the route param.** The `/overrides` JSON API is documented public
      surface and **ADR-142** makes machine-triggerable JSON actions a deliberate feature —
      removing the query param is an API break, not a cleanup.
      *~4 loc. Risk: none, scoped this way.*

- [ ] **D3 (rank 6). Inline the single-valued `field_name` parameter.**
      `backend/app/overrides/service.py:13` (signature), `:21` (interpolation), `:80` (sole
      call site, passing the literal `"system_content_record_id"`). The generalisation dates
      from the two-record-ID era — `docs/backlog.md:290` (Done 2026-07-12) records validating
      **both** IDs; the second was removed with record pins on 2026-07-15, the parameter that
      distinguished them was not.
      *2 loc. Risk: none — but **do R1 first**. If `system_content_record_id` is dropped the
      whole helper goes (~10 loc) and this is moot.*

- [ ] **R4 (rank 7). `ContentOverrideCreate.field_overrides` is optional in the schema and
      mandatory in the service.** `overrides/models.py:11` declares
      `dict[str, Any] | None = None`; `overrides/service.py:72-76` raises on a falsy value;
      `overrides/db_models.py:78-81` has a NOT NULL CHECK. The constraint is asserted in three
      places and optional in exactly one. The optionality dates from when a record pin alone
      made a valid override.
      *1 loc. Risk: moves a runtime 400 to a schema-boundary 422 on a public route;
      `tests/test_overrides.py:194` pins the current behaviour and needs updating.*
      **Note:** `not {}` is True, so the service catches the empty-dict case that a
      `| None` → required change alone would still let through. **The service check must stay.**

### Needs sequencing

- [ ] **S3 (rank 8). Blanket `except IntegrityError` misattributes any constraint failure.**
      `backend/app/overrides/service.py:94-102` reports every integrity error as "already has
      an active override" — an FK violation on `system_content_record_id` or
      `send_instance_id`, or the `ck_content_overrides_changes_something` CHECK, all land here.
      Same broad-catch class as the `except ValueError` at `delivery/service.py:383-387`
      (`docs/backlog.md` P3-03, now bundled into P0-02).
      *0 loc net — check `error.orig.diag.constraint_name` and re-raise otherwise. Risk: low;
      `tests/test_overrides.py:211` keeps passing.* **Do it with P0-02's typed-exception work.**

- [ ] **Q1 (rank 10). `create_decision_resolution` re-validates rows the caller already holds.**
      `backend/app/campaigns/service.py:413-425` — four existence SELECTs before every insert.
      Two are provably redundant on the hot path: `execute_decision_slot` has already loaded the
      `DecisionSlotDB` object (it reads `slot.decision_strategy` at `decision/service.py:44`),
      the strategy has already loaded the content record, and the recipient check duplicates
      the consent lookup at `decision/service.py:31-34`. In the send loop: 3-4 extra round
      trips per recipient per slot.
      *~6 loc via a pre-validated internal entry point. Queries per resolution 4 → 1. The
      public JSON route must keep full validation.*
      **Risk — read the comment first.** `campaigns/service.py:409-412` is explicit that this
      guards the silent-orphan bug class at `docs/backlog.md:290` "regardless of whether the DB
      engine happens to enforce FK constraints". The DB **is** Postgres
      (`backend/app/database.py:4`), but the comment is deliberately engine-agnostic for a
      reference architecture an adopter may re-point.
      **Overlaps `docs/backlog.md` P2-04** ("per-slot decision queries", parked in the
      "Bulk send: batching strategy + send-timing model" 📋 item). **Bundle with that work,
      do not raise independently.**

### Highest value — and it is not a deletion

- [ ] **R1 (rank 11). `ContentOverrideDB.system_content_record_id` has no writer left — and
      it is the sole key of a delete guard in `content/`.**
      Column at `backend/app/overrides/db_models.py:57`; Pydantic at `overrides/models.py:13, 23`;
      validated and assigned at `overrides/service.py:13-22, 79-80, 85`.
      **Consumer: `backend/app/content/service.py:491-492`.**

      Written by **nothing in `backend/app/`** — only `scripts/seed_override_events.sql:16,41`
      and `scripts/reset_all_data.sql:186`. The one UI producer,
      `content_override_create` (`frontend/router.py:990-999`), does not pass it.
      `POST /overrides/` accepts it but has no in-repo caller.

      **Why this outranks everything else:** `delete_content_record` refuses deletion when
      `ContentOverrideDB.system_content_record_id == content_id`. For any override created
      through the running application **that counter is always 0**. The stated protection —
      a content record with real history "can never be deleted, only its future use
      prevented" — is **inert outside seeded demo data**, surviving only via its
      `resolution_count` half.

      It lost its writer when record pins were removed, because the pin was what established
      *which* record was being deviated from. `docs/architecture/Code/overrides.md` calls it
      the "audit context for the trust loop"; `docs/backlog.md:212` calls it the counterfactual.

      *~4 loc to wire up (set it from the module's `content_record_id` in
      `content_override_create`); ~14 if dropped instead.*
      **Do not delete this one.** Dropping the column silently weakens
      `ContentRecordHasHistoryError` and deletes trust-loop design recorded in
      **ADR-040 / ADR-041**. It also mirrors the declared `AudienceOverrideDB` "reusable spine".
      **Unverified — name the check:** `overrides/db_models.py:54-56` says it may be left unset
      "for a per-recipient personalized module [where] the resolved record varies". If that
      holds, only the static-content path should set it, not the decision-slot path. A human
      must confirm the intent before wiring.

## Decide, don't delete

Declared-but-unimplemented capability, not residue. Deleting removes documented affordances
from a reference architecture; leaving them un-noted lets the API lie to users.

- **R5. `DecisionSlotDB.max_results` is written, exposed, and read by nothing.**
  Column `campaigns/db_models.py:86` (`default=1`); Pydantic `campaigns/models.py:75, 86`;
  service `campaigns/service.py:338, 365, 377`; route `campaigns/router.py:159`. Outside
  `app/campaigns/` it appears **only** in `scripts/reset_all_data.sql:136` and
  `scripts/seed_demo_data.py:186`. No strategy reads it; `decision/`, `rendering/`,
  `snapshots/` and `delivery/` do not. `execute_decision_slot` (`decision/service.py:51`) takes
  exactly one `result` and writes exactly one resolution row.
  **A slot saved with `max_results=3` silently behaves as 1.** Not in `docs/backlog.md`.
  *Recommended: neither delete nor implement — a comment pinning it to 1, or a validator
  rejecting `> 1`, until multi-pick exists. 0-7 loc.*

- **R3. `outcome_delta` / `record_outcome_delta` — consumer-free _and_ producer-free.**
  `overrides/service.py:160-183`, route `PATCH /overrides/{id}/outcome`
  (`overrides/router.py:58-63`), models `overrides/models.py:29, 35-36`, column
  `overrides/db_models.py:71`. 24 loc of row-locked (`with_for_update()`), merge-not-replace
  machinery — **both behaviours are fixes, not accidents**: the wholesale-replace bug is
  `docs/backlog.md:286` and the read-modify-write race is `:288`, both Done 2026-07-12.
  Nothing calls it; `rg 'outcome_delta' backend/app/templates/` returns **zero** hits
  (`campaign_detail.html:182-187` shows only the field-key summary and a reset button); its
  only exercise is `tests/test_overrides.py:256-265`.
  **The honest framing is not "dead code" but "the trust loop is modelled and has no
  producer".** See open fork F2. *0 loc recommended. Cutting it would delete an ADR-040/041
  deliverable and two fixed bugs' worth of concurrency correctness.*

- **S4. `DecisionSlotDB.decision_type` is rendered in three places and branched on nowhere.**
  `campaigns/db_models.py:82` (`default="content_recommendation"`), shown at
  `templates/decisions.html:37` and `decision_slot_detail.html:40` via
  `frontend/router.py:645, 1732, 1979`. Strategy selection goes through `decision_strategy`
  and the `pkgutil` registry. Unlike R5 it is **displayed truthfully**, so it reads as a
  reserved extension point rather than a lie. *Low confidence it is residue — noted only.*

- **S5. `CampaignDB.status` / `VariantDB.status` never transition.**
  `campaigns/db_models.py:11, 34`, both `default="draft"`. `rg '\.status = '` across
  `backend/app/` finds writers only in `content/`, `delivery/` and `recipients/` — never
  campaigns or variants. Both render as badges (`campaigns.html:43`,
  `campaign_detail.html:12, 26`), so the UI shows a field permanently reading "draft". A
  machine client *could* set it at create, but nothing ever changes it after, and there is no
  `delete_variant` or `delete_campaign` anywhere.
  *Pre-existing lifecycle gap, not override-churn residue.*

## Cross-module tension — report it, do not close it

**W1. `delete_module` hard-deletes override history that `content/service.py` declares
undeletable.** `backend/app/campaigns/service.py:225-242` removes **every** override row on
the module — `active=True` rows *and* `active=False` reverted history, including any recorded
`outcome_delta`.

Two modules give opposite answers about the same rows:

- `docs/architecture/Code/overrides.md`: *"**Reset keeps history** — `active=false` +
  `reverted_at`, **never a delete**, so the trust-loop comparison and `outcome_delta`
  survive (**ADR-041**'s 'used until deleted or reset')."*
- `backend/app/content/service.py:485-500` raises `ContentRecordHasHistoryError` rather than
  let override history vanish.
- `backend/app/campaigns/service.py:237-239` deletes it outright.

**But this was deliberate.** `docs/backlog.md:210` (Done 2026-07-15) records it — *"`delete_module`
(cascades the module's content overrides, which are meaningless without it…)"* — with a
verification note confirming the cascade covers active + reverted history. The UI is honest
too: `campaign_detail.html:205` reads *"Delete this module and its override?"*

**This is an ADR-041 question** — whether "never a delete" is absolute or has a module-lifetime
carve-out — **and an ADR beats tidiness.** The cheapest resolution is a comment naming the
carve-out (W1 in the to-do list). "Fixing" it the other way, by blocking module deletion when
an override exists, would break the Done 2026-07-15 feature.

**Secondary, resolves to leave-alone:** the function-local
`from app.overrides.db_models import ContentOverrideDB` at `campaigns/service.py:235` is the
only cross-module import written that way and looked like a style lapse. It is not —
`overrides/service.py:6` imports `app.campaigns.db_models`, so a module-level import creates a
**genuine cycle**. It should carry a comment saying so, as `_normalize_for_strategy` already
does at `campaigns/service.py:294-297`.

## Too large to be a cleanup item — open forks

### F1. Hand-written `to_*` converters vs `from_attributes`

`backend/app/campaigns/service.py` has five (`to_campaign:10`, `to_variant:20`,
`to_module_instance:128`, `to_decision_slot:329`, `to_decision_resolution:387`) — ~70 loc of
field-by-field mapping a single `model_config = ConfigDict(from_attributes=True)` would delete.

**But the direction is the opposite of what it looks like.** `rg -l 'from_attributes' backend/app/`
returns exactly one file: `overrides/models.py:32`. Project-wide the converter count is 5
(campaigns) + 3 (content) + 2 (delivery) + 1 each (snapshots, recipients, providers, insight)
= **14**. So `overrides/` — the newest, most recently rebuilt module — is the **outlier**, and
`campaigns/` follows a six-module convention.

~16 call sites project-wide, and it changes the return *type* of every service function (ORM
object vs Pydantic model), which several callers depend on. Noted as an option for the final
MVP package, not chased one module at a time. **Not ranked.**

### F2. The trust loop is modelled but has no producer

R3 (no `outcome_delta` writer or reader) + R1 (no counterfactual writer) + R2 (no send scoping)
are **one gap, not three**. `ContentOverrideDB` can record *that* a human overrode the system,
but nothing in the codebase can answer the question the whole layer exists to answer — *did the
edit outperform?*

Whether that gets a real computation path (a post-send job comparing engagement on overridden
vs system-governed modules) is a **product decision behind the ADR-040/041 story**, not a
slimming decision. `docs/backlog.md:93` already defers the *audience*-override half behind
Phase 3B; this is the content half of the same story. **Not ranked.**

## Open questions needing a human decision

1. **R1 direction.** Wire `system_content_record_id` up (restoring the `content/service.py`
   guard), or drop it and accept that override history no longer blocks content deletion?
   Opposite actions on the same ~14 loc.
2. **R1 scope, if wired.** Should the decision-slot path set it at all, given
   `overrides/db_models.py:54-56` says the resolved record varies per recipient — or
   static-content modules only?
3. **R5.** Is `max_results > 1` a real roadmap item, or should the field be pinned to 1 with a
   validator?
4. **W1.** Does ADR-041's "never a delete" have a module-lifetime carve-out?
   `docs/backlog.md:210` says yes in practice; the ADR and `overrides.md` say no in text.
5. **F2.** Is a trust-loop producer in scope, or is the model-only state the intended MVP
   endpoint?
6. **D2 exposure.** Is `POST /campaigns/decision-slots/{id}/resolutions` part of the ADR-142
   machine surface? If yes, D2 is a **live defect on a Mode B path**, not a latent one, and its
   priority rises above rank 2.

## Leave alone — looks dead, is not

- **All 5 `/overrides` routes and all 12 `/campaigns` routes.** Zero in-repo JSON callers is
  *normal* — they are documented public surface (`overrides.md` / `campaigns.md`), and
  **ADR-142** makes machine-triggerable JSON actions a deliberate product feature.
  `get_content_override` (`overrides/service.py:140`) and `record_outcome_delta` have no
  non-router caller **by design**.
- **`_normalize_for_strategy`'s lazy imports** (`campaigns/service.py:298-299`) —
  `decision/service.py` imports `campaigns.service`, so this breaks a **real** cycle. Its
  docstring says so. Unlike Cluster 1's 14 function-local AI imports, where the cycle
  hypothesis was ruled out, here it holds.
- **The function-local `ContentOverrideDB` import in `delete_module`**
  (`campaigns/service.py:235`) — same reason.
- **`ContentOverrideDB.reverted_at`** (`overrides/db_models.py:68`) — written by
  `reset_content_override`, read by no application code. It is an audit timestamp; being
  written and never read **is** the job.
- **The `postgresql_where` partial unique index** (`overrides/db_models.py:84-89`). Checked
  specifically because a SQLite backend would silently drop the `WHERE` clause, leaving "one
  active override per module" unenforced and making the `IntegrityError` branch at
  `overrides/service.py:94` unreachable. `backend/app/database.py:4` is `postgresql://…`.
  **The index exists and the branch is live.**
- **`delete_module` hard-deleting override history** — contradicts `overrides.md` and ADR-041
  in text, but is a deliberate carve-out recorded at `docs/backlog.md:210`. Report the missing
  comment, never the behaviour.
- **`to_module_instance` / `to_decision_slot` / `to_decision_resolution`** — all three are
  called from *outside* `campaigns/` (`decision/service.py`, `rendering/`).
- **`create_decision_resolution`** — despite Q1, it is on the hot path via
  `decision/service.py:91`, not router-only.
- **`update_variant` / `update_module` / `update_decision_slot`** — absent from the JSON router
  but live via `frontend/router.py:802, 847, 917`. An API-surface gap, not dead code.
- **Zero `relationship()` in the entire `app/`** — grepped; there are none anywhere. A
  project-wide convention, so its absence in `ModuleInstanceDB` is not missing wiring, and the
  manual cascade in `delete_module` is consistent with it. There is no `delete_variant` or
  `delete_campaign` at all, so no orphan risk exists above module level.
- **The `field_overrides IS NOT NULL` CHECK** alongside the service check
  (`overrides/db_models.py:78-81` + `overrides/service.py:72`) — deliberate defence in depth,
  and the comment says so.
- **`tests/test_overrides.py`** — 13 self-contained tests, no residue of removed behaviour.

**Findings dropped: 4**, all trivial style — an unsorted import block at
`campaigns/router.py:5-31`, a `Boolean` column / `.is_()` filter idiom mix, and two single-use
locals.

**Noticed out of scope, not filed:** `backend/app/database.py:4` hardcodes Postgres
credentials in source. Already covered as `docs/backlog.md` P2-09(b).

---

# Cluster 3 — `content` + `rendering`

**Swept:** 2026-08-21 · `backend/app/content/` (966 loc, 4 files) + `backend/app/rendering/` (387 loc, 3 files), both read in full
**Method:** every symbol, column, Pydantic field and `content`-JSON key grepped across `backend/app/`, `backend/scripts/`, `backend/tests/`, `storage/email_modules/` and `docs/`. Writers grepped separately from readers with `scripts/` excluded from the writer set (the Cluster 2 method). AST pass for unused imports. `docs/backlog.md` cross-checked before every finding.

## Headline

**No dead code and no orphaned schema.** All 26 `content/service.py` functions, all 16 `/content` routes, all 11 Pydantic models, all 5 rendering functions and the single `/rendering` route are reachable. Zero unused imports across all six files (AST-verified).

Three predicted targets that did **not** pay out — recorded so no one hunts them again:

1. **The `content` JSON blob is clean on both sides.** The six keys written by `content_create` / `content_edit` (`frontend/router.py:1381-1388`, `:1414-1421`) are *exactly* the six CMS manifest variables in `storage/email_modules/img_left.json`, `img_right.json` and `single_stack.json`. Set difference is empty in both directions.
2. **The content-schema redesign left no residue.** `docs/backlog.md:230` (Done 2026-07-12) dropped the `body` column for `content` JSON + `description`. Unlike the `overrides/` cut-backs, it was completed cleanly.
3. **`scripts/*.sql` and `seed_demo_data.py` are not the sole writer of anything in `content/`.** The Cluster 2 orphan pattern does not repeat here.

What the cluster carries instead is three themes: **missing DB constraints** (this is the one module in `backend/app/` with zero table-level constraints), **two override paths that agree on precedence but diverge on scoping**, and **one live ADR-062 contradiction** in what the snapshot records.

## The two override paths — the answer

Two independent implementations, **same precedence direction, two divergent scoping rules, and neither contradicts ADR-040 or ADR-041.**

**Path A — CMS modules**, `rendering/service.py:139-188`. Override → resolved content → `""`. Iterates `manifest.variables` and consults `field_overrides` only for **declared** variables.

**Path B — static modules**, `rendering/service.py:191-226`. Override → `module_data` → resolved content → absent. Iterates `field_overrides.items()` and writes **every** key into the Jinja context, including keys the manifest never declared.

**Both satisfy ADR-041**, whose Decision is that an override value is used until deleted or reset, with resolution order "override value, referenced content value, fallback if defined". Both put the override strictly first. The comment at `rendering/service.py:212-214` says so explicitly. **No violator to name** — this is a consistency finding, not an ADR finding.

Where they diverge:

1. **Override scoping.** A key not on the manifest is silently *dropped* on a CMS module and silently *accepted* on a static one. `field_overrides` is free-form JSON typed into a textarea — `content_override_create` (`frontend/router.py:975-987`) does `json.loads` and nothing else, and `ContentOverrideCreate.field_overrides` is `dict[str, Any]`. **So a typo'd override key behaves differently by module type, silently, with no feedback either way.** See D3.
2. **Rich text.** Path A applies `render_rich_text` at `:173-174`. Path B does not, at all. See D4.
3. **Wasted query.** Path A fetches the override at `:149`, before it knows whether content resolved; on the ADR-086 hidden-slot return at `:155-160` the override and its query are discarded. One wasted query per hidden slot.

## To do

Ranked by payoff ÷ risk. **Most of this cluster's value is correctness per loc, not deletion** — several top items *add* lines.

### Missing DB constraints — the systemic gap

`backend/app/content/db_models.py` is the **only module in `backend/app/` with zero table-level constraints** — no `__table_args__`, no `UniqueConstraint`, no `CheckConstraint`, no FK index. `auth`, `audience`, `campaigns`, `insight`, `overrides` and `recipients` all have them. `docs/backlog.md:294` (Done 2026-07-12) fixed the byte-identical case in `audience/service.py`, and its own note reads: *"worth checking whether other `create_*` functions across the codebase have the same silent-orphan gap once this is fixed, since it's likely a systemic pattern."* **Content is the module that check never reached.**

- [ ] **C3 (rank 1). The cycle guard only runs for one `relation_type` value.**
      `backend/app/content/service.py:284` runs the acyclicity check only
      `if relation_type == "parent_child"` — but `_would_create_cycle` (`:268-272`),
      `list_parent_relations_for_category` (`:313-317`), `list_child_relations_for_category`
      (`:326-330`) and the category-graph UI all traverse **every** row regardless of type.
      So `POST /content/category-relations` with `{"relation_type": "sibling"}` creates an
      **unguarded edge that is then walked as a hierarchy edge**, breaking the invariant
      `docs/architecture/Code/content.md` states as *"The category graph is acyclic."*
      Grepped across `backend/app/`, `scripts/`, `tests/` and `docs/`: the only value that has
      ever existed is `"parent_child"`.
      Same shape as Cluster 2's R5 `max_results`, but **strictly worse** — `max_results=3`
      silently under-delivers; this silently disables a guard.
      *−1 loc. Blast radius: one condition. Risk: none — it makes the guard stricter, and no
      non-`parent_child` row exists anywhere.* **Cheapest correctness win in the report.**
      Do **not** bundle the "should other relation types be rejected?" question into this —
      see open question 5.

- [ ] **C2 (rank 2). No index on any content FK, on the hot render path.**
      `content/db_models.py:45` (`content_versions.content_record_id`), `:36-37`
      (`content_category_assignments.content_id`, `.category_id`).
      `resolve_renderable_content` (`rendering/service.py:266-272`) filters `content_versions`
      on `content_record_id` with `ORDER BY version_number DESC` **once per module, per
      recipient, per send** — and `send_send_instance` renders per recipient since
      `docs/backlog.md:266`. In-repo precedent is explicit: `overrides/db_models.py:48` sets
      `index=True` on `module_instance_id` for exactly this lookup.
      *+2 loc. Blast radius: none in code.*
      **Risk:** `index=True` only takes effect on a fresh `create_all`. On an existing database
      this is a **silent no-op that looks fixed** — needs manual DDL. See the Unverified list.

- [x] **C1 (rank 3). `ContentCategoryAssignmentDB` has no unique constraint on
      `(content_id, category_id)`.** `content/db_models.py:33-38`. The duplicate check at
      `content/service.py:366-375` is check-then-insert with no DB backstop — a TOCTOU.
      `docs/backlog.md:294` fixed the identical race in `audience/service.py` with
      `uq_audience_group_members_group_recipient`; `:250` did the same for
      `RecipientPreferenceDB`. Both Done 2026-07-12. Content was missed.
      *~4 loc. Blast radius: one table, one 409 path. No caller signatures change.*
      **Risk:** duplicate rows may already exist, and `create_all` does not add constraints to
      an existing table — **run the GROUP BY check first** (see Unverified). Keep the SELECT as
      the fast path and add `except IntegrityError` — the defence-in-depth shape Cluster 2
      recommended keeping at `overrides/db_models.py:78-81`. No test covers this function.

 **✅ Promoted to `docs/backlog.md` 2026-08-21 — track it there, not here.**
- [x] **C5 (rank 4). `create_content_version` computes `version_number` read-then-insert with
      no unique constraint.** `content/service.py:411-429`. Two concurrent publishes produce
      two rows with the same `version_number`, after which
      `resolve_renderable_content`'s `ORDER BY version_number DESC ... .first()` picks one
      **arbitrarily** — and **ADR-128** makes versions the audit answer to "what exact content
      did this recipient receive at send time?". Directly comparable to `docs/backlog.md:222`,
      which added `uq_module_instances_variant_position` for the identical ambiguity.
      *~6 loc. Blast radius: one table, one route, one UI action.*
      **Risk: low today** — publish is a manual click, so the window is narrow. **But the
      "publish all" Feature at `docs/backlog.md:97` would make concurrent publishes routine.
      Do this before that feature ships, not after.**

### The ADR-062 gap

 **✅ Promoted to `docs/backlog.md` 2026-08-21 — track it there, not here.**
- [ ] **D1 + D2 (rank 5) — do them together. The snapshot does not record overrides, and
      rendering gives the caller no non-racing way to record them.**

      **D1.** ADR-062's Decision requires a snapshot to store *"final HTML, resolved content
      data, content references, **overrides**, metadata, render timestamp…"*.
      `render_variant_html` (`rendering/service.py:63-119`) returns
      `resolutions_by_module_id` when `collect_resolutions=True`, but the override it fetched
      at `:149` / `:215` is applied to the HTML and then **discarded**.
      `build_render_context` (`snapshots/service.py:50-92`) assembles a nine-key context per
      module with **no override reference and no resolved content data**.
      So a snapshot whose HTML was materially changed by a manager's override records nothing
      about it — the audit artefact cannot answer *why the HTML says this*, which is the entire
      ADR-062 claim. It also un-implements the audit end of Cluster 2's **F2**: you cannot
      compare overridden against system-governed output if the snapshot does not say which
      is which.

      **D2.** The same race `docs/backlog.md:240` closed for decision slots is **still open for
      static content**. Rendering resolves the latest `ContentVersionDB` at
      `rendering/service.py:266-272`; `build_render_context` then **independently** calls
      `get_latest_version_for_content` at `snapshots/service.py:79-83` for the same module.
      Publish a new version between them and the snapshot's `content_version_id` names a
      version that is not in its own HTML. The comment at `snapshots/service.py:63-68` spells
      out why this must not happen — and the `elif` eleven lines below does precisely that.

      **The mechanism already exists in this file.** `collect_resolutions` was added for the
      identical problem (`docs/backlog.md:240`, Done 2026-07-12). This is the same fix, two
      fields wider.
      *+12 loc total. Blast radius: `render_variant_html`'s return tuple — `rendering.md`
      flags that signature as load-bearing for `delivery.send_send_instance`
      (`delivery/service.py:396`) and `snapshots.create_snapshot_for_variant`
      (`snapshots/service.py:98`). `frontend/router.py:273` and `rendering/router.py:23` call
      it without the flag and are unaffected. `render_context` is a JSON column — no schema
      change.*
      **Risk / sequencing: cross-reference `docs/backlog.md:158`** — the 📋 item recording
      P1-04/P2-06, *"the snapshot is described as the immutable final state but is not what
      gets sent"*. If that is resolved by re-pointing send **at** the snapshot, this turns
      from a latent audit hole into a compliance-grade one. **Sequence D1 with `:158`, not
      before it** — doing D1 first means designing the render-context shape twice.
      **Do not split D1 from D2** — same return-value widening; splitting means touching the
      load-bearing signature twice.

### Consistency and cost

- [ ] **D3 (rank 6). Unify the two override-application rules into one
      `_apply_field_overrides(variables, manifest, override)`.**
      `rendering/service.py:162-171` versus `:215-218`. Full analysis above.
      *−6 loc. Blast radius: two functions, one file; no signature change outside `rendering/`.*
      **Risk: this is a judgment call, not a mechanical merge, and it needs open question 4
      answered first.** Unifying on the manifest-scoped rule would stop static modules
      receiving overrides for keys their `module_data` legitimately carries but the manifest
      omits — **check `scripts/reset_all_data.sql:151-154` first**, which gives `cta` modules a
      `button_label` key the `cta` manifest does not declare. Unifying on the permissive rule
      means CMS modules start accepting junk keys. No test covers either path.

- [ ] **D5 (rank 7). Cache `get_template_html` behind the mtime gate the manifests already
      use.** `rendering/service.py:176` and `:197` call it per module per render;
      `email_modules/registry.py:106-110` does an uncached `Path.exists()` + `read_text()`
      every call, and `get_manifest` (`:96-98`) calls `_ensure_fresh` → `_dir_mtime`, which
      **stats every file in `storage/email_modules/`** per call.
      `docs/backlog.md:238` (Done 2026-07-12) added `@lru_cache(maxsize=1)` to
      `_load_brand_css` for precisely this reason, and `send_send_instance` now **does** render
      per recipient (`docs/backlog.md:266`). The brand CSS was cached; the module templates
      were left behind, two functions away in the same call path.
      *+4 loc.*
      **Risk:** `_ensure_fresh`'s mtime check is what makes hot-editing a module template work
      in dev without a restart. Caching template HTML **without** hooking it to that gate
      breaks the edit-refresh loop that makes `storage/email_modules/` a usable seam. **Reuse
      the existing invalidation, do not add a bare `lru_cache`.** **ASSESSED — Cluster 7:** yes, behind the mtime gate.
      `_load_brand_css`'s bare `lru_cache` already makes `brand.css` un-hot-editable, so the
      directory has two contradictory policies today. See Cluster 7's answer 3.

- [ ] **S3 (rank 8). `create_demo_content_if_empty` writes 3 of the 6 CMS keys.**
      `content/service.py:147-176` writes `headline_medium`, `body_medium`, `button_label`
      only, so the three worked-example modules render `<a href="">` and an empty `<img src="">`
      **on the first boot of a fresh install** (`main.py:202` calls it on startup).
      The real signal is that the three writers disagree: this writes 3,
      `scripts/reset_all_data.sql:44-48` writes 4, `scripts/seed_demo_data.py:106-109` writes 4.
      No single definition of "a complete demo content record" exists.
      *+3 loc. Blast radius: first-boot demo data only — guarded by the `existing_count > 0`
      early return at `:142-145`. Risk: none.*

### Blocked on a decision or a check

- [ ] **C4 (rank 9). `CategoryDB.name` has no uniqueness of any kind.**
      `content/db_models.py:17-22`; `create_category` (`service.py:215-233`) inserts
      unconditionally with **no duplicate check at all**. `docs/backlog.md:296` fixed exactly
      this for `AudienceGroupDB.name` including the case-insensitive half — visible at
      `audience/db_models.py:29` as `Index("ux_audience_groups_name_lower", func.lower(name), unique=True)`.
      Categories are what decision strategies filter on (`candidate_filter.category_ids`) and
      what `insight` scores against, so **two "Beach" categories split the personalization
      signal silently**.
      *+3 loc, mirroring the audience index. Needs open question 2 first.*

- [ ] **D4 (rank 10). Rich text is CMS-only, keyed off one hardcoded field name.**
      `rendering/service.py:37` (`_RICH_TEXT_FIELD = "body_medium"`), applied at `:173-174`
      and nowhere in `render_static_module`. `hero`'s `text` variable is long-form copy by
      design and never gets `**bold**` or `[label](url)`. A manager has no way to tell which
      fields support formatting — the manifest does not say and the UI does not say.
      This re-hardcodes a CMS field name in the rendering layer, the same coupling
      `docs/backlog.md:230` claims to have removed (*"resolves the root cause of the hardcoded
      `headline_medium`/`body_medium` alias patch"*). One alias patch out, one field constant
      in. It also sits against `rendering.md`'s *"variable name = CMS field name exactly — no
      mapping layer"*, being a mapping layer with exactly one entry.
      **The seam exists and is unused:** `ModuleVariable` (`email_modules/registry.py:13-16`)
      carries only `name` and `required`. A `rich_text: bool = False` flag puts the decision
      with the module author, where the other per-variable metadata already lives.
      *+7 loc — smaller than the change that introduced the constant.*
      **Risk:** changes the manifest contract, so an adopter's custom manifest without the key
      must keep working — the default **must** be `False`, mirroring `v.get("required", True)`.
      **ASSESSED — Cluster 7:** right shape, cannot break an adopter's manifest — but it is a
      four-file change with a **mandatory same-commit edit to three manifests**, or `body_medium`
      silently stops rendering markdown on a live send. See Cluster 7's answer 2.

- [ ] **S1 (rank 11). `data-content-id` is emitted only by the CMS path.**
      `rendering/service.py:183-184` (CMS: `data-module-id`, `data-module-type`,
      `data-content-id`) versus `:223` and `:231` (first two only). A repo-wide grep returns
      **only these three lines** — no parser, no template, no test, no doc.
      **Do not delete these.** They are almost certainly deliberate click-attribution hooks for
      the `providers` inbound → `insight` path, and zero readers is the expected state for an
      instrumentation seam in a reference architecture. The reportable half is only the
      **asymmetry**: a static module bound to a content record resolves it at `:206` but never
      labels it, so any consumer built on these attributes attributes static-module clicks to
      nothing.
      *+1 loc. Blast radius: the HTML shape of static modules — changes future snapshots, not
      past ones.* **Unverified — see the checks list.**

- [ ] **D6 (rank 12). Per-module override and content queries inside the render loop.**
      `rendering/service.py:70-84` plus `:92` — roughly `1 + 3M` queries per render for `M`
      modules, multiplied by recipient count at send.
      **This is not P2-04** (that names the per-recipient recipient load, per-slot decision
      queries, per-recipient commit and the blocking 15s `httpx.post` in `delivery/service.py`).
      But it is the same send-loop cost centre. **Bundle it into P2-04's 📋 "Bulk send"
      item; do not raise independently** — same call Cluster 2 made for its Q1.
      *~0 net. A `get_active_content_overrides_for_modules(module_ids)` batch collapses `M`
      override queries to 1, but that function belongs in `overrides/service.py`.*
      **Risk:** batching changes the lookup from "current when that module renders" to "current
      at loop start", which should be checked against the ad-hoc `with_for_update()` in
      `send_send_instance` the backlog already flags as unconvention'd.

- [ ] **D7 (rank 13). `POST /content/versions` takes its parent id in the body; every other
      nested content route uses the path.** `content/router.py:189-201`, with
      `ContentVersionCreate.content_record_id` at `content/models.py:57`. The *same resource*
      is read via a path parameter (`GET /content/{content_record_id}/versions`, `:204`) and
      written via a body field.
      Cosmetic alone — it matters because this router's registration-order invariant is
      load-bearing and hand-guarded by two comments (`:50-54`, `:65-66`) documenting a bug that
      already happened. An inconsistent route shape is how the next route lands in the wrong
      place. *(Current ordering verified correct.)*
      *+4 loc. Risk: an API break unless the old route is kept alongside — ADR-142 makes these
      deliberate machine surface. Lowest-value item here; listed for completeness.*

## Decide, don't delete

- **S2. `content.md` advertises version *restore*; no restore exists.** A case-insensitive grep
  for `restore` across all of `backend/app/` returns **zero hits**. **ADR-128 (Accepted)** is
  titled *"Version Content for Auditability and Restoration"* and specifies the mechanism
  concretely — restoring version 2 creates version 5 with version 2's content.
  `ContentVersionDB` is fully live and read by `rendering`, `snapshots` and both decision
  strategies, so nothing is dead — only the affordance is missing.
  *~12 loc to implement (`create_content_version` already does the hard half), or 1 loc to
  correct the doc.* **The doc is the only thing wrong today, but "fixing" it by deleting the
  claim quietly drops a deliverable of an Accepted ADR.** See open question 1.
- **C3's second half — `relation_type` as a taxonomy dimension.** Once the guard hole is closed,
  whether `sibling` / `related_to` are a roadmap item or should be rejected by a validator is
  the same question as Cluster 2's R5, and deserves the same treatment.
- **C4 — category name uniqueness.** Whether the taxonomy is a flat unique namespace or
  brand-scoped is a product decision. `docs/backlog.md:252` records exactly this reasoning
  being used to *defer* email uniqueness on `RecipientDB` — there is precedent for deferring.
- **S1 — the `data-*` attributes.** The decision is whether the static path should participate,
  not whether the attributes should exist.

## Genuine residue to delete

**There is none.** No dead function, route, model, column, JSON key, import or file in either
directory. The only deletions recommended anywhere in this section are **one condition** (C3,
−1 loc) and **six lines of duplication** (D3) — and D3 is a merge, not a removal.

**Second cluster running where the expected residue was absent.** Recorded so the next sweep
does not go looking again.

## Open forks

**None originate in this cluster.** Two existing forks touch it:

- **Cluster 2's F1** (hand-written `to_*` converters vs `from_attributes`). `content/`
  contributes three of the fourteen — `to_content_record` (`service.py:33`),
  `to_category_relation` (`:236`), `to_content_version` (`:390`). One local wrinkle worth
  folding into that fork: `assign_category_to_content` (`:353-387`) is the module's **sole
  service function returning a raw ORM object**, forcing `content/router.py:181-186` to
  hand-build the Pydantic model — so `content/` is internally inconsistent as well as
  project-inconsistent. Do not chase it alone.
- **Cluster 2's F2** (the trust loop is modelled with no producer). **D1 is the audit-side face
  of the same gap** — even if a producer were built, the snapshot does not record which output
  was overridden, so "did the edit outperform?" stays unanswerable. Fold into F2's framing
  rather than tracking separately.

`category_graph` is already an open fork from Cluster 1 and is a `frontend/` problem. Not
re-raised — though note it reads `CategoryRelationDB` and `CategoryDB` directly rather than
through `content/service.py`.

## Open questions needing a human decision

1. **S2 direction.** Implement version restore per ADR-128 (~12 loc), or correct `content.md`
   to stop claiming it? The ADR is **Accepted**, which argues for the former.
2. **C4.** Should category names be unique, case-insensitively as `AudienceGroupDB` now is —
   or is a repeating name legitimate under a future brand-scoped taxonomy, making this a defer
   (the `docs/backlog.md:252` precedent)?
3. **D4.** Does `rich_text` belong on the manifest, making it the module author's call, or is
   `body_medium` the intended permanent single rich-text field? **The second answer is fine —
   it just needs a comment, so the next sweep stops re-flagging it.**
4. **D3.** Which override-scoping rule wins — manifest-declared keys only (CMS, stricter) or
   all keys (static, permissive)? Note `scripts/reset_all_data.sql:151-154` relies on `cta`
   carrying a `button_label` key its manifest does not declare, which is **evidence for the
   permissive rule**.
5. **C3 scope.** After the guard is unconditional, pin `relation_type` to `"parent_child"` with
   a validator, or keep it open as a reserved extension point?
6. **D1 sequencing.** Is `docs/backlog.md:158` (P1-04/P2-06) being resolved by re-pointing send
   at the snapshot? If yes, D1 rises sharply — the missing override reference becomes a
   compliance-grade audit hole rather than a latent one.

## Unverified — the specific checks a human should run

- **C1.** Run `SELECT content_id, category_id, count(*) FROM content_category_assignments GROUP BY 1,2 HAVING count(*) > 1`
  against the live database **and** against a fresh `scripts/reset_all_data.sql` restore before
  adding the constraint.
- **C1 / C2 / C4 / C5 — all of them.** Confirm how schema changes reach an **existing** database
  in this project. No migration tool was found and `content.md` implies there is none, so every
  constraint and index above needs a manual DDL step or it exists only on fresh installs. **If
  that assumption is wrong, several risk notes soften.**
- **S1.** Confirm no external tracking, QA or link-rewriting tooling **outside this repo** parses
  `data-module-id` / `data-content-id`, or relies on `data-content-id` appearing only on CMS
  modules. An in-repo grep cannot answer this.
- **D5.** Confirm that hot-editing a file in `storage/email_modules/` and refreshing a preview is
  a workflow anyone actually relies on. If not, the caching fix is simpler.
- **Cluster 7 boundary.** D4 and D5 both land in `email_modules/`, unswept. Its invariants may
  constrain both fixes in ways the caller side cannot see.

## Leave alone — looks dead, is not

Checked exhaustively, not sampled. **Do not re-run reachability on this cluster.**

- **All 16 `/content` routes and the 1 `/rendering` route.** Zero in-repo JSON callers is normal
  — documented public surface, **ADR-142**.
- **All 26 `content/service.py` functions.** The four `list_*` functions are router-only **by
  design**. `get_latest_version_for_content` is called from `snapshots/service.py:80` **and from
  both decision strategies** (`decision/strategies/top_score.py:64`,
  `recipient_top_score.py:126`) — which are `pkgutil`-discovered with no static importer, so a
  naive caller-count makes it look thinner than it is.
- **All 11 Pydantic models in `content/models.py`** — all imported by `content/router.py:5-17`.
- **Zero unused imports in all six files.** AST-verified. Do not re-check.
- **All 22 columns across the five content tables** have a live application writer.
- **`CategoryDB.parent_category_id` is genuinely gone** from `db_models.py` *and* all three seed
  scripts — the drift `content.md` warns about (a stale `reset_all_data.sql` breaking baseline
  restore) is **closed**. Verified because the doc explicitly asks for it.
- **`render_static_module` raising `UnpublishedContentError`** for a content-linked static module
  whose `module_data` is already complete (`rendering/service.py:206` → `:277-278`). Looks
  over-strict; it is the deliberate outcome of `docs/backlog.md:224`.
- **`resolve_content_for_module` silently preferring `content_record_id` when both FKs are set**
  (`rendering/service.py:307-315`). Documented at `campaigns/db_models.py:68` and settled by the
  mutual-exclusivity CHECK from `docs/backlog.md:276`.
- **`_load_brand_css`'s `lru_cache(maxsize=1)`** (`rendering/service.py:42-46`) — deliberate,
  `docs/backlog.md:238`.
- **`render_rich_text` and its two module-level regexes** (`rendering/service.py:38-39, 49-60`) —
  the controlled formatting mechanism promised when autoescaping was turned on
  (`docs/backlog.md:220`). Its narrow *scope* is D4; its *existence* is a fix, and the
  escape-first ordering at `:56` is the security property.
- **`render_unknown_module`** (`rendering/service.py:229-234`) — called from `:131`, `:178`,
  `:199`; the graceful-degradation path for a module type with no manifest or template.
  `docs/backlog.md:240`'s verification note records it catching a real seeded `content_card`
  module with no template.
- **`_would_create_cycle`'s iterative DFS with a `visited` set** (`content/service.py:246-275`) —
  reads over-built for a small taxonomy, but it is the only enforcement of the acyclic
  invariant. C3 is about *when it runs*, not the algorithm.
- **`CategoryDB.type`** — branched on at `frontend/router.py:2470, 2476`, ordered by at `:1464,
  :2240`. Live.
- **`ContentRecordDB.status` and `CONTENT_STATUSES`** (`content/service.py:47-51`) — two values,
  and the comment says the restricted vocabulary is deliberate pending the data-lifecycle ADR.
  Not an unfinished enum.
- **`ContentVersionDB.created_by`** — written from the publish form
  (`frontend/router.py:1428-1434`), no in-code reader. An audit attribution field; being written
  and not read **is** the job — same call Cluster 2 made for `ContentOverrideDB.reverted_at`.
- **`ContentRecordHasHistoryError`'s override half being inert** (`content/service.py:490-494`) —
  **already filed as Cluster 2 R1.** Deliberately not re-raised.
- **The bulk `.delete()` / `.update()` calls** in `delete_content_record` (`:530-538`) and
  `delete_category` (`:581-587`) — consistent with the project-wide zero-`relationship()`
  convention confirmed in Cluster 2. The manual cascade **is** the convention.
- **The route-ordering comments at `content/router.py:50-54` and `:65-66`** — they document a
  real bug that happened, and the ordering is currently correct. **Do not "tidy" this router by
  sorting its routes.**
- **`record.content or {}` on a `nullable=False` column** (`content/service.py:38, 427`,
  `rendering/service.py:275, 288`) — defensive, harmless, three lines.
- **No tests exist for `content/` or `rendering/`.** `backend/tests/` holds ten files, none
  covering either module. That is the standing risk under *every* finding above, not a separate
  finding.

**Findings dropped: 3**, all trivial style — missing `ORDER BY` on two `list_*` functions whose
callers sort anyway; the `record.content or {}` idiom; and inconsistent `created_at` presence
across the five tables.

**Noticed out of scope, not filed:** `scripts/reset_all_data.sql:151, 154` and
`scripts/seed_demo_data.py:192` give `cta` modules `module_data={"button_label": …}`, but
`storage/email_modules/cta.json` declares `label` and `url`. **The seeded CTA renders
`<a href="">` with an empty label on every demo send.** Rendering is behaving exactly as
specified — the seed drifted from the manifest. Belongs to `scripts/`, and it is the concrete
case arguing for D3's permissive rule.

---

# Cluster 4 — `insight` + `recipients`

**Swept:** 2026-08-21 · `backend/app/insight/` (290 loc, 5 files) + `backend/app/recipients/` (598 loc, 5 files), both read in full
**Method:** every symbol, column and Pydantic field grepped across `backend/app/`, `backend/scripts/`, `backend/tests/` and `docs/`; writers grepped separately from readers with `scripts/` excluded from the writer set (the Cluster 2 method); AST pass for unused imports; `docs/backlog.md` cross-checked before every finding.

## The table-status question — answered first, because the brief's premise is wrong

The working premise was that `RecipientPreferenceDB` was dropped and `preference_update_logs` replaced by contributions, making this prime dead-code territory. **The first half is true and complete; the second half is true and complete. Neither table was "retired in name only" — both are gone from the code entirely, and there is no coexistence and no half-migrated read anywhere in `backend/app/`.**

### What is declared

| Model / table | Declared where | Status |
|---|---|---|
| `SignalContributionDB` / `signal_contributions` | `backend/app/recipients/db_models.py:56-90` | **Live and authoritative** |
| `EngagementEventDB` / `engagement_events` | `backend/app/insight/db_models.py:6-26` | Live |
| `RecipientDB` / `recipients` | `backend/app/recipients/db_models.py:6-27` | Live |
| `ConsentSyncLogDB` / `consent_sync_logs` | `backend/app/recipients/db_models.py:30-53` | Live |
| `RecipientPreferenceDB` / `recipient_preferences` | **nowhere** | **Does not exist** |
| `PreferenceUpdateLogDB` / `preference_update_logs` | **nowhere** | **Does not exist** |

A repo-wide grep for `RecipientPreferenceDB`, `PreferenceUpdateLogDB`, `recipient_preferences` and `preference_update_logs` returns **zero hits under `backend/app/`**. The only hits anywhere are:

- `backend/app/recipients/db_models.py:61` — a *docstring* in `SignalContributionDB` explaining what it evolved from. Documentation, not a reference.
- `backend/scripts/reset_poc_data.sql:15, 18, 95` — real SQL against both dropped tables (finding **R1**).
- `backend/scripts/reset_all_data.sql:163` — a stale comment (finding **R3**).
- `docs/` — ADR-132, the module pages, the backlog, the ADR-drift report, the interview-prep notes. All historical.

### Writers, with `backend/scripts/` excluded

`signal_contributions` has **exactly one application writer**: `record_contribution` (`backend/app/insight/signals.py:83-95`). It is reached from precisely two places:

- `apply_event_to_signals` → `backend/app/insight/service.py:150` (the engagement path, called by `providers/service.py:180` on webhook)
- `create_recipient_preference` → `backend/app/recipients/service.py:261` (the declared/manual path)

Excluded from that set as seed-only, per the Cluster 2 method: `backend/scripts/seed_demo_data.py:150, 163` (direct `SignalContributionDB(...)` construction) and `backend/scripts/reset_all_data.sql:107`. **Unlike Cluster 2, removing the seed writers leaves live application writers behind — so this is not the orphaned-schema pattern.**

`engagement_events` writers: `create_engagement_event` (`insight/service.py:41-52`), called from `insight/router.py:22` and `providers/service.py:79`.

`recipient_preferences` and `preference_update_logs` writers: **none, in `app/` or `scripts/` — the tables they would write to do not exist.** (`reset_poc_data.sql` attempts to; it aborts, see R1.)

### Readers

`signal_contributions` readers, all live:

- `backend/app/insight/signals.py:108, 128, 151` — the three decay-fold functions
- `backend/app/insight/service.py:138` — the dedup guard in `apply_event_to_signals`
- `backend/app/frontend/router.py:427, 1272, 1600-1605, 2157, 2288-2294, 2415` — recipient detail, category detail, the category graph, delivery detail
- `backend/app/audience/service.py:168` — via `operational_signals_for_category`, the criteria min-score gate
- `backend/app/decision/strategies/recipient_top_score.py:73` — via `operational_signals_for_recipient`
- `backend/tests/test_signals.py` — 8 tests

`recipient_preferences` / `preference_update_logs` readers: **none.**

### Did one supersede the other, or do they coexist?

**Genuine supersession, cleanly completed in `backend/app/`.** `docs/backlog.md:208` (Done, 2026-07-15) records it: `RecipientPreferenceDB` — the mutable running total — was **dropped**, `PreferenceUpdateLogDB` was **evolved into** `SignalContributionDB` (`base_weight` replaces `delta`; `contribution_type` replaces `reason`; `previous_score`/`new_score` are gone because there is no total; `occurred_at` is added as the decay basis), and every consumer was re-pointed at `get_operational_signal` / `operational_signals_for_*`. `ADR-132 §6` is the governing decision. The `SignalContributionDB` docstring at `recipients/db_models.py:58-66` states the mapping field by field.

**Authoritative model now: `SignalContributionDB`, unambiguously.** There is no second source of truth for recipient↔category affinity, no stored running total anywhere, and nothing reads a preference row because no preference row exists.

### The two pieces of counter-evidence in the brief — both were misreadings

Recorded in detail so no future sweep re-opens this.

1. **Cluster 3 cited `recipients/db_models.py:71-72` as "indexing both FKs on a live preference table".** Those two lines are real and do index two FKs — but they are `SignalContributionDB.recipient_id` and `SignalContributionDB.category_id`. The table is `signal_contributions`. There is no live preference table.
2. **Cluster 3 cited `docs/backlog.md:250` as having added a unique constraint to `RecipientPreferenceDB`.** True, and Done **2026-07-12** — the table was dropped **2026-07-15**, three days later (`docs/backlog.md:208`). The constraint went with it. Its only surviving trace is the unused `UniqueConstraint` import (finding **R2**), which is why that import is worth reporting rather than just deleting silently.
3. **Cluster 1 cited `frontend/router.py:2503-2504` as computing `AVG(PreferenceUpdateLogDB.delta)`.** It computes nothing. Those lines read two keys named `total_delta` and `avg_delta` off an already-built dict. The actual aggregate is `func.avg(SignalContributionDB.base_weight)` at `frontend/router.py:2291`, alongside `func.count(SignalContributionDB.id)` at `:2289` and `func.coalesce(func.sum(SignalContributionDB.base_weight), 0)` at `:2290`. **The fossil is the variable naming, not the query** — see finding **N1**.

### Where the residue actually is

**`backend/scripts/`, and it is the inverse of Cluster 2.** Cluster 2 found application *columns* kept alive only by seed SQL. Here the application is clean and the *scripts* are stale: one whole file that cannot run (R1) and one misleading comment in a file that can (R3).

**Reporting the negative plainly, as asked:** this is the **third cluster running** where the expected residue was largely absent. `insight/` and `recipients/` carry **one dead file, one dead import and one stale comment** — and one live defect that has nothing to do with the migration (C1).

---

## Headline

Beyond the table question, the cluster carries four themes:

1. **The Settings screen's signal-*weight* editor is inert** (C1). It persists a config row that no writer reads, because `apply_event_to_signals` reads the module-level constant instead of the merged config. The half-life editor beside it works. This contradicts a **Done** claim in `docs/backlog.md:206`, whose verification note tested only the half-life half.
2. **The missing-constraint pattern Cluster 3 named as systemic continues here, in its harder form** — both modules have *partial* coverage (`insight/db_models.py:22-26` has a `UniqueConstraint`; `recipients/db_models.py` has `unique=True` and four `index=True`), so the gaps sit beside genuine awareness rather than in a module with none.
3. **Three query-cost findings**, one of which (Q2) is a correctness issue, not just cost.
4. **Vocabulary residue**: the modules still speak "preference" for a model ADR-132 renamed.

---

## To do

Ranked by payoff ÷ risk. Unchecked = not started.

### Confirmed — live defect

- [x] **C1 (rank 1). Editing a signal *weight* in Settings changes nothing. The half-life editor beside it works.**
      `backend/app/insight/service.py:92` reads `CONTRIBUTION_WEIGHTS[event.event_type]` — the **module-level dict** at `backend/app/insight/signals.py:22-29` — not `get_signal_weights(db)`.

      **Evidence, full trace of the config path:**
      - `backend/app/frontend/router.py:220` persists the form under `SIGNAL_WEIGHTS`.
      - `backend/app/settings/service.py:59-62` `get_signal_weights` merges the stored override over the code defaults.
      - `get_signal_weights` has exactly **two** consumers, repo-wide: `frontend/router.py:81` (re-displaying the form) and `backend/app/insight/signals.py:76-82` — the `if base_weight is None` fallback inside `record_contribution`.
      - **Both callers of `record_contribution` pass `base_weight` explicitly** — `insight/service.py:158` (`base_weight=category_weight`) and `recipients/service.py:267` (`base_weight=score`). So the fallback branch has **no in-app caller**, and the stored weight override reaches nothing at all.

      Half-lives are unaffected because they are applied **on read**: `_configured_half_lives` (`signals.py:54-59`) is called by all three of `get_operational_signal`, `operational_signals_for_recipient` and `operational_signals_for_category`.

      **Why it matters beyond the loc.** `backend/app/templates/settings.html:59-60` tells the user: *"set `click` weight higher to make clicks count more, or lower a half-life to make interest fade faster. Changes apply immediately to computed signals."* Half of that sentence is false. `docs/backlog.md:206` (Done 2026-07-15) asserts *"`app/insight/signals.py` now reads weights + decay half-lives from config (lazy import to avoid a cycle), so a change applies immediately to computed signals"* — and its verification note exercised **only** the half-life case (`manual` half-life 0.001d collapsing Anna's Beach signal 90→0). The weight half was never tested and has never worked.

      *Loc: **+3** — a lazy `from app.settings.service import get_signal_weights` mirroring the existing pattern at `signals.py:57`, and reading the merged dict at `:92`.*

      **Blast radius:** one line on the webhook hot path (`providers/service.py:180` → `apply_event_to_signals`). That caller already wraps the call in `try/except ValueError` with a log line at `:183-185`, so a missing-key case should use `.get(type)` plus the existing `raise ValueError` shape and will be handled without any new code.

      **Risk / the honest limitation that must ship with the fix:** weights are **frozen into `base_weight` at write time**, so even after the fix a weight change affects only *future* contributions, while a half-life change retroactively re-scores the entire log. **That asymmetry is inherent to ADR-132's design** — §1 makes the *decay constant* changeable "without losing history" and says nothing of the sort about the weight. It is not a defect, but the Settings copy must stop implying symmetry. **Fix the code and `settings.html:59-60` in one commit, or the next reader files this again.** No test covers `apply_event_to_signals` at all; `backend/tests/test_signals.py:131-141` covers only the half-life override.

 **✅ Promoted to `docs/backlog.md` 2026-08-21 — track it there, not here.**
- [ ] **C2 (rank 5). `open` events write zero-weight contribution rows, and the comment that says otherwise lives in a different module.**
      `backend/app/insight/service.py:17` puts `"open"` in `_CONTENT_TIED_EVENT_TYPES`; `backend/app/insight/signals.py:25` sets `"open": 0.0`. `apply_event_to_signals` does **not** short-circuit on a zero weight — it walks every category assignment (`:129`) and calls `record_contribution` with `base_weight = 0.0 * (score/10) = 0.0`, writing one permanent row per category per open.

      `backend/app/providers/service.py:182-185` believes otherwise: *"e.g. open weight 0, or content has no category assignments — the raw event is still recorded, it just moved no signal"* — sitting inside an `except ValueError` that **this path never raises for the weight-0 case**. (It does raise for the no-assignments case, `insight/service.py:121-124`, so the comment is half-right.)

      **Why it matters:** ADR-132 §4 makes the local contribution log a **bounded operational window**, and `docs/backlog.md:81` is the open item to prune it and build the DWH export. Opens are the highest-volume event class in email. This fills the table it is a stated architectural goal to keep small, with rows that contribute exactly 0.0 forever. It also inflates the `func.count(SignalContributionDB.id)` "update_count" metric at `frontend/router.py:2289` and `:1600` with no-op rows, so the category graph reports engagement that scored nothing.

      *Loc: **+2** (`if not base_weight: continue` before the dedup query) or −0 if the fix is the comment instead.*

      **Blast radius:** one loop in one function; plus the `frontend` metrics, which would start reporting smaller, truer counts.

      **Risk — sequence after C1, and the shape changes.** Once weights are config-driven, "open weight is 0" becomes a *runtime* fact rather than a constant, so any skip must read the **configured** weight, and an adopter who raises the open weight must immediately start getting rows again. **The zero-weight rows are also arguably deliberate audit trail** — "we saw the open, it scored nothing" — in which case the correct fix is the `providers/service.py:182-185` comment and not the write path. **Needs open question 2 before it is scoped.**

### Confirmed — genuine residue to delete

- [ ] **R1 (rank 2). `backend/scripts/reset_poc_data.sql` is dead and aborts on its first statement.**
      121 loc. Its own header (`:1-7`) reads *"TODO / Incomplete draft. Missing: send instances, delivery executions, engagement events, complete recipient test setup."*

      **Evidence:** `DELETE FROM preference_update_logs;` (`:15`), `DELETE FROM recipient_preferences;` (`:18`) and `INSERT INTO recipient_preferences (...)` (`:95-113`) — **three statements against two tables that no longer exist**, so the script fails on line 15 against any current database. **Zero references anywhere in the repo** — grepped for `reset_poc_data` across the entire working tree: no Makefile, no shell script, no doc, no README, no Python. `backend/scripts/reset_all_data.sql` is a strict superset, is current, and seeds `signal_contributions` correctly at `:107-115`.

      *Loc: **−121**, one file removed.*

      **Blast radius:** none in code. Nothing imports it, nothing invokes it, and it could not succeed if it were invoked.

      **Risk:** it is the only remaining written record of the pre-ADR-132 seed shape. If that has archival value, `git log` holds it — deleting a tracked file loses nothing a repo keeps. **The one check a human should run** is in the Unverified list: confirm no local shell alias or personal runbook *outside* the repo invokes it.

- [ ] **R2 (rank 3). Unused `UniqueConstraint` import — the fossil of the dropped table.**
      `backend/app/recipients/db_models.py:1`. AST-verified unused; the file has **no `__table_args__` at all**, so nothing in it can use the symbol. It is left over from `RecipientPreferenceDB`'s `(recipient_id, category_id)` constraint — `docs/backlog.md:250`, Done 2026-07-12, dropped with the table on 2026-07-15.

      *Loc: **−1 name** on a shared import line.*

      **Blast radius:** none — removal fails loudly at import time if wrong.

      **Risk: none, but sequence it with C3.** C3 puts the symbol back to work, at which point R2 is moot and removing it is pure churn. **Do C3 first; if C3 is declined, R2 stands.**

- [ ] **R3 (rank 4). A stale five-line comment in a file that is still current — and its premise is now wrong too.**
      `backend/scripts/reset_all_data.sql:163-166`: *"Preference-bump seed row intentionally omitted: `PreferenceUpdateLogDB.event_id` is NOT NULL and always traces to a real `EngagementEventDB` row, which itself requires a delivery_execution (which requires a send_instance + snapshot) — a chain this seed deliberately doesn't build."*

      Stale in its **name** (the class is gone) and **wrong in its premise**: the successor column, `SignalContributionDB.event_id` (`backend/app/recipients/db_models.py:84`), is `nullable=True` — deliberately, per its own comment at `:82-83`, so manual/declared contributions can exist with no engagement event behind them. The seed *does* insert contributions with a NULL `event_id`, at `reset_all_data.sql:107`, twelve lines above. The comment explains a constraint that no longer applies to a row the same file already writes.

      *Loc: **−5** (delete) or ~0 (correct it to name `SignalContributionDB` and say the omission is about the engagement chain, not nullability).*

      **Blast radius:** a SQL comment. None.

      **Risk:** none. The only cost of getting it wrong is another misleading comment.

### Missing DB constraints and indexes — the systemic gap continues

Cluster 3 found `content/` was the only module with zero table-level constraints, citing `docs/backlog.md:294`'s own note that the gap was *"likely a systemic pattern"*. **Both modules here have partial coverage, which is the harder case to spot:** `insight/db_models.py:22-26` has a `UniqueConstraint` with a thoughtful comment, and `recipients/db_models.py` has `unique=True` on `external_id` plus `index=True` on four FKs. The two gaps below sit *beside* that awareness rather than in a vacuum.

- [ ] **C3 (rank 6). The contribution dedup key has no DB constraint — the exact bug class `docs/backlog.md:282` was opened for.**
      `backend/app/insight/service.py:138-148` is a check-then-insert on `(recipient_id, category_id, event_id)` followed by a `record_contribution` that commits. **No unique constraint backs it** — `backend/app/recipients/db_models.py` has no `__table_args__`.

      `docs/backlog.md:282` (Done) fixed the *semantics* of this key: it used to be `(recipient_id, category_id, reason=event_type, delivery_execution_id)`, which wrongly conflated two distinct clicks in the same email. That fix corrected **which** columns identify a duplicate, at the application level only. Two concurrent webhook deliveries of the same provider event — the exact scenario `providers/service.py:64-77` and the `uq_engagement_events_provider_event` constraint at `insight/db_models.py:26` both exist to guard against — race straight through the check-then-insert and double-count the signal.

      **The precedent is in the same file, four lines apart.** `insight/db_models.py:22-26` adds a DB-level unique explicitly as *"safety net behind the application-level duplicate check in `ingest_provider_event`"*. The contribution log got the check without the net. In-repo precedents for the same fix elsewhere: `uq_audience_group_members_group_recipient` (`docs/backlog.md:294`), `uq_module_instances_variant_position` (`:222`).

      *Loc: **~+5** — a unique constraint on `(recipient_id, category_id, event_id)`.*

      **Blast radius:** one table, one 409-ish path in one function. No caller signature changes.

      **Risk — three specific ones.**
      (a) It **must not** collide on manual contributions: `event_id IS NULL` for those, and `create_recipient_preference` is *meant* to be callable repeatedly for the same `(recipient, category)`. Postgres NULLs do not collide, so a plain `UniqueConstraint` is safe and mirrors `insight/db_models.py:26`'s comment exactly; `postgresql_where=(event_id.isnot(None))` states the carve-out more explicitly. See open question 5.
      (b) Duplicate rows may already exist — **run the GROUP BY in the Unverified list before adding it**.
      (c) **`create_all` does not add constraints to an existing table** — the same silent-no-op caveat Cluster 3 raised for its C1/C2/C4/C5. This needs manual DDL or it exists only on fresh installs.
      Keep the SELECT as the fast path and add `except IntegrityError` — the defence-in-depth shape Cluster 2 endorsed at `overrides/db_models.py:78-81`.

- [ ] **C4 (rank 7). Two missing FK indexes, both on read paths that run per delivery.**
      `backend/app/insight/db_models.py:9-13` — `engagement_events.delivery_execution_id` has **no `index=True`**, while every other FK in these two modules does (`recipients/db_models.py:38, 71, 72, 82`). It is the filter in `list_events_for_delivery_execution` (`insight/service.py:63`), in `frontend/router.py:412` and `:2147` (the latter **per delivery row** in a list view), and the join predicate at `frontend/router.py:2060`.

      `backend/app/recipients/db_models.py:82` — `signal_contributions.event_id` is declared as a `ForeignKey` **without** `index=True`, and a `ForeignKey` does not create an index in SQLAlchemy. It is filtered in the hot dedup query (`insight/service.py:143`) and joined at `frontend/router.py:435, 1282, 2165, 2420`.

      In-repo precedent is explicit: `overrides/db_models.py:48` sets `index=True` for exactly this kind of lookup, and Cluster 3's C2 made the same call for `content_versions.content_record_id`.

      *Loc: **+2**.*

      **Blast radius:** none in code — no query, signature or behaviour changes.

      **Risk:** identical to Cluster 3's C2 — `index=True` **only takes effect on a fresh `create_all`**. On an existing database this is a **silent no-op that reads as fixed**. See Unverified.

### Redundant queries

- [ ] **Q1 (rank 8). `detect_consent_drift` — full table load plus one query per recipient.**
      `backend/app/recipients/service.py:191-224`. Loads **every row of `consent_sync_logs`** into Python (`:197-201`, ordered ascending), folds it down to a latest-per-recipient dict (`:203-204`), then issues **one `RecipientDB` query per recipient in that dict** (`:208-210`). Unpaginated and unbounded, over an append-only log that grows with every CRM sync — i.e. the cost grows with sync history, not with recipient count.

      **The fix pattern already exists in this repo.** Cluster 1 #4 named `frontend/router.py:1686-1725` as the in-repo precedent for collapsing this shape into one grouped query. A `DISTINCT ON (recipient_id)` (Postgres confirmed at `backend/app/database.py:4`) joined to `recipients`, with the comparison pushed into the `WHERE`, is one query total.

      *Loc: **~15 removed**. Queries: `1 + N` → `1`.*

      **Blast radius:** one function, one JSON route (`GET /recipients/consent/drift`, `router.py:59-63`). No template, no UI.

      **Risk:** the ordering tie-break at `:199` is `(synced_at ASC, id ASC)` with **last write wins**; a `DISTINCT ON` must invert to `(synced_at DESC, id DESC)` to select the same row. Get that backwards and drift silently reports the **oldest** CRM assertion — a wrong answer that looks like a right one. **No test covers this function and there is no UI for it**, so a regression is invisible until someone calls the endpoint. That combination — no test, no UI, an easy-to-invert ordering — is why this sits at rank 8 rather than higher despite the clean loc win.

- [ ] **Q2 (rank 9). `apply_event_to_signals` commits once per category assignment — a correctness issue, not just a cost one.**
      `backend/app/insight/service.py:129-159` loops over the content record's category assignments; `record_contribution` (`backend/app/insight/signals.py:92-94`) does `db.add` → **`db.commit()`** → `db.refresh()` on **every** call. A content record in three categories means three separate transactions on the webhook path.

      **The consequence is correctness:** a failure between commits leaves an event **partially applied**, and the dedup guard at `:138-146` will then skip the categories that already landed while re-applying the rest — so a retry produces a *different* signal than a clean run would have. The dedup comment at `:134-137` reasons carefully about *which events* count as duplicates and not at all about partial application of a single event.

      *Loc: **~+4** — a `commit: bool = True` parameter on `record_contribution`, one commit after the loop in `apply_event_to_signals`.*

      **Blast radius:** `record_contribution` is **declared public surface** (`docs/architecture/Code/insight.md` lists it), so the parameter must default to `True` and no existing caller changes.

      **Risk:** `backend/tests/test_signals.py:84, 101, 113` call `record_contribution` directly and read `.id` off the return value, which requires the flush — so the non-committing path must still flush, not merely `add`. Also, this is the only place in these two modules where a transaction-boundary question arises, and `docs/backlog.md` already flags that `send_send_instance`'s `with_for_update()` is the project's **one ad-hoc answer with no convention**. **Reference that item rather than inventing a convention here.**

- [ ] **Q3 (rank 10). `_configured_half_lives` hits `app_config` on every signal read.**
      `backend/app/insight/signals.py:54-59` → `get_half_lives` → `get_config` → one `AppConfigDB` SELECT. Called unconditionally by all three of `get_operational_signal` (`:107`), `operational_signals_for_recipient` (`:127`) and `operational_signals_for_category` (`:149`). `recipient_top_score` calls `operational_signals_for_recipient` **once per recipient per slot** in the send loop (`backend/app/decision/strategies/recipient_top_score.py:73`), so this is one extra round trip per recipient per slot for a value that only changes when an admin clicks Save.

      **Bundle into `docs/backlog.md` P2-04** — the "per-slot decision queries" item parked inside the 📋 *"Bulk send: batching strategy + send-timing model"*. **Do not raise independently**; same call Cluster 2 made for its Q1 and Cluster 3 for its D6.

      *Loc: **~0 net**.*

      **Blast radius:** all three public signal functions.

      **Risk:** the obvious precedent is `_load_brand_css`'s `@lru_cache(maxsize=1)` (`docs/backlog.md:238`, Done) — **do not copy it bare.** A process-lifetime cache on the half-lives would make the Settings page appear to stop working, which is exactly the trap Cluster 3's D5 flagged for `get_template_html`. Either pass the resolved half-lives down from a single call site per request, or scope any cache to the request.

---

## Ranking summary — payoff ÷ risk

| Rank | Item | Type | Loc | Risk |
|---|---|---|---|---|
| 1 | **C1** — Settings weight editor is inert | Live defect | +3 | Low; must ship with the help-text correction |
| 2 | **R1** — delete `scripts/reset_poc_data.sql` | Residue | −121 | None in repo; one out-of-repo check |
| 3 | **R2** — unused `UniqueConstraint` import | Residue | −1 | None; sequence after C3 |
| 4 | **R3** — stale `PreferenceUpdateLogDB` comment | Residue | −5 | None |
| 5 | **C2** — zero-weight `open` rows | Live defect | +2 | Needs OQ2; do after C1 |
| 6 | **C3** — no unique constraint on the dedup key | Constraint | +5 | Existing dupes; `create_all` no-op |
| 7 | **C4** — two missing FK indexes | Constraint | +2 | Silent no-op on an existing DB |
| 8 | **Q1** — `detect_consent_drift` N+1 | Query | −15 | Invertible ordering, no test, no UI |
| 9 | **Q2** — commit-per-category | Query/correctness | +4 | Public surface; tests need the flush |
| 10 | **Q3** — per-read config query | Query | ~0 | **Bundle into P2-04, do not raise alone** |

Not ranked: **S1-S4** (decisions, below), **N1-N3** (design smells, below), **H1-H2** (housekeeping).

---

## Three-way split

### 1. Genuine residue to delete

**Three items, all outside `backend/app/` except one import.**

- **R1** — `backend/scripts/reset_poc_data.sql`, 121 loc, unreferenced, cannot execute.
- **R2** — the unused `UniqueConstraint` import at `backend/app/recipients/db_models.py:1`.
- **R3** — the five-line stale comment at `backend/scripts/reset_all_data.sql:163-166`.

**Total: ~127 loc, and not one line of it is application logic.** No dead function, route, model, column, Pydantic field or JSON key exists in either module. Every one of the 3 `/insight` routes, 8 `/recipients` routes, 14 service functions, 6 signal functions and 9 Pydantic models is reachable.

### 2. Declared-but-unimplemented capability — a decision, not a cleanup

Deleting these removes documented affordances from a reference architecture; leaving them un-noted lets the UI lie.

- **S1. `"unsubscribe"` has a weight and a half-life and no producer — and it is editable in the UI.**
  `backend/app/insight/signals.py:26` (`-50.0`) and `:37` (`120.0`). Nothing anywhere calls `record_contribution(contribution_type="unsubscribe")` — grepped across `app/`, `scripts/` and `tests/`. `insight/service.py:15-16` states the reason deliberately: *"Unsubscribe/complaint is handled on the consent path (opt-out), not as a per-category signal."* `providers/service.py:186-205` confirms it in code — a complaint or hard bounce calls `suppress_recipient`, never the signal log. `audience/service.py:324` says the same from the other side.
  **The reportable half is the UI, not the constant.** `backend/app/templates/settings.html:24-40` renders one row per key of `CONTRIBUTION_WEIGHTS`, so an admin sees an `unsubscribe` weight field, edits it, saves it, and it can never fire. Exactly Cluster 2's **R5 `max_results`** shape.
  **This contradicts an Accepted ADR.** **ADR-132 §3**'s Decision table lists `unsubscribe` / complaint as a contribution type with a strong negative weight and a slow half-life. The code routes it elsewhere by design. That is a real divergence from an ADR's Decision, and per project rule it is an addendum question (the ADR-101 dated-addendum pattern), **not** something to resolve by editing code or the ADR's Decision.
  *Recommended: neither delete nor implement. 0-5 loc — a comment, or filter the settings table to producible types.*

- **S2. `ConsentSyncLogDB.applied` is hardcoded `True` at its only writer.**
  Column at `backend/app/recipients/db_models.py:50`; written `applied=True` at `service.py:155`; read only at `:182` to echo into the Pydantic model, and surfaced on `GET /recipients/consent/sync-log`. Its own comment declares *"Whether the asserted value was actually applied to the recipient row"* — but `sync_consent_from_crm` always applies, so **no code path can produce `False`**. There is no rejected-sync case anywhere.
  *Same class as S1. Keep it — the log's shape is the ADR-126 "sync drift is detectable, not silent" story, and a `False` case (a sync the platform refuses) is plausible future behaviour. 0 loc; a comment saying "no writer produces False yet" stops the next sweep re-raising it.*

- **S3. `suppress_recipient`'s `reason` parameter is accepted and never used.**
  `backend/app/recipients/service.py:17` declares it; the body (`:30-37`) never reads it. The sole caller passes it — `providers/service.py:200`, `reason=normalized.event_type`. The docstring at `:22-29` explains at length why *no log row* is written, so the drop is deliberate and the parameter is a placeholder.
  **`docs/backlog.md:186` is precisely this item** — the 📋 *"Recipient suppression + opt-out reason model — 'why is this person not getting communication?' as one auditable concept"*, which explicitly cites `suppress_recipient`'s decision to skip `ConsentSyncLogDB` as the reason a platform-only `consent_status` value was ruled out.
  **Do not delete the parameter and do not raise it as a fix** — it is the signature stub for a queued design. *A one-line comment pointing at that backlog item; 0 loc.*

- **S4. ADR-132 §4's bounded retention window and DWH export boundary are unimplemented.**
  No prune, no export, no retention setting anywhere in `backend/app/` — grepped `retention|prune|purge|export|DWH`, one docstring hit at `signals.py:7`. **Already logged as `docs/backlog.md:81`.** Recorded here only because **C2** (zero-weight `open` rows) makes the unbounded growth worse than that item assumes. **Not a new finding; do not re-file.**

### 3. Open forks — too large to rank

**None originate in this cluster.** Two existing forks touch it:

- **Cluster 2's F1** (hand-written `to_*` converters vs `from_attributes`). This cluster contributes two of the fourteen: `to_recipient` (`recipients/service.py:81`) and `to_engagement_event` (`insight/service.py:19`). `recipients/service.py:175-187` additionally hand-builds `ConsentSyncLog` inline in a list comprehension rather than via a converter, so the module is internally inconsistent as well — the same local wrinkle Cluster 3 noted for `assign_category_to_content`. **Fold into F1; do not chase alone.**
- **Cluster 1's `category_graph` fork.** `frontend/router.py:2233-2628` loads a full `SignalContributionDB × EngagementEventDB` join into memory per page view and computes the `total_delta` / `avg_delta` / `update_count` metrics that carry this cluster's naming residue (**N1**). The graph is a `frontend/` problem and already an open fork; **N1's frontend half should be folded into it rather than done separately.**

The one thing that *could* have become a fork here — "should the signal layer materialize a cache instead of folding on read?" — is **explicitly closed by ADR-132 §1**: *"Compute-on-read is sufficient at this project's scale; a materialized cache is a later optimization, never the truth."* Not raised.

---

## Design smells

- **N1. The "preference" vocabulary survived the model it named.**
  ADR-132 renamed the concept to signals/contributions; the names did not follow. Live today:
  - `RecipientPreference` and `RecipientPreferenceCreate` — `backend/app/recipients/models.py:70-82`
  - `create_recipient_preference` / `list_preferences_for_recipient` — `recipients/service.py:248, 276`
  - Routes `GET /recipients/{recipient_id}/preferences` (`router.py:112`) and `POST /recipients/preferences` (`router.py:126`)
  - `PreferenceUpdateResult` with fields `updated_categories` and `applied_deltas` — `backend/app/insight/models.py:26-31` — returned by `POST /insight/events/{event_id}/apply-signals`, a route whose *name* was migrated while its *response model* was not
  - Downstream: `total_delta` / `avg_delta` / `update_count` keys at `frontend/router.py:2288-2294`, `:1600-1605`, `:2501-2507`

  `RecipientPreference`'s own comment (`models.py:71-72`) has to explain that it is *"a computed operational signal per category (ADR-132), not a stored row — so no id/source/created_at"*. The model is documenting its way out of its own name.

  **Do not rename the routes or the response models.** `/recipients` and `/insight` are documented public surface and **ADR-142** makes machine-triggerable JSON a deliberate product feature; a rename is an API break, and `applied_deltas` in particular is a field an adopter integration reads.
  *Defensible scope is internal only: the two service function names and the frontend dict keys. ~10 mechanical renames, 0 loc net. **Lowest-value item in this report** — listed because "delta" is precisely the word ADR-132 §1 removed from the model, and because `docs/backlog.md:83` is now mis-grepbable as a result (see H1).*

- **N2. Three near-identical decay folds.**
  `backend/app/insight/signals.py:98-116`, `:119-138`, `:141-160`. Same `now` default, same `_configured_half_lives` call, same query-then-fold, differing only in the filter column and the grouping key. `get_operational_signal` is functionally `operational_signals_for_recipient(...).get(category_id, 0.0)` with a narrower query.
  *~20 loc into one private `_fold(rows, key)`. Blast radius: one file.*
  **Risk:** all three are ADR-132's public API (`insight.md` lists them individually) and `tests/test_signals.py` imports all three, so a shared helper must not change any signature. **Marginal payoff — noted, not ranked.**

- **N3. The 0–10 assignment-score scale is hardcoded in the signal math.**
  `backend/app/insight/service.py:132` — `category_weight = base_weight * (assignment.score / 10)`. `docs/backlog.md:280` (Done 2026-07-12) explicitly parked the range: *"The 0-10 range itself is a POC-only convention, not a hard rule — fold into the existing config-layer future work (Insight Q2) so a deployment can set its own limits rather than hardcoding 0-10."* The config layer then **shipped** (`docs/backlog.md:206`, Done 2026-07-15) without picking this up.
  **This is the same omission shape as C1**: the config layer landed, and two of its own stated consumers were never wired to it. Worth reporting as a pair, because a fix for C1 that does not also look at N3 will leave the second half of the same gap.
  *+2 loc if a bound is added to `settings/service.py`. **Needs open question 3.***

---

## Housekeeping — read-only notes, not work items

- **H1. `docs/backlog.md:83` is wrong on both halves.** It states the category-graph's negative branch is at `frontend/router.py:1765-1767` *"fed by `AVG(PreferenceUpdateLogDB.delta)`"*. Cluster 1 already flagged the ~740-line drift (the branch is at `:2503-2504`); **additionally, the query it names no longer exists in any form** — it is `func.avg(SignalContributionDB.base_weight)` at `:2291`. Whoever picks up that Feature will grep for a class that is not in the codebase and conclude the UI branch was removed.
- **H2. `docs/architecture/Code/recipients.md`'s "Public surface" still lists `create_recipient_preference` / `list_preferences_for_recipient`** as the declared surface, under names the page's own Data-model section contradicts two paragraphs later. Accurate as a *function* list; misleading as a *concept* list. Both module pages are otherwise **exact**: `insight.md`'s "3 routes" and `recipients.md`'s "8 routes" both verified by count, and `recipients.md`'s "Three tables, all owned here" is correct and complete.

---

## Open questions needing a human decision

1. **C1's help text.** Once weights read from config, should `settings.html:59-60` state that a **weight** change applies only to *future* contributions while a **half-life** change re-scores history? The asymmetry is inherent to ADR-132 §1 — it needs stating, not fixing. Without it the screen stays subtly misleading even after the code is right.
2. **C2 direction.** Are zero-weight `open` rows deliberate audit trail ("we saw it, it scored nothing"), or log pollution to skip? Opposite actions on the same four lines. Note `providers/service.py:182-185` currently assumes the latter and is wrong either way.
3. **N3.** Is the 0–10 assignment-score range a config value — as `docs/backlog.md:280` explicitly intended when it deferred to the config layer — or a fixed contract? The config layer shipped without it.
4. **S1 and ADR-132 §3.** The ADR's Decision table lists `unsubscribe` as a contribution type with a strong negative weight; the code deliberately routes it to the consent path instead. Is that a dated addendum to ADR-132, or is the per-category negative signal still intended? Note that `docs/backlog.md:83`'s negative-affinity Feature is the adjacent, larger version of this same question, and that its "Reinforced 2026-07-05" note treats unsubscribe as *"a genuine negative interest signal"* — which reads as arguing for the ADR, against the code.
5. **C3 scope.** Should the unique index be plain (relying on Postgres NULL non-collision, mirroring `insight/db_models.py:26` and its comment) or explicitly partial on `event_id IS NOT NULL`? The first matches in-repo precedent; the second states the manual-contribution carve-out where a reader will see it.

---

## Unverified — the specific checks a human should run

- **C3 / C4 — both, and this gates them.** Confirm how a schema change reaches an **existing** database in this project. No migration tool was found, and `docs/architecture/Code/recipients.md` says so outright in its change-impact section: *"Adding a column → no migrations; existing DBs need a manual `ALTER TABLE` (this is how several columns landed)."* Every index and constraint above is otherwise a **fresh-install-only no-op that reads as fixed**. Cluster 3 raised the identical check and it is still open.
- **C3 — run before adding the constraint**, against the live database *and* against a fresh `scripts/reset_all_data.sql` restore:
  `SELECT recipient_id, category_id, event_id, count(*) FROM signal_contributions WHERE event_id IS NOT NULL GROUP BY 1,2,3 HAVING count(*) > 1;`
- **R1.** Confirm no runbook, Makefile target or shell alias **outside this repo** invokes `reset_poc_data.sql`. An in-repo grep cannot answer this, and the file's own header suggests it was someone's working draft.
- **C1.** Confirm no adopter-facing or external doc promises that a weight change re-scores existing signals. An in-repo grep found only `templates/settings.html:59-60` and `docs/backlog.md:206`.
- **Q1.** Confirm whether `GET /recipients/consent/drift` has any consumer outside this repo before changing its query. It has no UI and no test, so an in-repo grep proves nothing about who calls it.

---

## Leave alone — looks dead, is not

Checked exhaustively, not sampled. **Do not re-run reachability on this cluster.**

- **All 3 `/insight` routes and all 8 `/recipients` routes.** Zero in-repo JSON callers is *normal* — documented public surface (`insight.md` / `recipients.md`), and **ADR-142** makes machine-triggerable JSON actions a deliberate product feature. `detect_consent_drift` and `list_consent_sync_logs` have **no UI at all** (no template in `app/templates/` mentions consent drift or the sync log) — an API-surface fact, not death.
- **`recipients/router.py`'s route ordering is correct and its comment at `:53-56` is accurate.** Verified: `/consent/drift` and `/consent/sync-log` are two-segment and cannot be swallowed by the one-segment `GET /{external_id}`; `POST /preferences` collides with nothing (`POST /{external_id}/consent` is two-segment). **Do not "tidy" this router by sorting it** — the same call Cluster 3 made for `content/router.py`.
- **The `recipients` ⇄ `insight` circular dependency.** Both module pages declare it, and it is real: `insight/signals.py:19` imports `recipients.db_models` at module level, so `recipients/service.py:259` and `:282` import `insight.signals` **function-locally** to break it. Same confirmed-real class as Cluster 2's `campaigns`/`overrides` cycle — **not** the style choice Cluster 1 found in `frontend`. `signals.py:55-57` and `:76` do the same for `settings.service`, and the comment at `:55-56` says why.
- **`SignalContributionDB` living in `recipients/` and being driven from `insight/`.** Documented as a known quirk in *both* module pages, each with a change-impact note pointing at the other. Not misplaced code — a recorded decision.
- **`record_contribution`, `get_operational_signal`, `operational_signals_for_recipient`, `operational_signals_for_category`, `CONTRIBUTION_WEIGHTS`, `HALF_LIFE_DAYS`** — all six are declared public surface in `insight.md` and all six have real cross-module callers (`settings/service.py:12`, `audience/service.py:8`, `decision/strategies/recipient_top_score.py:9`, `frontend/router.py:27`, `recipients/service.py:259, 282`, `tests/test_signals.py`).
- **`suppress_recipient` writing no `ConsentSyncLogDB` row.** Looks like a missing audit write; it is a deliberate, argued decision (`recipients/service.py:22-29`) that keeps drift detection honest, and `docs/backlog.md:186` records the same reasoning independently as a *ruled-out* alternative.
- **`validate_recipient_attributes`'s deny-list of 14 substrings** (`recipients/service.py:47-78`). Reads over-built for a projection table; it is the enforcement of **ADR-126**'s "must not become a full customer profile repository", and the comment at `:39-46` explains why a deny-list beats an allow-list here (the allowed set is intentionally open-ended).
- **`ConsentSyncLogDB.external_id` being denormalized** alongside `recipient_id` (`recipients/db_models.py:41-44`). Redundant by design — the comment states the reason: a log row stays interpretable if the recipient's `external_id` later changes, and a sync that could not be matched to a recipient can still be recorded.
- **`EngagementEventDB.occurred_at` *and* `created_at`** (`insight/db_models.py:18-19`), and the same pair on `SignalContributionDB` (`:79, 90`). Not duplication — `occurred_at` is the decay basis and `db_models.py:82-83` says so explicitly; `created_at` is when we recorded it.
- **The `uq_engagement_events_provider_event` NULL behaviour** (`insight/db_models.py:22-26`). Checked specifically, as Cluster 2 did for the partial index: `backend/app/database.py:4` is `postgresql://`, NULLs do not collide, so the constraint guards only rows that actually came from a provider — exactly as its comment claims. Manually-posted events with both fields NULL are unaffected and the 409 branch at `insight/router.py:32-38` is live.
- **The ten `import … # noqa: F401` lines in `backend/tests/test_signals.py:29-38`.** They look like a mass unused-import finding; the comment at `:25-28` explains they register every table in SQLAlchemy's metadata so the `signal_contributions → categories` FK resolves when the file is run alone. **Deleting them makes the suite order-dependent**, which the comment names as the thing to avoid.
- **`tests/test_signals.py` asserting only on contributions it creates and then removes** (`:3-10`, `_cleanup` at `:43-50`). Looks like weak testing; it is deliberate — signals decay in real calendar time, so an assertion against a seeded value passes the week it is written and fails a month later.
- **`PreferenceUpdateResult`'s legacy field names** (`insight/models.py:26-31`). Ugly (N1), but it is the response model of a live public route under ADR-142.
- **`RecipientPreferenceCreate.score` accepting any float unvalidated** (`recipients/models.py:79`). It is the *declared magnitude* by design under ADR-132 §3 ("heavy base weight = declared magnitude"), and the range question is N3, not a validation gap.
- **`_CONTENT_TIED_EVENT_TYPES` excluding bounce/complaint** (`insight/service.py:17`). The comment at `:13-16` and `audience/service.py:324` both say suppression belongs on the consent floor. Deliberate.
- **`backend/app/providers/service.py:100-139` `_primary_content_id_for_delivery`** guessing one "primary" content record per delivery and misattributing multi-module clicks — **already `docs/backlog.md:35`, P2, "corrupts the signal layer"**. It is the largest correctness risk touching `insight/`, and it is already logged. Not re-raised.

**Findings dropped: 4**, all trivial style — the unsorted import block at `recipients/db_models.py:1`, a missing blank line before `to_engagement_event` at `insight/service.py:18`, `list_recipients` having no pagination (same class as the `docs/backlog.md:87` Feature, not a fresh finding), and the `event_data or {}` / `assignment` defensive idioms.

**Noticed out of scope, not filed:** `docs/architecture/ADR-drift-report.md:170-178` describes `insight/service.py` applying events *"directly to `RecipientPreferenceDB` scores"* and `recipient_top_score` querying it directly. That document is now describing a pre-2026-07-15 codebase. Whether a drift report should be re-run or archived is a docs decision, not a code one.

---

## Single highest-value cleanup

Wire `backend/app/insight/service.py:92` to `get_signal_weights(db)` and correct `backend/app/templates/settings.html:59-60` in the same commit — three lines that turn half of the Settings screen from a lie back into the ADR-132 tuning surface `docs/backlog.md:206` already records as done.

---

# Cluster 5 — `audience` + `decision`

**Swept:** 2026-08-21 · `backend/app/audience/` (672 loc, 4 files) + `backend/app/decision/` (561 loc, 6 files), both read in full
**Method:** every service function, column, Pydantic field, `criteria` JSON key, `ConfigField` and strategy name grepped across `backend/app/`, `backend/scripts/`, `backend/tests/` and `docs/`. Writers grepped separately from readers with `scripts/` excluded from the writer set (the Cluster 2 method). Strategy reachability established through the registry's resolution path before judging anything in `strategies/` dead. `docs/backlog.md` cross-checked before every finding.

## Headline

**The premise is wrong, and the corrected picture is the finding.** There is no frozen-list-versus-rule-block supersession and therefore no supersession residue. `find_by_criteria` and `bulk_add_members` are both live, both have UI writers, and `AudienceGroupMemberDB` is written by the running application on two paths. Details below — settle this so no future sweep re-opens it.

**No dead code in either module.** All 22 `audience/service.py` functions, all 8 `/api/audience-groups` routes, all 2 `/decision` routes, both strategies, the registry and every `base.py` symbol are reachable. Zero unused imports in either package.

What Cluster 5 actually carries is three themes:

1. **Repeated whole-table evaluation.** `resolve_audience` re-runs a full consenting-recipient scan **per rule block**, and the audience-group detail page then runs the same evaluation a second time per block for its count column. One dict key — `suggest_include_blocks_for_campaign`'s `"count"` — is computed at full audience cost and read by nobody.
2. **The missing-constraint gap continues, and this time it lands on the hottest table in the app.** `decision_resolutions` has **no `__table_args__` and no index on any FK**, while being queried per recipient per slot per send from two modules.
3. **The extension seam is weaker than it advertises.** `_check_type` silently accepts anything for a `ConfigField.type` string it does not recognise, and the strategy contract structurally forbids the multi-pick that **ADR-084 (Accepted)** mandates.

**Also settled here: Cluster 2's open question 3 has an answer.** ADR-084 is Accepted and requires multi-result slots. `max_results` is not residue and must not be pinned to 1 as a tidy-up — see "Decide, don't delete".

---

## The premise — verified, and it does not hold

The working premise was that frozen member lists were replaced by live rule blocks, leaving residue in `find_by_criteria` / `bulk_add_members`. **Both mechanisms are live, and they coexist by design. Established by tracing writers and readers, not by reading the doc:**

| Mechanism | Live writer in `backend/app/` | Live reader |
|---|---|---|
| `AudienceGroupMemberDB` (pins) | `add_member` ← `frontend/router.py:2769` **and** `audience/router.py:56`; `bulk_add_members` ← `frontend/router.py:2827` | `get_member_recipient_ids` ← `resolve_audience:340`, `frontend/router.py:2671, 2790, 2816` |
| `AudienceRuleBlockDB` (rules) | `add_block` ← `frontend`, `create_suggested_group_for_campaign`, `recalculate_suggested_blocks` | `list_blocks` ← `resolve_audience:326` |

`resolve_audience` **needs both** — `(includes − excludes) ∪ pins` (`audience/service.py:314-353`). A pin is not a leftover frozen list; it is the documented manual-override half of the model, and its precedence (pins survive excludes, consent survives pins) was a fixed bug per `docs/architecture/Code/audience.md`.

**`prepare_send_from_audience`'s `freeze` mode is unrelated to the member table.** `freeze` / `rerun` (`delivery/service.py:125-215`, **ADR-052**) freezes `DeliveryExecutionDB` rows for one send instance. It never writes `audience_group_members`. The two are orthogonal mechanisms that were assumed to be the same one.

**`docs/backlog.md:71` plans to build *more* on pins** — the A/B split Feature says explicitly *"No new entity needed — reuse the existing pin mechanism (`resolve_audience`'s `… ∪ pins`)"*. Deleting the pin path would break a queued feature.

`find_by_criteria` has two live callers (`frontend/router.py:2793` criteria preview, `:2819` bulk-add) and is the shared definition `_recipients_for_criteria` adapts for rule blocks (`audience/service.py:221-233`). Its `exclude_ids` parameter — the only one that looked speculative — is passed at `frontend/router.py:2799, 2825`.

**Nothing in `audience/` is supersession residue. Do not look again.**

---

## To do

Ranked by payoff ÷ risk. Unchecked = not started. As in Clusters 3-4, several top items *add* lines.

### Free wins — zero risk

- [ ] **A1 (rank 1). `suggest_include_blocks_for_campaign` computes a `"count"` no caller reads — at full audience-evaluation cost, up to 5 times per call.**
      `backend/app/audience/service.py:415-428`. Line `:426` does `"count": count_for_criteria(db, criteria)` inside the per-category loop. `count_for_criteria` (`:236-237`) is `len(_recipients_for_criteria(...))`, i.e. a full `find_by_criteria` — a whole-table consenting-recipient scan plus a settings read plus a full `SignalContributionDB` scan for the category.
      **Grepped both callers:** `create_suggested_group_for_campaign:448-456` uses only `suggestion["criteria"]` and `suggestion["label"]`; `recalculate_suggested_blocks:474-500` uses only `s["criteria"]["category_id"]`, `["criteria"]` and `["label"]`. **There is no third caller** — `rg 'suggest_include_blocks_for_campaign' backend/app/` returns the definition and those two. The docstring's justification (*"a live count so the manager sees the impact before accepting"*) describes a preview screen that does not exist: `frontend/router.py:2911` goes straight to `create_suggested_group_for_campaign`.
      **So every "Suggest audience" and every "Recalculate" pays up to 5 full audience evaluations (≈15 queries, 5 full recipient scans, 5 full contribution scans) to populate a key that is discarded.**
      *−1 loc, or +1 for a `with_counts: bool = False` parameter that keeps the affordance for the preview screen if it is ever built.*
      **Blast radius:** one dict key, two internal callers, zero templates (`rg 'content_score\|"count"' app/templates/` finds no consumer of this dict).
      **Risk: none.** The safest form is the `with_counts=False` default rather than deletion — it costs 1 loc and keeps the documented intent honest.

- [ ] **A2 (rank 2). Unused local `added` in `recalculate_suggested_blocks`.**
      `backend/app/audience/service.py:490, 501` — `added = 0` then `added += 1`, and the function returns `group` (`:503`). Its sibling `removed` (`:481-487`) is used, to decide whether to commit, so this reads as an abandoned "return a delta summary" intent. The UI at `frontend/router.py:2921` only checks the return for `None`.
      *−2 loc, or return `(group, added, removed)` if the flash message should say what changed.*
      **Risk: none.**

- [ ] **D1 (rank 3). `_check_type` silently accepts anything for an unrecognised type string.**
      `backend/app/decision/strategies/base.py:45-61`. `ok = True` is the initial value and there is no `else` — a `ConfigField(type="bool")`, `"dict"`, `"float"` or a typo like `"integer"` passes **every** value unchecked. The `ConfigField` docstring (`:20-23`) promises the config *structure* is locked to the chosen strategy, and `normalize_slot_config`'s docstring (`:99-103`) promises "types checked".
      **This is a seam-quality defect, not an internal one.** The declared purpose of `ConfigField` is that an adopter drops in a strategy file (`docs/architecture/Code/decision.md`: *"just add a file; do not add a config table or touch the core"*). The adopter's typo produces silent no-validation, then a crash at resolution time — which is exactly what the docstring says this exists to prevent.
      *+2 loc: `else: raise ValueError(f"ConfigField '{spec.name}' declares unknown type '{spec.type}'")`.*
      **Blast radius:** validation only. Both shipped strategies use `"list[int]"` and `"number"`, both recognised, so nothing in-repo changes behaviour.
      **Risk:** a raise inside `normalize_slot_config` surfaces as a 400 on slot save. If an out-of-tree strategy already relies on an unrecognised type, its slots stop saving — loudly, which is the point. No test covers `base.py` (`backend/tests/` has no decision test at all).

### Missing DB constraints and indexes — the systemic gap, now on the hot path

Standing caveat, unchanged from Clusters 3-4: **there is no migration tool.** `index=True` and new `__table_args__` take effect only on a fresh `create_all`; on the existing database they are **silent no-ops that look fixed** and need manual DDL.

- [ ] **D2 (rank 4). `decision_resolutions` has no index on anything, and it is the most-queried table in the send path.**
      `backend/app/campaigns/db_models.py:96-106` — no `__table_args__`, no `index=True` on `decision_slot_id`, `recipient_id` or `created_at`. **Three hot readers, all filtering on exactly those columns:**
      - `backend/app/decision/service.py:65-73` — `WHERE decision_slot_id = ? AND recipient_id = ? ORDER BY created_at DESC LIMIT 1`, run **once per recipient per slot per send** (it is the dedup check that decides insert-vs-update-vs-skip).
      - `backend/app/rendering/service.py:317-338` — the same filter, up to twice per module per recipient (personalized lookup, then the NULL-recipient fallback).
      - `frontend/router.py`'s three resolution-stats implementations (Cluster 1 #11) aggregate the whole table.

      The table grows one row per recipient per personalized slot per send, so it is the fastest-growing table in the schema and the only sequential scan in the inner send loop.
      **The in-repo precedent is explicit:** `overrides/db_models.py:48` sets `index=True` on `module_instance_id` for a strictly colder lookup, and `recipients/db_models.py` indexes four FKs.
      *+3 loc (a composite `Index("ix_decision_resolutions_slot_recipient_created", decision_slot_id, recipient_id, created_at.desc())` serves all three readers).*
      **Blast radius:** none in code. Write cost on an insert-heavy table is the only trade, and the dedup logic at `decision/service.py:75-89` already suppresses most inserts.
      **Ownership note:** the table is declared in `campaigns/db_models.py`, so this is technically Cluster 2 territory — **it is not in the Cluster 2 report** (grepped) and the readers that make it matter are in `decision/` and `rendering/`. Filing it here rather than leaving it in the seam between clusters.
      **Risk:** the migration caveat above, plus this needs `ORDER BY created_at DESC` to actually use the index — verify with `EXPLAIN` rather than assuming.

- [ ] **A3 (rank 5). No index on `audience_rule_blocks.group_id` — read on every audience resolution.**
      `backend/app/audience/db_models.py:63`. `list_blocks` (`audience/service.py:240-246`) filters on `group_id` and is called by `resolve_audience:326`, by `recalculate_suggested_blocks:477`, and by the group detail page. `add_block:263-267` also counts on it.
      **This gap sits beside real awareness, which is why it is easy to miss:** the same file has `ux_audience_groups_name_lower` (`:29`) and `uq_audience_group_members_group_recipient` (`:42`) — and the latter's leading column gives `audience_group_members.group_id` an index for free, so `AudienceGroupMemberDB` is covered and `AudienceRuleBlockDB` is not. `audience_groups.source_campaign_id` (`:15`) is likewise unindexed and is filtered by `recalculate_suggested_blocks`.
      *+3 loc.* **Blast radius:** none in code. **Risk:** the migration caveat only. Low payoff at demo data volume — ranked here because it is 3 loc and it closes the module's last constraint gap.

### Redundant work — the audience resolution path

- [ ] **A4 (rank 6). `resolve_audience` re-scans the whole recipient table once per rule block.**
      `backend/app/audience/service.py:314-353`. The loop at `:330-335` calls `_recipients_for_criteria` per block, which calls `find_by_criteria` (`:136-182`), which does: a full `RecipientDB` query filtered only on consent + optional language/status (`:152-161`, **no category filter in SQL**), then `operational_signals_for_category` (`:168`) which itself does a settings read (`insight/signals.py:154` → `get_half_lives` → `get_config`, a DB query) **plus a full scan of `SignalContributionDB` for the category** (`:152-158`), then a Python dedupe by email over the full list (`:174-180`), then a Python threshold filter (`:169`).
      For the 5-block group `create_suggested_group_for_campaign` produces by default: **≈18 queries, 5 full recipient scans, 5 full contribution scans, 5 identical settings reads** — to produce a set of ids.
      Then `resolve_audience` throws the `RecipientDB` objects away and keeps only `{r.id}` (`:331`) before re-fetching the survivors at `:344-352`.
      **Three cheap, independent improvements, safest first:** (a) memoize `_configured_half_lives` per call — the settings row cannot change mid-resolution; (b) push the category filter into SQL so `find_by_criteria` stops loading non-matching recipients; (c) give `_recipients_for_criteria` an ids-only path so `resolve_audience` never materializes ORM objects it discards.
      *~15 loc.* **Blast radius:** `resolve_audience` is called from `delivery/service.py:147` and `:200` and three places in `frontend/router.py` — *who gets emailed* depends on it.
      **Risk: the highest in this cluster.** `audience.md`'s change-impact section says changing this order changes who gets emailed, and the pins-survive-excludes precedence was a **fixed bug**. The email dedupe at `:171-180` is load-bearing and must survive any SQL rewrite — it exists because `RecipientDB.email` has no unique constraint. **No test covers `audience/` at all** (`backend/tests/` has no audience test). Do (a) alone first; it is 2 loc and cannot change the result set.

- [ ] **A5 (rank 7). The group detail page evaluates every block twice.**
      `frontend/router.py:2715` computes `count_for_criteria(db, crit)` per block, then `:2718` calls `resolve_audience(db, group_id)` which re-runs `_recipients_for_criteria` for **the same blocks** (`audience/service.py:331`). For a 5-block group that is 10 full evaluations where 5 would do, and the second five recompute exactly the first five.
      **This is the audience-side answer to Cluster 1 #5/#6**, which recommended a count path belong in `audience/service.py`. The shape that serves both: one `resolve_audience_detailed(db, group_id)` returning `{per_block_ids, include_ids, exclude_ids, final_recipients}`, from which the page derives per-block counts, the net count and the list — one pass, and the count column can no longer drift from the resolve semantics.
      *~20 loc net across `audience/service.py` + `frontend/router.py`.* **Fold into Cluster 1 #5/#6 — one change, not two.**
      **Risk:** same as A4 plus a template contract (`audience_group_detail.html` reads `blocks[].count`). Do A4(a) first.

- [ ] **D3 (rank 8). `recipient_top_score` loads every active content×category row, then filters in Python.**
      `backend/app/decision/strategies/recipient_top_score.py:75-100`. The query filters only `status == "active"` (plus `category_ids` when the slot supplies one), calls `.all()`, and the actual selectivity — `if category_id in signals` (`:99`) — is applied in a list comprehension. `signals` is already in hand at `:73`, so `.filter(ContentCategoryAssignmentDB.category_id.in_(signals.keys()))` is available.
      This runs **once per recipient per slot per send**, and each run also does a settings read plus a full per-recipient contribution scan inside `operational_signals_for_recipient`.
      *~2 loc.* **Blast radius:** one strategy. **Not covered by `docs/backlog.md` P2-04** — that item is about the *number* of queries in the send loop; this is the *row volume* of one of them. Adjacent enough to bundle with it.
      **Risk:** low but real — `signals` may be empty, and `in_([])` must short-circuit to the existing `return None` at `:101-102` rather than emitting `IN ()`. Guard `if not signals: return None` before the query. No test covers either strategy.

### Router / Pydantic drift

- [ ] **A6 (rank 9). `PATCH /api/audience-groups/{id}` is a PUT wearing a PATCH verb — it nulls `description`.**
      `backend/app/audience/router.py:32-40` binds `AudienceGroupCreate` (`audience/models.py:14-16`, where `description: str | None = None`) and forwards `payload.description` unconditionally to `update_group`, which assigns `group.description = description` (`audience/service.py:48`). **A PATCH that sends only `{"name": "x"}` silently erases the description.** The same shape as Cluster 2's D1/D2: the UI path is fine (`frontend/router.py:2748-2749` always submits both fields from the form), so only the JSON surface is wrong — and ADR-142 makes that surface a deliberate product feature, not a leftover.
      *~4 loc: a separate `AudienceGroupUpdate` with all-optional fields plus a sentinel, or switch `update_group` to `**fields`.*
      **Risk:** low; changes behaviour on a route with no in-repo caller and no test.

- [ ] **A7 (rank 10). `AudienceGroup` never exposes `source_campaign_id`, so the JSON API cannot tell a suggested group from a hand-made one.**
      `backend/app/audience/models.py:6-11`. The column exists (`db_models.py:15`), the UI branches on it (`frontend/router.py:2723-2725`), and `audience.md` lists it as the thing that "enables Recalculate" — but a machine client reading `GET /api/audience-groups/` cannot see it, and there is no JSON route for Recalculate either (`recalculate_suggested_blocks` is UI-only, `frontend/router.py:2921`).
      *+1 loc to expose it.* **Risk: none** — additive on a read model.
      **Note this is an API-surface gap, not dead code**, in the same category as Cluster 2's `update_variant` observation.

- [ ] **D4 (rank 11). The strategy manifest drops `ConfigField.required` on the way to the UI.**
      `frontend/router.py:1945-1956` rebuilds each `ConfigField` as `{name, type, default, description}` — `required` (`base.py:27`) is omitted, and `decision_slot_detail.html:102-109` therefore renders only name and type. `GET /decision/strategies` *does* expose it (the dataclass is the response model, `decision/router.py:19`), so the JSON API and the UI disagree about the same manifest. A strategy with a required key gives the manager no warning before the save fails.
      *+1 loc in the comprehension, +1 in the template.* **Risk: none.** Owning file is `frontend/`, but the contract is `decision/`'s.

### Broad exception catch — sequence with P0-02

- [ ] **A8 (rank 12). `add_member`'s `except IntegrityError` reports an FK violation as a race.**
      `backend/app/audience/service.py:92-106`. The comment says the catch is for the TOCTOU race against `uq_audience_group_members_group_recipient`, but a nonexistent `group_id` or `recipient_id` violates an FK and lands in the same branch; the fallback query then returns `None`, and `audience/router.py:57-58` renders it as a 404. **The right answer arrives by accident**, via a path the comment says is for something else. `bulk_add_members:197-213` has the same catch, where a bad recipient id silently reduces the count instead of erroring.
      Identical class to Cluster 2's S3 (`overrides/service.py:94-102`) and `docs/backlog.md` P3-03, now bundled into **P0-02**'s typed-exception work.
      *0 loc net — inspect `error.orig.diag.constraint_name` and re-raise otherwise.* **Do it with P0-02, not before.**

---

## Decide, don't delete

Declared-but-unimplemented capability. These are decisions, not cleanups.

- **DD1. ADR-084 answers Cluster 2's open question 3 — and the gap is bigger than `max_results`.**
  **ADR-084 — Decision Slots May Resolve One or Multiple Content Records** is **Accepted** and its Decision requires a slot to define *minimum items, maximum items, allowed categories, excluded categories, allowed content types, optional fallback content*. Against that:
  - `StrategyResult` (`decision/strategies/base.py:10-15`) holds **one** `content_record_id`, and `DecisionStrategy.execute` (`:117-123`) returns `StrategyResult | None`. **The contract structurally cannot express a multi-pick** — so `max_results` is unreadable not because someone forgot to read it, but because there is nowhere for a second result to go.
  - `execute_decision_slot:51-98` takes one result and writes one row.
  - Of ADR-084's six required limits, exactly one is implemented: allowed categories, as `candidate_filter.category_ids` in both strategies. Minimum items, excluded categories, content types and fallback content have no representation anywhere.

  **This contradicts Cluster 2 R5's suggested resolution.** That item proposed pinning `max_results` to 1 with a validator; ADR-084 makes `max_results > 1` a recorded, accepted requirement, so a validator rejecting it would encode a contradiction of an Accepted ADR into the code. **An ADR beats tidiness — report the tension, do not close it.** The honest interim is a comment at `campaigns/db_models.py:86` naming ADR-084 and saying the strategy contract does not support it yet. *0-3 loc.* **Nothing to delete either way.**

- **DD2. Hot-reload is a development affordance running on the production send path.**
  `decision/strategies/registry.py:48-69`. Every `get_strategy` and `list_strategies` call runs `_dir_mtime()`, which globs the package directory and `stat()`s every `.py` — **once per slot per recipient inside the send loop** (`decision/service.py:44`), plus once per campaign-detail and slot-detail page view. On a mismatch it `importlib.reload`s every strategy module mid-request.
  **This is not residue and must not be removed** — `docs/architecture/Code/decision.md` names hot-reload as part of the "BI can add a decision strategy without touching the core" pillar, and it is the seam this reference architecture exists to demonstrate. The question is whether it should be **gated** (env flag, or a TTL on the freshness check) so an adopter's production deployment is not doing filesystem I/O per decision. *~5 loc if gated.* **A product decision about what the reference implementation should model, not a cleanup.**

- **DD3. `AudienceRuleBlockDB.position` is written by `add_block` and never maintained.**
  `audience/db_models.py:74`, set at `audience/service.py:274` to `COUNT(blocks in group)`. Three consequences: it is **not** `MAX(position) + 1`, so deleting a middle block makes the next insert collide with an existing position; `update_block` (`:282-302`) has no `position` parameter, so nothing can reorder; and there is no reorder route or template control. `list_blocks:244` orders by `(kind, position, id)`, so collisions silently fall back to id order.
  The in-repo precedent for the correct form is `campaigns/service.py`'s `MAX(position)` aggregate for module ordering.
  Reads as a reserved affordance rather than a defect — include blocks combine by OR, so their order does not affect the result. *Either 1 loc to make it `MAX+1`, or a comment saying order is cosmetic.* **Not in `docs/backlog.md`.**

- **DD4. `delete_group` enumerates the group's foreign keys and misses one.**
  `audience/service.py:58-68`. The comment at `:62-63` reads *"Clear both children first — members and rule blocks both FK to the group, so either left behind blocks the delete"* — but **`delivery/db_models.py:17` also FKs `audience_groups.id`** (`SendInstanceDB.audience_group_id`, nullable, no `ON DELETE`). Deleting a group that any send instance ever used raises an uncaught `IntegrityError`; `frontend/router.py:2758-2759` calls `delete_group` with no `try`, so the manager gets a 500 rather than a message.
  **Listed here rather than under "to do" because the fix is a policy choice, not a repair:** block the delete with a clear error (the `content/service.py:485-500` `ContentRecordHasHistoryError` precedent), null the send instances' `audience_group_id` (which breaks `reconcile_executions_to_audience` for `rerun` sends — **ADR-052**), or cascade. Only the first preserves send history.
  **Unverified — name the check:** I did not confirm the 500 empirically. Run `POST /ui/audience-groups/{id}/delete` on a group referenced by a `send_instances` row and confirm the traceback. *~6 loc for the guard.* **Not in `docs/backlog.md`.**

---

## Too large to be a cleanup item — open forks

### F1. The two strategies duplicate their candidate query, and that may be correct

`top_score.py:41-58` and `recipient_top_score.py:75-91` build the same `ContentRecordDB × ContentCategoryAssignmentDB` join with the same `status == "active"` filter and the same `category_ids` branch — ~15 duplicated loc, and the identical `get_latest_version_for_content` + `StrategyResult` tail at `:64-72` / `:126-140`.

**A shared `_candidate_query` helper is the obvious move and is probably wrong here.** The declared design rule is one worked example per seam, and the seam's promise is *drop a `.py` file in the directory* — a strategy that is readable and copyable standalone teaches the extension point better than one that inherits half its behaviour from a base helper the adopter must also learn. Pulling the shared query into `base.py` would also make `base.py` know about `content/`, which it currently does not (it imports only `DecisionSlotDB`).

**Noting it as an option, not proposing it.** If it is taken, the right shape is a helper in `content/service.py` that both strategies call explicitly, not a base-class method they inherit.

### F2. Audience resolution has no incremental path

A4, A5 and A1 are three symptoms of one thing: every audience question — a count, a preview, a per-block number, a send — is answered by re-evaluating every block from scratch against the whole recipient table, with signals recomputed on read (**ADR-132**, decay-on-read, deliberately no stored score).

That is the correct model for a reference architecture and the ADR says so. Whether it needs a caching or materialization layer is a scale question that depends on adopter volume, and the answer is not "add a cache" — it is a design fork about where the operational/historical split (**ADR-113**) actually cuts. **Not ranked.**

---

## Unverified — the specific checks a human should run

1. **DD4's 500.** Delete an audience group referenced by a `send_instances` row and confirm the uncaught `IntegrityError`. I traced the FK and the missing cleanup statically.
2. **D2's index actually being used.** `EXPLAIN` the `decision/service.py:65-73` query before and after; a composite index with a `DESC` ordering column does not always get picked.
3. **A4(b).** Whether pushing the category filter into SQL preserves the email-dedupe semantics at `audience/service.py:171-180`. The dedupe runs *after* the threshold filter today; moving the filter into SQL changes which duplicate survives when two rows share an email.
4. **The migration caveat on A3 and D2.** Both are fresh-install-only without manual DDL. Confirm whether the running database is ever recreated from `create_all` or only from `scripts/reset_all_data.sql`.

---

## Leave alone — looks dead, is not

Checked, not sampled. **Do not re-run reachability on this cluster.**

- **`top_score.py` and `recipient_top_score.py`** — zero static importers by construction. Resolved by `pkgutil.iter_modules` in `registry.py:19`, instantiated by `issubclass` inspection at `:31-34`, keyed by `instance.meta.name`, and looked up from the **string** in `DecisionSlotDB.decision_strategy` at `decision/service.py:44`. Both are live and both are the plugin system.
- **`registry.py:35-43`'s bare `except Exception`** — deliberate, and the comment says why: one broken strategy file must not take down the registry (and, historically, the app). Not a broad-catch finding.
- **`registry.py`'s `importlib.reload`** — deliberate hot-reload, see DD2. Removing it breaks the documented seam.
- **`ConfigField`** — instantiated only inside strategy files, consumed by `normalize_slot_config` and by `frontend/router.py:1945`. Its `required` field is read only by `_normalize_section:83`; that is not dead, see D4.
- **`normalize_slot_config`** — no caller in `decision/`; called from `campaigns/service.py:302` behind the lazy import Cluster 2 confirmed breaks a real cycle.
- **Both `/decision` routes and all 8 `/api/audience-groups` routes** — zero in-repo JSON callers is normal (**ADR-142**).
- **`find_by_criteria`, `count_for_criteria`, `bulk_add_members`, `get_member_recipient_ids`, `AudienceGroupMemberDB`** — all live. See the premise section above; this is the item most likely to be re-flagged.
- **`campaign_category_scores`** (`audience/service.py:360-412`) — no caller outside its own module, called by `suggest_include_blocks_for_campaign:420`. Its function-local imports at `:366-367` follow the same cycle-avoidance convention Cluster 2 confirmed.
- **`AudienceRuleBlockDB.source`** — written as `"manual"` / `"suggested"`, read by `recalculate_suggested_blocks:477` **and** the UI badge. Not a write-only provenance column.
- **`audience/service.py:171-180`'s email dedupe** — looks like belt-and-braces over a unique constraint; there is no unique constraint on `RecipientDB.email` and the comment says the decision was deferred. Load-bearing.
- **`DEFAULT_CONFIG` in `recipient_top_score.py:11-14`** — looks like a duplicate of the `ConfigField` defaults; the `ConfigField`s reference it (`:42`, `:48`), so it is one source of truth, and the `{**DEFAULT_CONFIG, **(slot.strategy_config or {})}` merge at `:66` is a legitimate guard for slots written before `normalize_slot_config` existed.
- **`random.choice` on ties** (`recipient_top_score.py:114`) — a deliberate, disclosed tie-break recorded in the `reason` string per **ADR-085**, fixed in commit `6b2f402`. Not nondeterminism to remove.
- **`execute_decision_slot`'s consent gate** (`decision/service.py:25-42`) — deliberate belt-and-suspenders. Its `ValueError` being swallowed by `delivery/service.py:383-387` is **`docs/backlog.md` P0-02**, already open. Not re-filed.
- **No tests exist for `audience/` or `decision/`** — `backend/tests/` has no file for either. That is the standing risk on every finding above, not a separate finding.

---

## Housekeeping

- **Symbol drift, corrected 2026-08-21.** The Cluster 2 section referred to `resolve_decision`; no such symbol exists — the function is `execute_decision_slot` (`decision/service.py:11`). Line numbers were right. Corrected in place so Cluster 2 Q1 is findable by symbol.
- **`docs/architecture/Code/audience.md` omits `bulk_add_members`** from its Public surface list, though it lists its siblings `add_member` / `remove_member` / `get_member_recipient_ids`. Given the premise this sweep was sent to test, the omission is probably how the "frozen list is residue" reading started.

---

**Findings dropped: 3**, all trivial style — an unsorted import block at `audience/service.py:1-8` (stdlib/third-party/local ordering differs from `decision/service.py`), `update_block`'s inability to clear a `label` back to `None` (`audience/service.py:298`, same `is not None` idiom as every other partial update in the repo), and `get_block` being a one-line wrapper used four times (it earns its keep).

**Highest-value single item:** add the composite index to `decision_resolutions` (D2) — three loc against the only sequential scan in the per-recipient send loop, on the fastest-growing table in the schema.

---

# Cluster 6 — `auth` + `settings`

**Swept:** 2026-08-21 · `backend/app/auth/` (1,032 loc, 6 files) + `backend/app/settings/` (157 loc, 2 files), both read in full
**Method:** every service function, dependency, permission constant, config key, ORM column and route grepped across `backend/app/`, `backend/main.py`, `backend/scripts/`, `backend/tests/` and `backend/app/templates/`. Config keys checked writer-side and reader-side separately (the Cluster 2 method). The route→permission table was replayed against all 43 `@router.post` templates in `frontend/router.py` plus the 10 in `auth/router.py`. AST pass for unused imports over both packages. `docs/backlog.md` cross-checked before every finding; the five items the brief pre-declared as filed are referenced, never re-filed.

## Headline

**The brief's expectation was right — the residue is near zero — and it was right for a second reason too: the interesting findings here are gaps, and two of them are security defects the external review did not catch.**

Clean negatives first, because they are the result:

- **Zero unused imports** in either package (AST-verified, not sampled).
- **Zero orphaned config keys.** All six `app_config` keys — `signal_weights`, `half_life_days`, `max_send_recipients`, `ai_spend_cap`, `ai_provider`, `auth_enforced` — have both a live writer and a live reader. Cluster 4's "config layer shipped with a consumer never wired to it" pattern **has exactly one instance**, and it is the already-filed Cluster 4 C1. I looked for a second and there is none.
- **Zero missing constraints or FK indexes.** The four-cluster streak ends here. Every FK in `auth/db_models.py` is indexed, both compound uniqueness rules that matter (`uq_role_permission`, `uq_user_role_brand`) exist, `users.email` and `auth_sessions.token_hash` are unique+indexed, and `app_config.key` is the primary key. This module is the one place in the repo where the constraint discipline is complete — the gap is in the *other* direction (A8, two redundant indexes).
- **Zero dead routes, zero orphaned templates, zero orphaned columns.** Every column on all seven auth tables has a reader. `login.html`, `login_verify.html`, `users.html`, `roles.html` and `forbidden.html` are all reachable.
- **Zero JSON-router / Pydantic drift** — neither module has a JSON router or a Pydantic model. Cluster 2/5's A6-shaped finding cannot occur here.
- **One dead symbol in the whole cluster**, three lines (A5).

What Cluster 6 actually carries is four themes:

1. **Two sign-in defects with authentication-bypass and account-enumeration consequences** (A1, A4). A1 is the one to read first: a provider delivery *failure* makes the six-digit code render in the browser of whoever typed the address. That is not in `docs/backlog.md`.
2. **A plus-addressed email can never sign in** in production (A2). Two characters. The default dev config hides it, which is why it survived review.
3. **The session is resolved twice per request, with two `UPDATE … COMMIT`s on `auth_sessions`, on every single page view** (A3). Not a scale worry — a per-request write on the app's busiest table.
4. **Three capabilities are declared and unimplemented, and all three are ADR-backed**: `credentials.manage` (S1), the ADR-153 audit log (S3), and brand scope (already `docs/backlog.md` P1-02). None is deletable; each is a human decision.

**Nothing in this cluster should be deleted except three lines.** Read the risk sections: five of the items below change authentication or authorization *semantics*, and they are marked.

---

## To do

Ranked by payoff ÷ risk. Unchecked = not started. The standing migration caveat from Clusters 3-5 does not apply to anything here — no finding in this cluster needs DDL except A8, which is optional.

### Confirmed — live security defects

- [x] **A1 (rank 1). A failed provider delivery renders the sign-in code on screen to whoever requested it. Authentication bypass.**
      `backend/app/auth/service.py:246-279` + `:310-311`, consumed at `backend/app/auth/router.py:59-76`.
      `deliver_code` returns `True` **only** on `result.success` (`:276`). Every other outcome — provider misconfiguration, an expired or revoked API key, a rate-limit rejection, a network error, a raised exception caught at `:277-279` — returns `False`. `request_login_code` then does:
      ```python
      delivered = deliver_code(address, code)
      return None if delivered else code          # service.py:310-311
      ```
      and the router does:
      ```python
      code = request_login_code(db, email)
      if code:
          return templates.TemplateResponse(
              request, "login_verify.html",
              {..., "prefilled": code, ..., "dev_mode": True, ...})   # router.py:63-76
      ```
      **So an unauthenticated visitor types a victim's address, delivery fails for any reason, and the platform prints the victim's live six-digit code into the attacker's browser and pre-fills the verification field with it.** The branch even hard-codes `"dev_mode": True`, so the page presents itself as the intended dev affordance.
      The function's own docstring (`service.py:284-288`) says *"Returns the code **only** when the dev path is active"*. That is the intent; the code does not implement it. The `dev_code_visible()` gate at `:253` is checked, but only as an *early* return — the failure path below it falls through to the same disclosure.
      **This is not `docs/backlog.md` P1-01** (fail-open enforcement default), **nor P2-03** (login rate limiting), **nor the P2-01 cookie item.** Grepped; it is new.
      *~3 loc: have `deliver_code` distinguish "not attempted (dev)" from "attempted and failed", and return the code only for the first.* A one-line form is `return None if not dev_code_visible() else code` in `request_login_code`, which keeps the neutral answer for a real-provider failure.
      **Blast radius:** the login path only. No other caller of `request_login_code` exists (grepped: the definition plus `router.py:59` plus two test references).
      **Risk — this changes authentication semantics and is a human's decision, not a cleanup.** The change makes a real-provider delivery failure a *silent* failure for the user: they see the neutral notice and no code ever arrives, with only a `logger.warning` at `service.py:275`. That is the correct security posture and a worse support experience, and the module docstring at `service.py:14-16` explicitly worries about exactly this ("a misconfigured sender would lock everyone out — including the Admin who would fix it"). **The recovery path must be decided at the same time**, and `AUTH_DEV_SHOW_CODE` (`service.py:241`) already is one. **Not covered by `tests/test_auth.py`** — the suite tests `verify_login_code` and `request_login_code`'s enumeration behaviour but never exercises a delivery failure.
      **Unverified — the specific check:** I traced this statically. Confirm by pointing `SYSTEM_MAIL_PROVIDER` at a real provider with a deliberately invalid key and requesting a code for a known address; the code should appear in the rendered page.

 **✅ Promoted to `docs/backlog.md` 2026-08-21 — track it there, not here.**
- [x] **A2 (rank 2). Any account with a `+` in its address cannot sign in — and the default configuration hides the bug.**
      `backend/app/auth/router.py:78-81` and `:107-112`. Both redirects interpolate the address into a query string without escaping, while the sibling parameter on the same line is escaped:
      ```python
      url=f"/ui/login/verify?email={address}&next={quote(target, safe='')}"   # :79
      ```
      Starlette decodes `+` in a query value as a space, so `diede.slembrouck+claude@googlemail.com` arrives at `verify_form` as `diede.slembrouck claude@googlemail.com`, pre-fills the form with the mangled value, and `verify_login_code` (`service.py:317`) finds no user. The user is told *"That code is not valid or has expired"* — the wrong diagnosis, which is what makes it expensive to find.
      **`quote` is already imported at `router.py:13`.** The fix is `quote(address, safe='')` in both places.
      **Why review missed it:** the dev path never takes this redirect. `dev_code_visible()` is true whenever `SYSTEM_MAIL_PROVIDER` is unset (`service.py:243`), which is the shipped default, and that branch renders `login_verify.html` inline (`router.py:71`). The bug only exists once a real provider is configured — i.e. only in the deployments that matter.
      *2 loc.* **Blast radius:** two redirect strings. **Risk: none.** Sub-addressing is common in exactly this product's operator population, and the maintainer's own address uses it. Not covered by tests — `test_auth.py` calls the service directly and never goes through the router.

 **✅ Promoted to `docs/backlog.md` 2026-08-21 — track it there, not here.**
- [x] **A4 (rank 4). In the shipped default configuration the login form *is* an account-enumeration oracle, which is the one property ADR-151 §2 makes load-bearing.**
      `backend/app/auth/router.py:51-81`. The docstring at `:58` says *"The response is the same whether or not the address exists"*, and the module docstring at `:6-7` calls it load-bearing. Under the default `SYSTEM_MAIL_PROVIDER=mock`:
      - **known active address** → `request_login_code` returns the code → `200` with `login_verify.html` rendered inline (`:71`)
      - **unknown or deactivated address** → returns `None` → `303` redirect to `/ui/login/verify` (`:78`)

      Different status code, different body, trivially distinguishable. The neutral-notice text is identical in both, which is what makes it look correct.
      **This is the same root cause as A1** — the `if code:` branch conflates "dev" with "not delivered" — and both are fixed by the same distinction. **Ranked separately because the decision differs:** A1 is a defect to fix; A4 in *dev* mode is arguably an acceptable trade (a developer machine has no accounts to enumerate). The question for a human is whether ADR-151 §2's property is meant to hold in the demo configuration a prospect is shown, or only in production.
      *0 loc if A1 is fixed as described; the dev branch would then only trigger under an explicit `AUTH_DEV_SHOW_CODE`.*
      **Risk — authentication semantics.** Making the dev path redirect-and-then-show would break the deliberate no-code-in-the-query-string decision documented at `router.py:64-70`, which is a good decision. The honest options are (a) accept the oracle in dev and say so in the docstring, or (b) gate the dev path behind `AUTH_DEV_SHOW_CODE` only and log the code rather than render it. Not covered by tests.

### Redundant work — the per-request auth path

 **✅ Promoted to `docs/backlog.md` 2026-08-21 — track it there, not here.**
- [ ] **A3 (rank 3). Every guarded UI request resolves the session twice, from two different DB sessions, and writes `auth_sessions.last_seen_at` twice.**
      `backend/main.py:216-236` (`attach_current_user` middleware) and `backend/app/auth/dependencies.py:94-95` (`enforce_policy`). Traced, per single guarded page view:

      | Step | Work |
      |---|---|
      | middleware `:225` | opens a second `SessionLocal()` outside the request's `get_db` |
      | middleware `:227` → `current_user_summary` → `user_for_token` (`service.py:358-383`) | `SELECT auth_sessions`, `SELECT users`, `UPDATE last_seen_at`, `COMMIT` |
      | middleware `:233` → `auth_enforced` → `get_config` | `SELECT app_config` |
      | `enforce_policy:94` → `user_for_token` **again** | `SELECT auth_sessions`, `SELECT users`, `UPDATE last_seen_at`, `COMMIT` |
      | `enforce_policy:95` → `auth_enforced` **again** | `SELECT app_config` |
      | `enforce_policy:111` → `has_permission` → `permissions_for` (`service.py:405-418`) | one 3-table join |

      **7 SELECTs and 2 write transactions per page view, of which 3 SELECTs and 1 write transaction are pure duplication.** `/ui/users` is worse: `require_permission` (`dependencies.py:68-70`) repeats the pair a *third* time, and `router.py:151-152` calls `auth_enforced` and `user_for_token` a fourth.
      `auth_sessions` is the only table in the app written on every request, so this is the closest thing the app has to a hot write path.
      **The clean shape:** resolve once in the middleware, stash the resolved `user_id` (not the ORM object — the middleware closes its session at `:235`, so an instance would be detached) plus `auth_enforced` on `request.state`, and have both guards read from there. `enforce_policy` still needs to run after routing for the route template, so it cannot simply move into the middleware.
      *~10 loc across `main.py` and `dependencies.py`.*
      **Blast radius: every request in the application.** This is the highest-blast-radius change in the report despite being the least conceptually interesting one.
      **Risk — this touches authorization plumbing, and "safe because it is small" does not apply.** Three specific hazards: (i) the middleware runs on *every* request including the unauthenticated JSON routers, so the cached value must not become an implicit auth mechanism for them; (ii) `user_for_token`'s idle-timeout check (`service.py:374`) reads `last_seen_at` *before* bumping it, so collapsing two calls into one changes which value the second check saw — deduping is safe but the reasoning must be written down; (iii) the two calls today use two different DB sessions and therefore two transactions, so a caching bug would make the guard read a stale `is_active` within one request, and `is_active` is the offboarding control ADR-151 §5 rests on. **`tests/test_auth.py` covers `user_for_token` and the expiry rules directly but nothing covers the middleware or `enforce_policy`** — there is no request-level test in the repo at all. Add one before touching this.

- [ ] **A7 (rank 7). `access_list` and `roles_with_permissions` are both `1 + 2N`.**
      `backend/app/auth/service.py:602-623` and `:582-599`. `access_list` runs one `SELECT users`, then **per user** a 3-table grants join (`:606-612`) and a live-session `COUNT` (`:613-617`). `roles_with_permissions` runs one `SELECT roles`, then **per role** a permissions query (`:586-591`) and a holders `COUNT` (`:595-597`).
      Both back admin screens with small row counts, so this is not urgent — it is filed because it is the same shape Clusters 1, 4 and 5 found elsewhere and because the fix is mechanical: one grouped query plus a `defaultdict`, the pattern already used at `access_list:607-609`'s own join.
      *~12 loc each.* **Blast radius:** two read-only functions, each with one caller (`auth/router.py:148` and `:218`).
      **Risk: low, and it is display-only** — neither function is on any authorization path. Not covered by tests (`test_auth.py` exercises the service functions the two of these compose, not these two).

### Genuine residue to delete — three lines

- [ ] **A5 (rank 6). `current_user` has zero callers.**
      `backend/app/auth/dependencies.py:52-54`. A FastAPI dependency documented *"Never raises — for optional use"*. Grepped across `app/`, `main.py`, `tests/` and `app/templates/`: the only other matches for the token are `current_user_summary` (a different function, `service.py:80`) and `request.state.current_user` (an attribute set by the middleware and read by `base.html:24,25,40`). **No route depends on it.**
      **This is the one item in the cluster I nearly filed as Suspected**, because it reads as a deliberate affordance in a reference architecture — "here is how you make a route optionally-authenticated". Two things push it to Confirmed as *residue* rather than *seam*: the repo's declared rule is one **worked** example per seam and this one has no worked example, and the actual optional-auth mechanism the app uses is the middleware, which makes `current_user` a second, unused answer to a question already answered.
      *−3 loc.* **Blast radius:** none.
      **Risk: none mechanically** — but this is the one deletion in the report, and if the human's intent is "keep it as the documented optional-auth seam", the right change is a comment saying so, not a deletion. **Defer to the human.**

### Cheap correctness, low payoff

- [ ] **A8 (rank 8). Two redundant indexes — the opposite of the four-cluster pattern.**
      `backend/app/auth/db_models.py:90` (`role_permissions.role_id`, `index=True`) and `:103` (`role_assignments.user_id`, `index=True`). Both are the **leading column** of a unique constraint declared on the same table — `uq_role_permission (role_id, permission)` at `:87` and `uq_user_role_brand (user_id, role_id, brand_id)` at `:99` — so each already has a usable index. The single-column indexes are duplicates that cost write throughput and nothing else.
      Note `role_assignments.role_id` (`:104`) and `.brand_id` (`:105`) are **not** redundant — they are non-leading columns — and `delete_role:572` and `roles_with_permissions:595` both filter on `role_id`. Do not remove those.
      *−2 loc, and a `DROP INDEX` if the running database is to match.* **Blast radius:** none in code.
      **Risk:** the standing migration caveat inverted — removing `index=True` is a fresh-install-only no-op, so the existing database keeps both indexes until someone drops them by hand. Lowest-value item here; filed for completeness because the constraint sweep is the thing this report is measured against.

- [ ] **A9 (rank 9). The policy table matches on bare `startswith` with no path-segment boundary.**
      `backend/app/auth/policy.py:77-79`. `("/ui/content", CONTENT_MANAGE)` would also match a future `/ui/contentmanager`; `("/ui/users", USERS_MANAGE)` would match `/ui/users-export`. **No collision exists today** — I replayed all 43 frontend write-route templates against the table and every one resolves to the intended permission.
      This is a **seam-quality** item in the same class as Cluster 5's D1: the file's own docstring (`:20-21`) presents ordering-by-specificity as the discipline that keeps the table correct, and a boundary-less prefix means specificity is not the only thing that can go wrong. A route added tomorrow can inherit a permission by accidental string prefix, and it fails **open** relative to intent (it gets *a* permission rather than `UNMAPPED`), which is the one direction this module is built to avoid.
      *~2 loc: require the match to be exact or followed by `/`, and add the two trailing slashes the table is already inconsistent about — `"/ui/send-instances/"` has one, `"/ui/campaigns"` does not.*
      **Risk — this changes authorization semantics.** Tightening the match could turn a currently-mapped route into `UNMAPPED`, i.e. a hard refusal. `tests/test_auth_policy.py:82-98` would catch that in CI, which is exactly what makes this cheap: **run that test first, change the matcher, run it again.** That test is the reason this item is safe and the reason it is ranked this low.

---

## Decide, don't delete

Declared-but-unimplemented capability. These are decisions, not cleanups, and all three are ADR-backed.

- **S1. `credentials.manage` is a permission that names no code path — and its own module says that must not happen.**
  `backend/app/auth/permissions.py:24` and `:35`. Grepped every occurrence in `app/`: the constant is defined, described in `ALL_PERMISSIONS`, granted to Admin via `sorted(ALL_PERMISSIONS)` at `:47`, and rendered as a checkbox row in the `/ui/roles` grid (`auth/router.py:219` → `roles.html`). **No route, no dependency and no service function checks it.** Its only other references are in `tests/test_auth.py:79, 85, 367, 369`, where it is used as a convenient arbitrary permission.
  The module docstring at `:3-4` states the rule this violates: *"**permission keys are code, role composition is data.** A permission names a code path, so inventing one requires writing the code it guards."* This one guards nothing.
  **It is not residue and must not be deleted.** `ADR-150 — Tenancy and Access Model` line 54 lists credentials in the Admin row, and **ADR-152 §4 (Proposed)** states *"Credentials are write-only in the user interface"* — a constraint on a credentials UI that does not exist yet, because credentials are environment variables today (`ANTHROPIC_API_KEY`, `RESEND_API_KEY`, `SYSTEM_MAIL_FROM`), read at `frontend/router.py:120` for a presence indicator and never written. **Deleting the permission would delete the hook ADR-152 §4 is waiting for.**
  **What is actionable now, and it is one line:** the `/ui/roles` grid presents `credentials.manage` to an operator as a grantable capability, and granting it does nothing. Either mark it in `ALL_PERMISSIONS`' description as reserved, or say in the grid that it is not yet enforced. *0-2 loc.* **The larger question — build the credentials UI, or drop the permission until ADR-152 is Accepted — is the human's.**

- **S2. Brand scope: the parameters exist, and nothing in `app/` ever passes one.**
  `permissions_for(db, user, brand_id=None)` (`service.py:405`), `has_permission(..., brand_id=None)` (`:421`), `create_user(..., brand_id=None)` (`:431`), `assign_role(..., brand_id=None)` (`:473`). Grepped: **every call site in `app/` uses the default**, and the only calls that pass a real brand are `tests/test_auth.py:100, 120-121`. `ensure_default_brand` supplies the id inside `create_user:448` and `assign_role:480`, so the dimension is populated but never varied — there is no route, form or service function that creates a second brand.
  **`docs/backlog.md` P1-02 already holds the enforcement half of this and I am not re-filing it.** What I am adding is the scope: P1-02 describes the two guards passing no brand; the fuller picture is that **no caller anywhere passes one**, and there is no way to create a second brand, so the dimension is inert end to end rather than merely unenforced. That matters for P1-02's second option ("defer brand RBAC and stop exposing a dimension that does not enforce its own meaning") — the cost of taking it is lower than P1-02 implies, because only the `brand_id` parameters and the `/ui/users` grants column would change, not any caller. **ADR-150 §2/§4 records the column-from-the-start decision and beats tidiness here; report the tension, do not close it.**

- **S3. ADR-153's audit log does not exist, and auth is the module that would own most of it.**
  Grepped `app/` for any audit table, model or write: there is none. The word appears only in docstrings — `auth/db_models.py:12` (*"lets each grant be audited and revoked on its own (ADR-153)"*), `auth/dependencies.py:64-65` (*"the audit trail (ADR-153) has an actor to attribute to"*), `auth/policy.py:5`. Those read as descriptions of a working system.
  **ADR-153 is Proposed**, and its §2 lists exactly the events that have no home anywhere else: *"Login success and failure, role assignment and removal, user deactivation, and credential changes."* All five are in this cluster — `verify_login_code:341-344`, `assign_role`, `revoke_assignment`, `set_active`, and S1's absent credentials path. §6's aggregate-not-per-attempt rule for failed logins also interacts with `docs/backlog.md`'s P2-03 rate-limiting item, which would need the same counter.
  **Nothing to delete; nothing to build until ADR-153 moves off Proposed.** Filed so the docstrings are read as forward references rather than as claims. *Sequencing note: this and P2-03 want the same per-address window counter — doing them separately builds it twice.*

- **S4. No session or login-code reaping exists.**
  `auth_sessions` and `login_codes` grow monotonically. `revoke_token` (`service.py:386-392`) and `revoke_all_sessions` (`:395-400`) set `revoked_at`; `verify_login_code` sets `consumed_at`. **Nothing anywhere deletes a row** (grepped `LoginCodeDB`/`SessionDB` for `delete` across `app/` — the only hits are the test fixture's own cleanup at `tests/test_auth.py:44-48`). `request_login_code` writes a row per request, and P2-03's open item notes that requesting is unbounded, so `login_codes` is an attacker-controllable-growth table holding SHA-256 digests.
  **`ADR-154 — Erasure and Retention` line 79 is directly on point:** *"the architecture's obligation is to provide a prune mechanism and to make the choice visible"* — and for these two tables it provides none. **`docs/backlog.md` has an open data-lifecycle item that ADR-154 line 79 points at; check whether these two tables belong under it rather than as a new entry.**
  *~15 loc for a prune helper called from `bootstrap`, or a `scripts/` job.* **Risk:** deleting a session row is indistinguishable from an unknown token, so pruning only rows already past `expires_at` is safe. Pruning *revoked* rows before expiry is not — it would erase the offboarding evidence ADR-151 §5 and ADR-153 depend on. **That distinction is the whole design of the item.**

---

## Report-only observations — the auth-specific questions the brief asked

- **Permission vocabulary consumption.** Eight of the nine permissions are consumed. `view`, `campaigns.manage`, `content.manage`, `audiences.manage`, `sends.execute`, `ai.run`, `settings.manage` are all resolved by `policy.py`; `users.manage` is enforced by ten explicit `require_permission` guards in `auth/router.py`. **`credentials.manage` is the one orphan — S1.** In the other direction, **no route checks a permission no role grants**: `UNMAPPED` is deliberately absent from `ALL_PERMISSIONS` (`policy.py:31-33`, asserted at `test_auth_policy.py:77-80`), which is the point of it.
- **Guard consistency.** Correct and deliberate everywhere I checked. `frontend_router` carries `enforce_policy` once at `main.py:293-296`; `auth_router` is included **without** it at `:279` and its ten admin routes carry individual `require_permission(USERS_MANAGE)` guards; `/ui/login`, `/ui/login/verify` and `/ui/logout` are unguarded, the last with a documented reason (`router.py:128-130`) that describes a real bug that was fixed. `policy.py:56-63`'s comment correctly labels its own `/ui/users` and `/ui/roles` entries as documentation rather than enforcement. The unguarded JSON routers are the already-filed machine-auth P0. **No inconsistency found.**
- **`GET /ui/settings` requires only `view`.** `required_permission` returns `VIEW` for any non-write method (`policy.py:74-75`), asserted at `test_auth_policy.py:21`. So a Viewer can read the Settings page: the AI token budget, spend-to-date, the configured model, and the full published prompt body (`frontend/router.py:132-133`). The write is correctly gated on `settings.manage`. **Flagged as an observation, not a defect** — reads-need-view is the recorded design, and the table entry `("/ui/settings", SETTINGS_MANAGE)` sitting in a file called "the policy" makes the page *look* Admin-only when only its writes are. Same holds for `/ui/campaigns/{id}` and every other read. If read-gating is ever wanted, `policy.py` is one function away from supporting it — but that is an ADR-150 semantics change, not a cleanup.
- **Session/cookie lifecycle: nothing declared-but-unimplemented.** Both expiries in the `SessionDB` docstring are enforced (`user_for_token:372-375`), `revoked_at` is honoured (`:365`) and set on deactivation (`set_active:466-467`), `last_seen_at` is bumped (`:381`). The absolute lifetime and the cookie `max_age` agree (`SESSION_ABSOLUTE_HOURS` used in both, `service.py:352` and `router.py:120`). `CODE_TTL_MINUTES`, `CODE_MAX_ATTEMPTS` and `SESSION_IDLE_MINUTES` all have live readers. The `Secure` flag gap is already `docs/backlog.md` P2-01. **One small asymmetry, not worth a numbered finding:** `logout` calls `response.delete_cookie(SESSION_COOKIE)` (`router.py:133`) without the `httponly`/`samesite` attributes `set_cookie` used; paths match at the default `/`, so it works, and browsers key deletion on name+path+domain. Noted only so a future sweep does not re-derive it.
- **`auth_enforced` is the one config key not declared in `settings/service.py`.** It is defined at `auth/dependencies.py:33` with its accessor at `:48-49`, while the other five keys and their typed accessors sit together in `settings/service.py:15-19`. Defensible — auth owns its own key, and the alternative creates a settings→auth import — but it means the config-key inventory is in two files, and `docs/architecture/Code/settings.md` documents neither it nor the two AI keys (see Housekeeping).

---

## Cross-module: the Cluster 4 C1 promise, quantified

Not re-filed — the brief pre-declared it. Adding one piece of evidence the human will want when triaging it, because it lands in this cluster's UI copy:

`app/templates/settings.html:61-62` reads *"e.g. set `click` weight higher to make clicks count more, or lower a half-life to make interest fade faster. **Changes apply immediately to computed signals.**"*

Half of that is true. Half-lives are read through `get_half_lives` on every signal computation (`insight/signals.py:52-58`), so the second clause holds. The **weight** clause does not for the engagement path: `insight/service.py:92` reads `CONTRIBUTION_WEIGHTS[event.event_type]` directly, so the `click` example in the help text is precisely the case that does not work. Note `record_contribution` (`insight/signals.py:76-78`) **does** call `get_signal_weights`, so the manual/declared path honours the editor — which is why the screen appears to work when tested by hand, and why this survived. `docs/backlog.md:206`'s Done entry records the verification that was done: it set a **half-life** to 0.001 and watched a signal collapse. The weight side was never verified.

---

## Unverified — the specific checks a human should run

1. **A1's disclosure.** Configure a real `SYSTEM_MAIL_PROVIDER` with an invalid key, request a code for a known address, and confirm the code appears in the rendered `login_verify.html`. This is the single most important check in the report.
2. **A2's mangling.** Create a user with a `+` in the address, configure a real provider, request a code, and confirm the verify form pre-fills a space where the `+` was.
3. **A4's oracle.** With the default mock provider, request a code for a known and an unknown address and diff the status codes (expect 200 vs 303).
4. **A3's query count.** Enable SQLAlchemy echo and load one guarded page; expect 7 SELECTs and 2 commits. I counted these by reading the call graph, not by running it.
5. **A8's redundant indexes.** `\d role_permissions` and `\d role_assignments` in psql, to confirm both the unique constraint's index and the single-column index exist on the running database.

---

## Leave alone — looks dead, is not

Checked, not sampled. **Do not re-run reachability on this cluster.**

- **`MockProvider` reached via `system_mail_provider()` defaulting to `"mock"`** (`service.py:217`) — a deliberate default with a written rationale (an inferred-from-key version *"once caused this code to email a live message to a throwaway test address"`). Not a leftover.
- **`BrandDB`** — one row, created by `ensure_default_brand`, joined by `access_list:609`. Live, even though nothing varies it. See S2.
- **`RolePermissionDB.id`, `RoleAssignmentDB.id`** — surrogate keys on tables that also carry unique constraints. `revoke_assignment:501-503` and the `/ui/users/assignments/{assignment_id}/remove` route address grants by `id`. Not redundant.
- **`UserDB.is_external`** — written by `create_user:440`, read by `users.html`. Documented at `db_models.py:51-53` as existing for *visibility*, not for access. A future sweep will want to call it write-only; it is not.
- **`RoleDB.is_customised`** — set only by `set_role_permissions:553`, read only by `ensure_builtin_roles:119`. Two references, both load-bearing: without it, startup silently reverts a company's edits. Covered by `tests/test_auth.py:380-390` (*"startup reverted a customised role"*).
- **`MANAGER` / `VIEWER` constants** (`permissions.py:40-41`) — referenced only as `BUILTIN_ROLES` dict keys in the same file and in tests. They are the preset, not dead constants.
- **`IMPLIED`** (`permissions.py:69`) — a one-element set that looks like over-abstraction. Three real call sites (`service.py:130, 530, 548`), each a different code path where forgetting `view` would lock someone out.
- **`DEFAULT_LANDING`** (`service.py:55`) — the fallback in `safe_next`, hit three times in that function.
- **`app_config` having no index beyond the PK** — `key` *is* the primary key and every query is an equality filter on it. Complete, not missing.
- **`settings/` having no router** — deliberate and documented in `docs/architecture/Code/settings.md`; the UI writes through `frontend/`. Zero JSON callers is not the ADR-142 case here, there is simply no JSON surface.
- **`get_config`/`set_config` being generic and untyped** — the "no migration for a new setting" property is the recorded design (`db_models.py:14-15`). The typed accessors above them are where the safety lives.
- **The `except (KeyError, TypeError, ValueError)` blocks in `get_ai_spend_cap:106, 118`** — not the broad-catch pattern Clusters 2/5 flagged. They are narrow, and the comment at `:108-109` explains the clamp they protect.
- **`tests/test_auth.py`'s use of the real shared dev database** — deliberate, documented at `:3-6`, with per-test cleanup. Not a test-isolation defect to fix.

---

## Housekeeping — read-only notes, not work items

- **There is no `docs/architecture/Code/auth.md`.** Every other module in `backend/app/` has a page under `docs/architecture/Code/`; the highest-blast-radius module in the codebase does not, and `MOC - System Overview.md` does not list it (grepped — the only `auth` hits are the word "authoritative"). The auth source carries unusually good docstrings, which is probably why: the module page's Purpose / Public surface / Invariants / Change-impact structure is what the earlier sweeps ran on before touching source, and this cluster had to be read from source instead.
- **`docs/architecture/Code/settings.md` is stale (last modified 2026-07-27).** Its Public surface lists four accessors; the module has six — `get_ai_provider_name` and `get_ai_spend_cap` are missing, as are the `ai_provider`, `ai_spend_cap` and `auth_enforced` keys. Its **Depends on** section lists only `insight`, but `settings/service.py:10` imports `app.ai.adapters.factory` at module level, and unlike the `insight` import that one is not lazy. Its **Depended on by** section omits `ai` (`ai/service.py:24`) and `auth` (`auth/dependencies.py:29`).
- **`tests/test_auth_policy.py:84` uses a CWD-relative path** — `Path("app/frontend/router.py")`. There is no `conftest.py`, `pytest.ini` or `pyproject.toml` in `backend/`, so the suite's best test silently fails to find the router if pytest is run from the repo root rather than from `backend/`. The `assert routes, "no write routes found — has the router moved?"` guard at `:88` turns that into a clear failure rather than a false pass, which is good design — but it makes the test fail for the wrong reason. *~1 loc: anchor on `Path(__file__).parent.parent`.*
- **Two tests the policy table is missing, both of which would have caught findings in this report.** `test_every_ui_write_route_has_a_policy_entry` (`:82`) checks the direction "route → has an entry". Neither reverse direction is checked: (a) every entry in `WRITE_POLICY` corresponds to a route that still exists — a renamed route leaves a dead prefix silently; (b) every permission in `ALL_PERMISSIONS` is reachable from some route or guard — **that one would have caught S1 in CI**. Noting the shape, not proposing the code.
- **The `providers/adapters/mock.py` deletion in the working tree** (`git status`, staged `D`) is outside this cluster and outside `auth`/`settings`. Not assessed.

---

**Findings dropped: 4**, all below the reporting bar. `login_request` recomputes `normalise_email(email)` after `request_login_code` already normalised it internally (`router.py:60`, 1 loc, no behaviour). `roles_page`'s `error: str = ""` query parameter is rendered unescaped-looking but Jinja autoescape handles it. `hash_secret` is a bare SHA-256 used for both session tokens and login codes where the docstring at `db_models.py:112-115` explains why a KDF is not used for codes — the same reasoning genuinely does hold for a 256-bit `token_urlsafe(32)`, so it is not the finding it first looks like. `ensure_initial_admin:171-172` does not guard against `role is None` before `role.id`, but `bootstrap:180` calls `ensure_builtin_roles` first, so the admin role always exists.

**Highest-value single item: A1** — three lines that stop a failed provider delivery from printing a live sign-in code into an unauthenticated visitor's browser. Fix A2 in the same commit; it is two characters on the adjacent line and it only exists in the deployments where A1 is dangerous.

---

# Cluster 7 — `ai` + `snapshots` + `email_modules`

**Swept:** 2026-08-21 · `backend/app/ai/` (746 loc, 8 files) + `backend/app/snapshots/` (253 loc, 4 files) + `backend/app/email_modules/` (156 loc, 2 files) — all eleven files read in full
**Method:** every symbol, ORM column, dataclass field, manifest JSON key and route grepped across `backend/app/`, `backend/main.py`, `backend/scripts/`, `backend/tests/`, `backend/app/templates/` and `storage/`. AST pass for unused imports over all three packages. Manifest keys checked against the five files in `storage/email_modules/` and against every consumer of `ModuleManifest`, not only the registry. `docs/backlog.md` cross-checked before every finding; the five items the brief pre-declared as filed are referenced, never re-filed.

## Headline

**The brief's prediction held for `ai/` and half-held elsewhere. `ai/` cleared its interview 8/8 and the *structure* is genuinely clean — but four things slipped through the interview because they are all on the one path the test suite does not reach: `run_task` itself.** There is no `tests/test_ai_service.py`. The four AI test files cover the adapters, the pricing table and the parser — the gate, the audit rows and the ledger are exercised by nothing.

Clean negatives first, because they are most of the result:

- **Zero unused imports** across all eleven files (AST-verified, not sampled).
- **Zero dead functions, zero dead routes, zero orphaned columns.** Every column on `ai_prompts`, `ai_runs` and `snapshots` has a reader. All three `/snapshots` routes and both `/email-modules` routes are registered and documented. `MODEL_PRICING` has a live consumer (`cost_usd` → `spend_to_date` → `frontend/router.py:104`), `FREE_PROVIDERS` has two.
- **No orphaned schema behind seed SQL.** I ran the Cluster 2 method (grep writers in `backend/app/` with `backend/scripts/` excluded) against all three tables. `scripts/seed_demo_data.py:225` writes `SnapshotDB` and `scripts/reset_all_data.sql` touches nothing in `ai/` — every column these tables carry is also written by application code. **Cluster 2's pattern does not recur here.**
- **`snapshots/` produced no dead code and no dead schema at all.** Saying so plainly, as the brief asked: the only findings in that module are one missing FK index and one duplicate query, and the two known items (ADR-062 override reference, non-atomic persistence) are already filed.
- **`email_modules/` produced no dead code either.** Its findings are one unenforced manifest key and a caching question — plus the one genuine piece of residue in the cluster, which is not in `email_modules/` at all but in a template that hardcodes around it.
- **The spend cap *is* enforced on the path that spends.** `provider.generate` is called in exactly one place (`ai/service.py:205`) and the pre-call gate sits above it. There is no second spender.
- **The audit row *is* written on failure as well as success** — all four exit paths of `run_task` write an `AIRunDB` row first. What the failure row omits is tokens (A2).

What Cluster 7 carries is four themes:

1. **One piece of genuine residue, and it is a live defect** (E1): a template hardcodes three module types after the registry loop, one of which has no manifest and renders nothing. `scripts/reset_all_data.sql:147` already records that fix being applied to seed data; the dropdown was never updated.
2. **The token ledger undercounts real spend** (A2). A Claude refusal returns HTTP 200 with a populated `usage` block — Anthropic bills those input tokens — and `run_task`'s error branch drops it, writing 0/0.
3. **The cap gate does not know about free providers although the ledger does** (A4). Once real spend fills the budget, mock runs are refused too, which is the opposite of `tokens_used`'s stated rationale.
4. **Two missing constraints** (A5, S1) — the streak Cluster 6 broke resumes. `ai_prompts` has no uniqueness anywhere despite a documented "exactly one published version" invariant.

**Nothing here should be deleted except three lines of template and one redundant import.** Everything else is a fix, a constraint, or a decision.

---

## To do

Ranked by payoff ÷ risk. Unchecked = not started. **Standing caveat from Clusters 3-5 applies to A5 and S1: there is no migration tool**, so `index=True` and new `__table_args__` take effect only on a fresh `create_all` and are silent no-ops on the running database until someone writes the DDL by hand.

### Confirmed — genuine residue, and it is a live defect

- [ ] **E1 (rank 1). Three hardcoded module types after the registry loop — one of them has no manifest and renders nothing.**
      `backend/app/templates/campaign_detail.html:312-317`, the *add-module* form:
      ```jinja
      {% for tpl in module_templates %}
      <option value="{{ tpl.name }}">{{ tpl.label }} ({{ tpl.name }})</option>
      {% endfor %}
      <option value="hero">hero</option>
      <option value="content_card">content_card</option>
      <option value="cta">cta</option>
      ```
      `module_templates` is `list_manifests()` (`frontend/router.py:699`), which already yields `cta`, `hero`, `img_left`, `img_right`, `single_stack`. So `hero` and `cta` are **duplicate options** in the same `<select>`, and **`content_card` is not a module at all** — there is no `content_card.json` or `.html` in `storage/email_modules/`, and the only other occurrence of the string in the entire repo is `scripts/reset_all_data.sql:147`:
      > `-- visible. (It was 'content_card', which has no manifest and renders nothing.)`
      **The seed data was fixed for exactly this reason and the dropdown was not.** A manager who picks it creates a `ModuleInstanceDB` whose `module_type` has no manifest; `render_module` (`rendering/service.py:130-131`) falls through to `render_unknown_module`, and `overrides/service.py:40-44` refuses to override it. Silent at creation time, visible only in the render.
      Residue from before the registry existed — this is the pre-plugin hardcoded list that was never removed when `list_manifests()` was wired in above it. Note the sibling *edit*-module form at `:216-222` was migrated correctly and has no hardcoded options, which is what makes this a leftover rather than a convention.
      *−3 loc.* **Blast radius:** one `<select>`. Removing the three lines strictly reduces the option set to what the registry can actually render.
      **Risk: near none, and name the one case** — if any existing row already has `module_type='content_card'`, removing the option does not repair it; the edit form's fallback at `:222` (`{% if module.module_type not in types %}`) is what keeps such a row selectable. Check with `SELECT DISTINCT module_type FROM module_instances;` before deleting. Not covered by any test; `docs/backlog.md` has no entry for it (grepped `content_card`).

### Confirmed — the ledger and the gate

- [ ] **A2 (rank 2). A model refusal is billed by the vendor and recorded as zero tokens, so the cap undercounts real spend.**
      `backend/app/ai/service.py:207-213`:
      ```python
      if not result.success:
          run = _record(
              db, task_key=task_key, prompt_id=prompt_row.id, provider=provider_name,
              model=result.model, status="error", target_type=target_type,
              target_id=target_id, message=result.message,
          )
      ```
      `input_tokens` and `output_tokens` are not passed, so the column defaults apply and the row stores 0/0. For a network error or an HTTP 4xx that is correct — nothing was spent. **It is not correct for the refusal branch**, and that branch exists deliberately: `adapters/claude.py:175-192` handles `stop_reason == "refusal"`, which Anthropic returns as **HTTP 200 with a populated `usage` block**, and constructs `AIResult(success=False, usage=usage, ...)`. The adapter goes to the trouble of carrying real usage through a failure result and the service throws it away.
      A refused request still bills its input tokens. So every refusal is invisible to `tokens_used` (`:89-104`) and to `spend_to_date` (`:107-133`), which means **the ADR-144 §5 gate is computing `remaining` against a ledger that is missing real spend** — the one direction `pricing.py`'s module docstring says the design must never fail in (*"the gate degrades to conservative, never to permissive"*).
      *+2 loc — pass `input_tokens=usage.input_tokens if usage else 0` and the same for output, exactly as the success branch at `:219-220` already does.*
      **Blast radius:** one `_record` call. The `status="error"` semantics do not change; only the token columns become truthful.
      **Risk: low, and it is a reporting change, not a semantics change** — but note it makes `spend_to_date`'s guard at `:125` (`not (input_tokens or output_tokens)` → skip) start pricing refusals, which is the intended outcome and is worth stating because the comment at `:123-124` currently reads *"A refused run spent nothing"*. **That comment is about the pre-call `status="blocked"` rows and stays true for them; it will no longer describe the `status="error"` rows, so it needs one word of clarification in the same commit.** Not covered by tests — `tests/test_ai_claude_adapter.py` asserts the adapter returns `success=False` with usage on a refusal, so the adapter half is pinned; nothing exercises what `run_task` does with it.

- [ ] **A4 (rank 3). The cap gate refuses free runs, although the ledger deliberately excludes them.**
      `backend/app/ai/service.py:187-203`. The gate computes `worst_case` and `remaining` and refuses, with **no check on whether this run can cost anything**. `run_task` knows `provider_name` at `:156` and `pricing.is_billable` is already imported at `:23` for `tokens_used`.
      The two halves therefore disagree. `tokens_used`'s docstring (`:90-95`) is explicit about why free runs are excluded from the ledger — *"counting them would let development and demo traffic consume a budget only the real model draws on"* — and then the gate turns around and spends the same budget's *headroom* on those very runs. **The observable consequence: once real Claude usage fills the cap, the mock adapter stops working too**, so a developer or a demo cannot run the Mode A flow at all until someone raises the cap. That is precisely the state `adapters/mock.py:1-12` says must never happen (*"ADR-143 requires development to work without production credentials"*).
      *+2 loc: skip the gate when `not is_billable(provider_name)`, or add the condition to the `if worst_case > remaining` test.*
      **Blast radius:** one branch in one function.
      **Risk — this is a governance decision, not only a cleanup, and it should be named as such.** ADR-144 §5 describes the cap as bounding *spend*; on that reading the fix is obviously right. But there is a second reading in which the cap also bounds *volume* of AI activity, and under that reading exempting mock is wrong. **The current behaviour implements neither reading consistently**, which is the actual finding. `count_input_tokens` is still worth calling for a free provider so the audit row records the shape of the run. Not covered by tests.

- [ ] **A3 (rank 4). `subject_preheader.suggest` re-imports a module it already imports, queries the same prompt row twice, and its fallback cannot fire.**
      `backend/app/ai/tasks/subject_preheader.py:107-111`. Three things stacked in five lines:
      1. **`from app.ai.service import get_published_prompt` inside the function** while `:20` already does `from app.ai.service import run_task` at module level. Same module, no cycle to break, no comment claiming one. Straight residue — and unlike Cluster 1's 14 lazy imports and Cluster 2's `_normalize_for_strategy`, both of which had a hypothesis behind them, this one has none. *−1 loc, hoist the name onto line 20.*
      2. **`get_published_prompt` is then called again inside `run_task` (`ai/service.py:157`)** — two identical queries per suggestion.
      3. **The `DEFAULT_PROMPT` fallback at `:110` is unreachable in effect.** If `prompt_row is None`, `suggest` renders `DEFAULT_PROMPT`, hands it to `run_task`, and `run_task:159-165` immediately refuses with *"No published prompt for this task — publish one in Settings."* The rendered text is discarded unused. **Do not delete `DEFAULT_PROMPT`** — `frontend/router.py:131` uses it to seed the Settings textarea, which is its real job. Delete the *fallback*, or decide the opposite (let `run_task` accept a caller-supplied prompt body) — those are opposite actions, see open question 2.
      **The non-cosmetic part:** the two lookups are a TOCTOU. A manager publishing a new version between `:109` and `service.py:157` produces an audit row whose `prompt_id` points at version N+1 while the text actually sent was version N. **That is an ADR-140 §3 reproducibility violation** — the entire reason the row stores an id rather than the text is that the id must resolve to what was used. Same shape as the race Cluster 3 D2 found in `build_render_context`, and the same fix: pass the object the caller already holds instead of re-fetching.
      *~4 loc: hoist the import, add a `prompt_row` parameter to `run_task`, drop the fallback.* **Blast radius:** one task file, one service signature with one other caller (none — `run_task` is called only from `subject_preheader.py:113`).
      **Risk: low.** The signature change is internal; the JSON surface does not expose `run_task`. The race is narrow (two queries microseconds apart) and has almost certainly never fired — file it for the correctness statement, not the probability. Not covered by tests; `tests/test_ai_subject_task.py` tests `parse_options` and the mock's format imitation, never `suggest`.

### Missing constraints

- [ ] **A5 (rank 5). `ai_prompts` has no uniqueness at all, and the invariant it needs is stated three times in prose.**
      `backend/app/ai/db_models.py:31-44` — no `__table_args__`, no `UniqueConstraint`, no `unique=True`. Two rules are asserted in comments and enforced only by application code:
      - *"Exactly one published version per task_key is the live one"* (`:40-42`), enforced by the bulk `UPDATE ... SET is_published=False` at `service.py:72-75`.
      - Version numbers are unique per task, enforced by `next_version = (latest.version + 1) if latest else 1` at `:70`.
      **Both are read-modify-write with no lock.** Two concurrent `publish_prompt` calls for the same `task_key` both read `latest.version = 3`, both write version 4, and both set `is_published=True` after the other's `UPDATE` — leaving two published version-4 rows. `get_published_prompt` (`:40-46`) then returns whichever `ORDER BY version DESC` picks first, non-deterministically, and every subsequent audit row points at a prompt id that is one of two different texts.
      This is the exact failure mode `db_models.py:10-14` says the design exists to prevent: *"that id is what makes a past decision reproducible."*
      **In-repo precedent is explicit and recent:** `docs/backlog.md:288` (Done 2026-07-12) fixed a read-modify-write race in `overrides.record_outcome_delta` with `with_for_update()`, and `auth/db_models.py:87, 99` carry the compound uniqueness this table lacks. Cluster 3 named the missing-constraint pattern as systemic; **`ai/` is another module it never reached.**
      *+3 loc: `UniqueConstraint("task_key", "version")` plus a partial unique index `postgresql_where=(is_published.is_(True))` on `task_key`. Optionally `with_for_update()` on the `latest` lookup, mirroring the 2026-07-12 fix.*
      **Blast radius:** one table. **Risk — read this before acting.** The partial unique index and the current code order are **incompatible as written**: `publish_prompt` inserts the new published row (`:77-83`) *after* the `UPDATE` that clears the old one, but both happen in one transaction and SQLAlchemy's flush order is not guaranteed to put the `UPDATE` first. Adding the index without forcing a flush between the two statements will make publishing fail intermittently. **The plain `UniqueConstraint(task_key, version)` is safe on its own and is the step to take first.** Standing migration caveat: no-op on the existing database without manual DDL, and the DDL will fail if duplicate rows already exist — check first.

- [ ] **S1 (rank 6). `snapshots.variant_id` is unindexed and is the filter on three read paths, one of them per-row in a list view.**
      `backend/app/snapshots/db_models.py:10-11` — neither `variant_id` nor `recipient_id` carries `index=True`, and a SQLAlchemy `ForeignKey` does not create one. Readers filtering on `variant_id`:
      - `list_snapshots_for_variant` (`snapshots/service.py:144-152`), behind `GET /snapshots/variants/{id}`
      - `frontend/router.py:654-658` — **inside the per-variant loop in `campaign_detail`**, so it is N queries on an unindexed column on the app's largest page (the same handler as Cluster 1 #7)
      - `frontend/router.py:2019-2020` and `providers/service.py:114` filter by primary key, which is fine
      `recipient_id` has no filter today and is the weaker half of the item; it becomes load-bearing the moment per-recipient snapshots are persisted, which `docs/backlog.md:158` is actively deciding.
      **In-repo precedent, identical to the one Cluster 4 C4 and Cluster 5 cited:** `overrides/db_models.py:48` indexes `module_instance_id` for a colder lookup; `recipients/db_models.py` indexes four FKs; `auth/db_models.py` indexes every FK.
      *+1 loc (`variant_id`), +2 with `recipient_id`.* **Blast radius:** none in code.
      **Risk: the standing caveat, and it is the whole risk** — `index=True` takes effect only on a fresh `create_all`, so on the running database this is a change that **reads as fixed and does nothing**. See Unverified.

### Redundant work

- [ ] **EM1 (rank 7). `get_template_html` re-reads from disk and Jinja re-compiles, per module, per recipient, on the send path.** *(This is Cluster 3 D5 — assessed from the owning side in the Open Calls section below rather than re-argued here.)*
      `backend/app/email_modules/registry.py:106-110` + `backend/app/rendering/service.py:176, 180, 197, 220`. Per rendered module: `_dir_mtime()` stats **all 11 files** in `storage/email_modules/` (via `get_manifest` → `_ensure_fresh`), then `Path.exists()`, then `read_text()`, then `_jinja.from_string(...)` compiles the template from scratch. A 5-module send to 1,000 recipients is ≈55,000 `stat` calls, 10,000 file operations and 5,000 Jinja compilations.
      *~10 loc to fold template HTML into `_ensure_fresh`'s rebuild.* **Blast radius:** `registry.py` plus two lines in `rendering/service.py` if the compiled template is cached too.
      **Risk and the design call are in "Open call D5" below** — including why `lru_cache` is the wrong tool here and why `_load_brand_css` should be folded into the same fix. Not covered by tests; `email_modules/` has no test file and is exercised only indirectly by `tests/test_overrides.py:75`.

- [ ] **A6 (rank 8). `/ui/settings` scans the whole `ai_runs` table twice per page load.**
      `backend/app/ai/service.py:89-104` and `:107-133`. `tokens_used` selects `(provider, input_tokens, output_tokens)` for every row and sums in Python; `spend_to_date` selects `(provider, model, input_tokens, output_tokens)` for **the same every row** and sums in Python. `frontend/router.py:103-104` calls both, back to back, on one request. `run_task:188` calls `tokens_used` a third time per AI run.
      **`docs/backlog.md` already holds the `tokens_used` re-sum** — the brief names it as a known-good example. **I am not re-filing it. What I am adding is that it has a twin**: the backlog item as written describes one function, and fixing only `tokens_used` leaves the second full scan in place on the same page. The two collapse into a single grouped query (`SELECT provider, model, SUM(input_tokens), SUM(output_tokens) ... GROUP BY provider, model`) that answers both questions, or into one ledger-total row maintained on write.
      *0 loc if scoped into the existing backlog item; ~15 as a standalone rewrite of both functions.* **Risk:** `spend_to_date`'s `unpriced_runs` is a **count of runs**, not a sum, so a grouped query must count rows per `(provider, model)` and not lose that. That is the one subtlety and it is why the two functions were written separately.

- [ ] **S2 (rank 9). `build_render_context` re-loads the module list that `render_variant_html` just loaded.**
      `backend/app/snapshots/service.py:35-40` issues the identical query to `rendering/service.py:70-75`, ordered the same way, moments after `create_snapshot_for_variant:98` returned from the render. Two queries, and — the part that matters — **two independent reads of a mutable table**, so a module added or moved between them makes the snapshot's `render_context` describe a composition the stored HTML does not have.
      That is the same class as **Cluster 3 D2**, and D2's fix is already the right shape: `render_variant_html` grew `collect_resolutions` to hand back what it used rather than have the caller re-derive it. **The module list is the second thing that should come back through that channel.**
      *~6 loc, folded into D1/D2.* **Do not raise or schedule this independently — it belongs in the same commit**, and `docs/backlog.md:158` sequences that work.
      **Risk:** none as scoped; the shape already exists. **ADR-062** is the governing record.

### Cheap correctness, low payoff

- [ ] **A7 (rank 10). Three of `TaskRun`'s six fields have no reader, and the comment explaining two of them is factually wrong.**
      `backend/app/ai/service.py:27-37`. The comment at `:35` reads *"Populated even when blocked, so the UI can explain **why** it was refused."* **All three blocked/error returns (`:165`, `:185`, `:203`, `:213`) pass only `ok`, `run_id` and `message`**, leaving both token fields at their 0 defaults. The one path that populates them is the success path at `:233-234`.
      And nothing reads them anywhere: the only consumer of a `TaskRun` is `frontend/router.py:827`, which uses `run.run_id` and nothing else, then reads the tokens back off `AIRunDB` at `:727`. `TaskRun.message` is likewise never read. So the dataclass carries three write-only fields **and** a comment describing behaviour it does not have.
      **This is the item in the cluster I am least willing to call deletable.** `TaskRun` is the return contract of the AI seam — an adopter writing a second task reads this dataclass to learn what a task run yields, and a richer return type is defensible in a reference architecture in a way a dead private helper is not.
      *The honest fix is 4 loc in the other direction: actually populate `input_tokens` on the blocked paths (the value is in hand at `:187`) and delete the "even when blocked" claim from the one path where it cannot be true — the missing-prompt branch at `:160`, which runs before any counting.* Deleting the fields instead is ~2 loc and shrinks the seam. **Human's call; do not delete without one.**
      **Blast radius:** none either way. **Risk: none.** Not covered by tests.

- [ ] **EM2 (rank 11). `ModuleVariable.required` is parsed, exposed on the public API, and enforced by nothing.**
      `backend/app/email_modules/registry.py:15-16` and `:36`; surfaced as `ModuleVariableOut.required` at `email_modules/router.py:11` on both `/email-modules` routes. Grepped every consumer of a manifest:
      - `rendering/render_cms_module` (`rendering/service.py:165-171`) iterates **all** `manifest.variables` and defaults a missing one to `""` — no required check
      - `rendering/render_static_module` (`:203-210`) has a comment saying it fills *"missing **required** variables"* and then loops over all of them regardless
      - `overrides/_validate_field_overrides` (`overrides/service.py:47-56`) reads `{v.name for v in manifest.variables}` only
      - `frontend/router.py:566-568` projects `[v.name for v in manifest.variables]`
      So a manifest can declare `"required": true` and a module renders with the field blank and no warning anywhere. Meanwhile the *decision-strategy* config spec — the sibling plugin system — does enforce its own `required` (`decision/strategies/base.py:83`). **Two plugin manifests, two meanings for the same word.**
      **Not residue: it is declared capability, and it is documented as real.** `docs/architecture/Code/email_modules.md` lists `variables` (label, required flag) as the manifest contract. Deleting it breaks the JSON API shape (ADR-142 surface) and removes a designer-facing affordance.
      *0 loc recommended now; ~6 to enforce it (a render-time warning log, or a validation error in `overrides`).* **This matters for D4 — see the assessment below.** Not covered by tests.

---

## Answers to the three parked questions

### 1. Cluster 1, open call A — is AI-optional boot a real requirement? **No. Definitively no.**

I own `ai/` and the property does not hold, has never held, and is not close to holding. Four independent pieces of evidence, any one of which settles it:

**(a) There is no `anthropic` dependency to be optional about.** `rg -i anthropic` across `backend/` returns environment-variable names, a URL, a header value and test fixtures — **no package import**. `adapters/claude.py:25` imports `httpx` and calls `https://api.anthropic.com/v1` directly over HTTP. The Anthropic SDK is not in `requirements.txt` and not used. The hypothesis "keep the app bootable with `anthropic` uninstalled" is answering a question the codebase never asked.

**(b) `main.py:121` imports `app.ai.db_models` at module scope**, unconditionally, so that `AIPromptDB` and `AIRunDB` register with `Base.metadata` before `create_all`. Delete `app/ai/` and the app does not start — it fails on line 121, long before any route is reached.

**(c) Cluster 6's observation is correct and it is worse than "may already break the property" — it breaks it on the boot path.** The chain is unconditional and entirely module-level:

| Step | Line |
|---|---|
| `main.py:145` → `app.frontend.router` | module level |
| `frontend/router.py:28` → `app.settings.service` | **module level** (the AI-specific settings imports at `:100, 141, 179` are lazy; this one is not) |
| `settings/service.py:10` → `app.ai.adapters.factory` | **module level** |
| `factory.py:10` → `app.ai.adapters.claude` | module level |
| `claude.py:25` → `httpx` | module level |

So by the time FastAPI has finished importing the application, `app/ai/adapters/claude.py` and `httpx` are already loaded. **The 14 function-local imports in `frontend/router.py` protect nothing that is not already unprotected two lines above them at `:28`.**

**(d) The factory degrades correctly at *runtime*, which is the reason it does not need import-time optionality.** `get_ai_provider` (`factory.py:23-35`) returns `MockAIProvider` by default and raises `ValueError` only for a name that is not in the governed list — and a name outside `AVAILABLE_AI_PROVIDERS` cannot be saved (`frontend/router.py:183`). `ClaudeProvider.__init__` never fails without a key; the degradation happens where it should, at call time: `generate` returns `AIResult(success=False, message="ANTHROPIC_API_KEY is not set")` (`claude.py:126-131`) and `count_input_tokens` raises `TokenCountUnavailable` (`:217-218`), which `run_task:173-185` turns into an audited blocked run. **Missing credentials are handled properly. Missing code is not handled at all, and does not need to be.**

**Resolution for Cluster 1's 14 imports: hoist them.** No cycle exists — I verified the full graph, not just the leaf claim. `app.ai.service` → `app.settings.service` → `app.ai.adapters.factory` → `{base, claude, mock}`, and none of those four import `app.settings` or `app.frontend`. So `frontend → ai.service → settings.service → ai.adapters.factory` is a chain, not a cycle, and it is already exercised today via `frontend/router.py:28`.

**Two caveats a human should weigh before the commit, neither of which changes the answer:**

- **Hoisting makes the `httpx2` pin a boot-blocker in writing, not just in effect.** It already is one — `settings/service.py:10` guarantees `httpx` is imported at startup — but with 14 lazy imports in the router the pin *looks* like it only endangers delivery. `requirements.txt:8` pins `httpx2` while `claude.py:25` and `delivery/providers/resend.py:19` both import `httpx`. **That backlog item is more severe than its entry suggests: a clean-install of the pinned requirements produces an application that cannot start.** Fix the pin in the same change or before it. (Already in `docs/backlog.md`; not re-filed, only re-scoped.)
- **Import time.** Hoisting moves the cost of importing `httpx` and the adapters from first-AI-use to startup. That cost is already paid at startup today. No change.

**If the human decides the other way** — that AI-optional boot *should* become a real property — the 14 lazy imports are the least of it. It would need `main.py:121` guarded, `settings/service.py:10` made lazy (which means moving `AVAILABLE_AI_PROVIDERS`/`DEFAULT_AI_PROVIDER` or importing them inside the accessors), and a decision about what the Settings page renders with no AI package. That is a fork, not a cleanup, and **ADR-140 governs enablement as a runtime choice, which the code already implements correctly** — so I see no ADR pushing toward import-time optionality.

### 2. Cluster 3 D4 — the `rich_text` manifest flag. **Right shape, safe for adopters, but it is a four-file change with a mandatory data migration, not the two-line change the proposal implies.**

**On the shape: yes.** `rich_text: bool = False` on `ModuleVariable` with `rich_text=v.get("rich_text", False)` in `_load_manifest` mirrors `required` byte for byte. It is the only shape consistent with the file.

**On breaking an adopter's manifest: it cannot, and that is exactly the problem.** `_load_manifest` (`registry.py:28-39`) reads every optional key through `.get` with a default and **ignores unknown keys entirely** — there is no schema validation, so an old manifest loads unchanged and a manifest carrying a key the code does not know is silently accepted. So the flag is backward-compatible in the trivial sense and **behaviourally destructive in the real one**: `rich_text` defaulting to `False` means that on the day the flag ships, `img_left`, `img_right` and `single_stack` all **stop rendering markdown in `body_medium`** unless their three JSON files are edited in the same commit. The failure is silent — `**bold**` renders as literal asterisks, `[label](url)` as literal brackets. No exception, no log, and it would reach a live send.
**So: the three manifest edits are not a follow-up, they are part of the change.** And an adopter who has forked `storage/email_modules/` gets the same silent regression on upgrade with no signal — which argues for defaulting `rich_text` to `True` on `body_medium` specifically, or for a one-time startup warning when a `cms: true` manifest declares `body_medium` without the flag. Worth deciding; I would not ship the plain `False` default without one of the two.

**Three invariants the caller side could not see:**

1. **`ModuleVariable` is not private to the registry, and adding a field is a three-file edit.** `email_modules/router.py:10-13` re-declares `ModuleVariableOut` field-by-field and `_to_out` (`:23-33`) copies fields explicitly. **A new dataclass field does not reach the JSON API by itself** — `GET /email-modules` would keep returning manifests without `rich_text`, silently omitting a key the adopter put in their own file. Since that route is documented public surface under ADR-142, the Pydantic model has to be updated in the same commit or the API starts lying. `overrides/service.py:47-56` also consumes `manifest.variables`, but only `.name`, so it is unaffected.
2. **The flag is per-variable; the current behaviour is per-*path*.** `_RICH_TEXT_FIELD` is applied only in `render_cms_module` (`rendering/service.py:173-174`). `render_static_module` (`:191-226`) never applies it — yet both paths build the same `variables` dict, and **both paths apply field overrides** (`:162-171` and `:212-218`), deliberately: `overrides/service.py:30-35` states that overrides apply *"regardless of the manifest's cms flag."* So a manifest-driven flag will start rendering markdown on the static path, where today it does not. That is arguably the correct outcome — the two paths already diverge for no stated reason and this would close it — but it is a **behaviour change on `cms: false` modules that D4 does not mention**, and it needs to be an explicit decision rather than a side effect.
3. **`required` is precedent pointing the wrong way** (finding EM2): a manifest boolean that is parsed, exposed on the API and enforced nowhere. Adding a second boolean without wiring the first leaves the manifest schema two-thirds decorative, and the next reader cannot tell which flags are real. **If `rich_text` goes in, either wire `required` in the same pass or note in `email_modules.md` that `required` is documentation-only.**

**Verdict:** do it, in this order — (i) add the field and the `_load_manifest` line; (ii) update `ModuleVariableOut` and `_to_out`; (iii) **edit the three cms manifests in the same commit**; (iv) change `rendering/service.py:173-174` to iterate the manifest instead of matching `_RICH_TEXT_FIELD`, and decide the static path deliberately; (v) delete the `_RICH_TEXT_FIELD` constant. ~12 loc plus three JSON edits. **Risk is concentrated entirely in step (iii)** and nothing tests it — there is no `test_rendering.py` and no `test_email_modules.py`.

### 3. Cluster 3 D5 — caching `get_template_html`. **Yes, behind the mtime gate, and the same answer should apply to Cluster 5's DD2 — but not the same implementation.**

**Agreed, and `lru_cache` is the wrong tool here for a reason stronger than "hot-editing is nice":** the repo already contains both answers and they contradict each other **inside the same directory**. `rendering/service.py:42-46` puts `_load_brand_css` behind a bare `@lru_cache(maxsize=1)` that is never invalidated — so **`storage/email_modules/brand.css` already cannot be hot-edited**, while every other file in that folder can. And `brand.css` is one of the files `_dir_mtime()` stats (`registry.py:79` globs `*`, not `*.json`), so the registry is already paying to watch a file whose cache ignores the answer. Fixing D5 with `lru_cache` would propagate the wrong half of that split; fixing it with the mtime gate lets `_load_brand_css` be folded in and gives the directory one policy.

**The cost is real and it is on the send path, not just previews.** Per module, per recipient (`rendering/render_module:128` → `get_manifest` → `_ensure_fresh` → `_dir_mtime` → `stat()` × 11, then `:176`/`:197` → `get_template_html` → `exists()` + `read_text()`, then `:180`/`:220` → `_jinja.from_string()` compiles from source). Five modules to a thousand recipients is roughly 55,000 stats, 10,000 file operations and 5,000 template compilations for one send — on top of the per-recipient work `docs/backlog.md` P2-04 already tracks.

**The clean shape, from the owning side:** `_discover()` already opens both files to decide whether a module is valid (`registry.py:49-57` checks `html_path.exists()`), so it is one line from also reading the HTML and — if wanted — pre-compiling the Jinja template. Populate `_TEMPLATES` alongside `_REGISTRY` in the same rebuild; `get_template_html` becomes `_ensure_fresh(); return _TEMPLATES.get(name)`. That also collapses the double directory-stat per module render (today `get_manifest` and `get_template_html` are independent) down to one.

**Two things the owner should say out loud before this lands:**

- **It removes a disagreement that currently exists between the two functions, which is a behaviour change even though it is an improvement.** Today a `.json` whose `.html` is missing is skipped by `_discover` while `get_template_html` would still find that `.html` if it appeared later within the same mtime tick. After the change the two can no longer disagree. In practice `_dir_mtime` moves when the file appears, so the window is theoretical — but it is the kind of thing that gets rediscovered as a "regression."
- **Pre-compiling the Jinja template moves the environment dependency into `email_modules/`.** `docs/architecture/Code/email_modules.md` records the module's one structural property: *"Depends on → **Nothing** (no `app.*` imports — it's a leaf that reads the filesystem)."* Caching the compiled template means importing `jinja2` and knowing about `_jinja`'s autoescape setting, which turns the registry into something that knows how its output is consumed. **Cache the HTML string in `email_modules/`; cache the compiled template in `rendering/`, keyed on module name and invalidated by the same mtime.** That keeps the leaf a leaf and gets both wins.

**On the parallel with Cluster 5's DD2 (`decision/strategies/registry.py`): same gate, deliberately different implementation, and they should be decided together rather than in two commits.** The two registries already share the shape almost line for line — `_dir_mtime`, `_REGISTRY`, `_ensure_fresh`, and the same "one broken plugin must not take down the registry" comment. But the work behind the gate is not comparable: `email_modules` re-reads text files, while `decision/strategies/registry.py:22-30` calls `importlib.reload()` on Python modules on every miss. A reload rebinds classes, so instances created before it fail `isinstance` against the new class, and any module-level state in a strategy file is discarded. **That is materially riskier on a send path than re-reading a file**, and it is why I would give the strategies registry the stronger form — the mtime gate plus an environment switch that disables reloading entirely outside development — while `email_modules` can keep the gate always-on.

The honest framing: **there are now three caches over the same kind of resource with three different policies** (mtime-gated manifests, never-invalidated `brand.css`, uncached template HTML), plus a fourth in `decision/strategies`. **The valuable output of D5 is not the cache — it is one written-down hot-reload convention that all four follow.** That is a small ADR or a paragraph in `email_modules.md`, and it is cheaper than discovering the inconsistency a third time.

---

## Decide, don't delete

- **`SnapshotDB.html_storage_type` — always `"file"`, and `get_snapshot_html` never reads it.** Written at `snapshots/service.py:117`, echoed to the Pydantic model at `:20`, and `get_snapshot_html:155-170` goes straight to `Path(snapshot.html_location)` with no branch on the storage type. **Not residue, and explicitly so:** `docs/architecture/Code/snapshots.md:40, 55, 60` calls it *"the extension point for `"s3"`/`"db"`"* and *"an open decision"*, and `docs/backlog.md:158` holds that decision. **Already filed — referenced here only so a future reachability sweep does not re-derive it.** The one thing worth adding: when that decision lands, the read path is the half that does not exist yet, so the work is `get_snapshot_html` + the writer, not just the writer.

- **`AIRunDB.target_type` / `target_id` are written generically and read as if they were always a variant.** `run_task:161` etc. store whatever the caller passes; `frontend/router.py:726` does `ai_suggestions_variant_id = row.target_id` with **no check that `row.target_type == "variant"`**. Correct today because `subject_preheader` is the only task, and the generality is the point — ADR-141 §3 frames this as the *first* Mode A action, so the columns are the seam for the second. *0 loc recommended; a one-line `target_type` check at `:726` is what stops the second task from silently rendering its output as subject-line suggestions.* **Decide when task two exists, not now.**

- **`AIPromptDB` versioning has no delete or unpublish path.** `publish_prompt` only ever adds; nothing ever removes a version or leaves a task with zero published prompts once one exists. That is almost certainly right — ADR-140 §3 needs old versions to keep resolving — but it means `ai_prompts` grows monotonically with no prune mechanism, which is the same **ADR-154** gap Cluster 6 S4 raised for `auth_sessions` and `login_codes`. **Different from those two in one way that matters: an `ai_prompts` row is referenced by `ai_runs.prompt_id`, so pruning is not merely undesirable, it would break the FK.** Worth noting under whichever data-lifecycle item absorbs Cluster 6 S4: for this table the answer is "never prune", and that should be written down rather than inferred.

---

## Report-only observations — the AI-specific questions the brief asked

- **Is the spend cap enforced on the path that spends?** **Yes, structurally — and it is the cleanest thing in the cluster.** `provider.generate` has exactly one call site (`ai/service.py:205`); `get_ai_provider` has exactly one non-test caller (`:167`); `run_task` has exactly one caller (`subject_preheader.py:113`). There is no second spender and no way to reach the adapter without passing the gate. **Two defects sit *inside* the gate rather than around it** — A2 (the ledger it measures against undercounts) and A4 (it fires for providers that cannot spend). Both are arithmetic, not architecture.
- **Is the audit row written on failure as well as success?** **Yes, on all four exit paths**, and the two pre-call ones are written before anything is spent, exactly as `db_models.py:52-54` claims. `prompt_id` is correctly nullable so the missing-prompt refusal is still recordable. The gap is A2's missing token columns on the error path, and A7's mislabelled `TaskRun` fields.
- **Does the pricing table have a live consumer?** **Yes.** `MODEL_PRICING` → `cost_usd` → `spend_to_date:127` → `frontend/router.py:104` → `settings.html`. `FREE_PROVIDERS` → `is_billable` → `tokens_used:103` and `spend_to_date:125`. `tests/test_ai_pricing.py:54` even asserts every entry has both rates. **The one thing to note is not deadness but drift risk:** `MODEL_PRICING`'s four keys are matched against `AIRunDB.model`, which is whatever the **provider** returned (`claude.py:172` prefers `payload["model"]` over `self.model`), so a vendor returning a dated id like `claude-opus-5-20260401` would go unpriced and land in `unpriced_runs`. That is the designed-for degradation, the comment at `pricing.py:23-25` anticipates the maintenance, and `unpriced_runs` is surfaced in the UI — so it is working as intended. Flagged only because "prices go stale" is the kind of thing a future sweep will read as rot.
- **`?ai_run=` reads any run row by id with no ownership check.** `frontend/router.py:720-733` fetches `AIRunDB` by the query-string id and renders its `output_text` on the campaign page, without checking that `row.target_id` belongs to `campaign_id`. **Not filed as a defect:** the page requires only `view`, and any user with `view` can already open every campaign, so nothing is disclosed that is not otherwise reachable. It becomes a real finding the day brand scope is enforced (`docs/backlog.md` P1-02) — noting it here so that item's blast radius is known to include this line.
- **`variant_suggest_subject` does not verify the variant belongs to the campaign** (`frontend/router.py:812-833`). Same reasoning as above, and the same pattern exists across the router, so it is a cluster-wide observation rather than an AI finding.

---

## Housekeeping — read-only notes, not work items

- **There is no `docs/architecture/Code/ai.md`.** `ai/` is the second module with no page, after `auth/` (Cluster 6). Every other package in `backend/app/` has one. `ai/` is the better-documented of the two in-source — the module docstrings in `service.py`, `pricing.py`, `db_models.py` and `adapters/base.py` carry the Purpose / Invariants content a module page would — which is presumably why. Worth knowing that the two modules with the highest ADR density (140/141/143/144) and the highest blast radius (auth) are the two without pages, since the module pages are what makes these sweeps cheap.
- **`docs/architecture/Code/snapshots.md` is accurate**, including the `html_storage_type` extension point and the open decision. No drift found. Stating it because Clusters 4 and 6 both found stale pages.
- **`docs/architecture/Code/email_modules.md` is accurate on everything except `required`** — it lists the manifest's `required` flag as part of the contract without noting that nothing enforces it (EM2).
- **`requirements.txt` has no `anthropic` entry and needs none** — the Claude adapter is raw `httpx`. Recording this so the next reader does not "fix" a missing dependency. What it *does* need is `httpx` instead of `httpx2` (already filed; see open call A for why that pin is a boot-blocker rather than a delivery-only problem).
- **`storage/email_modules/brand.css` is globbed by `_dir_mtime()`** (`registry.py:79` uses `glob("*")`, not `glob("*.json")`), so editing the stylesheet invalidates the manifest cache while **not** invalidating the stylesheet's own `lru_cache`. Harmless today; the exact inversion of what a reader would expect. Folds into D5.

---

## Unverified — the specific checks a human should run

1. **E1's orphan rows.** `SELECT DISTINCT module_type FROM module_instances;` — if `content_card` appears, removing the dropdown option does not repair the existing rows, and the edit form's fallback (`campaign_detail.html:222`) is what keeps them editable.
2. **A2's billing claim.** I am asserting from the adapter's own handling (`claude.py:175-192`) that Anthropic returns HTTP 200 with a real `usage` block on a refusal, and from general billing practice that those input tokens are charged. **Confirm against the current Anthropic pricing documentation before treating the ledger gap as spend rather than as bookkeeping.** The code change is correct either way; the severity depends on this.
3. **A5's duplicate rows.** `SELECT task_key, version, COUNT(*) FROM ai_prompts GROUP BY 1,2 HAVING COUNT(*) > 1;` and the same for `is_published` — the `UniqueConstraint` DDL will fail if the race has already fired.
4. **A5's flush-order hazard.** If the partial unique index is added, publish a prompt twice in a row and confirm it does not raise; SQLAlchemy's ordering of the bulk `UPDATE` against the new `INSERT` inside one flush is the specific thing to watch.
5. **S1's index.** `\d snapshots` in psql. `index=True` is a fresh-install-only no-op, so the running database will not have it until the `CREATE INDEX` is run by hand.
6. **EM1's syscall count.** Enable a filesystem trace (or just instrument `_dir_mtime`) and render one variant; expect 11 stats per module. I counted these by reading the call graph, not by running it.

---

## Leave alone — looks dead, is not

Checked, not sampled. **Do not re-run reachability on this cluster.**

- **`MockAIProvider`** (`ai/adapters/mock.py`) — the deliberate default, reached via `DEFAULT_AI_PROVIDER = "mock"` (`factory.py:15, 27-28`). Its own docstring at `:1-12` pre-empts the deletion argument: *"This is not scaffolding to delete later."* ADR-143. Same class as `MockProvider` for sends.
- **`MockAIProvider.__init__`'s `canned_response` and `fail` parameters** — no caller in `app/`, four in `tests/test_ai_adapters.py:63, 68, 81, 90`. The comment at `:94-96` says why they exist. Test-only construction arguments on a seam example are not dead parameters.
- **`imitate_requested_format`** (`mock.py:37-72`) — 36 loc of prompt-shape imitation that looks over-built for a mock. It is the thing that makes the mock exercise `parse_options` for real, and `tests/test_ai_subject_task.py:52-71` tests exactly that, including *"works for a format it was never told about."* Deleting it would make the mock stop testing the parser.
- **`ClaudeProvider`'s `thinking` parameter** (`claude.py:83, 96, 135-136`) — always `False` in `app/`, set to `True` once in `tests/test_ai_claude_adapter.py:101`. The comment at `:89-95` makes it a cost-cap decision with a stated future trigger. Reserved extension point with a written rationale, not a stray flag.
- **`AIProvider` / `AIResult` / `AIUsage` / `TokenCountUnavailable`** (`adapters/base.py`) — the seam contract. `AIResult.stop_reason` in particular is set by both adapters and read at `service.py:226`.
- **All three `/snapshots` routes and both `/email-modules` routes** — zero in-repo JSON callers is normal; documented public surface, ADR-142. `main.py:176` describes the `/email-modules` tag as the drop-a-file plugin registry, which is the whole positioning claim.
- **`GET /snapshots/{id}/html` being unauthenticated** — the already-filed machine-auth P0 covers every JSON router. Worth one sentence when that item is picked up: this route returns rendered newsletter HTML that may be recipient-personalised, so it is not in the same disclosure class as a list of ids.
- **`storage/email_modules/*.json` + `*.html`** — discovered by `EMAIL_MODULES_DIR.glob()`. Five module pairs, all reachable, all listed by `list_manifests`. `brand.css` is neither and is read separately by `rendering/service.py:33-46`.
- **`app/ai/tasks/__init__.py`, `app/ai/adapters/__init__.py`, `app/snapshots/__init__.py`, `app/email_modules/__init__.py`** — all 0 bytes and all required as package markers. **Not** the `providers/adapters/mock.py` case from the delivery sweep; that one was a 0-byte *module*, these are `__init__.py`.
- **`ModuleManifest.description`** — never rendered in any template; returned by both `/email-modules` routes and read by a designer choosing a module through the API. Public surface, not a dead field.
- **`Snapshot` Pydantic model's `html_location`** — exposed on the JSON API and pointing at an absolute filesystem path. Ugly, and `docs/backlog.md:158` already owns the storage question. Not dead, not a fresh finding.
- **`tokens_used` excluding free providers** — deliberate, with the reasoning written at `service.py:90-95`. The finding is A4 (the gate not matching), never the exclusion itself.

---

**Findings dropped: 3**, all below the reporting bar. `snapshots/service.py:27` has a bare `#Helper` comment and inconsistent blank-line spacing around `create_snapshot_for_variant` — cosmetic, and the file is due to be rewritten by `docs/backlog.md:158` anyway. `spend_to_date` returns an untyped `dict` where the rest of the module uses a dataclass (`TaskRun`) — one function, two consumers, not worth the churn. `MODEL_PRICING` uses a bare tuple where a `NamedTuple` would document `(input, output)` — the comment at `pricing.py:22` already does that job.

**Highest-value single item: A2** — two arguments on one `_record` call, so that a model refusal Anthropic actually billed stops being recorded as zero tokens and the ADR-144 §5 cap stops measuring against a ledger it cannot see. Fix A4 in the same commit; it is the other half of "does the cap know what money is," it is two lines, and together they are the only findings in this cluster that make a governance control wrong rather than merely slow.

---

# Assessment — "vibecodeness factor", 2026-08-21

**What this is:** a judgement, not a sweep finding. Written by Claude from the seven cluster
sections above, stress-tested by the `positioning-critic` agent against the source, then
revised. **The number is opinion; the sub-scores and their evidence are the useful part.**
Recorded so a later sweep has a baseline to argue with.

**Scale as posed:** 1 = "absolutely vibecoded — no guidelines, a mess of features and tons of
dead code." 10 = "thoroughly planned, still in charge, slim code, no unnecessary complexity."

## Project stage — read this before the score

This is a **local proof of concept**. Three things are deferred **by decision**, not overlooked,
and they are excluded from the score for that reason:

- **Installation and deployment are not designed or built yet** — that work starts after the base
  is built. The `httpx2` pin (`backend/requirements.txt:8`), the hardcoded Postgres credentials
  (`backend/app/database.py:4`), the absence of any migration tool, and the missing
  `conftest.py` / `pytest.ini` all belong to that unstarted story.
- **The six-digit login code shown on screen will not exist in the future.** Cluster 6 A1 remains
  a genuine must-fix before any exposure; it is not a live risk on a local POC with no users.
- **Nothing is publicly exposed.** Public beta is blocked on positioning regardless — see
  `docs/business/POSITIONING.md` and `docs/business/LAUNCH-GATES.md`.

These stay in the report as findings. They are **deferred**, not defects, and they must not be
allowed to drag a quality judgement.

## Score: 7.6 / 10

| Dimension | Score | Evidence |
|---|---|---|
| Dead code / abandonment | **9** | ~139 deletable lines in ~13,700 swept (≈1.0%); zero `TODO`/`FIXME`/`HACK` in 11,958 loc |
| Rationale & traceability | **7** | Rich ADR + dated-backlog trail — **but it contains confident false assertions** |
| Slimness / altitude | **7** | One 2,927-loc router; three implementations of one stat; a 395-loc handler |
| Complexity restraint | **9** | Over-built-looking code repeatedly proved justified; no gratuitous abstraction |
| Being "in charge" | **6** | Deferrals are known and deliberate — but five dead controls and one false Done record are not |

**9 + 7 + 7 + 9 + 6 = 38 ÷ 5 = 7.6.**

## Why it is not vibecoded

Seven sweeps went looking for abandonment and found ~1%. More telling than the count: **the
sweeps kept trying to delete things and being stopped by recorded reasoning.** `MockProvider`
carries *"this is not scaffolding to delete later."* The route-ordering comments in
`content/router.py` document a bug that actually happened. `_would_create_cycle` looks
over-built until you find it is the only enforcement of a declared invariant. The ten
`# noqa: F401` imports in `test_signals.py` look like dead weight and are load-bearing.

A vibecoded repo does not survive that test — you can delete freely from one, because nothing
knows why anything is there.

## Why it is not a 9 or 10

**The rationale trail is not uniformly trustworthy, and that is the finding the critique
surfaced that the first draft missed.** In `auth/`, the highest-blast-radius module:

- `auth/router.py:64-70` asserts the disclosure is *"confined to a branch production never
  reaches."* The code three files away does not implement that.
- `auth/service.py:285-288` asserts the code is returned *"only when the dev path is active."*
  Also not implemented.
- `docs/backlog.md:206` records the signal-config work **Done** with a verification note — and
  the note tested only the half-life half. The weight half has never worked.

Prose that confidently states false things is worse than thin prose, because it is trusted.
That is why traceability is a 7 and not the 10 the first draft gave it.

**Five operator-facing controls do nothing** (verified in source): the Settings signal-weight
field and its help text, the `unsubscribe` weight row, the `credentials.manage` checkbox, and
two dropdown options that create unrenderable modules. Each is individually defensible as a
reserved seam; collectively they are things a user can act on that have no effect. Note
`max_results` is **not** among them — it is JSON-API-only, no template renders it.

## Corrections the critique forced — recorded so they are not repeated

1. **The first draft said 8; its own sub-scores averaged 7.0.** No weighting was stated. Arithmetic
   error, not a judgement call.
2. **"0.15% dead code" was scoped to flatter.** The denominator excluded `delivery/` + `providers/`
   (where the P0 consent defect lives) and all 3,739 template lines — while the numerator drew
   from templates, and the phrase "inside `backend/app/`" excluded the 121-line dead
   `scripts/reset_poc_data.sql`. Counted consistently: **≈1.0%**. **Do not quote 0.15%.**
3. **"Seven independent sweeps" is false.** Each cluster was briefed with the previous ones'
   findings and carries a "do not re-run reachability" section. They are one method applied seven
   times with a deliberate bias against deletion — efficient, but not corroboration.
4. **"Completes the design and under-completes the enforcement" is too kind.** A missing unique
   constraint is an enforcement gap. A Settings screen promising *"changes apply immediately"*
   when they do not is the design being written down and then contradicted.

**Where the critique overreached:** it scored installability, security and test coverage on a
scale defined as planning / control / slimness / complexity, and it read Cluster 4's section
heading as a wrong premise when that premise held (the *counter-evidence* was wrong). Its
proposed "mean minus one for not reading the code" docks the method rather than fixing the
sub-scores.

## The objection to keep

> *"What is the score measuring, if not how thoroughly you documented the parts that don't work?"*

It does not land against the deferred items — those are a schedule, not a failure. It lands
squarely against the five dead controls and the false Done record, and it is the right question
to re-ask at the next sweep.

## Recommendation

**Do not put a composite number in a README, a launch post, or in front of an adopter.**
`docs/business/LAUNCH-GATES.md:35` — *"A gate moves to ✅ only with something checkable behind
it — 'Designed' is not 'done'"* — is the repo's own standard, and a self-issued score does not
meet it. The gates table deliberately refuses to collapse its dimensions into one number for
exactly this reason. The sub-score table above does the useful work; the composite is the part
that travels badly.
---

# Sweep status

| # | Cluster | Status |
|---|---|---|
| — | `delivery` + `providers` | Done — findings in `docs/backlog.md` (review 2026-08-07) |
| 1 | `frontend` + `templates` | **Done 2026-08-21 — this file** |
| 2 | `overrides` + `campaigns` | **Done 2026-08-21 — this file** |
| 3 | `content` + `rendering` | **Done 2026-08-21 — this file** |
| 4 | `insight` + `recipients` | **Done 2026-08-21 — this file.** Swept together; `SignalContributionDB` is defined in `recipients/` but used by `insight/` |
| 5 | `audience` + `decision` | **Done 2026-08-21 — this file** |
| 6 | `auth` + `settings` | **Done 2026-08-21 — this file.** Lowest residue as predicted; two new security defects |
| 7 | `ai` + `snapshots` + `email_modules` | **Done 2026-08-21 — this file.** Also closes Cluster 1's open call A and Cluster 3's D4/D5 |

**All seven clusters swept, 2026-08-21.** `backend/app/` has no unswept module.
