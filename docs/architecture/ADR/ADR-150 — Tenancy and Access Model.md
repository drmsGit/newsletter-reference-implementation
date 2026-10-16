---
type: adr
status: accepted
topic:
  - architecture
  - security
  - access
  - governance
created: 2026-08-02
modified: 2026-10-16
source:
  - "Security Chapter design interview, Part 1 (playbook-strategy.md Decision Log, 2026-08-02)"
depends_on:
  - "[[ADR-004 — Privacy Operations as a First-Class Architectural Concern]]"
  - "[[ADR-120 — CRM as Customer Source of Truth]]"
  - "[[ADR-126 — Maintain Local Recipient Projection]]"
  - "[[ADR-144 — AI Data and Model Governance]]"
enables:
  - "[[ADR-151 — Authentication and Sessions]]"
  - "[[ADR-152 — Secret and Credential Handling]]"
  - "[[ADR-153 — Audit and Accountability]]"
  - "[[ADR-154 — Erasure and Retention]]"
  - "[[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]"
---

## Status
Accepted

## Context

The platform has no authentication, no users and no roles. Everything built so far assumes a single trusted operator sitting in front of a server-rendered UI.

Adding access control touches every route, so its shape has to be settled before more surface is built — retrofitting is the expensive path. Two further pressures make it urgent rather than merely due. First, publishing the playbook (Phase 4C) is explicitly blocked until every part is designed, security included. Second, the intended operating model has an external party in it: the target buyer is an **agency or freelancer serving Mittelstand clients**, and the agency does not host the system — it helps the client host it on the client's own infrastructure and then helps operate it. That means people outside the company hold real accounts inside it.

A second question arrives with the first: companies frequently run **several brands**. Whether those are separate systems, separate tenants, or a scope inside one system determines how much of the codebase access control touches.

## Decision

**1. Single-tenant per deployment.**
One installation serves one company. Several brands of the *same* company may share an installation, but no agency runs multiple clients on one system. Consequence: no tenant discriminator on any query, and separation between companies is a **deployment boundary**, not a code path. This is ruled in deliberately rather than by omission, because multi-tenancy is the one decision here that cannot be retrofitted without touching every query in the system.

**2. Brands are a scope, not a hierarchy — and multi-brand is the ordinary case.**
A brand switcher in the top navigation selects the working context. Content and branding differ per brand; most everything else carries over. No nested organisation machinery, no per-brand duplication of settings, strategies or taxonomy. Brands behave "like categories."

Several brands is what the customers we have actually look like, not a state a company escalates into: the first pilot customer runs around ten brands today and creates several new ones every year. The scope is therefore **designed for from the start rather than held dormant until someone needs it**. Concretely, **a `brand` column belongs on every table that needs one** — beginning with content, campaigns, audiences and the permission grants — and the brand a request is working in is carried into the queries that read them.

This is a scope *inside* one company and does not reopen point 1. A second brand is another working context in one company's own data; a second *company* on the same installation stays refused. The brand column is not the tenant discriminator point 1 rules out, and the two must not be conflated — point 1 is the only reason there is no tenant column to begin with.

**3. Where GDPR forces brand separation, the answer is two installations — and we ship no alternative.**
If a company must keep brand A's and brand B's people apart, they run two systems. We deliberately do **not** offer a mixed-but-separated mode. Shipping one would imply we had judged that arrangement compliant, which is precisely the data-protection liability [[ADR-144 — AI Data and Model Governance]] §3 already refuses to take. A company that wants it anyway is changing its own code, with its own legal advice.

**4. The visual-only case is a degenerate case of the same model, not a separate mode.**
Many companies use "brand" to mean a logo and a palette. One default brand always exists, so such a company never has to think about the switcher and never sees a second context. That is where the invisibility ends: the column is on the tables and the queries carry it from the first migration, filled with the default brand. A company treating brands as a skin pays a default value in a column — not a mode of its own, and not the retrofit that waiting would cost everyone else.

**5. Three seeded roles over a real permission model — not a role enum.**

| Role | Surface |
|---|---|
| **Admin** | Settings, user management, credentials, provider and AI model configuration |
| **Manager** | Campaigns, content, audiences, sends, AI actions |
| **Viewer** | Read-only — dashboards, signals, delivery history |

Roles and permissions are **rows, not code**. The three ship as a preset a company can extend, replace or ignore; adding a role or scoping a permission further requires no code change. This is the same convention-based-extension posture the decision strategies and email module templates already use. We explicitly do not model the average company's org chart: companies mostly run everything as admin, or arrive with a scheme of their own, and copying an imagined average serves neither.

