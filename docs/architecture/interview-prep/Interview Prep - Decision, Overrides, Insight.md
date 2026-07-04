---
type: interview-prep
status: open
topic:
  - architecture
  - review
  - baseline
created: 2026-07-04
modified: 2026-07-04
source:
  - claude-baseline-review-2026-07-04
depends_on:
  - "[[ADR-040 — Introduce Override Layer]]"
  - "[[ADR-041 — Override Precedence]]"
  - "[[ADR-079 — Dynamic Resolution Outside Builder]]"
  - "[[ADR-080 — Human-governed Taxonomy Before AI Selection]]"
  - "[[ADR-081 — AI Ranks Within Governed Candidate Sets]]"
  - "[[ADR-082 — AI May Recommend but Not Publish]]"
  - "[[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]"
  - "[[ADR-085 — Decision Resolution Should Be Optionally Explainable]]"
  - "[[ADR-086 — Decision Slots Fail Gracefully]]"
  - "[[ADR-110 — Insight Layer Transforms Events Into Signals]]"
  - "[[ADR-111 — Decision Layer Consumes Signals, Not Raw Events]]"
  - "[[ADR-112 — Signals Use Time-Based Decay]]"
  - "[[ADR-113 — Separate Operational and Historical Signals]]"
---

# Interview Prep — Decision, Overrides, Insight

Baseline review generated 2026-07-04. Check off each item once discussed, and record the decision made in **Resolution**.

## Decision

- [ ] **Q1.** Why plugin auto-discovery via `pkgutil`/`importlib` instead of an explicit registration list?
    **A:** Zero-friction to add a strategy (drop a file in `strategies/`, per the "no Python changes" philosophy) — but `_discover()` runs once into a module-level `_REGISTRY` at import time, so a broken import in one strategy silently breaks the whole registry at startup. `backend/app/decision/registry.py:11-29`.
    **Resolution:**

- [ ] **Q2.** What happens if a strategy's `execute()` raises an exception that isn't `ValueError`?
    **A:** Unhandled — propagates as a 500. `service.py:30` calls `execute()` directly; `router.py:36` only catches `ValueError`. The plugin contract only documents "return None for missing content," not other exception types. Related: [[ADR-086 — Decision Slots Fail Gracefully]].
    **Resolution:**

- [ ] **Q3.** Why does `execute_decision_slot` own the DB write for `DecisionResolution` instead of letting strategies persist it themselves?
    **A:** Deliberate refactor (commit cf4f745) — centralizing avoids per-strategy duplication and guarantees every strategy gets [[ADR-085 — Decision Resolution Should Be Optionally Explainable]] storage for free. `service.py:9-43`.
    **Resolution:**

- [ ] **Q4.** `RecipientTopScoreStrategy` inner-joins `RecipientPreferenceDB` — what happens for a brand-new recipient with zero preferences?
    **A:** Empty candidate set → correctly returns `None` (slot hidden, per ADR-086) — but there's no cold-start default, so new recipients never get this strategy's recommendations until at least one engagement event has fired. `recipient_top_score.py:56-71`.
    **Resolution:**

- [ ] **Q5.** Both strategies re-run their full candidate query per slot per recipient with no caching — what's the cost at scale?
    **A:** N recipients × M slots query pairs. `top_score` (non-personalized) recomputes an identical result per recipient with no memoization, despite being recipient-independent — an obvious optimization target.
    **Resolution:**

- [ ] **Q6.** Why is a computed float score cast to `int` before persisting (`score=int(result.score)`), when `recipient_top_score` computes a weighted float combination?
    **A:** Silently truncates precision (`service.py:42`) — two candidates differing only in fractional score (12.4 vs 12.9) both round to 12, losing explainability/tie-breaking granularity relevant to ADR-085.
    **Resolution:**

- [ ] **Q7.** Ties in `recipient_top_score`'s `max()` selection have no tiebreaker at all — is resolution deterministic?
    **A:** No — resolves to whichever row Python's `max()` sees first in DB-returned order (non-deterministic without `ORDER BY`), undermining reproducibility/debuggability of resolutions. `recipient_top_score.py:73-76`.
    **Resolution:**

## Overrides

