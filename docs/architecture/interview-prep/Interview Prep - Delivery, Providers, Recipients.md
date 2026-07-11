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
  - "[[ADR-051 — Delivery Package Includes More Than HTML]]"
  - "[[ADR-054 — Use Internal Recipient Identifiers]]"
  - "[[ADR-101 — Provider Capabilities Are Explicit]]"
  - "[[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]"
  - "[[ADR-121 — Minimal Recipient Model]]"
  - "[[ADR-122 — Minimal Consent Model Required]]"
  - "[[ADR-126 — Maintain Local Recipient Projection]]"
  - "[[ADR-129 — Correlate Provider Events to Delivery Executions]]"
---

# Interview Prep — Delivery, Providers, Recipients

Baseline review generated 2026-07-04. Check off each item once discussed, and record the decision made in **Resolution**.

## Delivery

- [x] **Q1.** `DeliveryExecutionDB.recipient_id` is a bare `String(255)` populated with the recipient's `external_id` (e.g. `"r-001"`), with no FK to `recipients.id` — how does this square with [[ADR-054 — Use Internal Recipient Identifiers]]?
    **A:** Confirmed drift from ADR-054/126. No referential integrity is enforced; joins to `RecipientDB` require an `external_id` lookup. Also inconsistent with `decision`/`insight`, which use the internal integer PK — **the same recipient is addressed by two different ID types across modules.** `delivery/db_models.py:29`.
    **Resolution:** act/fix. Same finding as [[Interview Prep - Decision, Overrides, Insight]] → Insight Q5 — already logged to [[backlog]] (Bugs), no separate entry needed.

- [x] **Q2.** `send_send_instance` sends identical HTML from one variant-level snapshot to every recipient — where's the personalization [[ADR-051 — Delivery Package Includes More Than HTML]] calls for?
    **A:** Not implemented. `DeliveryProvider.send()` only takes `recipient_id, subject, html` — no campaignId/variantId/snapshotId/preheader/audience metadata, and `subject=send_instance.name` conflates an internal label with the actual subject line. `service.py:111-172`, `providers/base.py:14-19`.
    **Resolution:** act/fix, narrowed. Providers don't need campaignId/variantId/snapshotId at all — internal-only bookkeeping. Same variantId across recipients within one send is correct (personalization stays inside the variant via decision slots, ADR-083); it would only legitimately differ per recipient for true split-delivery/A/B, which is the separate Needs-ADR "shadow variant" item. Real gap: resolve per-recipient HTML instead of reusing one shared snapshot. Logged to [[backlog]] (Bugs).

- [x] **Q3.** No retry or per-recipient exception handling in the send loop — what happens if `provider.send()` raises mid-batch (e.g. execution 5 of 100)?
    **A:** The whole function aborts before the single end-of-loop `db.commit()` — so already-"sent" executions 1–4 roll back their DB status despite the emails having actually gone out. No idempotency check (skip already-`"sent"` executions) exists for a safe retry. `service.py:160-173`.
    **Resolution:** act/fix (partial). Stop-on-failure stays the safe default (provider-dependent whether skip-and-continue is even safe) — but completed executions before the stop must still get persisted, not silently lost. Safe-retry reconciliation against the provider's send log is fine to keep as an IT/ops issue for now. Logged to [[backlog]]: the commit-persistence gap as a Bug, and the "proactive reconciliation" idea as a parked future Feature.

- [x] **Q4.** Why did commit 380ebe1 remove seeded snapshot/send/delivery rows instead of fixing the snapshot storage path directly?
    **A:** Seeded `html_location` values pointed to nonexistent files, breaking delivery-detail rendering. Rather than commit to a snapshot storage strategy (file vs. DB vs. object storage — still open, see project notes) just to unblock seeding, the fake rows were dropped. Side effect: `PreferenceUpdateLogDB.event_id` (declared `nullable=False`) now gets a NULL inserted by the seed — a schema/seed mismatch that would only surface via strict ORM loading or a future NOT NULL migration.
    **Resolution:** act, but needs a final decision first — not a quick fix. The per-recipient personalization fix (Delivery Q2) raises the stakes on the already-open snapshot-storage question (do we need to persist full HTML at all vs. re-render on demand, and in what medium, with historical per-recipient access from the service). Logged to [[backlog]] § Needs ADR.

