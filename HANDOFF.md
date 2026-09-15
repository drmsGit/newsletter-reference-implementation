# HANDOFF — Newsletter Blueprint

**Last updated:** 2026-09-15 · **Branch:** `main` · **Brand scoping step 1 built; five security ADRs accepted**

The account migration this file was originally written for (2026-09-04) is
**done** — sessions now run on the business account, and nothing is left
stranded on the old one. What follows is the current state.

---

## ▶️ Paste this into a fresh session

```
Continue work on the Newsletter Blueprint at
/Users/diedeslembrouck/Projects/newsletter-reference-implementation — a
vendor-neutral reference architecture for email marketing systems (FastAPI
modular monolith + server-side Jinja UI), published as a playbook + starter
package.

READ FIRST (in order):
1. HANDOFF.md (repo root) — current state and the open queue.
2. CLAUDE.md (repo root) — project rules. ADR discipline is strict: required
   sections, status-in-two-places, never edit an Accepted ADR's Decision
   (supersede or append a dated addendum), never renumber. Highest ADR is 165.
3. docs/playbook-strategy.md §5 (Decision Log — read the 2026-09-12 and
   2026-09-13 entries),
   docs/backlog.md, docs/business/ (BRIEF, POSITIONING, LAUNCH-GATES,
   ASSUMPTIONS, BETA-SCOPE).
4. .claude/agent-memory/backlog-sequencer/ — the dependency graph and
   cost-of-delay classification. Refine it, don't rebuild it.
5. Your own memory entry "Newsletter Blueprint". Trust but verify any
   file:line claim against current code — several in the docs were wrong.

WORKING STYLE:
- State, before touching any file: which files change, what the change does,
  which ADR governs it (by number, or "none"), and what could break.
- Architecture decisions are ADRs in the repo, written BEFORE implementing.
  Business-side decisions go in docs/business/decisions/, not ADRs.
- One question at a time in interview/review passes; I decide each, nothing
  is written into an ADR until I've made the call.
- Use the project's own subagents in .claude/agents/ — adr-author for ADRs and
  addenda, backlog-sequencer for queue work, bug-fixer for a named 🔴 bug whose
  entry states its own fix (runs in a worktree; invoke with isolation:
  "worktree"), code-slimmer, adr-drift, positioning-critic, assumption-scanner. They are NOT selectable as
  subagent_type in the desktop app: launch general-purpose and tell it to read
  .claude/agents/<name>.md and follow that persona, restating hard constraints
  (e.g. backlog-sequencer must never edit docs/backlog.md).
- Never read all ADRs into the main session — delegate the sweep.
- Run the test suite from backend/, not the repo root.

Do NOT touch the 14 Needs-ADR items unless I ask — they were deliberately
left open across multiple review passes.
```

---

## Current state (2026-09-13)

### Omni-channel — designed and accepted; the consent half is built

