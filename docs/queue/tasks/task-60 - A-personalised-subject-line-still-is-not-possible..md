---
id: TASK-60
title: A personalised subject line still is not possible.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
type: feature
ordinal: 201300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — a benefit [[ADR-162 — Channel Rendering and Artifacts]] point 1 claims and does not yet deliver.** **A personalised subject line still is not possible.** Point 1's case for moving subject and preheader into a module is partly that *"overrides work unchanged — the override layer edits module fields, so a personalised subject line comes free instead of needing its own mechanism, which it cannot have today because subject is not a module field"*. Subject became a module field on 2026-09-18 and the sentence still is not true.

  **Why:** `campaign_detail`'s `overrideable` test requires a module that **resolves content** — `content_record_id is not None or decision_slot_id is not None` — and an envelope module has neither; it carries its values in `module_data`. So the header module never reaches the override picker, and `_overrideable_manifest` in `app/overrides/service.py` would refuse it for the same reason with "content overrides only apply to modules that resolve content". Found by rendering the page and reading the override choices back, not by assuming the ADR's claim had landed.

  **What it needs:** deciding whether the override layer's subject is "a module that resolves content" or "a module with declared fields". The second is the reading that makes point 1's sentence true, and it is a change to ADR-040/041's territory rather than to ADR-162's — a static `cta` carrying only `module_data` is the same shape and is equally excluded today, so this is not a push-specific or envelope-specific gap. Source: found while implementing ADR-162 point 1, 2026-09-18.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 172, section "Features", position 13 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
