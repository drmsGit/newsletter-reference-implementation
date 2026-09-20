# React Migration Inventory — what is actually in the Jinja router

**Purpose:** `backend/app/frontend/router.py` is 4,419 lines and has a deletion date
([[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]]). This is the
inventory of what deleting it would delete. It is the input to the pre-React work
list in `docs/backlog.md`, not a plan in itself.

**Method:** every route enumerated, every write route matched against the JSON
routers by **the service function it calls**, not by URL shape. Swept 2026-09-19.
The findings that carry a security claim were re-verified by hand against the
source before being written down here.

**Do not read this as "refactor the Jinja UI."** The external quality review of
2026-09-19 is right that refactoring a disposable verification harness is wasted
work. The question this document answers is narrower and sharper: **which backend
rules exist only in the presentation layer**, and would therefore be *deleted*
rather than *replaced* when the SPA lands.

---

## The count

| Category | Routes | Meaning |
|---|---|---|
| **A — pure presentation** | 33 | one service call plus a redirect or a template. Safe to delete with the UI. |
| **B — logic only in this file** | 24 routes + 3 cross-cutting helpers | a backend rule living in the presentation layer. Must move behind the service boundary. |
| **C — capability with no JSON route** | 26 | the service exists; nothing but the Jinja UI reaches it. API gaps the SPA hits on day one. |

83 routes total. **Half of this file is not presentation.**

---

## The headline: the brand boundary is implemented in the UI

**B1 is not a migration cost. It is a live authorisation gap, and it is the read
side of the same defect the external review found on the write side.**

Every detail and list page in the Jinja router re-filters by the working brand and
answers "does not exist in this brand" identically to "deleted" — 15 call sites.
The JSON routers do none of it. Verified by hand:

- `content/router.py:59` — `list_content_records(db)`, no `brand_id`
- `content/router.py:96` — `get_content_record(db, content_id)`, no brand check at all
- `campaigns/router.py:58` — `list_campaigns(db)`
- `audience/router.py:27` — `service.list_groups(db)`

The services all *accept* `brand_id`. Only the Jinja router passes it.

So: `GET /content/`, `GET /content/{id}`, `GET /campaigns/` and
`GET /api/audience-groups/` return **every brand's rows to any authenticated
caller**. Combined with the external review's P1-02 (writes authorised against the
declared brand, rows addressed by bare id), the position is:

> **The JSON plane has never had a brand boundary. The boundary was built in the
> UI layer, and the UI layer is the thing we are about to delete.**

Retiring the Jinja UI without moving this does not move the boundary. It removes it.

Two more of the same shape:

- **B2 — cross-brand write authorisation.** `_duplication_targets` / `_may_in_brand`
  (`frontend/router.py:1265`, `:1285`) check the permission against the *target*
  brand chosen in the form, not the working brand, and answer identically for
  "brand does not exist" and "you hold no grant there" — an enumeration defence.
  Nothing in `app/auth/` does this.
- **B3 — per-row approval authorisation.** `_may_decide` (`:4167`) resolves the
  permission from the *action's own* `approve_permission`, brand-scoped against the
  row's brand. `auth/policy.py:129` explicitly documents that the policy table
  cannot express this and that the real gate is in the route. The real gate is in
  the file with the deletion date.

## The second: a documented rule with two call sites, both here — ✅ CLOSED 2026-09-20

`channel_available` enforces ADR-160 point 8 — a deployment may not use a channel
it has not enabled. Verified: **exactly two call sites, both in
`frontend/router.py`** (`:1254` campaign create, `:1466` variant create).
`campaigns/router.py:63` creates a campaign on a disabled channel without
complaint today. Deleting the Jinja UI removes the server-side enforcement of that
ADR entirely.

**Closed 2026-09-20.** The refusal moved into `create_campaign` and
`create_variant_for_campaign`, before anything is written, as a
`ChannelUnavailable` exception rather than a bool — every caller's correct
response was the same one, and a bool is a thing a caller can ignore, which is
exactly how the JSON routers came to ignore it. It subclasses `ValueError` so
that everything which caught it before still does, while a route that wants a
400 rather than a 404 can name it.

`channel_available` now has one call site, in the service. The Jinja
campaign-create refusal had no test at all before the move; it has one now.

---

## B — logic that must move behind the service boundary

Beyond B1–B3 above:

| # | Route | What only exists here | Size |
|---|---|---|---|
| B4 | `GET /` | six dashboard counts, each with its own scoping rule (content active-only + brand; snapshots/deliveries/events joined to brand; recipients deliberately unscoped) | moderate |
| B5 | `POST /ui/settings/ai` | budget parsing: blank keeps the code default, `>0` required for token caps, `budget_usd` accepts comma decimals, clamps at 0 (0 is meaningful). `set_config` is a dumb key-value writer | moderate |
| B6 | `POST /ui/settings/ai-provider` | a provider outside `AVAILABLE_AI_PROVIDERS` is silently ignored, not stored | one line |
| B7 | `POST /ui/settings/ai-task-approval` | anything but `require_approval` normalises to the default | one line |
| B8 | `POST /ui/settings` | weight/half-life decoding by field prefix, non-numeric dropped, `max_send_recipients` stored only when a positive int | moderate |
| B9 ✅ | `POST /ui/send-test` — **DONE 2026-09-20, the last B item with real behaviour.** `delivery.service.send_test_email` holds the three decisions (render through the email path, never block the send on a render failure but say so, an unknown provider is a failed result not an exception); `POST /delivery/send-test` is the JSON twin. Needed its own `policy.py` entry above the broad `/delivery` prefix — the **third** such downgrade — which is why the set of routes that mail a person is now asserted exactly, in both directions. Also closed a brand gap: the router rendered a variant by bare id. | composed here: render through the email path, fall back to a plain body with a user-visible note if rendering raises, then `get_provider().send`. **No send-test service function exists** | moderate |
| B10 | `GET /ui/recipients/{id}` | derived preference rows + category join + sort; nested delivery → event → signal-contribution tree | moderate |
| B11 | `GET /ui/campaigns/{id}` | the largest block: overrideability rule (`:892`), envelope modules hidden from the module table and the picker (`:917`, `:1063`), `module_limit`/`can_add_module` from the channel manifest, content picker scoped to the **campaign's** brand rather than the viewer's (`:1117`), audience counts per distinct channel, providers filtered by channel, AI run read-back with option parsing and raw-reply fallback | substantial |
| B14 | `GET /ui/campaigns/{id}/duplicate` | which brands may be duplicated into, and `COPY` removed as a content mode unless the user holds `content.manage` **in the target brand** | moderate |
| B15 ✅ | `POST .../suggest-subject` — **DONE 2026-09-20.** The envelope guard, the approval-mode branch and the duplicate case moved to `app/ai/orchestration.py`; both planes call it, and `POST /campaigns/variants/{id}/suggest-subject` is the JSON twin. It needed its own `policy.py` entry above the broad `/campaigns` prefix, which would have priced a token-spending route as `campaigns.manage` — the second time that ordering shape has been caught. The router's variant lookup was also unscoped, so this closed a small brand gap ADR-172 missed by virtue of it living in a router. | refuse channels with no envelope module *before* spending tokens (`:1529`); `NothingToWorkFrom` pre-call refusal; then branch on the per-task approval mode — redirect with a run id, or build an approval request and handle `DuplicateRequest` | substantial |
| B16 ✅ | `POST /ui/decisions/slots/{id}/edit` — **DONE 2026-09-20, and narrower than described here.** "Empty means all" was never at risk: `_normalize_section` fills `category_ids` with its `[]` default and both strategies read `if category_ids:`, so `[]` and absent already agree. The picker-wins-over-JSON half is presentation — two form inputs for one field, which a JSON client does not have. The real risk was `strategy_config`: an absent declared key is filled with its spec DEFAULT, so a partial `PUT` resets tuned weights rather than leaving them. `PATCH /campaigns/decision-slots/{id}` leaves unsent sections alone. | the category multi-select **wins over** `candidate_filter.category_ids`; an empty selection *removes* the key (empty means all); other keys preserved. `PUT /campaigns/decision-slots/{id}` replaces `candidate_filter` wholesale | moderate |
| B17 | `GET /ui/content/{id}` | signal rows filtered in Python after a 100-row fetch; version headline/body fallback across three key spellings | moderate |
| B18 | `POST /ui/content` | push fields written **only when non-empty** — "not prepared for push" and "prepared with nothing" are different states, and that difference is what ADR-161's catalogue-readiness reads | moderate |
| B19 ✅ | `POST /ui/content/{id}/edit` — **DONE 2026-09-20.** The rule is `content.service.merge_content_fields`, both planes call it, and `PATCH /content/{id}` exposes it. `PUT` still replaces and now says so. | **merge, not replace**: push keys applied only if the form rendered them; clearing a field removes the key. `PUT /content/{id}` replaces the whole dict — **the SPA will re-introduce the data-loss bug this guards** | moderate |
| B20 | `GET /ui/categories/{id}` | signal-impact aggregation, recipients ranked by operational signal, top-50 cut | moderate |
| B21 | `GET /ui/decisions` | slot list joined through variant/campaign for brand scoping, with resolution aggregates | moderate |
| B22 | `GET /ui/decisions/slots/{id}` | per-content share %, reason histogram, and the per-strategy field manifests the edit form needs | moderate |
| B23–B24 | `GET /ui/deliveries`, `.../send-instances/{id}` | per-send counts; nested execution → event → contribution tree | moderate |
| B25 | `GET /ui/graph` | ~400 lines: category co-occurrence edges, per-edge event attribution, radial layout, radius/colour/thickness formulas, rankings. Entirely router-local | substantial |
| B26 | `GET /ui/audience-groups` | `recipient_count` is a **live consent-gated `resolve_audience` per group**, not the pinned member count. Also an N+1 | moderate |
| B27 | `GET /ui/audience-groups/{id}` | human-readable rule-block summaries from criteria, per-block counts against the **group's** brand, resolved preview, non-member list | moderate |

