# HANDOFF — Newsletter Blueprint

**Last updated:** 2026-09-13 · **Branch:** `main`, clean, everything pushed

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
3. docs/playbook-strategy.md §5 (Decision Log — read the 2026-09-12 entry),
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
  addenda, backlog-sequencer for queue work, code-slimmer, adr-drift,
  positioning-critic, assumption-scanner. They are NOT selectable as
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

### Omni-channel — designed and accepted; consent half part-built

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

* **Phase A — consent.** Schema and service layer **done and pushed**. Consent
  is append-only events keyed `(recipient, channel, purpose)`, latest wins.
  All three gates read events. `ConsentDenied` (a `ValueError` subclass)
  replaces the bare `ValueError` at the decisioning gate. Drift is
  **directional** — `platform_ahead` means relay outward, `crm_ahead` means
  re-run the sync.
* **Phase B — email → addressability.** Not started. ~22 mostly-display sites
  (templates, the audience-group JS doing `${r.email}`, the send-test picker).

### ⚠️ The dev database is in the EXPANDED state

`scripts/migrate_0001a_consent_expand.sql` **has been applied** to the local
dev database. `consent_events` and `recipient_addresses` exist and are
populated (41 recipients → 41 events, 41 addresses), and `delivery_executions`
has `channel` + `purpose`.

`recipients.consent_status` **still exists but is vestigial** — nothing reads
it for a decision. `scripts/migrate_0001b_consent_contract.sql` drops it and
**has not been run**. It refuses unless every recipient already has a consent
event and an address, so it is safe to attempt.

Both scripts are idempotent and were verified against a restored copy of the
dev database: expand→contract clean, both re-runnable, contract-without-expand
refused, and a recipient inserted between the two runs correctly refused rather
than silently losing its consent state.

There is **no Alembic and no migration runner**. Decided 2026-09-12: schema
change is hand-written, numbered, idempotent DDL in `backend/scripts/`.
`Base.metadata.create_all()` only ever creates missing tables.

### Tests

156 green. **Run from `backend/`** — `test_auth_policy.py` opens a file by
relative path and fails from the repo root (pre-existing, not a regression).

`tests/test_consent_gates.py` is new and load-bearing: before it, the suite
stayed green whether the consent gates were intact or deleted. Every test in it
was mutation-verified — removing a gate fails only that gate's tests.

---

## Open queue

1. **Finish Phase A** (the current thread):
   - `app/providers/service.py:186-207` — the bounce/complaint webhook calls
     `suppress_recipient` without `channel`/`purpose`; read both off the
     `DeliveryExecutionDB` row, which now carries them.
   - `app/delivery/service.py:404` — the send address should come from
     addressability (`resolve_email`), not `recipient.email`.
   - Move the email dedupe (`app/audience/service.py:171-182`) into the
     addressability stage with a recorded exclusion reason.
   - Seed scripts: `reset_all_data.sql`, `seed_demo_data.py`, and
     **`reset_poc_data.sql`, which is already broken** — it still references
     `recipient_preferences`, dropped in the ADR-132 signal migration.
   - Then run `migrate_0001b_consent_contract.sql`.
2. **The P0 consent fix** (Gate 2), in ADR-163 §8's ordered-stack shape:
   addressability → consent → suppression → frequency, **recording why** each
   recipient was excluded. The P1 send-status fix is in the same function
   (`app/delivery/service.py:273-433`) — do them together, it is one context.
3. **Cowork timeline pass** — turn the sequencer's ranked graph into
   weeks/milestones. The graph is in `.claude/agent-memory/backlog-sequencer/`.
4. **Phase B** (email → addressability) — possibly deferrable to the React
   frontend work, since those display sites are what that rewrite replaces.
5. *(Optional)* the `content_card` dropdown fix from the code-slimmer report.
   The Settings weight-editor no-op is also still open and is now rising in
   cost — ADR-164 §10 extends that same settings grid with channel weights.

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

Two P0 defects also block public exposure — see `docs/business/LAUNCH-GATES.md`.

*Git remote: `github.com/drmsGit/newsletter-reference-implementation`.*
