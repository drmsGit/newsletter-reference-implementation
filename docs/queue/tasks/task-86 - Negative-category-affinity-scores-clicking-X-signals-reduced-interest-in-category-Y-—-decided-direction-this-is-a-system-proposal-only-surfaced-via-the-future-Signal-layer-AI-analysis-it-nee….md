---
id: TASK-86
title: >-
  Negative category-affinity scores ("clicking X signals *reduced* interest in
  category Y") — decided direction: this is a system proposal only, surfaced via
  the future Signal layer/AI analysis (it nee…
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 203900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** Negative category-affinity scores ("clicking X signals *reduced* interest in category Y") — decided direction: this is a **system proposal only**, surfaced via the future Signal layer/AI analysis (it needs real behavioral evidence to get the sign/magnitude right), with the existing override mechanism as the channel for a manager to accept, reject, or manually adjust it. **Reinforced 2026-07-05:** a related, simpler negative signal is now separately confirmed — unsubscribe (incl. spam-complaint, which providers normalize to the same event) counts as a genuine negative interest signal, distinct from this per-category-affinity feature. Philosophy: "better to stop emailing someone who's checked out than keep pushing." A softer alternative — a "pause/snooze" option instead of only a hard unsubscribe — was also floated; explicitly flagged as beyond POC scope. See `docs/playbook-strategy.md` Decision Log, 2026-07-05, item 6, and `docs/business-interview-baseline.md` §M2. Explicitly **not** a general "just type in a negative score" input — no freeform manual negative-scoring capability. Depends on the Signal layer (Insight Q1) and the override-strategy redesign (Campaigns Q3/Overrides Q1) both landing first. **Confirmed connection:** the category impact graph view already has a working `avg_delta < 0` display branch (`frontend/router.py:1765-1767`, fed by `AVG(PreferenceUpdateLogDB.delta)`) — today it's only reachable via the Q4 validation bug (an accidentally-entered negative assignment score), not any legitimate signal. This feature is what would make that existing UI branch meaningfully fire on purpose, once the Q4 zero/range validation closes off the accidental path. Source: [[Interview Prep - Decision, Overrides, Insight]] → Insight Q4 (addendum).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 248, section "Features", position 39 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
