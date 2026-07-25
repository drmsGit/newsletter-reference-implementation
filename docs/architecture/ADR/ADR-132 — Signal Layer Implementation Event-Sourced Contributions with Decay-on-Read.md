---
type: adr
status: accepted
topic:
  - architecture
  - insight
  - signals
  - decision
created: 2026-07-15
modified: 2026-07-15
depends_on:
  - "[[ADR-110 — Insight Layer Transforms Events Into Signals]]"
  - "[[ADR-111 — Decision Layer Consumes Signals, Not Raw Events]]"
  - "[[ADR-112 — Signals Use Time-Based Decay]]"
  - "[[ADR-113 — Separate Operational and Historical Signals]]"
  - "[[ADR-054 — Use Internal Recipient Identifiers]]"
  - "[[ADR-126 — Maintain Local Recipient Projection]]"
enables:
  - "[[ADR-085 — Decision Resolution Must Be Explainable]]"
---

## Status
Accepted

## Context

ADR-110–113 mandate a Signal Layer (events → reusable signals, time-based decay,
operational/historical separation) but deliberately leave the model and storage
open. The current Insight implementation satisfies none of it:

- `apply_event_to_preferences` handles only `"click"`, and **adds** a delta to a
  mutable running-total `RecipientPreferenceDB.score`. The score only ever grows
  — a click from a year ago counts the same as yesterday's (no decay, ADR-112).
- The decision layer reads that raw mutable number, not a "signal" (ADR-110/111).
- There is no operational/historical distinction (ADR-113).

Two realities shape the design:

**Engagement data is dominated by clicks.** Research into how provider-agnostic
sending actually captures engagement: the sender does **not** rewrite or hash
links — an ESP, when click tracking is enabled, rewrites links and hosts the
open pixel + click redirect on its own tracking domain (optionally a customer-
owned CNAME vanity domain), and emits open/click events via webhook. But Apple
Mail Privacy Protection pre-fetches the open pixel for ~50%+ of opens regardless
of real reads, and security bots inflate opens and clicks. **Opens are
statistically unreliable; clicks (bot-filtered) are the north star.** Conversions
would be the most reliable of all (server-side, MPP/bot-proof) but their sourcing
is entirely company-specific (tracking provider / DWH / CRM), so they are an
extension point here, not a built integration.

**This system is operational, not an analytical warehouse.** Unbounded historical
engagement storage doesn't belong here (same spirit as ADR-126: don't become a
customer-data repository). Most adopters run a DWH / data lake; long-term history
and AI training belong there.

## Decision

**1. Event-sourced signals, decay computed on read.**
An append-only `SignalContributionDB` (evolving `PreferenceUpdateLogDB`) is the
source of truth. Each row is one engagement's contribution:
`(recipient_id, category_id, contribution_type, base_weight, occurred_at,
source_event_id, source)`. A signal is a decay-weighted aggregation over it:

```
signal(recipient, category) = Σ base_weight × 0.5 ^ (age / half_life)
```

No mutable per-signal score is stored as source of truth. This keeps the layer
fully auditable (ADR-085): every contribution and its decayed weight is
inspectable, the decay constant can change without losing history, and a signal
is re-derivable at any point in time. Compute-on-read is sufficient at this
project's scale; a materialized cache is a later optimization, never the truth.

**2. One worked signal type: recipient–category affinity.**
It is what the decision layer consumes today (`recipient_top_score`). Storage is
shaped so content / composition / audience signals (ADR-110) slot in later
behind the same log + decay mechanism — architecture plus one example.

**3. Contribution types and default weights (tunable — future config layer).**

| Contribution | Base weight | Half-life | Rationale |
|---|---|---|---|
| `manual` (declared) | heavy | long (~180d) | on-purpose; dominates, then behavior wins |
| `click` | heavy | operational (~45d) | reliable behavioral signal, bot-filtered |
| `open` | low, or disabled | operational | MPP/bot noise — weak signal |
| `unsubscribe` / complaint | strong negative | slow | genuine disinterest |
| `conversion` | *extension point* | operational | most reliable, but company-specific sourcing |

