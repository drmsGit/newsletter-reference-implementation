---
type: code-module
module: decision
topic:
  - architecture
  - decision
created: 2026-07-27
modified: 2026-07-27
---

# decision

> Part of [[MOC - System Overview]]. Architecture rationale: [[MOC - Decision Architecture]].

## Purpose

The decision module owns **the personalization engine: turning a decision slot
into an actual content pick, per recipient, via a pluggable strategy**. A
strategy is a `.py` file dropped into `strategies/` — the registry auto-discovers
it, no wiring. This is the "BI can add a decision strategy without touching the
core" pillar. The module resolves a slot, records the result as a
`DecisionResolutionDB` (owned by [[campaigns]]), and enforces the consent gate a
second time. It does **not** define slots (that's [[campaigns]]) or render
anything (that's [[rendering]]).

## Key files
- `backend/app/decision/service.py` — `execute_decision_slot` (the one public entry point)
- `backend/app/decision/strategies/registry.py` — auto-discovery + hot-reload of strategy files
- `backend/app/decision/strategies/base.py` — the `DecisionStrategy` contract, `StrategyResult`, `StrategyMeta`, `ConfigField`, `normalize_slot_config`
- `backend/app/decision/strategies/top_score.py`, `recipient_top_score.py` — the two shipped strategies
- `backend/app/decision/router.py` — the `/decision/*` JSON endpoints

## Public surface
**Service / registry functions:**
- `execute_decision_slot(db, slot_id, recipient_id=None)` — resolve one slot; returns a `DecisionResolution` or `None`. **The entry point [[delivery]] and [[rendering]] rely on.**
- `get_strategy(name)` / `list_strategies()` (`strategies/registry.py`) — the live strategy registry
- `normalize_slot_config(meta, candidate_filter, strategy_config)` (`strategies/base.py`) — validate a slot's JSON config against a strategy's declared shape (called from [[campaigns]])

**Routes** (`/decision`, tag `decision`): 2 routes — list strategies (`GET /decision/strategies`), execute a slot (`POST /decision/slots/{id}/execute`).

## Data model
**None of its own.** Reads `decision_slots`, writes `decision_resolutions` — both owned by [[campaigns]]. Strategies are **code plugins**, not DB rows.

## Depends on →
- [[campaigns]] — reads `DecisionSlotDB`, writes `DecisionResolutionDB`
- [[content]] — strategies rank content records + their category assignments
- [[recipients]] — the consent gate; personalized strategies key off `recipients.id`
- [[insight]] — `recipient_top_score` ranks by the recipient's live per-category **signals**

## Depended on by →
- [[campaigns]] — slot-config normalization
- [[delivery]] — resolves each recipient's content at send time
- [[frontend]] — the decision-slot editor + strategy picker

## Invariants & decisions
- **Strategies never raise for missing content — they return `None`** and the slot renders hidden ([[ADR-086 — Decision Slots Fail Gracefully]]).
- **Convention-based registry.** Drop a `.py` in `strategies/`; the registry discovers it by subclassing `DecisionStrategy` and hot-reloads on file change. A broken strategy file is logged and skipped, not fatal.
- **AI ranks within a governed candidate set, never publishes** — human-governed taxonomy comes first ([[ADR-080 — Human-governed Taxonomy Before AI Selection]], [[ADR-081 — AI Ranks Within Governed Candidate Sets]], [[ADR-082 — AI May Recommend but Not Publish]]). No AI strategy ships yet; the seam is the strategy contract.
- **Decision consumes signals, not raw events** ([[ADR-111 — Decision Layer Consumes Signals, Not Raw Events]]) — `recipient_top_score` reads [[insight]] signals.
- **Resolution history is bounded.** A non-personalized slot keeps one row (updated in place); a personalized slot only writes a new row when the pick actually changes — "no new signal, keep the last recommendation."
- **Consent gate is belt-and-suspenders** — refuses per-recipient decisioning for a non-consenting recipient even though [[audience]] already excluded them.

## ⚠️ Change-impact — if you touch this, also check…
- **The `DecisionStrategy.execute` signature or `StrategyResult` shape** → every strategy file implements it, and [[delivery]] / [[rendering]] consume the resolution it produces.
- **`execute_decision_slot`'s return contract** (`Resolution | None`) → [[delivery]]'s send loop and [[rendering]]'s resolve path both branch on `None`.
- **`ConfigField` / `StrategyMeta`** → [[campaigns]] `update_decision_slot` validates against them; changing the declared shape re-validates existing slots.
- **Adding a strategy** → just add a file; do **not** add a config table or touch the core (that's the whole point). If it needs AI, respect [[ADR-082 — AI May Recommend but Not Publish]].