**The vocabulary is sixteen keys, not nine (2026-09-13).** Making an inbound machine caller a principal in this model ([[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]) forced the key set wider, for two reasons, of which the second is the larger. First, the nine were too coarse to express the grants that record's own worked example describes: a website form that may pin a recipient but may not restructure an audience was inexpressible, because pinning sat under `audiences.manage`, which also deletes groups and edits rule blocks. Second, the nine did not reach the API at all. `app/auth/policy.py`'s `WRITE_POLICY` maps only `/ui/…` prefixes and the vocabulary named UI concerns; of the twelve JSON routers, **four had no key naming what they do** — recipients (3 write routes), overrides (3), insight (2) and provider (2). Splitting was therefore the smaller half of the work. The larger half was that the vocabulary stopped at the UI boundary, so an integration could not have been granted the things [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]'s examples describe.

- **Unchanged (7):** `view`, `campaigns.manage`, `content.manage`, `ai.run`, `settings.manage`, `users.manage`, `credentials.manage`.
- **Split (2 → 4):** `audiences.manage` keeps group and rule-block CRUD; **`audiences.pin`** covers adding and removing individual members. `sends.execute` keeps firing a real send; **`sends.plan`** covers creating send instances and delivery executions without dispatching. Both splits serve humans identically — a junior marketer who may pin but not restructure, or prepare a send but not release it, is the same grant — which is why they land in the shared vocabulary rather than in a machine-only scope list.
- **New, filling the gaps (5):** **`recipients.manage`** (create and edit recipients), **`recipients.consent`** (write a consent record), **`insight.write`** (write engagement events, including the locked `POST /provider/events` ingest route), **`overrides.manage`**, and **`integrations.manage`** (issue, rotate and revoke machine credentials — added by [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]).

Two grain choices inside that set are decisions rather than consequences, and are recorded as such.

**`recipients.consent` is separate from `recipients.manage`.** An integration that only imports contact records cannot also assert consent for them. Consent is the record [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §7 calls a hard floor and the defence a UWG §7 complaint is answered with, so the narrowest possible grant for writing it is warranted. The cost, which should be stated rather than discovered: the common case — a real signup form — needs two grants rather than one, and whoever configures it can get that wrong.

**`POST /provider/events` is gated by `insight.write` rather than by an `events.ingest` key of its own.** Ingesting a provider event and posting an insight event both end in an engagement row feeding the signal layer, so one key names the capability that matters rather than two naming the doors. The cost, equally worth stating: an integration allowed to post conversions can also post opens and clicks, so a compromised website-form credential could still steer personalization.

What does not change is as load-bearing as what does. Roles remain **rows, not an enum** — only the key set grows, not the model — and `VIEW` remains implied by every role. `permissions.py`'s own rule also still holds: **a permission key names a code path**, so each new key is real only once the guard it names exists. This list is therefore a specification for work, not a finished state.

One consequence follows at once, and it fails closed. `required_permission()` returns `UNMAPPED` for any write route with no policy entry, and `UNMAPPED` is refused. `WRITE_POLICY` must therefore gain entries for the JSON routes at the same time the routers are guarded, or every API write fails closed — loudly and safely, but completely.

**6. Access is assigned as `(user × role × brand)`.**
One mechanism serves both role assignment and brand scoping, rather than a role system with a scoping system bolted alongside it. A user may be Manager on one brand, Viewer on another, and absent from a third.

**7. The agency operator is not a role.**
External staff are Admins or Managers who happen to work for the agency. What distinguishes them is **accountability, not capability** — the audit trail records who acted ([[ADR-153 — Audit and Accountability]]). Introducing an `agency` role would encode an organisational relationship into the schema and immediately be wrong for the next company.

**8. Signals are shared at person level; content candidates are scoped to the sending brand.**
Brands are presentation, so engagement is engagement — a recipient who moves from brand A to brand B arrives with useful history rather than as a stranger. The accident worth preventing is *content* crossing brands through those shared signals, so a decision slot resolves **only the sending brand's content by default**. Safe by construction; widening it is a deliberate and visible act, matching the idiom already used by the mock-provider default, ADR-144's PII line and the governed model list. The brand column point 2 puts on content records is what makes that default enforceable rather than merely intended.

**9. `recipient.brand` is the sending brand, not an attribute of the person.**
A person connected to brands A and B *is* brand A in the context of a send from brand A; the brand comes from the navigation context. A brand affiliation may additionally arrive from the CRM as a projected attribute ([[ADR-120 — CRM as Customer Source of Truth]] / [[ADR-126 — Maintain Local Recipient Projection]]) feeding the permission table — a source of the data, not a competing concept.

**10. Brand as a decision-strategy filter is demonstrated, not built.**
Restricting candidates to the sending brand, to a named list of brands, or to none of the above is expressible through the existing `candidate_filter_fields` manifest, so it needs no new machinery. It is **out of scope for the POC and the standard package**; the playbook's obligation is to show *that* it is possible and *how*. What is deferred is the configurable filter, not point 8's default: resolving only the sending brand's content is part of the brand-column work and ships with it.

## Consequences

### Positive
- No tenant filter on any query, and therefore no class of cross-tenant leakage bug at all.
- GDPR separation between companies is a deployment decision an adopter can verify by looking at their server list, not an invariant they have to trust our code to hold.
- Role and brand scoping share one mechanism, so there is one place to reason about "may this person do this here."
- Companies with their own role scheme are unblocked without a fork; companies with no scheme get three roles that work.
- Cross-brand content leakage is prevented structurally rather than by care, because the brand a record belongs to is a column rather than a convention.
- A company running many brands is served by the model it already has, not by a second product, and a company using brands as a skin still only carries a default value in a column.
- The brand scope stops being a promise the schema cannot keep: the filter `has_permission` already implements gets something to filter on.

### Negative
- An agency operating twenty clients runs twenty installations. That is real operational weight, accepted because the alternative is the irreversible one.
- A company that genuinely needs brand separation *and* wants one system is told no. Some will consider that a missing feature; it is a deliberate refusal to make a compliance judgement on their behalf.
- Sharing signals across brands is defensible only while brands are presentation. A company using brands as a proxy for separate legal entities is in case 3 and should not be on one installation.
- Introducing users and roles requires an actor on every audited action, which is a change to code written when no actor existed.
- Brand scoping is now a **schema change across several modules** rather than a dormant column on the access grants. Content, campaigns, audiences and sends each gain a column, a migration and a filter in queries already written, and the reach goes further than the four: `ConsentEventDB` has no brand column either, which is the same gap this record's Notes already flag as "brand carried on the grant" in the unwritten consent purpose-split. (**Superseded by the 2026-10-04 status addendum below** for this claim only — `consent_events.brand_id` is NOT NULL now — and left as written because it records the cost as it was booked when this consequence was written.) That is work bought now, before the first pilot, instead of work avoided until someone asks.
- It is adopted on the strength of **one pilot customer's needs** — a real customer with around ten brands, but one data point. If that customer proves unrepresentative, we will have paid a cross-module migration for a scope most adopters leave at its default. Accepted because the retrofit is the expensive direction and this is the cheap one, but the evidence should be visible rather than buried.

## Notes

- **Open, deliberately not decided here:** the **consent purpose-split** (marketing opt-in versus transactional basis as distinct permissions on the same person, with brand carried on the grant) is recorded in the Decision Log as a proposed amendment to [[ADR-122 — Minimal Consent Model Required]]. It is not folded into this ADR because it changes an existing accepted decision rather than adding a new concern, and that amendment has not been written.
- Known implementation cost of that amendment, corrected 2026-09-14 — the point has inverted, because the *mechanism* shipped first. `RecipientDB.consent_status` is no longer a column: [[ADR-163 — Per-Channel Consent and Addressability]] replaced it on 2026-09-12 with append-only `ConsentEventDB` rows keyed `(recipient, channel, purpose)`, where `purpose` is already a real column defaulting to `"marketing"` (`backend/app/recipients/db_models.py`). Two things are still genuinely open. First, the amendment recorded above has not been written as such — [[ADR-122 — Minimal Consent Model Required]] carries a dated addendum (2026-09-12) widening consent to the `(channel, purpose)` grid, and that addendum itself still describes this purpose-split as a *proposed* amendment. Second, **brand on the grant is unbuilt**: `ConsentEventDB` has no brand column — one of the columns point 2 now requires. (**Superseded by the 2026-10-04 status addendum below** for this claim only — `consent_events.brand_id` is NOT NULL now — and left as written because the 2026-09-15 addenda refer back to it.) (Corrected 2026-09-15: this bullet previously added that `role_assignments.brand_id` was the only brand foreign key in the database. It no longer is; see the implementation status below. The consent gap itself is unchanged.)
- Interacts with [[ADR-081 — AI Ranks Within Governed Candidate Sets]] and [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]: the brand candidate filter composes with the governed candidate set rather than replacing it.
- **Implementation status, 2026-09-14:** Points 5 and 6 are built as rows rather than code — `RoleDB`, `RolePermissionDB` and `RoleAssignmentDB` exist with the three seeded roles, and a grant is one `(user × role × brand)` row (`backend/app/auth/db_models.py`). Brand scoping was **modelled but not enforceable as the code stood**, verified 2026-09-14 — at that point `role_assignments.brand_id` was the only brand foreign key in the database, and no campaign, content record, audience or send belonged to a brand. **Superseded by the 2026-09-15 status below**, which is the current picture; this paragraph is left as written because the addendum's reasoning refers back to the state it describes. `has_permission(db, user, permission, brand_id=None)` in `backend/app/auth/service.py` already accepts a brand and narrows the grants it reads to it — **no caller ever passes one**: both call sites in `backend/app/auth/dependencies.py`, `require_permission` and `enforce_policy`, omit the argument. Points 2, 8, 9 and 10 therefore have no implementation, and the work point 2 creates is three things: brand columns on the resource tables (content, campaigns, audiences, sends, and in due course the consent grants), a way for a request to say which brand it is acting in, and passing that brand into the filter that already exists. How each of those is done is not decided here. The sixteen-key vocabulary in point 5 is a specification, not a state: `backend/app/auth/permissions.py` still holds the original nine, and `policy.py`'s `WRITE_POLICY` still maps only `/ui/…` prefixes, so the twelve JSON routers are included in `backend/main.py` with no guard at all. The rule that a permission key names a code path is already broken by one of the nine — `credentials.manage` appears only in `permissions.py` and its tests, and no guard names it — before any of the seven new keys are added.

- **Implementation status, 2026-09-15 — what changed since the day before.**
  The columns point 2 calls for exist: `content_records`, `campaigns`,
  `audience_groups` and `send_instances` each carry a NOT NULL `brand_id`, and
  `auth_sessions` carries a nullable one as the working context
  (`scripts/migrate_0007_brand_scoping.sql`). A brand switcher renders in the
  navbar **only for a user holding grants on more than one brand**, which is
  point 4's promise made testable. Brands can be created, renamed and deleted
  on `/ui/users`, and the create-user and add-role forms carry a brand — none
  of which existed in the first cut, which left the scope enforced and
  unadministrable. List views filter by the working brand and a decision slot
  resolves only the sending brand's content (point 8).

  **Superseded by the 2026-10-04 status addendum below** — the paragraph that follows is left as written because the 2026-09-15 addendum beneath it argues from the state it describes.

  **Still unbuilt, and it is the half that matters:** `require_permission` and
  `enforce_policy` still call `has_permission` with no brand, so every
  permission behaves platform-level regardless of the classification in the
  addendum below. Detail-by-id routes are not scoped — the lists filter, but
  another brand's campaign opens by URL. `consent_events` carries no brand, so
  a send still reaches every consenting recipient whatever brand it claims;
  that is the separate consent work and it needs an [[ADR-163 — Per-Channel Consent and Addressability]] addendum first.

## Addendum 2026-09-15 — permission scope is a property of the permission, not of the role

Prompted by the question of whether an admin is an admin *globally*, with only manager, viewer and custom roles applying per brand. The answer is yes in substance and no in form, and the form is the part worth recording.

**The rule.** A permission is **brand-scoped** if the rows it guards carry a `brand_id`. Otherwise it is **platform-level** and is checked without a brand.

- **Brand-scoped (7):** `content.manage`, `campaigns.manage`, `audiences.manage`, `audiences.pin`, `sends.plan`, `sends.execute`, `overrides.manage`.
- **Platform-level (9):** `view`, `users.manage`, `settings.manage`, `credentials.manage`, `integrations.manage`, `recipients.manage`, `recipients.consent`, `insight.write`, `ai.run`.

**Why it is said about permissions rather than about the Admin role.** Saying "Admin is global" hardcodes a role name, and point 5 makes roles **rows, not code** — a preset a company may rename, extend or delete, which would leave the rule naming something that need not exist tomorrow. Said about permissions, the same outcome is derived from the schema instead of decreed: recipients carry no brand (point 9) and signal contributions carry none (point 8), so `recipients.manage`, `recipients.consent` and `insight.write` land platform-level on their own rather than because a list says so.

**The strongest argument, and it should be stated plainly: scoping `users.manage` per brand would be theatre.** An Admin on brand A can grant themselves Admin on brand B in two clicks. A control the controlled party can lift is not a control, and pretending otherwise is worse than admitting the permission is platform-level.

**The awkwardness this removes.** Without the split, enforcing the brand naively would mean **switching brand to reach Settings or Users** — even though there is one settings table and one user list, which point 2 already establishes when it refuses "no per-brand duplication of settings, strategies or taxonomy". That absurdity is the symptom that revealed the rule.

**`ai.run` is platform-level deliberately, and it is the one entry that breaks the rule's own logic.** An AI task writes rows that *do* carry a brand, so the rule as stated would scope it. It is platform-level anyway because the thing actually protected is **spend**, and the budget is one company-wide pot with one ledger and one bill ([[ADR-144 — AI Data and Model Governance]] §5). This is not deferred indecision: we must not assume how a company wants to share a budget across brands, or whether they want to move unspent budget from brand A to brand B at year end. The standard package therefore ships one platform-wide budget, and a company needing per-brand budgets edits the structure. The intended answer for them is a **playbook article on building per-brand budgets** — direction, not a build commitment.

**`view` is platform-level; the brand filter does the work.** `view` means "may open the app". What a person actually sees is already limited by the brand filter on every list, so scoping the permission adds nothing. It also preserves point 5's property that `VIEW` is implied by every role and is never the thing that locks somebody out.

**Several roles on one brand stay legal, and the access list must show the union.** Forbidding it was considered and rejected — it is useful with customised roles, which can be combined. `backend/app/auth/dependencies.py` already documents that a user holding several roles gets the **union** of their permissions, and that stays true. What changes is that the union must be **visible**: `backend/app/templates/users.html` renders one line per grant, so "Manager on Default" and "Admin on Default" sit as two lines and leave a reader to combine them in their head. The display obligation is recorded here; the design of that display is not decided here. This is unchanged from point 6 rather than an amendment to it — point 6 says a user may be Manager on one brand and Viewer on another, and never promised one role per brand.

**Superseded by the 2026-10-04 status addendum below** — the paragraph that follows is left as written because the classification above was argued against the state it records.

**What is not built, which is the whole of the enforcement.** Verified 2026-09-15: `require_permission` and `enforce_policy` in `backend/app/auth/dependencies.py` both call `has_permission(db, user, permission)` with **no brand**, and they are the only two callers in the codebase. The other side exists — `has_permission` and `permissions_for` in `backend/app/auth/service.py` take `brand_id` and narrow the grants when given one, and `resolve_session_brand` already resolves the working brand from the session — so both halves are present and nothing joins them. **Today every permission behaves platform-level**, and a Viewer on brand B who is Admin on brand A currently passes an Admin check while working in brand B. The split above is therefore a specification for work, not a state, exactly as point 5's sixteen keys are ([[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]): `backend/app/auth/permissions.py` still holds the original nine, so seven of the sixteen keys classified here have no code path to be scoped yet.

One correction the above depends on, since the Notes above it now read older than they look: the 2026-09-14 statement that `role_assignments.brand_id` is the only brand foreign key in the database no longer holds. `content_records`, `campaigns`, `audience_groups`, `send_instances` and `sessions` each carry one as of 2026-09-15, which is what makes "the rows it guards carry a `brand_id`" a test that can be applied rather than a prediction. `consent_events` still carries none, so the brand-on-the-grant gap those Notes flag is unchanged. (**Superseded by the 2026-10-04 status addendum below** for this last sentence only — `consent_events.brand_id` is NOT NULL now — and left as written for the same reason as the paragraph above.)

## Addendum 2026-09-15 — the category vocabulary is global; which content is in a category is already per-brand

Prompted by switching into an empty brand: content and campaigns came back correctly empty while **the category list and the category graph stayed fully populated**. That is point 2 working exactly as written — "no per-brand duplication of settings, strategies or taxonomy" — but the question it raised is the fair one, and it is that **"most everything else carries over" is too vague to act on**. Categories look like they belong to the *content* area, which is brand-scoped, rather than to the *taxonomy*, which is not. This settles it by naming them.

**The rule, and the distinction that resolves the doubt: the category vocabulary is global, and the category assignments already are not.**

Verified against the schema on 2026-09-15, in `backend/app/content/db_models.py`:

- `categories` and `category_relations` carry **no `brand_id`**. One shared vocabulary and one graph — "Beach" means the same thing in every brand, and the taxonomy is one graph rather than one per brand.
- `content_category_assignments` carries **no `brand_id` either**, and does not need one. It hangs off `content_records`, which has carried a NOT NULL `brand_id` since the 2026-09-15 brand-scoping migration (`backend/scripts/migrate_0007_brand_scoping.sql`). **Which content is Beach is therefore already per-brand, transitively, with no column of its own.**

A taxonomy is one shared language and each brand writes its own sentences in it. Duplicating the vocabulary per brand would produce two "Beach" categories that cannot be compared, which is precisely what point 2's refusal of per-brand taxonomy protects against — and comparability is what makes a governed taxonomy worth having at all ([[ADR-080 — Human-governed Taxonomy Before AI Selection]]).

**Duplication was considered as the general answer and rejected, and that rejection is what holds the line here.** The alternative shape was to make everything brand-specific and answer the resulting "but then I have to do it for every brand" with a duplicate-and-sync convenience. It is refused because **duplication as a comfortable default is bad for data hygiene**: a per-brand taxonomy would need syncing to stay comparable, and a synced copy is a copy that drifts. The global vocabulary is kept on that argument, not on a preference for the status quo.

**Flagged, not decided: a brand filter on the category graph and its analytics.** The need is real and stated — recipients of different brands react differently to the same categories. Two halves of that requirement have very different costs, and only the first is a reporting question.

- **Engagement is already brand-derivable today.** `engagement_events` → `delivery_executions` → `send_instances`, and `send_instances.brand_id` exists as of 2026-09-15. A per-brand *engagement* view over categories is computable with joins, needing **no new column and no decision here**.
- **Signal contributions are not.** `signal_contributions` (`backend/app/recipients/db_models.py`) carries recipient, category, contribution type, base weight, `occurred_at`, `source` and a nullable `event_id` — **no brand**, by point 8. A per-brand view of the decayed *affinity* score would need one.

That second half **is in tension with point 8 and is deliberately not resolved here.** Point 8 shares signals at person level because "brands are presentation, so engagement is engagement". The observation behind the new requirement is that a person may respond to "Beach" under brand A and ignore it under brand B, which the shared-signal premise does not model. So, stated as the split it is: **a brand filter on engagement analytics is available now; a brand filter on the affinity score is a change to point 8's model.** It is an open question for whoever picks it up, not a decision taken by this addendum.

One warning for anyone tempted to derive per-brand affinity at read time instead of answering that question. [[ADR-164 — Channel Feedback and Signals]] §9 rejected deriving `channel` from `event_id` for three reasons that transfer unchanged to deriving brand: the join path (five there, three here — contribution to event to execution to send instance) sits on every read in a layer designed around compute-on-read; `event_id` is **nullable**, since manually declared preferences have no event behind them, so brand would come back *unknowable* rather than *not applicable*; and [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]] prunes, so old contributions would lose their brand retroactively over exactly the window worth analysing. The same three objections point at the same answer — a column — which is why this is a point 8 question rather than a reporting one.

**Resolved 2026-09-15 — the question was mis-framed, and re-framing it dissolves the tension rather than settling it either way.**

It was posed as "does a person have different affinities per brand". The answer is **no, and that was never the requirement**. Somebody who subscribes to more than one brand can still have **one affinity profile**, because they will not in fact behave differently between brands — the profile shows their interests as one entity.

**What differs is the population an analytics view aggregates over, not the contribution.** Brand A is "Winter resorts and Spa"; brand B is "Summer Sports Vacations". Brand A's audience will react differently to Beach content than brand B's, and averaging across both produces a grey blend of *every category works the same*. So "what do I see when I open the category graph with brand A selected" has exactly one correct answer: **the affinities of brand A's audience**, not an average across every brand. **That audience is everyone who has consented to that brand** — not everyone the brand has mailed, which was the alternative and is a *history* rather than an audience.

**Point 8 is untouched and needs no amendment.** Signals stay shared at person level and one person keeps one affinity profile; what is scoped is *which people are summed*, and that is a query, not a column. `signal_contributions` therefore needs **no `brand_id`**, and the three objections borrowed above from [[ADR-164 — Channel Feedback and Signals]] §9 — the join path on every read, the nullable `event_id`, and [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]'s pruning — do not apply, because nothing derives a brand per contribution. The expensive answer was not paid for; it was avoided by asking a better question.

**It is blocked on the consent work.** "Consented to this brand" cannot be expressed until a consent grant carries a brand, which is the unbuilt brand column on [[ADR-163 — Per-Channel Consent and Addressability]]'s `(recipient, channel, purpose)` cell that the Notes above already flag. The brand filter on the category graph therefore ships **with** that work, not before it.

**Do not half-ship it.** Verified 2026-09-15 in `backend/app/frontend/router.py`: `/ui/graph` filters by no brand at all today and aggregates three figures per category — a content count and a selection count, both reached through `content_category_assignments.content_id` → `content_records` and so brand-scopable now with no new column, and a signal-impact figure read straight off `signal_contributions`, which is the one needing the population. Scoping the first two while the third still averages every brand would put two different populations side by side on one page, which recreates the grey blend in a subtler and harder-to-spot form. They ship together, edge metrics included — those mix both sources on the same canvas.

**Parked, named, and out of scope:** seeing **how subscribers who unsubscribed behaved** — whether particular categories drove them away. The want is real and is recorded here so it is not lost, but it belongs to an analytics scope not yet discussed (report building), not to the brand filter decided above.


## Addendum 2026-09-20 — `recipients.consent` moves to brand-scoped

**The 2026-09-15 addendum's own rule decides this, and the list it shipped with
got it wrong.** That rule reads: *"A permission is **brand-scoped** if the rows
it guards carry a `brand_id`."* `recipients.consent` was filed platform-level on
the stated grounds that *"recipients carry no brand (point 9) and neither do
signal contributions (point 8), so `recipients.manage`, `recipients.consent` and
`insight.write` have no brand to be checked against."*

That was true when it was written. It stopped being true when
`consent_events.brand_id` became NOT NULL under [[ADR-163 — Per-Channel Consent and Addressability]]'s own 2026-09-15 addendum — the same day. The rows this
permission guards are consent events, not recipients, and consent events have
carried a brand ever since.

**The lists are therefore 8 and 8**, not 7 and 9. `recipients.consent` joins the
brand-scoped set; `recipients.manage` and `insight.write` stay platform-level,
and their justification is unchanged and still correct — recipients and signal
contributions genuinely carry no brand.

### What was actually wrong

`policy.py` maps `POST /recipients/{external_id}/consent` to
`recipients.consent`; `_permitted` took the non-scoped branch; and the route
read the brand it wrote from **`ConsentSyncRequest.brand_id`, a field in the
request body**. So a principal granted `recipients.consent` on brand A could
write brand B's consent record — and the compliance record is the one
[[ADR-142 — Autonomous Workflows and the Automation Boundary]] §7 names as the
answer to a UWG §7 complaint.

It is also the shape [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] point 8 refuses by name: *"that would let a payload choose the
scope against which its own authorization is checked."*

### The decision

**The declared brand authorises; the body's `brand_id` must agree with it.**

Both halves matter, and they answer different questions. `X-Brand` (or the
session's working brand) says *which brand this caller may act in*, and the
grant is checked against it exactly as for every other brand-scoped write. The
body field says *which brand the CRM is asserting about*, which is ADR-120's
point and the reason `ConsentSyncRequest`'s docstring gives for requiring it:
"an assertion that does not say which brand is not an assertion about consent".

A mismatch is refused loudly rather than resolved in either direction. The
payload never chooses the scope; it only has to match it. Keeping both fields is
redundancy on purpose — the redundancy is what makes a disagreement visible
instead of silently picking a winner.

### Consequences

- **`X-Brand` becomes required on this route**, and an existing integration that
  omits it starts receiving a 400 until it is updated. That is a breaking change
  to a documented contract, taken deliberately: the alternative is a consent
  record written to a brand nobody checked.
- **`GET /recipients/` requires a working brand too**, and this is a consequence
  rather than a second decision. Consent is per-brand, so a recipient's consent
  status is not a fact until a brand is named — `to_recipients` has required a
  `brand_id` since the 2026-09-15 work. Note the split
  [[ADR-172 — The Working Brand Is Resolved Once and Carried Into Every Query]]
  point 1 makes available here: the route needs a brand as **context** to
  project consent, while `recipients.manage` stays platform-level as
  **authorisation**. The two are no longer the same question.
- **This also fixes a route that could not return.** `list_recipients` called
  `to_recipients(db, records)` with two arguments where three were required, so
  `GET /recipients/` has been raising `TypeError` for as long as consent carried
  a brand. Nothing in the repo called it, which is why a route that cannot
  return has looked fine.

## Addendum 2026-09-24 — findability is not affinity, so facets are per brand while categories stay global

Prompted by [[ADR-175 — Facets Are the Manager's Own Taxonomy, Not the Engine's]],
which introduces a second kind of vocabulary over content and deliberately scopes it
the opposite way to the one this record's 2026-09-15 addendum scopes categories.

**That addendum's rule is unchanged and correct.** The category vocabulary is global —
`categories` and `category_relations` carry no `brand_id` — on the stated grounds that
*"Content is per-brand; what a category MEANS is not."* Two brands share what "Beach"
means as an interest, each writes its own sentences in that shared language, and
duplicating the vocabulary per brand would produce two "Beach" categories that cannot
be compared. Nothing here touches that.

**What is added is the boundary of the argument, which was never stated because
nothing had tested it.** The reasoning above is about **affinity semantics**: a
category is a claim about a *recipient* — what this person responds to — and a claim
about a person does not change because a different brand is doing the sending.

**Findability is a different claim and does not inherit that reasoning.** A facet is a
claim about *how a team works* — which axes they file their content and campaigns along
so they can find a record among many. That is a property of the team and its business,
not of the person being mailed. An airline brand thinks in Destination and Cabin; a
hotel brand thinks in Property and Season. There is no shared meaning being protected
by forcing those into one list, because the two brands are not describing the same
thing in the first place — and comparability, the whole reason the category vocabulary
is global, buys nothing when there is nothing to compare.

**So the rule this record now carries is a distinction rather than a list.** A
vocabulary that describes a *recipient* is global, because a person is one person
across brands. A vocabulary that describes *how a team files its work* is per brand,
because a brand is a working context. Categories are the first; facets are the second.
The test is what the term is a claim about, not which table it happens to sit next to.

**Point 2 is not weakened by this, and the sentence that looks like it should be is
worth quoting exactly.** Point 2 refuses "per-brand duplication of settings, strategies
or taxonomy". Facets are per brand and are not a counterexample: the thing point 2
protects is one shared, comparable *meaning*, and a per-brand facet has no shared
meaning to fracture. The refusal of duplication-as-a-comfortable-default also stands —
ADR-175 ships no sync between brands' facets, on exactly this record's reasoning that a
synced copy is a copy that drifts.

**The cost is booked in ADR-175 rather than here, and it is not nothing:** a multi-brand
adopter redeclares common axes per brand, and a cross-brand copy gains a facet-value
reassignment step in `duplicate_campaign`.

**Facet administration is platform-level, and the reason is worth stating because it
generalises to every admin surface.** Facets are per brand while their administration
sits in Settings, so a platform-level `settings.manage` lets an administrator declare
facets in any brand. That is accepted deliberately: **there is no brand separation in the
admin role, and there cannot usefully be one while an admin can grant themselves a
role assignment on any brand.** Scoping an admin surface by brand would be theatre — the
administrator simply grants themselves the brand first and proceeds — so the scoping
would cost a permission and buy nothing. The decision recorded 2026-09-24 is that *an
administrator is capable of not breaking anything, so it is acceptable that they see all
settings.*

**What would change it is a superadmin role, and that is the thing to build if this
stops being acceptable** — a tier that can grant brand access and an admin tier that
cannot. Until that exists, a brand-scoped admin permission describes a boundary the
model does not enforce, which is worse than an honest platform-level one. Consistent
with this record's 2026-09-15 addendum: permission scope is a property of the
permission, and `settings.manage` is platform-level because what it governs is.

**Nothing in this record's Decision changes.** The category vocabulary stays global and
the classification of permissions is not affected.

## Addendum 2026-10-02 — the category graph's brand filter is built, and "brand A's audience" is defined

Prompted by task-57, decided by the user on 2026-10-02 and implemented the same day.

**The 2026-09-15 addendum resolved this and parked it; the blocker had cleared without
the work being picked up.** That addendum settled the shape — scope *which people are
summed*, "a query, not a column" — and held it back on the consent work, because
"consented to this brand" could not be expressed until a consent grant carried a brand.
`consent_events.brand_id` has been NOT NULL since 2026-09-15 under
[[ADR-163 — Per-Channel Consent and Addressability]]'s addendum of that date, so the
dependency was met the same day it was recorded. Nothing was waiting any more; the
filter had simply not been built. It is now.

**The decision: "brand A's audience" is every recipient whose latest *marketing*
consent for brand A is `opted_in` on any registered channel** — email or push as the
channel registry stands today. Three cases follow from it and are stated so nobody has
to derive them:

- a **push-only** subscriber to brand A counts in brand A's graph;
- someone who has consented **only to another brand** does not;
- someone with **no consent at all** counts in no brand's graph.

Two narrower definitions were weighed and not taken. **Email-only** was refused because
it would silently drop push-only subscribers from an audience they are plainly part of.
A **per-channel selector** was refused as premature: nothing yet asks for a per-channel
view of the graph, and the any-channel definition does not preclude adding one.

**All figures are scoped together, as the 2026-09-15 addendum required.** That addendum's
"do not half-ship it" is honoured in full:

- **content counts** and **co-occurrence edges** count only the brand's content records;
- **selection counts** count only resolutions of the brand's content;
- **signal impact**, on nodes and on edges alike, sums only the brand's audience.

No figure on the canvas averages across brands while its neighbour does not. The
category vocabulary and its relations stay the shared vocabulary this record's
2026-09-15 addendum keeps global, so **every category appears in every brand's graph**,
at zero where the brand has nothing in it — an empty brand shows the full taxonomy with
no weight on it, rather than a smaller taxonomy.

**Point 8 is untouched.** One person keeps one affinity profile, and nothing derives a
brand per contribution: `signal_contributions` still carries no `brand_id`, and the
filter selects which recipients' contributions are summed rather than tagging any
contribution with a brand. This is exactly the re-framing the 2026-09-15 addendum
recorded, now in code.

**Where it lives.** The computation is `category_graph` in `backend/app/insight/graph.py`,
with the audience as `brand_audience` beside it; `/ui/graph` in
`backend/app/frontend/router.py` only lays the result out. Tests are in
`backend/tests/test_category_graph.py`.

**Not done, and named so it is not mistaken for done:**

- **There is no JSON route for the graph yet.** The SPA will need one. Because the
  computation now sits behind the service boundary rather than in the UI router, that
  route is a thin wrapper over `category_graph`, not a second implementation.
- **The "how did unsubscribers behave" analytics stays parked** exactly as the
  2026-09-15 addendum left it — an analytics scope not yet discussed, not part of the
  brand filter.

**Nothing in this record's Decision changes.**

## Addendum 2026-10-02 (second) — who may change settings: people only, and AI configuration needs `settings.manage` and `ai.run` together

Prompted by task-49 (C2) and task-50, which give the settings surface a JSON API for
the React client of [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]],
and decided by the user on 2026-10-02. The Jinja settings page that surface replaces
is the one point 3's correction is about.

**1. Publishing a prompt version and choosing a model need both keys.** Publishing a
new version of an AI task's prompt ([[ADR-140 — AI Capability Layer]] point 4) and
choosing the model an AI task runs on ([[ADR-144 — AI Data and Model Governance]])
each require **`settings.manage` and `ai.run` together**. Either one alone is refused.
The reason is what the change reaches: each one alters what *every later* AI run does
and what it spends. That is authority over settings and authority over AI spend at
once, and the 2026-09-15 addendum above already names spend as the thing `ai.run`
protects. Holding only `settings.manage` would let someone redirect spend they may not
incur; holding only `ai.run` would let someone who may run a task rewrite it for
everybody.

Both keys are platform-level under the 2026-09-15 classification, so requiring both
raises no brand question: neither is checked against a brand, and the result is
platform-level too.

**2. Settings writes are people only.** A bearer (machine) credential is refused on
**every** settings write route, even when it holds `settings.manage` — and, for the
routes in point 1, `ai.run` as well. The guard is the one approvals and integration
management already use: `require_person` and `require_person_with` in
`backend/app/auth/dependencies.py`, which refuse a machine credential before any
permission is looked at, so the answer does not depend on what the credential holds
([[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] and its addendum
of 2026-10-02). The reason is what a machine with `settings.manage` could do: raise
the send cap, change the AI spend limits, or switch an AI task from require-approval
to auto-apply. Each of those takes the human out of the loop that the setting exists
to keep them in — the same reason a machine may request an approval and never grant
one. **Settings reads stay open to any principal holding `view`**, machine or person;
the refusal is on writes only.

**3. A correction: reading settings has always been `view`.** It would be easy to
describe `settings.manage` as the key that lets somebody *into* settings. That is not
how the platform works and never was. `required_permission` in
`backend/app/auth/policy.py` returns `view` for every non-write method, and `/ui/settings`
appears in `WRITE_POLICY` under `settings.manage`, which governs writes only. So the
Jinja settings page has always been readable by anyone holding `view`; only saving
needs `settings.manage`. **Reading stays `view`, and the JSON read does the same.**
Nothing is tightened by this addendum on the read side.

**4. Recorded for later, not built: free text typed into an AI action at run time needs
`ai.run` only — on one condition.** A feature in which a user types free text into an
AI action — for example a "create email" dialog where the user narrows the topic —
needs `ai.run` and nothing else, **provided the free text enters as an input to the
published prompt and never edits the prompt itself.** The condition is what keeps
point 1 intact. If typed text could alter the prompt, `ai.run` alone would become a
way to rewrite a prompt that point 1 says needs `settings.manage` as well. Whoever
builds such a feature has to show the text arrives as an input the published prompt
version receives, not as a change to that version.

**5. Channel availability is readable through the settings API, and not writable
anywhere yet.** Which channels this deployment has switched off — the settings row of
[[ADR-160 — Channel Model and Composition]] point 8 — becomes readable through the
settings API, so a client offers only the enabled channels rather than offering one
the server will then refuse. **No route writes it**, JSON or otherwise. Switching a
channel off while campaigns are planned on it raises questions nobody has answered,
starting with what happens to sends already scheduled on that channel. Writing it
therefore waits until somebody needs it, and it is a candidate for the "danger zone"
section that [[ADR-142 — Autonomous Workflows and the Automation Boundary]]'s addendum
of today names. ADR-160 point 8's server-side refusal of a disabled channel is
unchanged.

**What it costs.**

- **`WRITE_POLICY` maps one key per route prefix**, so a route that needs two keys is
  not expressible in that table as it stands. The second check has to be made
  somewhere the table does not describe, which makes it one more place a reader of the
  policy table will not see. How it is made is an implementation matter, not decided
  here.
- **No orchestrator can tune settings**, however it is granted. An adopter who wanted a
  flow to adjust a threshold or a cap has to put a person in front of that change. That
  is intended, and it is consistent with [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §10, which keeps AI-driven settings tuning as direction only.
- **A company whose Admin role lacks `ai.run`**, or whose Manager role lacks
  `settings.manage`, finds that neither can change a prompt or a model until one
  role carries both. The seeded Admin preset is the intended holder; an adopter with a
  custom scheme has to grant it deliberately.
- **A channel can only be switched off by editing the settings row directly** until the
  write path is designed, which is the same position it was in before this addendum.

**Nothing in this record's Decision changes.** Point 5's sixteen keys and the 2026-09-15
classification are untouched; this addendum says who may make settings writes and which
combination two specific writes require.

## Addendum 2026-10-04 — implementation status: brand enforcement is built

Prompted by task-44. **This is a status record, not a decision.** Three passages above
still described brand enforcement as unbuilt, and they are the passages someone
checking whether the brand boundary is real would read first. Each fact below was
verified against the code on 2026-10-04.

**Brand-scoped permissions are checked against the working brand.** `_permitted` in
`backend/app/auth/dependencies.py`, which both `require_permission` and
`enforce_policy` call, checks a platform-level permission with `brand_id=ALL_BRANDS`
(the union of every grant the user holds, asked for by name) and a brand-scoped one
against `request.state.current_brand`. **A brand-scoped permission with no working
brand is refused, never checked without one**, because checking it against the union
would let a grant on brand A act in brand B. `enforce_api_policy` in the same file
makes the same split on the JSON plane, and raises `BrandNotDeclared` rather than a
permission refusal when no working brand resolves. Built in commit `cb8b5b1`
(2026-09-15, "check brand-scoped permissions against the working brand"). The
`BRAND_SCOPED` set in `backend/app/auth/permissions.py` matches the 2026-09-15
classification as this record's 2026-09-20 addendum amended it.

**Consent carries a brand.** `ConsentEventDB` in `backend/app/recipients/db_models.py`
carries a NOT NULL `brand_id` with no default, and the latest-row-wins cell is
`(recipient, brand, channel, purpose)`. It was decided in
[[ADR-163 — Per-Channel Consent and Addressability]]'s addendum of 2026-09-15 and
committed the next day as `619194b` (2026-09-16, "scope consent to the sending brand").
That is why the earlier addenda date the column 2026-09-15 and the code dates it
2026-09-16. This record's 2026-09-20 addendum moved `recipients.consent` to brand-scoped
because of it. The brand-on-the-grant gap is closed. This addendum does not check
whether the consent purpose-split amendment to
[[ADR-122 — Minimal Consent Model Required]], named in the first Notes bullet, has been
written, and says nothing about it.

**The JSON routers are guarded.** Commit `ee01e8a` (2026-09-18, "the JSON API stops
being an open control plane"). Each JSON router is included in `backend/main.py` with
`enforce_api_csrf` and `enforce_api_policy` as dependencies, and `WRITE_POLICY` in
`backend/app/auth/policy.py` no longer maps only `/ui/…` prefixes. It now maps the JSON
prefixes beside them, among them `/content/`, `/campaigns/`, `/delivery/`,
`/snapshots/`, `/recipients/`, `/insight/`, `/provider/events`, `/overrides/`,
`/api/audience-groups`, `/approvals`, `/integrations` and `/settings`. A write route
with no entry still resolves to `UNMAPPED` and is refused, so the fail-closed
consequence point 5 predicted holds. Two entries are deliberate exemptions named as
sentinels rather than permissions: `/provider/webhooks/` (`PROVIDER_SIGNED`, because a
provider signs its own callbacks) and `/auth/session` (`PUBLIC_AUTH`, the door a
session comes through). One later change matters to a reader of that commit. At
`ee01e8a` the plane accepted machine credentials only, and the session-cookie principal
the React client uses arrived afterwards under
[[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]].

**Detail-by-id reads are brand-scoped.**
[[ADR-172 — The Working Brand Is Resolved Once and Carried Into Every Query]]
(accepted, dated 2026-09-19) separated context from authorisation. Every request
resolves a working brand, brand-owned service queries take it, and an out-of-brand row
answers exactly as an absent one does. Another brand's campaign no longer opens by URL.
Two tests pin this:

- `test_another_brand_s_campaign_answers_instead_of_crashing` in
  `backend/tests/test_brand_scoping.py` opens a default-brand campaign at
  `/ui/campaigns/{id}` while working in another brand. It expects a redirect to the
  campaigns list with a message, not the page and not an error.
- `test_a_record_in_another_brand_answers_as_absent` in
  `backend/tests/test_brand_boundary.py` expects `GET /content/{id}` from a foreign
  brand to answer 404, the same answer as an id that never existed.

The list-side counterpart is `test_content_is_invisible_from_another_brand` in
`backend/tests/test_brand_scoping.py`, which asserts at the service query.

**The vocabulary point 5 specifies is in code.** `backend/app/auth/permissions.py` no
longer holds only the original nine. It defines every key point 5 lists, including the
split and new ones: `audiences.pin`, `sends.plan`, `recipients.manage`,
`recipients.consent`, `insight.write`, `overrides.manage` and `integrations.manage`.
Each of those added keys names a route in `WRITE_POLICY`, so each is real in the sense
point 5 requires. The 2026-09-14 status paragraph made one further observation, and it
still holds, so it is stated here so nobody takes it as fixed: `credentials.manage`
appears in `backend/app` only in `permissions.py`, so it still names no guard.

**What this supersedes.** These passages above described this work as unbuilt, and this
addendum supersedes them:

- in `## Consequences` → `### Negative`, the claim in the "Brand scoping is now a
  schema change across several modules" bullet that `ConsentEventDB` has no brand
  column. The rest of that bullet is not superseded;
- in `## Notes`, the claim in the "Known implementation cost" bullet that brand on the
  grant is unbuilt. The rest of that bullet, about the purpose-split amendment, is not
  superseded;
- in `## Notes`, the "Still unbuilt, and it is the half that matters" paragraph of the
  2026-09-15 implementation status;
- in the 2026-09-15 permission-scope addendum, the "What is not built, which is the
  whole of the enforcement" paragraph, and the sentence in the correction after it that
  `consent_events` still carries no brand.

Each now opens with, or carries, a one-line marker pointing here. Otherwise each is left
as written for the same reason as the 2026-09-14 status paragraph: later text in this
record, including its own 2026-09-15 addenda, refers back to the state they describe.

**Nothing in this record's Decision changes.** Status, the sixteen keys and the
classification of permissions are untouched; this addendum records that what they
specified has been built.

## Addendum 2026-10-09 — what brands cost a single-brand company is two costs, and point 4 names only one

Prompted by finding P2-A1 of the business interview baseline
(`docs/business-interview-baseline.md`, "The cost ADR-150 quoted to a single-brand
adopter is falsified by what got built"), and decided by the user in the 2026-10-09
interview review. The decision is logged in `docs/playbook-strategy.md` under
"2026-10-09 — Business findings decided one by one in the interview review". The
evidence below was checked against the code on 2026-10-09.

**What point 4 says, and what it leaves out.** Point 4 prices the single-brand case in
one sentence: *"A company treating brands as a skin pays a default value in a
column."* The sixth bullet under `### Positive` repeats it: *"a company using brands as
a skin still only carries a default value in a column."* Both sentences read as the
whole cost. They are the cost of **running** the product. They say nothing about the
cost of **extending** it, and for anyone who writes code against this platform that
second cost is the larger one.

**The decision: the two costs are said apart.**

**1. Running the product costs a single-brand company a default value. That holds,
and it is tested.** One default brand always exists, the working context supplies it,
and nothing asks a single-brand user for one. `TestTheSingleBrandCompanyPaysNothing` in
`backend/tests/test_brand_scoping.py:112` pins this three ways. A user granted only one
brand gets a working brand that is not switchable (`:121`). Over HTTP, the
server-rendered `/ui/content` page renders no brand switcher (`:134`). Creating a
content record needs no brand from the caller (`:158`). The React client makes the same
promise: its switcher is absent entirely when the session is not switchable
(`frontend/src/shell/BrandSwitcher.test.tsx:8`).

**2. Extending the code costs a cross-cutting rule: every new table, route and
permission follows brand scoping.** Brand handling is mandatory in every route that
touches a brand-owned row, and a single-brand deployment does not exempt the code from
it. A brand-owned route takes its brand from `working_brand` in
`backend/app/auth/dependencies.py:339-361`, which **raises rather than defaulting**.
The exception it raises, `BrandNotDeclared` (`:281`), is explicitly not a fallback to
"the one brand this integration holds". A single-brand company never meets that
refusal, because its one brand always resolves. Whoever writes the next route has to
call it all the same. The rest of the rule is written down on the brand page,
[[brand]] (`docs/architecture/Code/brand.md`), under its change-impact section:

- a call to `has_permission` passes a scope;
- a new permission key is classified in `BRAND_SCOPED` and given a `WRITE_POLICY`
  entry;
- a new detail route gets a `SWITCH_LANDINGS` entry;
- a cross-brand write checks its target brand with `brands_with_permission`.

A key left out of `BRAND_SCOPED` is platform-level by omission
(`backend/app/auth/permissions.py:107`). For a key that guards brand-owned rows, that
means it is checked against the union of every grant its holder has.

**The rule is not hypothetical, and the evidence is that it has already been missed.**
The Brand Boundary interview ([[Interview Prep - Brand Boundary]], Q7, resolved
2026-09-19) found `delete_brand` counting five brand-carrying tables where seven
existed. `consent_events` and `integration_grants` had been added *"without following a
maintenance rule the brand page already states."* That one list has since been derived
from the models (`brand_holders()`, task-19, 2026-10-01, as the brand page records), so
a new brand-carrying table no longer needs anything for `delete_brand`. The rest of the
rule above is still kept by hand. Two tables slipped past it in a codebase written by
people who knew the rule. That is the measure of what the rule costs someone who does
not.

**What the positioning may say.** It may claim the first cost to anyone: a single-brand
company runs the product without meeting brands. When it speaks to developers or
agencies who extend the code, it must also name the second: brand scoping is a rule
that every new table, route and permission follows, as the brand page documents.
Claiming the first to that audience without the second is the understatement this
addendum corrects.

**Wording only.** Nothing is built, and no guard task was chosen. Nothing checks that a
new route uses `working_brand`, or that a new key that guards brand-owned rows is in
`BRAND_SCOPED`. The one part that already fails closed is unchanged: a write route with
no `WRITE_POLICY` entry is refused as `UNMAPPED` (point 5). The rest of the rule is held
by the brand page and by review.

**What it costs.**

- **Positive:** the record no longer understates what a developer pays. Someone
  deciding whether to extend the platform for a single-brand client learns from this
  record that brand scoping is part of every change, not only from the code.
- **Negative:** the single-brand pitch carries a qualification for the developer
  audience. "Brands cost you nothing" can no longer be said to an agency that will
  write code, and the shorter claim is the more attractive one.

**Nothing in this record's Decision changes.** Point 4 stands as written. It is true of
running the product, and this addendum records that it says nothing about extending
it. The sixth `### Positive` bullet is read the same way.

## Addendum 2026-10-16 — administering people, roles and brands from the client

Prompted by task-358, which gives user, role and brand administration a JSON API
and Settings subpages in the React client of
[[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]]. Until now
they existed only in the Jinja UI. The user decided it on 2026-10-16, one
question at a time. **This does not touch the Decision.** Points 5 and 6 stand:
roles are rows, and a grant is one `(user × role × brand)` row. What this records
is how those rows are administered from the client, and two rules that hold
wherever they are administered. The code facts below were checked on 2026-10-16.

**1. Nobody can lock the installation out of its own administration.** Three acts
are refused, each with the reason:

- deactivating yourself;
- any deactivation, any grant revoked, or any role's permissions replaced, that
  would leave no active person holding `users.manage`.

The guards live in the auth service, in `set_active`, `revoke_assignment` and
`set_role_permissions` (`backend/app/auth/service.py`, with `user_managers` and
`AccessLockout`). So the Jinja forms get them too, and not only the new routes:
both now write through `backend/app/auth/admin.py`. **This changes prior
behaviour.** Until today the Jinja pages had no such guard. An installation in
which nobody holds `users.manage` (access control never set up) is left as it is.

Two other writes already could not lock anyone out, which is why they are not in
the list. `delete_role` refuses a built-in role and a role somebody still holds.
`delete_brand` refuses the default brand, and refuses any brand that still has
rows belonging to it, role assignments included (`brand_holders()`).

**2. Every administration write is audited** ([[ADR-153 — Audit and Accountability]]).
The actions already recorded are kept: `user.role_granted`, `user.role_revoked`,
`user.deactivated`, `user.reactivated` and `brand.created`. The writes the Jinja
forms never logged gain an entry: `user.created`, `role.created`,
`role.permissions_set`, `role.deleted`, `brand.renamed` and `brand.deleted`
(`backend/app/audit/service.py`). Like the guards, this is a rule about the
write, not about which screen made it: the Jinja forms log them too.

**3. The JSON routes sit under `/auth/users`, `/auth/roles`, `/auth/brands` and
`/auth/permissions`**, in `backend/app/auth/admin_router.py`.
`/auth/permissions` is the read-only catalogue of keys, each marked
platform-level or brand-scoped as the 2026-09-15 addendum and its 2026-09-20
correction classify them. The rules are:

- **People only.** A machine credential is refused, using `require_person_with` in
  `backend/app/auth/dependencies.py`, the guard the settings and integration
  routes already use (this record's second 2026-10-02 addendum, point 2;
  [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]], addendum
  2026-10-02).
- **`users.manage` for reads as well as writes**, set once at the router. This is
  not a tightening. The Jinja access list and role grid have always needed
  `users.manage` to read. It does differ from settings, where reading is `view`
  (point 3 of the second 2026-10-02 addendum), and the difference is kept.
- **One copy of each rule.** The routes and the Jinja forms call the same functions
  (`backend/app/auth/admin.py`, over the service), so a refusal reads the same on
  both planes.
- **Policy entries.** `WRITE_POLICY` in `backend/app/auth/policy.py` gains entries
  for `/auth/users`, `/auth/roles` and `/auth/brands`. Without them the writes
  would resolve to `UNMAPPED` and be refused (point 5).

**4. Settings gains four subpages: Users, Roles, Integrations and Brands.** They
are parts of Settings, not areas of their own, by the user's ruling of 2026-10-11
("a setting part, not an area"), the one already applied to brand profiles.
Brands are created with a key and a name, and can be renamed. The key stays
permanent. A brand can be deleted, after the client asks once, except that the
delete is refused while anything belongs to the brand, as `delete_brand` already
refuses it.

**5. The access-control switch stays out of the React client.** Switching
enforcement on or off is a development switch. Turning access control off is not
something a manager screen should offer. It stays on the Jinja page
(`POST /ui/users/enforcement`), where it is today.

**6. A grant always names a brand, and the client shows the brand only when there
is a choice.** `RoleAssignmentDB.brand_id` is NOT NULL, so every grant is a role
on a brand. The client shows "role on brand", and offers the brand choice, only
when the installation has more than one brand. The Jinja page already did this.
It is point 4's promise kept on the new screen: a single-brand company never
sees the brand.

**Consequences.**

- **Positive.** An installation can no longer be locked out of its own
  administration by one form submission, from either UI. The audit trail now
  covers every change to the access model, including role permissions, which
  decide what everyone holding the role may do. Each rule exists once, so the two
  UIs cannot drift apart while both exist.
- **Negative.** The last person holding `users.manage` cannot step down, or have
  that permission removed from their role, until somebody else holds it. Handing
  administration over now takes two steps. The access-control switch keeps the
  Jinja page alive for this one control. Retiring the Jinja UI (task-312) must
  decide where the switch goes, or keep that one page.

**Nothing in this record's Decision changes.** Points 5 and 6 and the
classification of permissions are untouched.

## Related ADRs

### Depends On
- [[ADR-004 — Privacy Operations as a First-Class Architectural Concern]]
- [[ADR-120 — CRM as Customer Source of Truth]]
- [[ADR-126 — Maintain Local Recipient Projection]]
- [[ADR-144 — AI Data and Model Governance]]

### Enables
- [[ADR-151 — Authentication and Sessions]]
- [[ADR-152 — Secret and Credential Handling]]
- [[ADR-153 — Audit and Accountability]]
- [[ADR-154 — Erasure and Retention]]
- [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]