---

## C — capability the SPA cannot reach

The ones that block a screen, in order of weight:

| # | Route | Service it is the only path to | Size |
|---|---|---|---|
| C8 | `POST /ui/campaigns/{cid}/snapshots/{sid}/send-instances` | **`prepare_send_from_audience`** — resolve the audience, consent-gate per channel, enforce the send cap, materialise one execution per recipient, freeze-vs-rerun, schedule. Verified: one call site in the whole codebase, this one. `delivery/router.py:67` creates the send-instance *row* only, and its own docstring points at this UI route. **The largest gap in the send path** | substantial |
| C2 | `GET /ui/settings` | twelve settings/AI service functions. **There is no `app/settings/router.py` and no `app/ai/router.py`** — the entire settings surface is UI-only | substantial |
| C14 | `/ui/integrations` ×8 | the whole of `auth/integrations.py`: create, issue, revoke, grant, revoke grant, set unattended, deactivate. `:4044` must **not** redirect — the secret exists in one response body only (ADR-166 pt 3), and the React equivalent needs the same property | substantial |
| C15 | `/ui/approvals` ×5 | list, detail, approve, reject, `process-expired`. Approve/reject over JSON is **decided** (session-authenticated person, bearer refused) and not built. `process-expired` is the cron seam `/delivery/process-due` got and this did not. Carries live `describe()` vs frozen `summary`, and `choice_index` → pick-one | substantial |
| C6 | `POST /ui/campaigns/{id}/duplicate` | `duplication.duplicate_campaign` + audit + variant subset. Nothing in `campaigns/router.py` touches `duplication`. B2's authorisation moves with it | substantial |
| C1 | `POST /ui/brand` | **`set_session_brand`** — verified, one call site. `session_router` has request/verify/end only. Without it a cookie-authenticated SPA cannot change brand | one line, moderate semantics |
| C11 | `GET .../criteria-preview` | `find_by_criteria` — already returns JSON, from the Jinja router | moderate |
| C12 | `POST .../bulk-add` | bulk add **by criteria**. The JSON route takes an explicit id list only | moderate |
| C7 | `GET .../suggestions` | `runs_for_target` + `parse_options` — AI run history | moderate |
| C9 | `POST /ui/content/{id}/duplicate` | `duplicate_content_record` + audit + target-brand check | moderate |
| C13 | `POST .../suggest-audience` | `create_suggested_group_for_campaign` | one line |
| C3, C4 | AI prompt publish, per-task model | `publish_prompt`, `set_task_model` | one line each |
| C5, C10 | unassign a category, delete a category relation | JSON can create both and delete neither | one line each |

---

## What this changes

1. **The pre-React list is bigger than the external review implied**, because the
   review saw the router's *size* and not its *contents*. Category B is 27 items,
   not a handful.
2. **B1 + P1-02 together are one finding, not two.** The brand boundary does not
   exist on the JSON plane in either direction. Fix reads and writes in one pass,
   with cross-brand negative tests per capability rather than per endpoint.
3. **Category C is the real API-completeness number.** The "four remaining gaps"
   recorded on 2026-09-19 was measured against what the SPA's first screens need.
   Measured against what the current UI can do, it is 26.
4. **Category A is genuinely safe**, and that is worth something: 33 routes can be
   deleted without a thought once their screens exist.

## Related

- `docs/backlog.md` — the act/fix items this document feeds
- [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]]
- [[ADR-002 — API First Architecture]] — the claim this inventory measures against
- `CODE_REVIEW_2026-09-19`, `CODE_QUALITY_RELEASE_POSITIONING_2026-09-19` (external, on the Desktop)