- [x] **Q5.** What stops two concurrent calls to send the same send instance twice?
    **A:** Nothing — no status guard before the loop runs, no unique constraint or row lock. Would produce duplicate sends and `provider_message_id` last-write-wins on the same row.
    **Resolution:** act/fix. Add a status guard + row lock/unique constraint for this specific case (logged to [[backlog]] Bugs). Also surfaces a systemic gap — the project needs a general concurrency-guard pattern across write endpoints (including "two managers editing the same object simultaneously"), not per-issue fixes; logged as a separate Feature, cross-referenced with the Overrides Q4 race.

- [x] **Q6.** The mock provider's `send()` always returns `success=True`, and the result is never checked — what does that mean for failure-handling coverage?
    **A:** Execution status is unconditionally set to `"sent"` regardless of `result.success` (`service.py:168`) — failure paths (status="failed", retry) are both unimplemented and untested since the mock never exercises them.
    **Resolution:** act/fix (partial) + keep in poc (partial). Consult `result.success` and log every attempt's result now (small, low-risk). Defer designing reactions to varied real-provider failure modes until real providers exist. Logged to [[backlog]] (Bugs).

## Providers

- [x] **Q1.** Two separate "provider" concepts exist — `delivery/providers/` (send-side) and `providers/adapters/` (feedback-side, whose mock file is empty) — intentional per [[ADR-100 — Provider Layer as Send and Feedback Adapter]], or incomplete?
    **A:** Looks incomplete — the inbound webhook-translation adapter layer was scaffolded but never implemented. `ingest_provider_event` currently accepts an already-normalized payload directly rather than translating a raw provider webhook.
    **Resolution:** act/fix. Build the adapter contract (analogous to `DeliveryProvider`), not a vendor-specific plugin — consistent with the earlier decision to stay architecture + one worked example, not ship maintained ESP/CRM plugins. Logged to [[backlog]] (Features).

- [x] **Q2.** What happens when `ingest_provider_event` finds no matching `DeliveryExecutionDB` via `provider_message_id`?
    **A:** Raises `ValueError` → HTTP 400, and the event is lost — no quarantine/retry table. Violates [[ADR-129 — Correlate Provider Events to Delivery Executions]]'s "must not be silently discarded" requirement. `providers/service.py:15-27`.
    **Resolution:** act/fix. Store unmatched events in a quarantine/dead-letter table for later reconciliation instead of losing them. Logged to [[backlog]] (Bugs).

- [x] **Q3.** Correlation is keyed solely on `provider_message_id` with no secondary/fallback strategy — is that column indexed or unique?
    **A:** Matches ADR-129's primary correlation strategy, but the column has no unique constraint or index (`delivery/db_models.py:32`) — collisions would silently pick the wrong execution, and the lookup (the hot path for every inbound webhook) degrades linearly with volume.
    **Resolution:** act/fix. Add a unique constraint + index. Logged to [[backlog]] (Bugs).

- [x] **Q4.** `ProviderEventCreate.event_type` is unconstrained free text — how is "normalize into internal events" actually enforced?
    **A:** It isn't, at the schema level. Only `insight`'s hardcoded `"click"` check gives any event type real downstream meaning; bounce/complaint (mandatory per [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]) are accepted into storage but have no defined handling.
    **Resolution:** act/fix. Centralize event-type normalization in the provider adapter layer (Providers Q1), not a single hardcoded enum, since valid event types vary per provider. Folded into that same [[backlog]] Feature entry.

- [x] **Q5.** Does the system dedupe a webhook delivered twice?
    **A:** No uniqueness check on `provider_event_id` at ingestion — a duplicate webhook creates a second `EngagementEventDB` row unconditionally. Dedup only exists one layer downstream in `apply_event_to_preferences`, which isn't auto-invoked from ingestion.
    **Resolution:** act/fix. Add a uniqueness check/constraint on `provider_event_id` at ingestion — a distinct, earlier-layer gap from the Insight Q3 fix. Logged to [[backlog]] (Bugs).