**ADR-160–164** accepted 2026-09-12, and **ADR-165** written to supersede
**ADR-001** — the repository's **first supersession ever**. Seven dated addenda
were written to ADR-021/062/063/101/103/121/122, plus an eighth to ADR-163
recording four questions the implementation surfaced. Three decisions the
interview left open are closed (unlicensed-channel disable via a settings row;
address-pick via an optional `is_primary` flag with most-recently-verified
fallback; ADR-001's fate).

**Decided 2026-09-12:** the consent/addressability migration lands **before**
the Gate-2 P0 fix, so the P0 is built once, in ADR-163 §8's shape. Split into
two phases:

* **Phase A — consent. ✅ COMPLETE** (2026-09-13), and **launch gates 2 and 4b
  are closed**: the P0 send-time consent gate is built in ADR-163 §7's ordered-stack
  shape (`app/delivery/exclusion.py`), recording *why* each recipient was
  excluded, and the P1 beside it (a send reporting `sent` when every delivery
  failed) is fixed in the same function. Consent is append-only
  events keyed `(recipient, channel, purpose)`, latest wins.
  `recipients.consent_status` **is gone**, from the model and the database.
  All three gates read events. `ConsentDenied` (a `ValueError` subclass)
  replaces the bare `ValueError` at the decisioning gate. Drift is
  **directional** — `platform_ahead` means relay outward, `crm_ahead` means
  re-run the sync. The send path resolves its address from addressability, the
  webhook scopes opt-outs to the execution's channel/purpose, and dedupe runs
  on the resolved address in one bulk query.
* **Phase B — email → addressability. ✅ COMPLETE** (2026-09-13).
  `RecipientDB.email` is gone. Every display site resolves the address through
  `resolve_email(s)` or projects via `to_recipient(s)`. `to_recipients` is the
  bulk path — use it for any list, since the per-record form issues two queries
  each.

### Gate 4 — sign-in is guarded end to end (2026-09-13)

Three things landed, in this order: enforcement **defaults to ON**; CSRF covers
all 62 forms through one router-level dependency beside `enforce_policy`,
failing closed; and requesting a sign-in code is **rate limited per address and
per IP** (ADR-151 §2), five per address per 15 minutes and twenty per client per
hour, counted in `login_code_requests` rows.

A throttled request answers with the **same neutral 303** as every other
outcome, and **refusals are not counted** — counting them would let an attacker
hold a real person's address over the limit indefinitely, turning a mail-volume
control into a denial of sign-in. Both identifiers are stored hashed.

**Known limit:** behind a reverse proxy every visitor shares one per-IP bucket
unless `TRUST_PROXY_HEADERS=true`. Off by default, because an attacker who can
set `X-Forwarded-For` would otherwise get a fresh rate-limit identity per
request — a limit that is too broad fails safely, one that does not exist does
not.

### Database state: migrations 0001a–0005 applied

Both `scripts/migrate_0001a_consent_expand.sql` and
`scripts/migrate_0001b_consent_contract.sql` **have been applied** to the local
dev database. `consent_events` and `recipient_addresses` exist and are
populated (41 recipients → 41 events, 41 addresses), `delivery_executions` has
`channel` + `purpose`, and neither `recipients.consent_status` nor `recipients.email` exists any more.
`delivery_executions` also has `exclusion_reason`, and `send_instances` has
`sent_count` / `failed_count` / `excluded_count`. `migrate_0005` adds
`login_code_requests` — the sign-in rate-limit counter — and has been applied.
It was rehearsed twice on a scratch database first, and the schema it builds is
identical to the one `create_all()` produces.

Both scripts are idempotent and were rehearsed against a restored copy before
being applied: expand→contract clean, both re-runnable, contract-without-expand
refused, and a recipient inserted between the two runs correctly refused rather
than silently losing its consent state. `migrate_0001b` guards rather than
trusts — it will not drop anything unless every recipient already has a consent
event and an address.

**"Address" means the email address stored as a row, nothing postal**, and a
recipient is never required to have one — the guard only asks for an address
where the old email column had a value, and a recipient without one is simply
unreachable on that channel rather than rejected.

There is **no Alembic and no migration runner**. Decided 2026-09-12: schema
change is hand-written, numbered, idempotent DDL in `backend/scripts/`.
`Base.metadata.create_all()` only ever creates missing tables.

### Tests

207 green. **Run from `backend/`** — `test_auth_policy.py` opens a file by
relative path and fails from the repo root (pre-existing, not a regression).

`tests/test_consent_gates.py` is new and load-bearing: before it, the suite
stayed green whether the consent gates were intact or deleted. Every test in it
was mutation-verified — removing a gate fails only that gate's tests.

---

## Open queue

> **Naming:** the brand work's steps are "brand step 1/2/3", not "Phase N".
> [[ADR-130]] already uses "Phase 2" for an unrelated architecture phase, and
> an `adr-author` run refused to write "Phase 2" into ADR-150 for exactly that
> reason. The label was only ever chat shorthand.


**ADR acceptance, decided 2026-09-14.** ADR-004, 150, 151, 153 and 154 are
**Accepted**. ADR-152 and ADR-166 stay Proposed, for different reasons:

1. **ADR-152 needs its own session — an interview, taught rather than asked.**
   The user's words: *"I can't make a decision here because I don't understand
   it."* The subject is credential handling and the goal is a state-of-the-art
   setup, so the session has to explain the options before asking anything.
   Do not fold this into another pass.
2. **ADR-166 stays Proposed** by decision. Nothing about it is blocked — the
   design is complete and the key list settled — the user simply is not
   adopting it yet.

**Work the acceptances create, in the order it makes sense:**

3. ~~**ADR-150 — multi-brand.**~~ **BRAND STEP 1 BUILT 2026-09-15.** `brand_id` is
   on `content_records`, `campaigns`, `audience_groups` and `send_instances`
   (NOT NULL), plus `auth_sessions` (nullable, the working context).
   `migrate_0007` backfilled everything to the single default brand and
   rescoped `ux_audience_groups_name_lower` to `(brand_id, lower(name))`, so
   two brands may each own a "VIPs". A switcher sits in the navbar and
   **renders only when the user holds grants on more than one brand** — ADR-150
   point 4's promise, and the thing most worth not breaking. 229 tests.

   **The sending brand is derived, never taken from the session.**
   `brand_for_snapshot` walks snapshot → variant → campaign, so a manager who
   switches brand between building a send and firing it cannot send brand 1's
   campaign as brand 2.

   **What brand step 1 deliberately does NOT do — read before going near a real
   send.** Brand scoping is **authoring-side only**. A brand 2 campaign is
   filtered to brand 2's content and audiences, but the send still reaches
   **every consenting recipient**, because consent carries no brand yet.
   Audience criteria are `{language, status, category_id, min_score}` — all
   properties of the person — and recipients deliberately carry no brand
   (point 9). Two brands' "VIPs" contain the same people.

   **Brand administration is on `/ui/users`** — a Brands panel (create,
   rename, delete) plus a brand selector on the create-user and add-role forms,
   both of which render only above one brand. Gated on `users.manage`, not a
   new permission key: a brand is the scope in every grant (point 6), so
   creating one acts on the access model that permission already guards.
   Delete refuses the default brand outright and any brand still holding
   content, campaigns, audiences, sends or grants — and says which.

   **This was missing from the first cut and made the whole feature
   unreachable.** `ensure_default_brand` was the only code that ever created a
   brand, `assign_role` was called without one so every grant landed on the
   default, and no form offered the field — so the switcher could never appear
   for anybody. Enforced and unadministrable is worse than absent, because it
   looks finished. The planning error was covering scoping without ever asking
   how a second brand comes into existence.

   **Three known gaps, none hidden:**
   - ~~Detail-by-id routes are not scoped.~~ **DONE 2026-09-15** for campaigns,
     content, audience groups, sends and decision slots. Two things that only
     surfaced by loading the pages: scoping `content_detail` made `record is
     None` reachable for the first time and the template raised a 500 rather
     than saying no; and `/ui/campaigns/{id}` still leaked another brand's
     campaign *name* through an audience picker beside it, because suggested
     groups are named after the campaign that produced them. The page refused
     and the dropdown did not.
   - **The twelve JSON routers default to the default brand**, with a comment
     pointing at ADR-166. They are unauthenticated, so there is no session to
     read a brand from; ADR-166's one-credential-per-brand is the real answer.
   - **`categories`, `recipients`, `signal_contributions`, `app_config` carry
     no brand** — ruled out by ADR-150 points 2, 9 and 8 respectively. Email
     module templates are files, so already shared.

4. ~~DECISION NEEDED — should anything stay global by design?~~ **DECIDED
   2026-09-15: yes, the category vocabulary stays global**, and it is being
   named explicitly in ADR-150 rather than left to "most everything else
   carries over".

   The distinction that settled it: **the vocabulary is global, the assignments
   already are not.** `categories` and `category_relations` are one shared
   language — "Beach" means the same thing in every brand — while
   `content_category_assignments` hangs off `content_records`, which carries a
   brand, so *which content is Beach* is already per-brand with no column of
   its own. Each brand writes its own sentences in one shared language.

   **Duplication was considered as the general answer and rejected**: as a
   comfortable default it is bad for data hygiene. A per-brand taxonomy would
   need syncing to stay comparable, and a synced copy is a copy that drifts.
   That keeps brand step 3 duplication as an escape hatch for campaigns and content,
   not as the mechanism the model leans on.

   **The brand filter on category analytics — DECIDED 2026-09-15, and the
   question turned out to be mis-framed.** It was posed as "does a person have
   different affinities per brand". No, and that was never the requirement: a
   person keeps **one** affinity profile, their interests as one entity. What
   needs scoping is the **population an analytics view sums over**, not the
   contribution.

   The example that makes it obvious: Brand A is "Winter resorts and Spa",
   Brand B is "Summer Sports Vacations". Their audiences react differently to
   Beach content, and averaging across both yields "a grey blend of *every
   category works the same*".

   **Decided: that population is everyone who has CONSENTED to the brand** —
   not everyone the brand has mailed, which is a history rather than an
   audience.

   Three consequences:
   - **Point 8 needs no amendment and `signal_contributions` needs no brand
     column.** ADR-164 §9's three objections (join path on every read, nullable
     `event_id`, ADR-132 pruning) all evaporate, because nothing derives a
     brand per contribution. The expensive answer was avoided by asking a
     better question.
   - **It is blocked on brand step 2.** "Consented to this brand" is inexpressible
     until consent carries a brand, so this ships *with* the consent work.
   - **Do not half-ship it.** `/ui/graph` aggregates a content count and a
     selection count, both brand-scopeable today via `content_records`, plus
     the signal impact, which is not. Scoping the first two now would put two
     populations side by side on one page — the same grey blend, harder to
     spot. They ship together.

   **Parked, named, out of scope:** analysing how subscribers who *unsubscribed*
   behaved, and whether particular categories drove them away. The user placed
   it in a future analytics/reporting scope not yet discussed.

