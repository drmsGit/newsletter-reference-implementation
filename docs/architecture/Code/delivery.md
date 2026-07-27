---
type: code-module
module: delivery
topic:
  - architecture
  - delivery
created: 2026-07-27
modified: 2026-07-27
---

# delivery

> Part of [[MOC - System Overview]]. Architecture rationale: [[MOC - Delivery Architecture]].

## Purpose

The delivery module owns **the act of sending a rendered campaign to real
people, and the record of what happened**. It sits between a finished
[[snapshots|snapshot]] and an external [[providers|provider]]: it plans *who* a
send goes to (materializing one execution per recipient from an [[audience]]
group), it runs the send loop (personalize → render → hand to the provider →
record the outcome per recipient), and it keeps a minimal history of every
delivery attempt. It deliberately does **not** decide content, render HTML, or
talk to a provider's API directly — it orchestrates those other modules and
stores the results.

## Key files

- `backend/app/delivery/service.py` — all orchestration logic (plan, reconcile, schedule, send)
- `backend/app/delivery/db_models.py` — the two tables: `SendInstanceDB`, `DeliveryExecutionDB`
- `backend/app/delivery/models.py` — Pydantic request/response schemas
- `backend/app/delivery/router.py` — the `/delivery/*` JSON endpoints
- `backend/app/delivery/providers/` — the **outbound** provider adapters (see [[providers]] for the boundary): `base.py` (the `DeliveryProvider` contract + `SendResult`), `factory.py` (`get_provider`), `mock.py`, `resend.py`

## Public surface

*What other modules and the UI call. One line each — internals live in the docstrings.*

**Service functions** (`delivery/service.py`):
- `prepare_send_from_audience(...)` — resolve an audience group (consent-gated), check the send cap, create the send instance + one execution per recipient. Nothing is sent. **The main entry point for planning a send.**
- `send_send_instance(db, send_instance_id)` — run the actual send loop for a planned instance (row-locked, one-shot). **The main entry point for firing a send.**
- `reconcile_executions_to_audience(db, send_instance)` — for `"rerun"` sends: re-resolve the group just before firing and add/drop executions.
- `process_due_scheduled_sends(db)` — fire every scheduled send whose time has arrived (the seam a cron/worker/n8n drives).
- `create_send_instance(...)` / `create_delivery_execution(...)` — low-level record creation (used by the JSON API and legacy paths).
- `list_send_instances_for_snapshot(...)` / `list_delivery_executions_for_send_instance(...)` — read history.
- `get_provider(name, from_address)` (`providers/factory.py`) — resolve a provider name to an adapter instance.

**Routes** (`delivery/router.py`, prefix `/delivery`, tag `delivery`):
- `POST /delivery/executions` — create a single execution
- `POST /delivery/send-instances` — create a send instance
- `GET /delivery/snapshots/{id}/send-instances` — list sends for a snapshot
- `GET /delivery/send-instances/{id}/executions` — list executions for a send
- `POST /delivery/send-instances/{id}/send` — trigger a send

> The rich planning flow (audience → provider → timing) is driven from the
> **UI**, not this JSON router — see [[frontend]] routes
> `POST /ui/campaigns/{campaign_id}/snapshots/{snapshot_id}/send-instances` (plan),
> `POST /ui/send-instances/{id}/send` (fire), `POST /ui/deliveries/process-due` (fire due scheduled).

## Data model

*Two tables, both owned here. History is intentionally minimal ([[ADR-053 — Maintain Minimal Delivery Execution History]]).*

- **`send_instances`** (`SendInstanceDB`) — one planned/fired send. Columns of note:
  - `snapshot_id` → the frozen render it sends
  - `audience_group_id` → who it targets (nullable for ad-hoc sends)
  - `provider`, `from_address` → which adapter + verified sender
  - `audience_resolution_mode` → `"freeze"` (executions fixed at plan time) or `"rerun"` (re-resolved at send time) — [[ADR-052 — Delivery Layer Supports Multiple Audience Resolution Modes]]
  - `scheduled_at`, `status` → `draft` → `scheduled` → `sending` → `sent` / `failed`
- **`delivery_executions`** (`DeliveryExecutionDB`) — one row **per recipient per send**. Columns of note:
  - `recipient_id` → **direct FK** to `recipients.id` ([[ADR-054 — Use Internal Recipient Identifiers]], no external-id translation)
  - `status` → `created` → `sent` / `failed`
  - `provider_message_id` → the provider's id for the sent message; **nullable + unique + indexed** (the correlation key inbound webhooks match against — see [[providers]])

