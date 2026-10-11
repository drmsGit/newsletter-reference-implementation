---
id: TASK-60
title: A personalised subject line still is not possible.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-10-11 19:11'
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

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Decided what a personalised subject line means and where it lives
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 172, section "Features", position 13 in that section (top = do next). The description is the original entry, verbatim.

2026-10-11, decided with the user. ADR-162 point 1 meant a subject adjusted through the override layer, which is per variant, not per recipient. A subject already is the variant's own text, edited directly in its envelope module, so nothing is missing; override eligibility is not widened (ADR-162 addendum 2026-10-11). The user's two other readings went elsewhere: personalising inside a text (a salutation in the subject) is the new expression dictionary, task-365; a wholly different subject per recipient is an AI case (note on task-125) or an automation. Dynamic links went to task-366.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Closed as moot: the subject is the variant's own text and is edited per variant directly; ADR-162's claim that it comes through overrides is corrected by a dated addendum. Inline personalisation moved to task-365, dynamic links to task-366, per-recipient subjects to task-125.
<!-- SECTION:FINAL_SUMMARY:END -->