5. **Brand step 2 — consent by brand. The phase that makes the boundary
   real, and it needs an ADR-163 addendum FIRST** (that record is Accepted and
   defines the consent cell). Consent becomes
   `(recipient, brand, channel, purpose)`; the latest-wins index changes with
   it. Touches the compliance path: `app/recipients/consent.py`, both audience
   gates, `app/delivery/exclusion.py`, `app/decision/service.py`, the CRM sync
   and the provider webhook. **Opt-out defaults to the sending brand**, with a
   visible "all brands" option a company can switch off. Decided 2026-09-15.
   Consequence to tell an adopter: a newly created brand starts with **zero
   reachable recipients** until consent is captured for it.

6. **Brand step 3 — duplication.** "Duplicate campaign to brand X", content
   copied with it. **An escape hatch, not the mechanism** — item 4 rejected
   duplicate-and-sync as the general answer to brand scoping, so this covers
   campaigns and content only, where the alternative is rebuilding by hand. This is what makes single-brand content tolerable: sharing
   was rejected because the same copy under two brands needs different URLs and
   domains. No duplication machinery exists;
   `create_role(copy_from_role_id=…)` copies one flat list and is the only
   precedent. **Accepted cost:** copies diverge — a typo fixed in brand 1 stays
   wrong in brand 2.

