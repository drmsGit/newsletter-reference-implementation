---
id: TASK-102
title: AI ledger sums the whole `ai_runs` table on the hot path — twice.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 205500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — LOW priority.** **AI ledger sums the whole `ai_runs` table on the hot path — twice.** Surfaced 2026-08-02 (`/interview-review`, AI Q5). `tokens_used()` pulls every run into Python and filters there, because `is_billable` tests a *provider set* rather than a column, so it cannot be a plain `WHERE` (`service.py:97-104`). It runs before every gated call. `spend_to_date()` (added the same day for the USD readout) walks the same table again, so the Settings page and every AI run each pay two full scans. **Genuinely not urgent** — the table holds 20 rows, and even at ~1,000 runs/month it is low tens of thousands of rows a year, summed in milliseconds against a model call that takes seconds. **Agreed fix is the cheap one:** push the provider filter into SQL (`SUM(...)` with `WHERE provider NOT IN (...)`), which removes both scans from Python and needs no running counter and no cache that can go stale. Rejected for now: a materialised counter or windowed sum — more moving parts than the problem justifies, and a counter introduces its own consistency question under the concurrency item above. Source: [[Interview Prep - AI]] → AI Layer Q5.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 322, section "Features", position 55 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
