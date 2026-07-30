---
type: code-module
module: providers
topic:
  - architecture
  - providers
created: 2026-07-27
modified: 2026-07-27
---

# providers

> Part of [[MOC - System Overview]]. Architecture rationale: [[MOC - Provider Architecture]], [[ADR-100 — Provider Layer as Send and Feedback Adapter]].

## Purpose

The providers module owns **the inbound feedback boundary: taking a raw provider
webhook (an open, click, bounce) and turning it into a canonical internal event,
correlated back to the exact message that caused it**. It's the mirror of the
*outbound* adapter (which lives in `delivery/providers/` — see [[delivery]]).
Together they form the "provider is an adapter, not architecture core" boundary
that makes the ESP swappable. This module normalizes, correlates, dedupes,
quarantines the un-correlatable, and hands content-tied events to [[insight]].

## Key files
- `backend/app/providers/adapters/resend.py` — the one worked-example inbound adapter (Svix signature verify, event-name map, payload → `NormalizedEvent`)
- `backend/app/providers/service.py` — `ingest_provider_event`, `process_provider_webhook_event`, content attribution, quarantine
- `backend/app/providers/db_models.py` — `ProviderEventQuarantineDB`
- `backend/app/providers/router.py` — the `/provider/*` endpoints incl. the public webhook

## Public surface
**Service functions** (`providers/service.py`):
- `process_provider_webhook_event(db, normalized)` — **the end-to-end entry point**: correlate → record (dedup/quarantine) → apply signals for a content-tied event
- `ingest_provider_event(...)` — correlate a normalized event to a `DeliveryExecutionDB` by `provider_message_id`; dedupe; quarantine if no match
- `list_quarantined_events(db)` — read the dead-letter table

**Adapter** (`providers/adapters/resend.py`): `verify_signature`, `parse_webhook` → `NormalizedEvent`.

**Routes** (`/provider`, tag `provider`): 3 routes — `POST /provider/events` (manual/normalized ingest), `GET /provider/quarantine`, and the public **`POST /provider/webhooks/resend`** (returns 200 for handled *and* ignored events so Resend won't retry unmapped ones; 401 only on a bad signature).

## Data model
*One table.*
- **`provider_event_quarantine`** (`ProviderEventQuarantineDB`) — dead-letter storage for inbound events that couldn't be correlated to a delivery execution, so nothing is silently dropped ([[ADR-129 — Correlate Provider Events to Delivery Executions]]).

## Depends on →
- [[delivery]] — correlates on `DeliveryExecutionDB.provider_message_id`
- [[snapshots]] / [[campaigns]] — `_primary_content_id_for_delivery` walks send → snapshot → variant → resolution/module to find what the recipient received
- [[insight]] — records the `EngagementEventDB` and applies signals

## Depended on by →
- [[frontend]] — (indirectly) surfaces quarantine; the webhook itself is called by the external provider, not another module

## Invariants & decisions
- **Provider is an adapter, not the core** ([[ADR-100 — Provider Layer as Send and Feedback Adapter]]); **capabilities are explicit** ([[ADR-101 — Provider Capabilities Are Explicit]]).
- **Events must never be silently discarded** — an un-correlatable event is quarantined for later reconciliation, not dropped ([[ADR-129 — Correlate Provider Events to Delivery Executions]]).
- **Correlation key = `provider_message_id`**, set by [[delivery]] at send. Backed by a unique+indexed column so dedup is safe and the lookup (hot path per webhook) is fast.
- **Deterministic `provider_event_id`** (email_id + type + created_at) makes webhook redelivery idempotent — the same event twice records once.
- **Adapters are small and provider-specific by design** — a new ESP copies the Resend adapter and changes three things (signature check, event-name map, field paths); we do **not** build a generic auto-fitting layer, and we do **not** ship a second maintained integration.
- **Signature verify is skippable only for local dev** (no `RESEND_WEBHOOK_SECRET`) — with a warning; production must set the secret. Note the secret is read at startup, so it needs a full restart to take effect.
- **Attribution is "what was shown", not link-parsing** — a click attributes to the recipient's resolved decision pick (or the variant's first fixed-content module); mapping specific links to content ids is a later refinement.
- **Content-tied = open/click only** — those move per-category signals. **Bounce/complaint instead drive consent suppression**: a hard/permanent bounce or spam complaint calls [[recipients]]'s `suppress_recipient` (opt-out). A soft/transient bounce is spared. The Resend adapter decides suppression (`NormalizedEvent.suppresses_consent`), keeping the handler provider-agnostic. (ADR-106 — bounce/complaint feedback is mandatory.)

## ⚠️ Change-impact — if you touch this, also check…
- **The correlation on `provider_message_id`** → depends entirely on [[delivery]] setting it uniquely; breaking that constraint mis-attributes or drops engagement.
- **`_primary_content_id_for_delivery`** → walks [[delivery]] → [[snapshots]] → [[campaigns]]; a schema change on that path changes what a click attributes to.
- **The event-name map / signature scheme** → provider-specific in `adapters/resend.py`; a new provider is a new adapter file, not edits here.
- **Webhook status codes** → returning non-200 for an ignored event makes Resend retry forever; keep the 200-for-ignored behavior.
- **Env secret loading** → `RESEND_WEBHOOK_SECRET` only applies after a full server restart. Never read `backend/.env` to check it — ask/observe.
