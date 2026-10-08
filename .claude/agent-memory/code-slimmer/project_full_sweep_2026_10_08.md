---
name: full-sweep-2026-10-08
description: Full backend sweep before the external-review break — what was reported (paging residue, consent drift brand gap, registry copies, misplaced logic) and the method that found it
metadata:
  type: project
---

Fresh full sweep 2026-10-08, ahead of interview reviews and a possible external
code review. Report went to the caller; nothing is in the queue unless the
human files it. Check `docs/queue/` before re-raising any of these.

**Reported (untriaged as of 2026-10-08):**
- **task-88 paging residue:** the pre-paging `list_*` service functions were
  left behind when routes moved to `page_*` (commit b7f0443). Each router still
  imports the old name unused. One of them, `list_events_for_delivery_execution`,
  is not brand-scoped. Module pages under `docs/architecture/Code/` still
  advertise them.
- **`detect_consent_drift` ignores brand.** It keys on (recipient, channel,
  purpose), `ConsentDriftItem` has no brand, and its tests use one brand.
  Tension with the ADR-163 addendum of 2026-09-15 (consent is per brand). The
  "latest event wins" ordering is written out separately at each consent read.
- **Registry copies:** every drop-a-file registry carries its own
  `_discover`/`_dir_mtime`/`_ensure_fresh`, and they have drifted (exclusion by
  filename vs by marker; only `modules` uses rglob, which sees deletions).
  task-104 plans another copy.
- **ADR-180 helpers live in campaigns.** Other routers import the private
  `_expected` and `IF_MATCH` from `campaigns/router.py`.
- **`main.py` `_approval_required` handler** holds approval-domain logic,
  including a raw `PendingActionDB` query, that no service owns.
- **`scripts/seed_override_events.sql`** targets the `override_events` table,
  which was removed 2026-07-15. Genuinely dead.
- **`backend/project_tree.txt`** is 0 bytes and separate from the root file
  task-306 covers.
- **Small dead symbols** (this repeats the 2026-08-21 finding for
  `current_user`, which is still unfixed).

**Settled, do not re-investigate:** the Jinja router (frozen, task-50) makes
**no direct DB writes**; all its writes go through services. Its residue is
read duplication only. Report it as one "goes when Jinja retires" item.

**Method notes that paid off:**
- **Ruff F401 in a router is a migration-residue detector.** An unused import
  of `list_X` next to a function-local import of `page_X` is the fingerprint of
  a refactor that swapped the call and kept the old function.
- An AST "loaded names" pass must **exclude import statements**. A regex count
  treats the dead import as a use and hides exactly these functions.
- An AST pass that counts `ast.Attribute` names misses a dead function whose
  name matches an attribute elsewhere (`current_user` vs
  `request.state.current_user`). Grep for `Depends(name)` too.
- Vulture is not installed; the stdlib AST pass in the session scratchpad did
  the job. Expect the plugin classes in [[seams-do-not-flag]] as false positives.

Related: [[seams-do-not-flag]], [[backlog-already-logged]], [[review-only-never-edit]]
