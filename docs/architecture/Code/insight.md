---
type: code-module
module: insight
topic:
  - architecture
  - insight
  - signals
created: 2026-07-27
modified: 2026-07-27
---

# insight

> Part of [[MOC - System Overview]]. Architecture rationale: [[MOC - Insight Architecture]], [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]].

## Purpose

The insight module owns **the learning loop: turning engagement into signals that
shape future decisions**. It records normalized engagement events, and turns
content-tied ones (clicks, opens) into **per-category signal contributions** —
append-only, weighted by reliability, and **decayed on read** so recent behavior
matters more. A "signal" is never a stored running total; it's a decay-weighted
sum computed from the contribution log at read time. This closes the loop back
into [[decision]] (which ranks by these signals) and [[audience]] (which targets
by them).

## Key files
- `backend/app/insight/signals.py` — the signal math: weights, half-lives, decay, `get_operational_signal` and friends
- `backend/app/insight/service.py` — engagement events + `apply_event_to_signals`
- `backend/app/insight/db_models.py` — `EngagementEventDB`
- `backend/app/insight/router.py` — the `/insight/*` endpoints
- **Note:** the contribution *table* (`SignalContributionDB`) is defined in [[recipients]]; the *logic* is here.

## Public surface
**Service / signal functions:**
- `apply_event_to_signals(db, event_id)` — turn a click/open into per-category contributions (called by [[providers]] on webhook)
- `create_engagement_event(...)` / `list_events_for_delivery_execution(...)`
- `record_contribution(...)` — append one contribution (used for manual/declared prefs too)
- `get_operational_signal(db, recipient, category)` — the current decayed signal for one pair
- `operational_signals_for_recipient(...)` / `operational_signals_for_category(...)` — the bulk reads [[decision]] and [[audience]] use
- `CONTRIBUTION_WEIGHTS` / `HALF_LIFE_DAYS` — the POC defaults (retunable via [[settings]])

**Routes** (`/insight`, tag `insight`): 3 routes — post an engagement event, list events for a delivery execution, apply-signals for an event.

## Data model
- **`engagement_events`** (`EngagementEventDB`, owned here) — one normalized event: `delivery_execution_id`, `event_type`, `provider`, `provider_event_id`, `event_data`. Unique `(provider, provider_event_id)` as a dedup safety net.
- **`signal_contributions`** (`SignalContributionDB`) — **defined in [[recipients]]**, read/written here. Append-only: `(recipient, category, contribution_type, base_weight, occurred_at, event_id, source)`.

## Depends on →
- [[content]] — reads `content_category_assignments` to spread a click across the content's categories (scaled by the 0–10 score)
- [[delivery]] — an engagement event FKs a `DeliveryExecutionDB`; the recipient is read from it
- [[recipients]] — writes/reads `SignalContributionDB`
- [[settings]] — pulls configured weights/half-lives (with the code defaults as fallback)

## Depended on by →
- [[decision]] — `recipient_top_score` ranks by these signals ([[ADR-111 — Decision Layer Consumes Signals, Not Raw Events]])
- [[audience]] — criteria min-score reads per-category signals
- [[recipients]] — the recipient detail view + `recipient_top_score`
- [[settings]] — imports the default weights/half-lives it overrides
- [[providers]] / [[frontend]] — webhook applies signals; UI shows the category graph

## Invariants & decisions
- **Events → signals, not a mutable score** ([[ADR-110 — Insight Layer Transforms Events Into Signals]]). The old `RecipientPreferenceDB` running-total was **dropped**.
- **Decay-on-read** ([[ADR-112 — Signals Use Time-Based Decay]], [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]) — a signal is computed from the log each read; exponential half-life per type.
- **Reliability-weighted:** click = the reliable behavioral signal (half-life 45d); **open weight = 0 by default** (Apple MPP makes opens noise); unsubscribe = strong negative; **manual/declared preference = heavy but slow-decaying (180d), no permanent floor** so behavior eventually wins over stale stated interest.
- **Operational-local, historical-in-DWH** ([[ADR-113 — Separate Operational and Historical Signals]]) — this stores a bounded operational window; long-term history/AI-training belongs in the adopter's DWH (export boundary, backlog).
- **Conversions are a pluggable extension** — sourcing is company-specific ([[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read|ADR-132]]), not built.
- **Same event applied twice moves the signal once** — contribution dedup is per `(recipient, category, event_id)`, so two *different* clicks each count.

## ⚠️ Change-impact — if you touch this, also check…
- **`SignalContributionDB`'s columns** → the table lives in [[recipients]]; change both together. `signals.py` reads every field to compute decay.
- **`CONTRIBUTION_WEIGHTS` / `HALF_LIFE_DAYS`** → [[settings]] overrides these; [[decision]] and [[audience]] outputs shift when they change. Open weight being 0 is deliberate.
- **`apply_event_to_signals`'s content-tied gate** → only click/open; wiring bounce/complaint here (instead of the consent path) would be wrong.
- **The decay formula** → drives every downstream ranking; it's a documented ADR decision, not a casual tweak.