## Depends on →

- [[audience]] — `resolve_audience()` to turn a group into the recipient list (imported *inside* the functions, so audience never has to know about delivery)
- [[settings]] — `get_max_send_recipients()` to enforce the send cap at plan time and after a rerun reconcile
- [[snapshots]] — a `SnapshotDB` gives the `variant_id` to render and anchors the send to a frozen state
- [[campaigns]] — `VariantDB` (for the subject line) and `DecisionSlotDB` (the slots to resolve per recipient)
- [[decision]] — `execute_decision_slot()` to personalize each recipient's content *at send time* before rendering
- [[rendering]] — `render_variant_html()` to produce each recipient's own HTML
- [[recipients]] — `RecipientDB` for the target email address
- **`delivery/providers/`** — the outbound `DeliveryProvider` adapter (`mock` / `resend`) that actually transmits. Note this is a **subpackage of delivery itself**, not the top-level [[providers]] module (which is the *inbound* webhook side). The [[providers]] module and this subpackage together form the "provider boundary" concept — see [[providers]].

## Depended on by →

- [[frontend]] — the UI drives planning, triggering, and the "run due scheduled sends" button
- [[providers]] (inbound side, `app/providers/`) — reads `delivery_executions` to correlate an incoming engagement webhook back to the message that caused it ([[ADR-055 — Separate Delivery Execution from Engagement Events]])
- [[insight]] — reads `delivery_executions` when attributing engagement to content

## Invariants & decisions

- **A send is provider-agnostic.** Delivery talks only to the `DeliveryProvider` contract; the concrete ESP is a swappable adapter. [[ADR-050 — Delivery Layer is Part of the Reference Architecture]], [[ADR-100 — Provider Layer as Send and Feedback Adapter]].
- **One-shot guard.** `send_send_instance` takes a `SELECT ... FOR UPDATE` row lock and refuses to send an instance already `sending`/`sent` — prevents double-sends from concurrent triggers.
- **Per-recipient rendering, resolved at send.** Each recipient gets their own decision resolution and their own rendered HTML — not one shared variant snapshot — because decision slots can pick different content per person. [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]].
- **Never crash on a bad send.** Provider `send()` returns `success=False` rather than raising; a failed execution is recorded `failed` with the provider's message. [[ADR-086 — Decision Slots Fail Gracefully]] (spirit).
- **Commit per execution.** The loop commits after each recipient so a mid-batch failure doesn't roll back already-sent rows.
- **Consent floor is upstream.** Delivery trusts `resolve_audience()` to have already dropped non-consenting recipients — it does not re-check consent.
- **Minimal history, internal ids.** [[ADR-053 — Maintain Minimal Delivery Execution History]], [[ADR-054 — Use Internal Recipient Identifiers]].

## ⚠️ Change-impact — if you touch this, also check…

- **The `provider_message_id` shape or uniqueness** → [[providers]] inbound correlation matches on it; the unique+indexed constraint is load-bearing for webhook dedup. Breaking it silently mis-attributes engagement.
- **The send loop's decision/render calls** → depends on [[decision]] `execute_decision_slot` and [[rendering]] `render_variant_html` signatures; a change there ripples into every send.
- **`SendInstanceDB` / `DeliveryExecutionDB` columns** → there are **no migrations** in this project; new columns auto-create via `Base.metadata.create_all` on a fresh DB, but an **existing DB needs a manual `ALTER TABLE`** (this is how `audience_group_id`, `from_address`, `audience_resolution_mode`, `scheduled_at` were added). Grep `backend/scripts/*.sql` for seed/reset drift too.
- **The status vocabulary** (`draft`/`scheduled`/`sending`/`sent`/`failed`) → the UI delivery page and `process_due_scheduled_sends`'s `status == "scheduled"` filter both depend on these exact strings.
- **`audience_resolution_mode` semantics** → `"rerun"` re-resolves via [[audience]] at fire time; changing the reconcile rule changes who a scheduled send reaches.
- **Adding a provider** → add a class implementing `DeliveryProvider` + one line in `providers/factory.py`; do **not** build a second full ESP integration (architecture + one worked example is the rule). See `docs/how-to-swap-send-provider.md`.