Manually-declared preferences are contributions like any other, just heavy and
long-lived. There is **no permanent baseline**: a manual preference decays (very
slowly) and, if never reinforced by behavior, fades to negligible — so behavior
wins over stale stated interest. Manual preferences are the recipient's lever to
"break the cycle" and push a new direction; a floor would defeat that. (A floor
is a tunable option if a deployment wants one.)

**4. Operational lives here; historical lives in the DWH (ADR-113 made concrete).**
- **Operational signal** = computed locally over a **bounded retention window**
  (a few operational half-lives; older contributions are negligible for scoring
  anyway). This drives audience resolution and sends.
- **Historical signal** = the adopter's DWH / data lake, fed by an **export
  boundary** (contributions are exportable). Long-term learning and AI training
  (Phase 3D) read from there, not from local tables. This bounds local storage
  and keeps the operational system lean. The local retention/prune policy is
  governed by the general data-lifecycle policy (separate ADR).

**5. Engagement source = ESP webhooks, normalized by the inbound adapter.**
The provider adapter (ADR-100/101, backlog H1) normalizes each ESP's open/click
events into canonical contributions and applies bot filtering (drop MPP opens,
scanner clicks) before they enter the log. Because the data is normalized and
owned locally, ESP lock-in is not a concern; an adopter who already tracks on
their own domain ignores the webhook and feeds the same canonical shape from
their own source. Self-hosted tracking is a supported adaptation point, not a
built component.

**6. Retire the mutable running-total.**
`RecipientPreferenceDB` (the ever-growing score) is dropped. Manual/seed
preferences become `manual` contributions. `recipient_top_score` and audience
`find_by_criteria` read `get_operational_signal(recipient, category)` instead of
a stored score, keeping resolution explainable.

## Consequences

### Positive
- Decay (ADR-112), signal abstraction (ADR-110/111), and operational/historical
  separation (ADR-113) are all satisfied, with one auditable mechanism.
- Fully explainable (ADR-085): every signal decomposes into dated, weighted
  contributions.
- Bounded local storage; historical/analytical load offloaded to the DWH.
- Enables the deferred category archive-vs-decay lifecycle (an archived category
  simply stops adding contributions; its influence decays naturally).
- The reliability-weighted model (clicks over opens, unsubscribe negative)
  reflects how email engagement actually behaves post-MPP.

### Negative
- Compute-on-read cost for signals (negligible at this scale; cache later if
  needed).
- A retention/prune policy and a DWH export boundary must be defined and run.
- Conversions — the most reliable signal — are not captured out of the box; the
  adopter must wire their own source.
- Decay constants and weights are judgement calls needing real data to tune.

## Notes

Explicitly out of scope for the first build (companion items, tracked in
`docs/backlog.md`):
- **Anti-bubble / exploration** — "occasionally show a different category even
  when the engine is confident" is a *decision-layer* explore-vs-exploit
  behavior fed by signals, not signal storage.
- **Content / composition / audience signals** — later, same mechanism.
- **Bot-filter rules + per-provider open/click normalization** — live in the
  inbound provider adapter (H1); the signal layer consumes clean canonical
  events.
- **Conversion sourcing**, **DWH export/retention policy**, **materialized
  operational cache** — future, provider/deployment-specific.

## Related ADRs

### Depends On
- [[ADR-110 — Insight Layer Transforms Events Into Signals]]
- [[ADR-111 — Decision Layer Consumes Signals, Not Raw Events]]
- [[ADR-112 — Signals Use Time-Based Decay]]
- [[ADR-113 — Separate Operational and Historical Signals]]
- [[ADR-054 — Use Internal Recipient Identifiers]]
- [[ADR-126 — Maintain Local Recipient Projection]]

### Enables
- [[ADR-085 — Decision Resolution Must Be Explainable]]