- [ ] **Q1.** The new `OverrideEventDB` table (commit 7790f53) — is it actually the [[ADR-040 — Introduce Override Layer]] override layer, or something else?
    **A:** It's an audit/analytics log comparing system vs. human-chosen content outcomes. Nothing in rendering/decision/snapshot code ever queries `OverrideEventDB` — zero references outside the `overrides/` module. The mechanism rendering actually reads is still the old `module_data.*_override` JSON blob (`rendering/service.py:92-93`). **Two independent, non-integrated override concepts coexist under the same name** — this is the single highest-priority architectural gap from this review.
    **Resolution:**

- [ ] **Q2.** What enforces that `system_content_record_id` and `override_content_record_id` actually differ or exist?
    **A:** Nothing — no validation in `OverrideEventCreate` (`models.py:6-14`); FK enforcement depends on whether `PRAGMA foreign_keys` is on for the dev DB. A bad ID silently creates an orphaned audit row.
    **Resolution:**

- [ ] **Q3.** `record_outcome_delta` replaces `outcome_delta` wholesale rather than merging — what happens with incrementally-arriving outcome data (e.g. open-rate today, click-rate a week later)?
    **A:** Second PATCH overwrites the first entirely instead of merging keys. `test_overrides.py:130-138` only checks non-`outcome_delta` fields survive — this specific merge case is untested and would currently fail. `service.py:32-39`.
    **Resolution:**

- [ ] **Q4.** Is there a race between concurrent PATCH calls to `/overrides/{id}/outcome`?
    **A:** Yes — read-modify-write with no optimistic locking or `SELECT ... FOR UPDATE`; two concurrent outcome-delta computations racing on the same override_id have last-write-wins semantics.
    **Resolution:**

- [ ] **Q5.** Given this is event-sourced/append-only, how would a "reset to original" (ADR-041's "until it is deleted or reset") ever be expressed?
    **A:** There's no DELETE endpoint and no explicit reversal event type; `override_type` is unconstrained free text (`"content" | "segment"` only documented in a comment, not an enum) rather than a validated set of values.
    **Resolution:**

## Insight

- [ ] **Q1.** Why does `apply_event_to_preferences` write straight to a mutable `RecipientPreferenceDB.score` instead of the Signal abstraction ADR-110–113 describe?
    **A:** Confirms the drift report — decay, recency-weighting, and operational/historical separation are structurally impossible without a schema change, not just a missing feature toggle. This is 3C on the roadmap (Signal layer design) — worth reading this alongside that planning work. Related: [[ADR-110 — Insight Layer Transforms Events Into Signals]], [[ADR-112 — Signals Use Time-Based Decay]], [[ADR-113 — Separate Operational and Historical Signals]].
    **Resolution:**

- [ ] **Q2.** Why is `EVENT_PREFERENCE_DELTAS` hardcoded to only `{"click": 5.0}`?
    **A:** Any other event type raises `ValueError` (→ 400) rather than being a no-op — a footgun for any caller iterating over all recorded events without knowing in advance which types are "preference-worthy." `service.py:12-14,83-86`.
    **Resolution:**

- [ ] **Q3.** The dedupe key `(recipient_id, category_id, reason=event_type, delivery_execution_id)` doesn't include `event_id` — can two distinct legitimate engagement events get collapsed?
    **A:** Yes — two different clicks (e.g. on two different links) within the same email/category/execution would have the second silently dropped as a "duplicate," even though they're distinct engagements. `service.py:137-150`.
    **Resolution:**

- [ ] **Q4.** What happens if `ContentCategoryAssignmentDB.score` is negative, zero, or exceeds the expected 0–10 range?
    **A:** No validation at write or read time. A negative score flips the delta's sign (decreasing preference on a click — backwards), and `new_score` has no ceiling — preference scores can grow unbounded, compounding into `RecipientTopScoreStrategy`'s weighted ranking. `service.py:135,170`.
    **Resolution:**

- [ ] **Q5.** Why look up the recipient via `delivery_execution.recipient_id` treated as `external_id` string-matched against `RecipientDB.external_id`, rather than a direct FK?
    **A:** Adds an extra failure mode (mismatched external_id → `ValueError`) at a schema seam between provider-facing and internal identity — this is the same `recipient_id` type inconsistency flagged in the Delivery/Recipients cluster. `service.py:105-118`.
    **Resolution:**

---
## Related
- [[MOC - Interview Prep Baseline]]
- [[MOC - Decision Architecture]]
- [[MOC - Insight Architecture]]
