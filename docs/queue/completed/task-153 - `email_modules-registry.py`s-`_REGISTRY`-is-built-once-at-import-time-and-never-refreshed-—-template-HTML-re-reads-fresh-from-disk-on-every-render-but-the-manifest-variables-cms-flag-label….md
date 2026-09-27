---
id: TASK-153
title: >-
  `email_modules/registry.py`'s `_REGISTRY` is built once at import time and
  never refreshed — template *HTML* re-reads fresh from disk on every render,
  but the *manifest* (variables, cms flag, label)…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
  - frontend
dependencies: []
type: bug
ordinal: 501700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `email_modules/registry.py`'s `_REGISTRY` is built once at import time and never refreshed — template *HTML* re-reads fresh from disk on every render, but the *manifest* (variables, cms flag, label) stays frozen until restart, an inconsistent freshness split within the same registry. No "save template" endpoint exists to hook a notification into anyway — templates get added by dropping files directly into `storage/email_modules/`, outside any request lifecycle. Fix: real hot-reload instead of restart+notify — `_discover()` is already side-effect-free, so re-run it (behind a cheap directory-mtime check, or via an explicit manual "reload registry" admin action) instead of only running it once at import. Same stale-until-restart pattern exists in `decision/strategies/registry.py` too — worth applying consistently, though not expanding scope here beyond what was asked. Source: [[Interview Prep - Snapshots, Rendering, Email Modules]] → Email Modules Q2. **Done 2026-07-12** — both registries now check a cheap directory-mtime before serving, re-running `_discover()` only when something changed on disk; the strategies registry also uses `importlib.reload()` so code edits are picked up, not just re-imports. Verified live: edited a module manifest's label on disk and saw it update via the API with no app restart.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 535, section "Done", position 17 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
