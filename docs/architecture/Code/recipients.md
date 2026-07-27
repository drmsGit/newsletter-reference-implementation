---
type: code-module
module: recipients
topic:
  - architecture
  - recipients
created: 2026-07-27
modified: 2026-07-27
---

# recipients

> Part of [[MOC - System Overview]]. Architecture rationale: [[MOC - Data Foundation]].

## Purpose

The recipients module owns **the local projection of the people you send to** —
*not* a CRM. The CRM stays the system of record; this module keeps a lightweight
copy (email, language, attributes, status) plus two things the platform needs to
operate: **marketing consent** (synced from the CRM, used to gate every send) and
the **append-only signal-contribution log** that backs recipient↔category
affinity. It deliberately does not try to own contact management.

## Key files

- `backend/app/recipients/db_models.py` — `RecipientDB`, `ConsentSyncLogDB`, **and `SignalContributionDB`** (the signal table lives here — its *logic* lives in [[insight]])
- `backend/app/recipients/service.py` — recipient CRUD, consent sync + drift detection, `recipient_top_score`
- `backend/app/recipients/router.py` — the `/recipients/*` JSON endpoints
- Exposes `CONSENTING_STATUS` (= `"opted_in"`) — the single constant every consent gate imports

## Public surface

**Service functions** (`recipients/service.py`):
- `create_recipient` / `list_recipients` / `get_recipient_by_external_id` / `validate_recipient_attributes`
- `sync_consent_from_crm` — apply a CRM-asserted consent value, logging the before/after
- `detect_consent_drift` / `list_consent_sync_logs` — surface divergence between CRM and platform
- `create_recipient_preference` / `list_preferences_for_recipient` — declared (manual) preferences → seed `manual` signal contributions

**Routes** (`/recipients`, tag `recipients`): 8 routes — create/list recipients; get by external id; consent drift; consent sync-log; post a consent update.

## Data model

*Three tables, all owned here.*
- **`recipients`** (`RecipientDB`) — `external_id` (the CRM key, unique), `email`, `language`, `attributes` (JSON), `status`, **`consent_status`** (`opted_in`/`pending`/`opted_out`; only `opted_in` consents). [[ADR-126 — Maintain Local Recipient Projection]].
- **`consent_sync_logs`** (`ConsentSyncLogDB`) — append-only log of CRM→platform consent syncs, so drift is detectable, not silent.
- **`signal_contributions`** (`SignalContributionDB`) — append-only contribution log ([[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]). Defined here, but written/read by [[insight]]'s signal code.

## Depends on →
- [[insight]] — `recipient_top_score` and the recipient detail view compute signals via `insight.signals` (function-local import)

## Depended on by →
- [[audience]] — resolves and consent-gates recipients
- [[campaigns]] / [[decision]] — decision resolutions and per-recipient decisioning key off `recipients.id`
- [[delivery]] — an execution FKs a recipient; the send reads their email
- [[insight]] — writes contributions and reads consent
- [[frontend]] — the recipients admin UI

## Invariants & decisions
- **Projection, not CRM.** The CRM owns the contact; this is a synced copy. [[ADR-126 — Maintain Local Recipient Projection]].
- **Internal integer id is the identity.** Other modules FK `recipients.id` directly ([[ADR-054 — Use Internal Recipient Identifiers]]); `external_id` is only for CRM correlation.
- **Consent is a synced gate, not a system of record.** Only `opted_in` clears the [[audience]] consent floor; the CRM remains authoritative. Sync drift is logged, never silently reconciled.
- **`CONSENTING_STATUS` is the one source of truth** for "who counts as consenting" — imported by [[audience]] and [[decision]] rather than re-hardcoded.

## ⚠️ Change-impact — if you touch this, also check…
- **`SignalContributionDB`'s shape** → [[insight]] `signals.py` reads every column (`base_weight`, `occurred_at`, `contribution_type`) to compute decay. This table's home being *this* module is a known quirk — change it in lockstep with [[insight]].
- **`consent_status` values or `CONSENTING_STATUS`** → [[audience]] `resolve_audience` (consent floor) and [[decision]] `execute_decision_slot` (belt-and-suspenders gate) both compare against it.
- **`external_id` uniqueness** → CRM sync and consent-drift matching rely on it being unique.
- **Adding a column** → no migrations; existing DBs need a manual `ALTER TABLE` (this is how several columns landed).
