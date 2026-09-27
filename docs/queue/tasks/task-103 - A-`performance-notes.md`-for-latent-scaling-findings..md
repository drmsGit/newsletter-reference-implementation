---
id: TASK-103
title: A `performance-notes.md` for latent scaling findings.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - docs
dependencies: []
type: feature
ordinal: 205600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — LOW priority.** **A `performance-notes.md` for latent scaling findings.** Proposed by the user 2026-08-02 during `/interview-review` (AI Q5): reviews keep surfacing small "this is O(n) and n will grow" observations that are real but never "do next", and putting them in a prioritised backlog either buries them or inflates them. Collect them in one document instead. **Design note that decides whether it works:** give each entry a **trigger threshold** — the number at which it starts to matter (rows, recipients, runs/month) — alongside symptom, location, current cost and candidate fix. Without that column it becomes a graveyard of things nobody can tell are urgent; with it, a reader can scan for "have we crossed this yet?" Seed it with the AI ledger item above, and sweep the existing backlog for others already logged (the serial per-recipient send loop in `send_send_instance` is an obvious first candidate). **Two more from the 2026-08-07 code review, both P3 and both textbook entries for this document rather than the backlog:** every authenticated request writes — `user_for_token()` updates `last_seen_at` and commits on each call, turning read-heavy UI traffic into write traffic, so persist only when the stored value is older than 5–10 minutes (P3-01); and **many UI list views call `.all()` with no pagination** — **REPRICED 2026-09-21 by [[Manager Workflow - design interview]] question 2.10, which resolved that the product must not assume a record count: pagination and server-side filtering are now a precondition for the React list screens existing, not latent scaling. It applies to content, campaigns, audiences, recipients and approvals, and it must land before those screens are finished rather than after, because every dimension and readiness filter is a query parameter the API has to accept.** Original note follows — — categories, campaigns, users, assignments and the graph/report routes — which is fine on seed data and grows linearly, with the graph routes becoming expensive first (P3-02). Source: [[Interview Prep - AI]] → AI Layer Q5; code review 2026-08-07 P3-01, P3-02.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 324, section "Features", position 56 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
