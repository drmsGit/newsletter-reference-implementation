---
id: TASK-64
title: Let the duplication wizard choose WHICH assets of a campaign come across.
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels: []
dependencies: []
type: feature
ordinal: 201700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Feature] — small, and worth more since channels landed. Done 2026-09-18.** **Let the duplication wizard choose WHICH assets of a campaign come across.** Today `duplicate_campaign` takes every variant; the wizard's right-hand panel (`summarise_source`) already lists them with their module and slot counts, but purely as display. Making that list selectable is a checkbox per variant and a filter in the copy loop — the content side needs no work at all, because `_target_content_id` is driven by the modules actually copied, so copying one variant already copies only the records that variant references.

  **Why it is worth more now than when the wizard was built (2026-09-16).** Variants carry a channel since [[ADR-160 — Channel Model and Composition]] point 4 landed, so "duplicate this campaign" now means "duplicate its email *and* its push", which is frequently not what a manager wants — the user hit exactly this while testing: a campaign with a push variant and an email variant duplicated from the second brand to the first and brought both. "Give brand A just the push" is a real operation and there is currently no way to express it short of deleting the unwanted variant afterwards.

  **Two things to settle when building it.** A campaign must always have a variant, so **at least one must stay selected** — the invariant `create_campaign` protects by manufacturing one. And the wizard's content options are per-campaign today; if only a push variant is selected, the "copy content" count shown in step 2 must reflect *that variant's* records, not the whole campaign's, or the warning lies about how many records land in the target brand. Source: user, 2026-09-17, after testing the channel work. **Built 2026-09-18** — a checkbox per variant in step 1, all ticked by default so an untouched wizard behaves as before. Both settled points landed as predicted: an explicitly empty selection is refused rather than read as "all" (a campaign must always have a variant), and `summarise_source` is scoped to the selection so step 2's content count cannot advertise records the copy never creates. One thing the entry did not anticipate: variant ids arrive from a form, so a variant belonging to another campaign is refused too.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 192, section "Features", position 17 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
