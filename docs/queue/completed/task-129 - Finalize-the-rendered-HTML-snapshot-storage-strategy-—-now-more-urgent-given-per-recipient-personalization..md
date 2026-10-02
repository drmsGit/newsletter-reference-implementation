---
id: TASK-129
title: >-
  Finalize the rendered-HTML/snapshot storage strategy — now more urgent given
  per-recipient personalization.
status: Done
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-10-02 15:21'
labels:
  - needs-adr
  - backend
dependencies: []
type: decision
ordinal: 301300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
📋 **Finalize the rendered-HTML/snapshot storage strategy — now more urgent given per-recipient personalization.** **Update 2026-08-07 (code review P1-04, P2-06) — the review found something sharper than a storage question: the snapshot is described as the immutable final state but is not what gets sent.** `send_send_instance()` reads only `snapshot.variant_id` and then **re-renders from current database state for every recipient** — it never sends the stored HTML. So after a snapshot is approved, the subject can change, the preheader is not part of the payload at all, static modules can resolve a newer frozen content version, composition and overrides can change, and decisions are recalculated. Per-recipient rendering is legitimate and intended; the defect is that "snapshot reviewed" therefore does not prove "content sent", which is precisely what an approval and audit trail is for. **The reviewer's framing is worth adopting: these are two artifacts, not one.** (1) a campaign/variant **approval** snapshot, and (2) an immutable **per-delivery package** — exact subject, preheader, resolved content-version ids, applied overrides, and the final HTML or its hash — with the provider request traceable to (2). That also settles what has to be durable, which is where the storage question comes back: filesystem paths relative to the source tree lose artifacts on container replacement, are not shared between instances, are absent from database backups, and break when the project moves. Decide (1)/(2) first; the medium follows from it. Currently writes flat HTML files (`storage/snapshots/`), with `SnapshotDB.html_storage_type` as an unused extension point for object storage (per project notes: this was already an open decision). Commit 380ebe1 worked around a related seed-data bug (bad `html_location` paths) rather than resolving the underlying strategy, and left a side-effect NULL in `PreferenceUpdateLogDB.event_id` (a `nullable=False` column). The Delivery Q2 fix (per-recipient HTML resolution instead of one shared variant-level snapshot) raises the stakes: instead of one rendered artifact per variant, this could mean one per recipient per send — making "do we even need to persist full HTML files at all" a much more pressing question than before. Needs a decision on: whether to store full rendered HTML historically at all vs. re-render on demand from stored `render_context` + pinned content versions; if storing, what medium (file/DB/object storage); and how per-recipient historical renders stay accessible from the service layer rather than being opaque static files. **Candidate direction:** rather than persisting full HTML per recipient, store a compact structured reference per recipient per send — `variantId` + resolved `content_record_id`s + position — and reconstruct/re-render on demand when a historical view is needed. This is largely what `SnapshotDB.render_context` (JSON, added commit 431c053) already captures, so this may mostly be a matter of confirming/extending that existing field rather than inventing a new one. **Confirmed gaps to resolve as part of this decision** (Snapshots Q2): `render_context` today captures resolved content/decision data per module but not (1) active overrides — `module_data.*_override` values applied at render time are never recorded, and (2) merge-context (recipient-specific substitution values like firstname) — both explicitly required by ADR-062's "overrides" and the related ADR-005 merge-context concept. **Also needs to answer:** should per-recipient snapshots be persisted proactively at send time at all, or should "what did recipient X actually receive" always be reconstructed on-demand (e.g. by a support/audit service reading the structured log + re-rendering), only when actually requested rather than for every send? Source: [[Interview Prep - Delivery, Providers, Recipients]] → Delivery Q4; [[Interview Prep - Snapshots, Rendering, Email Modules]] → Snapshots Q2.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 459, section "Needs ADR", position 13 in that section (top = do next). The description is the original entry, verbatim.

2026-10-02: decided and built as ADR-183 — no persisted HTML; the snapshot is a frame of copied values the send renders from; each delivery execution records sent_at, its slot picks with copied values, and an output hash; reconstruction re-renders (content exact, layout best-effort with a template fingerprint). Not done here: merge context (none exists yet), retention/erasure of delivery records (task-136).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Decided by ADR-183 and built on 2026-10-02: frames instead of HTML files, per-delivery records, on-demand reconstruction.
<!-- SECTION:FINAL_SUMMARY:END -->
