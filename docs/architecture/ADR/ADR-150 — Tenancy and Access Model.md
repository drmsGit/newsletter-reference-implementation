---
type: adr
status: accepted
topic:
  - architecture
  - security
  - access
  - governance
created: 2026-08-02
modified: 2026-09-15
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
- Brand scoping is now a **schema change across several modules** rather than a dormant column on the access grants. Content, campaigns, audiences and sends each gain a column, a migration and a filter in queries already written, and the reach goes further than the four: `ConsentEventDB` has no brand column either, which is the same gap this record's Notes already flag as "brand carried on the grant" in the unwritten consent purpose-split. That is work bought now, before the first pilot, instead of work avoided until someone asks.
- It is adopted on the strength of **one pilot customer's needs** — a real customer with around ten brands, but one data point. If that customer proves unrepresentative, we will have paid a cross-module migration for a scope most adopters leave at its default. Accepted because the retrofit is the expensive direction and this is the cheap one, but the evidence should be visible rather than buried.

## Notes

- **Open, deliberately not decided here:** the **consent purpose-split** (marketing opt-in versus transactional basis as distinct permissions on the same person, with brand carried on the grant) is recorded in the Decision Log as a proposed amendment to [[ADR-122 — Minimal Consent Model Required]]. It is not folded into this ADR because it changes an existing accepted decision rather than adding a new concern, and that amendment has not been written.
- Known implementation cost of that amendment, corrected 2026-09-14 — the point has inverted, because the *mechanism* shipped first. `RecipientDB.consent_status` is no longer a column: [[ADR-163 — Per-Channel Consent and Addressability]] replaced it on 2026-09-12 with append-only `ConsentEventDB` rows keyed `(recipient, channel, purpose)`, where `purpose` is already a real column defaulting to `"marketing"` (`backend/app/recipients/db_models.py`). Two things are still genuinely open. First, the amendment recorded above has not been written as such — [[ADR-122 — Minimal Consent Model Required]] carries a dated addendum (2026-09-12) widening consent to the `(channel, purpose)` grid, and that addendum itself still describes this purpose-split as a *proposed* amendment. Second, **brand on the grant is unbuilt**: `ConsentEventDB` has no brand column — one of the columns point 2 now requires. (Corrected 2026-09-15: this bullet previously added that `role_assignments.brand_id` was the only brand foreign key in the database. It no longer is; see the implementation status below. The consent gap itself is unchanged.)
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

  **Still unbuilt, and it is the half that matters:** `require_permission` and
  `enforce_policy` still call `has_permission` with no brand, so every
  permission behaves platform-level regardless of the classification in the
  addendum below. Detail-by-id routes are not scoped — the lists filter, but
  another brand's campaign opens by URL. `consent_events` carries no brand, so
  a send still reaches every consenting recipient whatever brand it claims;
  that is the separate consent work and it needs an [[ADR-163 — Per-Channel
  Consent and Addressability]] addendum first.

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

**What is not built, which is the whole of the enforcement.** Verified 2026-09-15: `require_permission` and `enforce_policy` in `backend/app/auth/dependencies.py` both call `has_permission(db, user, permission)` with **no brand**, and they are the only two callers in the codebase. The other side exists — `has_permission` and `permissions_for` in `backend/app/auth/service.py` take `brand_id` and narrow the grants when given one, and `resolve_session_brand` already resolves the working brand from the session — so both halves are present and nothing joins them. **Today every permission behaves platform-level**, and a Viewer on brand B who is Admin on brand A currently passes an Admin check while working in brand B. The split above is therefore a specification for work, not a state, exactly as point 5's sixteen keys are ([[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]): `backend/app/auth/permissions.py` still holds the original nine, so seven of the sixteen keys classified here have no code path to be scoped yet.

One correction the above depends on, since the Notes above it now read older than they look: the 2026-09-14 statement that `role_assignments.brand_id` is the only brand foreign key in the database no longer holds. `content_records`, `campaigns`, `audience_groups`, `send_instances` and `sessions` each carry one as of 2026-09-15, which is what makes "the rows it guards carry a `brand_id`" a test that can be applied rather than a prediction. `consent_events` still carries none, so the brand-on-the-grant gap those Notes flag is unchanged.

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
`consent_events.brand_id` became NOT NULL under [[ADR-163 — Per-Channel Consent
and Addressability]]'s own 2026-09-15 addendum — the same day. The rows this
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

It is also the shape [[ADR-166 — Inbound Machine Callers Are Authenticated
Principals]] point 8 refuses by name: *"that would let a payload choose the
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
