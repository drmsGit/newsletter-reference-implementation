---
id: TASK-43
title: Three comments still place subject and preheader on the variant row.
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 13:56'
updated_date: '2026-10-04 18:48'
labels:
  - backend
dependencies: []
priority: p3
type: bug
ordinal: 104300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P3, comments only, but they describe a world two migrations old.** **Three comments still place subject and preheader on the variant row.** `campaigns/service.py:141-143` says they *"stay on the row for now — ADR-162 point 1 … is not built"* immediately above a call to `set_envelope_fields`; `rendering/renderers/base.py:50-56` says *"Subject and preheader are still read off the variant … and is not built"*; `delivery/service.py:568-569` says *"Subject lives on the variant until ADR-162 point 1 moves it into a header module."* `migrate_0011_variant_header_module.sql` moved them into a header module and `migrate_0012_drop_variant_envelope_columns.sql` dropped the columns. All three describe the pre-0011 world and will send the next reader looking for a column that is gone. Source: `/interview-prep-baseline` 2026-09-18.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 No comment or docstring says subject and preheader live on the variant, or that ADR-162 point 1 is unbuilt
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 124, section "Bugs", position 43 in that section (top = do next). The description is the original entry, verbatim.

Done 2026-10-04. Still true when checked, at new lines.
- The three named comments were rewritten to say where the envelope lives now: campaigns/service.py (create_variant_for_campaign docstring), rendering/renderers/base.py (RenderedArtifact.envelope) and delivery/service.py (the send path's subject fallback). They now say: the envelope module, written by set_envelope_fields, read by envelope_fields_for_variant, frozen into the snapshot frame at send; columns dropped in migration 0012.
- A sweep for "ADR-162 point 1" found three more stating the same false thing, also rewritten: templates/campaign_detail.html ("still columns"), rendering/renderers/email.py ("still falls back to those while they exist") and campaigns/service.py:345 ("The columns still exist"). Verified VariantDB has no subject or preheader column and migration 0012 drops both. approvals/actions/ai_subject_apply.py:153 is accurate and was left alone.
- Comments only, so no test; a test asserting on comments would test nothing. Full backend suite 1248 passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Six comments that placed subject and preheader on the variant, or called ADR-162 point 1 unbuilt, now describe the envelope module, its writer and reader, and the snapshot frame at send. Comments only; verified against the models and migration 0012, full suite green.
<!-- SECTION:FINAL_SUMMARY:END -->
