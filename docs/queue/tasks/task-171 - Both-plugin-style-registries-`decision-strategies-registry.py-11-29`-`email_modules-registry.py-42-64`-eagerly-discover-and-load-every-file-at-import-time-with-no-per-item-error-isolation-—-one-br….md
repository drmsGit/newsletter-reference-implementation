---
id: TASK-171
title: >-
  Both plugin-style registries (`decision/strategies/registry.py:11-29`,
  `email_modules/registry.py:42-64`) eagerly discover and load every file at
  import time with no per-item error isolation — one br…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 503500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** Both plugin-style registries (`decision/strategies/registry.py:11-29`, `email_modules/registry.py:42-64`) eagerly discover and load every file at import time with no per-item error isolation — one broken strategy file (bad import, failing constructor) or one malformed `.json` manifest crashes the entire registry, taking down the whole app at startup. `email_modules/registry.py` already isolates the *missing-counterpart-file* case gracefully (logs a warning, skips just that pair) but not malformed content within a file. Fix: wrap each individual file's discovery/import/instantiation in its own try/except inside both `_discover()` loops — log a clear warning naming the broken file, skip just that one, keep the rest of the registry working. Auto-discovery ("drop a file, no code changes") and full graceful degradation aren't in tension — this is a standard pattern, not a tradeoff. Apply to both registries in one pass. Source: [[Interview Prep - Decision, Overrides, Insight]] → Decision Q1 (also affects the not-yet-reviewed email-modules question on the same gap). **Done 2026-07-12** — both `_discover()` loops now wrap each file's load in its own try/except, logging a warning naming the broken file and skipping just that one. Verified live: dropped in a malformed `.json` manifest and a syntactically invalid strategy `.py` file at the same time — the app kept serving the real strategies/modules with no crash, then both broke test files were removed and the registries recovered cleanly.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 571, section "Done", position 35 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
