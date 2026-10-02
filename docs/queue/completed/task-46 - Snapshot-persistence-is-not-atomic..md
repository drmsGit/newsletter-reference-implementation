---
id: TASK-46
title: Snapshot persistence is not atomic.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-10-02 15:21'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 104600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P2.** **Snapshot persistence is not atomic.** The row is committed with `html_location="pending"` before the file is written (`snapshots/service.py:105-138`), so a filesystem failure leaves a snapshot row pointing at nothing — and send instances can be anchored to it. **Fix:** write to a temporary file and commit metadata only after a successful atomic rename, or store the artifact transactionally. Ties to the snapshot-storage Needs-ADR item, which questions filesystem storage at all. Source: code review 2026-08-07 P2-05. **HELD 2026-09-14 — deliberately not fixed, and the reason outranks the bug.** Investigated on the way to fixing it: the snapshot-storage Needs-ADR item already records the **candidate direction** of dropping persisted HTML entirely in favour of reconstructing from `SnapshotDB.render_context` plus pinned content versions, because per-recipient personalization would otherwise mean one rendered artifact per recipient per send. Making this write atomic would harden an artifact the project intends to delete. **And it would harden the wrong artifact anyway:** that same item records that `send_send_instance()` reads only `snapshot.variant_id` and **re-renders from current database state for every recipient — it never sends the stored HTML**, so the file is not what went out. **State checked 2026-09-14:** 7 snapshots, 0 stuck at `pending`, 0 send instances anchored to a pending one, so nothing is currently broken and there is no cleanup owed. **Two confirmed gaps** before "reconstruct on demand" is actually possible: `render_context` captures neither active overrides nor merge-context (recipient substitutions), both required by ADR-062 and ADR-005. Resolve the storage ADR first; this entry follows from it.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 130, section "Bugs", position 46 in that section (top = do next). The description is the original entry, verbatim.

2026-10-02: resolved by ADR-183 (user decision: reconstruct what each recipient got; drop HTML snapshot storage). The non-atomic write is gone with the file: snapshots store only the frame (render_context), previews render from it. Stages: frame (2cdafea), send renders the frame + delivery record + migration 0027 (9ddf662), reconstruction GET /delivery/executions/{id}/as-sent (e47a20e), no HTML on disk + scripts/drop_frameless_snapshots.py. The user runs the script against the dev database (dry run first).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Snapshot persistence can no longer be half-written: there is no file. ADR-183 makes the snapshot a frame of frozen values in its row; the send renders it and records per recipient what it sent, and previews render the frame on demand. Verified by tests/test_frame.py (parity, freezing, recorded picks, send, reconstruction, no files) and tests/test_drop_frameless_snapshots.py, each mutation-checked; full suite 928 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
