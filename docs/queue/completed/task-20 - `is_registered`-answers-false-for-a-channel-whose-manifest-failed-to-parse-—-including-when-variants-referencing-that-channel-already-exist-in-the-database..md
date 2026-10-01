---
id: TASK-20
title: >-
  `is_registered` answers false for a channel whose manifest failed to parse —
  including when variants referencing that channel already exist in the
  database.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-10-01 19:49'
labels:
  - backend
dependencies: []
priority: p3
type: bug
ordinal: 102000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P3. A broken channel and an undeclared one are different facts, and the code reports them as the same.** **`is_registered` answers false for a channel whose manifest failed to parse — including when variants referencing that channel already exist in the database.** `channels/registry.py:69-83` logs and skips a malformed manifest, deliberately, so that a typo in an unused channel cannot take down the ones in use. That asymmetry against the module registry (which raises `MisfiledManifestError` at startup) is correct and stays — blast radius plus detectability, since a misfiled module is silent and recipient-facing while a missing channel is loud at the first picker. **What is wrong is downstream:** a malformed manifest and an absent one are indistinguishable, so a channel that broke this morning looks exactly like one that was never declared, at the moment rows already depend on it. **Fix:** surface a loaded-with-errors state, or refuse at startup when an unreadable manifest names a channel that variants are already using — the narrow case where skipping quietly costs more than it saves. Source: [[Interview Prep - Channels, Audit]] → A-Q4.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 76, section "Bugs", position 20 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Both halves the entry offered, narrowly: the channel registry remembers why a manifest failed, so the one refusal site says 'declared but unreadable' instead of 'not available'; and startup refuses only when an unreadable manifest names a channel existing variants use — an unused broken channel is still just skipped, keeping the blast-radius tolerance. Four tests (startup checked in a fresh process), four mutations caught; 752 pass.
<!-- SECTION:FINAL_SUMMARY:END -->
