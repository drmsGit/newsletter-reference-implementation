---
id: TASK-107
title: 'Nothing can remove an audience group member, and a membership cannot expire.'
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-10-06 20:00'
labels:
  - backend
dependencies: []
type: feature
ordinal: 206000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — a temporary exclusion with no expiry is a permanent one somebody has to remember to undo. Raised by the user 2026-09-24.** **Nothing can remove an audience group member, and a membership cannot expire.** `AudienceGroupMemberDB` (`app/audience/db_models.py:41-47`) carries `id`, `group_id`, `recipient_id` and `added_at` — no deletion date, no TTL, no record of who added the row or why. Surfaced by [[ADR-176 — A Negative Decision Outranks a Positive One]] and the [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §7 addendum, which move the soft-suppression override from a per-recipient pin up to *"remove the exclusion segment from the group"*. That shape is better — a list can be inspected, reasoned about and removed as a unit, where a pin is a quiet exception nobody reviewing the audience would notice — but it only works if an orchestrator writing *"this recipient should not get newsletters at the moment"* (news fatigue, over-mailing) can also **stop** saying it. Today it cannot. **Two candidate shapes, and the choice is the design question:** a delete call on a membership, or an `expires_at` that resolution honours. They are not exclusive and lean different ways — a delete leaves no trace of the suppression having happened, an expiry leaves the row and dates it, which suits an audit story better and costs a filter in `resolve_audience`. **Also unrecorded either way: who added the member and on what grounds**, which is the *"why is this recipient getting a reactivation email"* question the Manager Workflow interview raised at Q1.5 and answered as *"comments are always optional"* — optional for a person, but a system-written exclusion with no reason is unreviewable. Sequence with the audience screens, not before them.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 364, section "Features", position 60 in that section (top = do next). The description is the original entry, verbatim.

2026-09-27: related — task-217 (a membership records no reason; external automation must say why this recipient).

2026-10-06, task-293 interview: removing a member exists (DELETE /api/audience-groups/{id}/members/{recipient_id}) and the React editor will offer it, audited (task-295, task-297) — the title's 'nothing can remove a member' is stale. Expiry was not chosen: groups are temporary by design (ADR-123), so a hand-add lives as long as its group; the expiry question stays open, if it is wanted at all.
<!-- SECTION:NOTES:END -->