## Recipients

- [x] **Q1.** [[ADR-122 — Minimal Consent Model Required]] requires a consent model gating delivery eligibility — where is it, and is it checked before sending?
    **A:** It doesn't exist. `RecipientDB.status` is a free-form string never consulted by `send_send_instance`. **Direct compliance gap** — highest-priority item in this cluster.
    **Resolution:** ~~keep in poc, unresolved~~ → **act/fix (reconciled 2026-07-11 via `/business-review`).** The deeper tension is resolved: not a CRM replacement, but a minimal `consent_status` field on `RecipientDB` (synced from CRM, already permitted by ADR-126's "communication preferences" allowed-field list) plus a consent-sync log, checked at audience-resolution time before decision/rendering run — driven by both legal (GDPR processing scope) and cost (avoid paying for AI/token-driven decisioning on non-consenting recipients) reasons. Full narrative in `docs/business-interview-baseline.md` §F1 and `docs/playbook-strategy.md` Decision Log (2026-07-11). Logged to [[backlog]] (Features).

- [x] **Q2.** `email` has no unique constraint — intentional?
    **A:** Consistent with [[ADR-126 — Maintain Local Recipient Projection]] (email shouldn't be the identity key) — but means duplicate-email rows are possible from a bad import, with nothing catching it.
    **Resolution:** small fix, act. Whether email must be unique is a business decision, deferred (config-layer territory). For now: deduplicate by email before send and when calculating segments. Logged to [[backlog]] (Bugs).

- [x] **Q3.** No unique constraint on `(recipient_id, category_id)` for preferences, and `create_recipient_preference` always inserts rather than upserts — how does `apply_event_to_preferences` cope with duplicates?
    **A:** It doesn't fully — `.first()` picks one non-deterministically when duplicates exist; the other becomes a stale, inconsistent score with no defined resolution order.
    **Resolution:** act/fix. `RecipientPreferenceDB` is the current/aggregate score (distinct from `PreferenceUpdateLogDB`'s append-only log, which correctly has no such constraint) — add a unique constraint and switch to upsert. Logged to [[backlog]] (Bugs).

- [x] **Q4.** Confirmed: is `recipient_id` a consistent concept across modules?
    **A:** No — `recipients`/`decision` use the internal integer PK; `delivery` uses the string `external_id`. Any new caller must know which flavor a given function expects, disambiguated only by type hints, not validation. Same finding as Delivery Q1.
    **Resolution:** act/fix. Same backlog entry as Delivery Q1 / Insight Q5 — no new entry needed.

- [x] **Q5.** No duplicate check before insert in `create_recipient` — what happens on a repeat CRM sync?
    **A:** Unhandled `IntegrityError` → raw 500, rather than a clean upsert keyed on `external_id` — a realistic operational path (re-running a sync) that isn't handled gracefully.
    **Resolution:** act/fix. Upsert keyed on `external_id`. Logged to [[backlog]] (Bugs).

- [x] **Q6.** `attributes` is an open JSON blob alongside first-class `language`/`preferred_airport` columns — doesn't this risk becoming the de facto customer profile ADR-126 warns against?
    **A:** Yes — nothing bounds what goes into `attributes` today; it's an extensibility escape hatch that could silently grow into an unmanaged profile store.
    **Resolution:** act/fix, two items. (1) `attributes` needs documented/validated bounds — a rich profile over time is fine per ADR-126's Allowed Responsibilities, the actual line is engagement/personalization data vs. forbidden CRM-scope data (service cases, addresses, invoices). (2) Also flagged: `preferred_airport` is a domain-specific example wrongly hardcoded as a first-class column in the generalized schema — should be removed and folded into a generalized preferences structure instead. Both logged to [[backlog]] (Bugs).

---
## Related
- [[MOC - Interview Prep Baseline]]
- [[MOC - Delivery Architecture]]
- [[MOC - Provider Architecture]]
