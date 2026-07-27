---
type: code-module
module: snapshots
topic:
  - architecture
  - rendering
  - delivery
created: 2026-07-27
modified: 2026-07-27
---

# snapshots

> Part of [[MOC - System Overview]]. Architecture rationale: [[MOC - Rendering Architecture]], [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]].

## Purpose

The snapshots module owns **freezing what an email looked like at a moment in
time** — the render context plus the rendered HTML — so a send is reproducible and
auditable. A snapshot is the anchor a [[delivery]] send attaches to; crucially, a
**snapshot ≠ a send** ([[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]]) and a snapshot ≠ a per-recipient delivery artifact. It captures the
final render state ([[ADR-062 — Snapshot Stores Final Render State]]); it does not
send anything.

## Key files
- `backend/app/snapshots/db_models.py` — `SnapshotDB`
- `backend/app/snapshots/service.py` — build render context, create snapshot (+ write HTML file), read HTML
- `backend/app/snapshots/router.py` — the `/snapshots/*` endpoints

## Public surface
**Service functions** (`snapshots/service.py`):
- `create_snapshot_for_variant(db, variant_id, recipient_id=None)` — render + freeze; writes HTML to `storage/snapshots/` and metadata to the DB
- `build_render_context(...)` — assemble the audit context (which resolutions/versions were used)
- `list_snapshots_for_variant(...)` / `get_snapshot_html(...)`

**Routes** (`/snapshots`, tag `snapshots`): 3 routes — create for variant, list for variant, get HTML (`GET /snapshots/{id}/html`, HTML response).

## Data model
*One table.*
- **`snapshots`** (`SnapshotDB`) — `variant_id`, optional `recipient_id` (recipient-aware snapshots), `html_storage_type` (`"file"` today — the extension point for `"s3"`/`"db"`), `html_location`, `html_size`, `render_context` (JSON audit). The HTML *bytes* live on disk under `storage/snapshots/`; the row holds metadata + location.

## Depends on →
- [[campaigns]] — snapshots a variant's composition
- [[content]] — captures which content/versions were rendered (in the render context)
- [[rendering]] — calls `render_variant_html` to produce the HTML it freezes

## Depended on by →
- [[delivery]] — a `SendInstanceDB.snapshot_id` anchors the send; the send reads the snapshot's `variant_id`
- [[providers]] — inbound correlation walks send → snapshot → variant to find what a recipient received
- [[frontend]] — the snapshot list / HTML preview

## Invariants & decisions
- **Snapshot ≠ Send ≠ Delivery artifact** — separate concerns ([[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]], [[ADR-061 — Snapshot Based Final Rendering]]).
- **A snapshot stores the *final* render state** for auditability ([[ADR-062 — Snapshot Stores Final Render State]]) — including the render context so you can see which resolutions/versions produced it.
- **Storage is pluggable via `html_storage_type`** — file today; `"s3"`/`"db"` are the intended future values (object storage: Hetzner/Scaleway/MinIO). This is an **open decision** — and per-recipient personalization raises the question of whether full HTML must persist at all vs. re-render on demand from `render_context` + pinned versions.
- **HTML on disk, metadata in DB** — the row points at a file; the 4000-char API-limit worry that originally motivated files turned out to be a non-issue.

## ⚠️ Change-impact — if you touch this, also check…
- **`SnapshotDB.variant_id`** → [[delivery]] `send_send_instance` reads it to know what to render; [[providers]] inbound walks it to attribute engagement.
- **`html_storage_type` / `html_location`** → any move to S3/DB storage changes `get_snapshot_html` and the write path; this is a tracked open decision, not a casual change.
- **The `storage/snapshots/` path** → anchored to `__file__`; moving `storage/` breaks reads of existing snapshots.
- **Per-recipient snapshots** → note the live send path in [[delivery]] renders per recipient *without* necessarily creating a snapshot per recipient — reconcile any change here with `Flow - Send a campaign`.