7. **ADR-154 — ready to implement; plan it.** Nothing exists today: no erasure
   route, no service function, no script. Its own Consequences admit snapshot
   handling is blocked behind the undecided storage strategy, so that Needs-ADR
   item gates part of it.
8. **ADR-153 — the audit log, now accepted and entirely unbuilt.** There is no
   audit table anywhere in `backend/`; the only actor field in the system is
   the free-text `ContentVersionDB.created_by`. **The user gave a second reason
   for wanting it that is not in the ADR:** concurrent editing — stopping two
   users working the same asset, possibly with a *"user 1 is working on this —
   overwrite?"* prompt. That is a **contention model**, which is already a
   separate Needs-ADR item (*"Concurrent actors: a contention model, not just
   row locks"*), and it is not what ADR-153 decides. Keep them apart: the audit
   log records who did what; preventing a collision is a different mechanism.

9. **Gate 3 — inbound machine authentication (P0).** Designed and fully
   specified, but ADR-166 is deliberately still Proposed, so this is not ready
   to build. The interview **happened
   on 2026-09-13** and **[[ADR-166 — Inbound Machine Callers Are Authenticated
   Principals]] is written** — status **Proposed**, awaiting your acceptance.
   Written by `adr-author`; wikilinks verified (69 of 70 mentions, the one
   exception a protected verbatim quotation), every target resolves.

   **Before implementation can start, four things are unspecified** — the ADR
   flags each as such rather than inventing an answer:

   - ~~The concrete key list for the vocabulary split.~~ **SETTLED 2026-09-13 —
     9 keys become 16**, recorded as an amendment to ADR-150 point 5. Working it
     out found something larger than the split: `WRITE_POLICY` maps only `/ui/…`
     prefixes, so **four of the twelve JSON routers had no key naming what they
     do** — recipients, overrides, insight, provider. Splitting was the smaller
     half; the vocabulary stopping at the UI boundary was the larger.
     Unchanged (7): `view`, `campaigns.manage`, `content.manage`, `ai.run`,
     `settings.manage`, `users.manage`, `credentials.manage`. Split (2→4):
     `audiences.manage` + **`audiences.pin`**, `sends.execute` + **`sends.plan`**.
     New (5): **`recipients.manage`**, **`recipients.consent`**,
     **`insight.write`**, **`overrides.manage`**, **`integrations.manage`**.
     Consent is a separate key from recipient CRUD deliberately; the locked
     `POST /provider/events` is gated by `insight.write` rather than its own key.
     **Still a specification, not a state:** a key names a code path, so each one
     is real only once its guard exists, and `WRITE_POLICY` must gain JSON-route
     entries in the same change or every API write fails closed.
   - **What "unattended" is scoped to.** Decided for real sends; consent writes,
     bulk recipient reads and credential changes are unstated.
   - **Rotation overlap** — may an integration hold two live credentials at
     once? Without it every rotation is a small outage for the caller; with it,
     revocation semantics need stating.
   - **Brand selection on inbound calls.** A human picks the brand from
     navigation context (ADR-150 §2); a machine has none. Sits directly under
     decision 7's derivation.

   **Also pending:** the **ADR-150 amendment** for the finer permission
   vocabulary. `adr-author` supplied the text and deliberately did not apply it
   — ADR-150 is Proposed, so it is a direct edit to point 5 or a dated addendum,
   and that is your call. The text is in the agent's report.

   **And check before building decision 5:** its safe default ("machine sends
   land in ADR-142's approval surface") needs that approval surface to exist. If
   it does not yet, the default has nothing to fall back to.

   The six decisions, for reference:

   1. **A machine caller is a principal inside ADR-150**, not a parallel
      authorization system — it holds permission rows in the same table a user
      does, brand-scoped, and resolves to an ADR-153 actor. A company wanting a
      cleaner separation may build one; the reference build does not. Issued as
      **key + secret pairs** so systems are distinguishable.
   2. **The permission vocabulary gets finer keys, for humans and machines
      alike.** The nine in `app/auth/permissions.py` are too coarse for this
      feature's own example — pinning a recipient lives under
      `audiences.manage`, which also deletes groups. An **amendment to ADR-150**
      (still Proposed), not a supersession.
   3. **An integration owns its credentials**, and the *integration* is the
      durable audit actor — so history stays continuous across a rotation and
      still reads "n8n triggered this send" a year later.
   4. **`integrations.manage` gates issuance, any holder may hold it.** A
      credential is **independent of its creator**: deactivating a user does
      *not* revoke keys they issued, because the key belongs to the integration.
      **Known gap, accepted deliberately:** ADR-151 pt.5 calls deactivation "the
      whole offboarding control" and this is a hole in that story.
   5. **Unattended real sends are configurable per integration, defaulting to
      requiring approval** — a machine send lands in ADR-142's approval surface
      unless that integration is deliberately flagged otherwise.
   6. **`POST /provider/events` is kept and locked**, not removed. Two inbound
      mechanisms coexist on purpose: platform-issued credentials for systems the
      adopter controls, provider signature verification for providers, who
      cannot hold a credential the platform issued. ADR-164 pt.7 plans the
      conversion callback on exactly that endpoint's shape.

   **Scale of the hole being closed:** 69 unguarded JSON routes, 36 of them
   state-changing — including `POST /delivery/send-instances/{id}/send` (fires
   real mail), `POST /recipients/{external_id}/consent` (writes the compliance
   record), `GET /recipients/` (dumps PII) and `POST /insight/events`.
10. **Gate 1 — the positioning statement.** Still the named blocker on public
   beta, and unchanged by any of this: rule 2 was tested on 2026-09-12 and
   held, so omni-channel stays out of the headline claim until a second channel
   actually sends.

## Known-stale or wrong claims to distrust

The 2026-09-12 sequencer pass found the docs assert things that are not true.
Corrected already, but the lesson stands — **verify before trusting a status
claim in this repo**:

- The roadmap's ✅ marks are **asserted, not audited**. One item the backlog
  listed as open (the category picker) was already built; two Done items are
  reversed by the new ADRs.
- `requirements.txt` said `httpx2` while all code imports `httpx`. Fixed —
  note `httpx2` is a real package (Pydantic's successor), so `pip install`
  *succeeded* and failed later at import.
- The claim that `database.py`'s engine-at-import made four test modules
  uncollectable was **wrong** — I put it in LAUNCH-GATES.md on trust and had to
  correct it. The tests collect fine; three of them need a live seeded Postgres,
  which is the isolated-test-DB design item.
- The 11-broken-wikilink count is disputed; re-run `adr-drift` rather than
  citing either number.

## Positioning gate

Public beta is blocked on the positioning statement, not on features.
**Tested 2026-09-12 and it held:** omni-channel being designed-and-accepted does
**not** clear POSITIONING.md's rule 2 ("no claim that cannot be demonstrated in
the repo today"), because only email is built. The channel-neutral sharpening
stays out of the headline claim until a second channel actually sends.

One P0 defect still blocks public exposure — gate 3. See `docs/business/LAUNCH-GATES.md`.

*Git remote: `github.com/drmsGit/newsletter-reference-implementation`.*
