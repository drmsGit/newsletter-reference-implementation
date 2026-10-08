---
id: TASK-106
title: >-
  Benchmark the recipient-processing pipeline at 100 / 1,000 / 10,000 / 100,000
  recipients.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-10-08 20:51'
labels:
  - backend
dependencies: []
priority: p3
type: chore
ordinal: 205900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Chore] — P3 in urgency, P1 in honesty: we currently have no basis for any claim about scale.** **Benchmark the recipient-processing pipeline at 100 / 1,000 / 10,000 / 100,000 recipients.** "Postgres and a modular monolith scale fine" is an argument about architecture, and the workload that actually decides it is per-recipient: audience resolution, consent and exclusion gating, decision resolution, rendering, delivery preparation. Measure SQL query count (the N+1 detector), database time, application time, peak memory and throughput per stage. **Why it matters here specifically:** the playbook makes claims to readers who cannot run the code, and a reference implementation that is quietly O(n) in queries teaches the N+1 to everyone who copies it. A pilot customer needs this run again against their real volumes — this baseline is for the public artefact's credibility, not for their capacity planning. Source: `CODE_QUALITY_RELEASE_POSITIONING_2026-09-19` §5.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 362, section "Features", position 59 in that section (top = do next). The description is the original entry, verbatim.

2026-10-08, from task-98: the 2026-08-07 review also suggested three performance smoke tests on the per-recipient send path tracking query COUNT as well as duration ("runtime alone hides the per-recipient query/commit pattern"). Nothing in backend/tests measures query count on that path today (query counting exists only for the recipient list projection, tests/test_channels.py around line 1905, and session updates in tests/test_auth.py). They belong here, with this benchmark's per-stage query count, rather than in task-98; whether a small query-count assertion should then guard the send loop in CI is this task's call.
<!-- SECTION:NOTES:END -->
