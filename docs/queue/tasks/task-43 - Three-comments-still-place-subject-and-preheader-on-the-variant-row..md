---
id: TASK-43
title: Three comments still place subject and preheader on the variant row.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 124, section "Bugs", position 43 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
