---
id: TASK-136
title: >-
  General data lifecycle / deletion & retention policy — not designed at all
  yet.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-10-01 21:24'
labels:
  - needs-adr
  - backend
dependencies: []
type: decision
ordinal: 300150
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
📋 **General data lifecycle / deletion & retention policy — not designed at all yet.** Confirmed during the interview review: the project has no deletion/cleanup story anywhere. Two concrete instances found so far, both symptoms of the same missing policy:
  - **Category/content record deletion vs. archival.** Categories accumulate historical value via preference/engagement scoring (`ContentCategoryAssignmentDB.score`, `RecipientPreferenceDB`) — hard-deleting a category breaks the ability to interpret that historical data (what a past engagement signal even meant). Leaning toward: never hard-delete a category/content record that has any historical usage — **archive** instead. An archived category stops contributing to *new* preference scoring; existing preference influence from it decays naturally over time (same mechanism as the not-yet-built Phase 3C signal decay, [[ADR-112 — Signals Use Time-Based Decay]]) rather than being force-zeroed. Only once a category is fully unused *and* decayed out would actual deletion become safe to consider.
  - **Snapshot lifecycle.** No uniqueness/idempotency key on snapshot creation means unbounded accumulation of near-duplicate snapshots per variant/recipient — consistent with "immutable append-only history" (ADR-061) but with no TTL, retention rule, or delete endpoint at all.

  Needs a dedicated ADR (none exists today) covering deletion/retention policy generally — likely also relevant to other accumulating tables (engagement events, decision resolutions, preference logs) once they're examined the same way. Tightly coupled to the Phase 3C signal layer design already flagged as open in `docs/playbook-strategy.md` §7. Source: [[Interview Prep - Content, Campaigns, Audience]] → Content Q6 (addendum); [[Interview Prep - Snapshots, Rendering, Email Modules]] → Snapshots Q6.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 489, section "Needs ADR", position 20 in that section (top = do next). The description is the original entry, verbatim.

2026-10-01, from task-33: integration_auth_failures needs a retention period, and nothing prunes it. Deferred here by the user's decision because ADR-153 leaves the audit/evidence retention question to this item. Urgency is low: since task-33 the table grows linearly in time and in the number of sources (one row per real credential plus one shared UNKNOWN_KEY bucket, per client per hour), no longer per attempt. The login rate-limit counters, by contrast, are pruned on write to their longest window, because they are rate limits rather than evidence.
<!-- SECTION:NOTES:END -->
