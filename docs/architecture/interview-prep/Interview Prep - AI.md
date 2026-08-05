---
type: interview-prep
status: open
topic:
  - architecture
  - review
  - ai
created: 2026-08-02
modified: 2026-08-02
source:
  - interview-prep-2026-08-02
depends_on:
  - "[[ADR-140 — AI Capability Layer]]"
  - "[[ADR-141 — In-App Assistive AI Actions]]"
  - "[[ADR-144 — AI Data and Model Governance]]"
  - "[[ADR-100 — Provider Layer as Send and Feedback Adapter]]"
  - "[[ADR-101 — Provider Capabilities Are Explicit]]"
---

# Interview Prep — AI Layer

Generated 2026-08-02 via `/interview-prep`, for the `backend/app/ai/` feature: the `AIProvider` contract, the real Claude adapter, the token-based pre-call spend gate, cost accounting, prompt versioning, and the first Mode-A task (subject/preheader). Focus: why-this-over-the-alternative, edge cases / failure modes, performance / concurrency. Companion business-classification in `docs/business-interview.md` (same date). Check off each item once discussed, and record any decision in **Resolution**.

## AI Layer

- [ ] **Q1.** Why enforce the spend cap as a *pre-call* token gate instead of tracking spend after each call and stopping when you cross the line?
    **A:** A post-hoc ledger only tells you you've *already* overspent — the overage is the run that crossed the line. The design makes the worst case knowable before spending: `count_input_tokens() + max_output_tokens` (`service.py:187`), refused if it doesn't fit the remaining cap. A stop always lands *between* runs, never mid-run, and nothing is spent on work that can't finish (`service.py:1-14`). The cost is a second network round-trip (the count call) before every generate — deliberately paid because the alternative is a cap that only enforces after the money's gone.

- [ ] **Q2.** `count_input_tokens` is a required abstract method, not optional. Why bake it into the contract rather than treat it as a nice-to-have?
    **A:** The cap is only real if every model behind the contract can be gated. An adapter that can't count can't compute a worst case, so it can't participate in the pre-call gate — making it optional would mean some models silently bypass the cap (`base.py:57-71`). This is the ADR-101 "capabilities are explicit" posture: the gate is a property of the contract, not of whichever vendor happens to support it.

- [ ] **Q3.** When token counting fails, you refuse the run rather than fall back to a word-count estimate. Isn't refusing worse UX than proceeding on an approximation?
    **A:** An estimate-based gate isn't a gate — it lets a run start against a number nobody verified (`base.py:13-21`). `TokenCountUnavailable` is raised and the run is recorded `blocked` with "Nothing was spent" (`service.py:171-185`). The failure mode this protects against: a network blip on the cheap count endpoint quietly disabling the cap on the expensive generate endpoint. Refusing is both the conservative branch and the honest one — and it's auditable, so the manager sees *why*.

- [ ] **Q4.** The biggest failure mode: `tokens_used()` reads the ledger, the gate checks it, then `generate()` runs — but two concurrent runs can both pass the gate. Is the cap actually enforced under concurrency?
    **A:** No — a genuine TOCTOU gap. `tokens_used()` sums the table (`service.py:89-104`), the gate compares against it (`service.py:193`), but there's no lock or reservation between the check and the `_record()` of the resulting run. Two requests reading the same "remaining" both proceed, and the cap can be overshot by up to one concurrent batch's worst case. Unlike `send_send_instance` (which uses `with_for_update()` on the status transition), there's no equivalent serialization here. Tolerable at single-operator/few-runs scale; the first thing that breaks if AI runs fan out. Same systemic concurrency gap already flagged in the backlog for override/double-send races.

- [ ] **Q5.** `tokens_used()` re-sums the entire `ai_runs` table on every single run. Performance concern?
    **A:** Yes, latent. It's a full-table scan filtered in Python (`is_billable` isn't a simple WHERE since "free" is a provider set), run once per task (`service.py:97-104`). Negligible now, O(all runs ever) as the ledger grows — and it's on the hot path *before* every call, so every AI run gets slower as history accumulates. Deferrable fixes: a running counter, a windowed sum, or a SQL `SUM` with a provider filter.

- [ ] **Q6.** Billability defaults to "billable" but cost defaults to "unknown/zero-contribution." Those are opposite defaults — why not make them consistent?
    **A:** They answer opposite-risk questions (`pricing.py:9-19`). For the *cap*, the safe error is to over-count: a paid adapter someone forgot to price still burns budget (`is_billable` returns True for anything not named free), so the gate degrades conservative, never permissive. For the *money display*, the safe error is to *not* invent a number: an unpriced model contributes nothing to the USD total and is surfaced as `unpriced_runs` (`service.py:107-133`), because silently pricing it at zero would show a manager a total wrong in the direction that matters. Same-direction defaults would get one of the two wrong.

- [ ] **Q7.** Extended thinking is off by default. Preference or correctness?
    **A:** Correctness-of-cost. `max_tokens` is a ceiling on thinking *plus* reply, so on a task declaring a 400-token output ceiling the model could burn the whole budget reasoning and return a truncated answer (`claude.py:89-96`). With thinking off, the ceiling means what the task intended and the worst-case arithmetic the gate relies on stays tight. A task that genuinely needs reasoning turns it on *and* raises its own ceiling to match — the two must move together.

- [ ] **Q8.** A model refusal comes back as HTTP 200 with empty content, and `max_tokens` truncation comes back as apparent success. How are these kept from looking like normal output?
    **A:** Both handled off `stop_reason`, not status code. A `refusal` at HTTP 200 is mapped to `success=False` with a reason (`claude.py:175-192`) — otherwise the UI shows an empty box and reads it as a formatting bug. A `max_tokens` stop is returned to the caller as a *partial* (ADR-144: showing isn't committing) but the audit row records "output hit its ceiling and is truncated" (`service.py:223-227`). And `parse_options` is deliberately tolerant — a model that drifts from the requested layout degrades to fewer options, never an exception in the request path (`subject_preheader.py:74-98`).

## Cross-cutting note

The standout finding is **Q4 — the cap's check-then-act race**, the one place the "the cap is a real gate" claim has a hole under concurrency. It shares a root cause with the existing systemic concurrency-guard item in `docs/backlog.md` (override outcome-delta race, delivery double-send race).
