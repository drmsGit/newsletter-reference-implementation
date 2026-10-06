---
id: TASK-214
title: No per-recipient delivery query and no reverse membership lookup
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 14:20'
updated_date: '2026-10-06 18:54'
labels:
  - backend
dependencies: []
priority: p2
type: feature
ordinal: 200385
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** **No per-recipient delivery query and no reverse membership lookup** (Q5) — and the second is structural, not missing: rule-based membership is **computed at resolution time and never stored**, so only pins are rows. "Which groups is Anna in" is answerable only by resolving every group. Bears on [[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]].

Source: [[Manager Workflow - design interview]] → What Cluster 4 produced, gap 14 (Q4.5).

**Verified against the code 2026-09-27:** delivery lists by snapshot (`backend/app/delivery/router.py:90`) and executions by send instance (`:107`), never by recipient; audience lists members by group only (`backend/app/audience/router.py:72`). No `groups_for_recipient` / `executions_for_recipient`-shaped function exists in `backend/app/`.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Background: Manager Workflow Q4.5 — the recipient screen answers "why did Anna get this": consent (exists), what was sent (since task-50: GET /recipients/{id}/activity, this brand's deliveries with engagement), and which audiences (missing; rule membership is never stored).
2. Decision with the user (2026-10-06): worked out on request for one person, per channel, as of now, with the reason; nothing stored (ADR-093).
3. Tests first: tests/test_audience_memberships.py — a rule match names the rule, a hand-add, an exclusion, not agreed, untouched groups and other brands left out, per channel, and member == in what a send resolves (every person x group x channel), the route (paged, 404, channel required).
4. audience/service.py: find_by_criteria(only_ids=...) to check one person against a rule; audience_memberships. recipients: RecipientAudienceGroup / MembershipReason, GET /recipients/{id}/audience-groups (paged per ADR-185, classified in test_pagination).
5. Mutation-check, suite, contract, a read of dev recipients.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

Choices within the design: only the groups that touch the person are listed (a rule matches, agreed or not, or a hand-add), in name order; reasons are structured (rule, pinned, excluded, not_agreed) in that order; exclusions are checked the way resolution checks them (among people who agreed), so an exclusion never appears for someone who has not agreed; the route is paged like the group list because the number of groups grows with use (ADR-185) — test_pagination's classification test caught it.
The per-delivery half of the entry was already built (task-50, recipient_activity); no React recipient page exists yet, so nothing in the manager client shows either — raised with the user as a follow-up.
Validation: 15 tests, failing first; 9 mutants caught, 1 equivalent (dropping the brand filter on groups still lists no foreign group, because list_blocks and get_member_recipient_ids are brand-scoped too — isolation guarded twice). Backend 1395, contract regenerated and matching. Live, read-only: dev recipients 1-3 and 20 on email and push — every row agrees with what a send resolves; recipient 20 is in 'All demo recipients' on email and out on push, 'not agreed to push'.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
One person's audience groups can now be asked for, per channel and as of now: GET /recipients/{id}/audience-groups lists the working brand's groups that touch them, each with in/out and why — matched rule, added by hand, removed by exclusion, not agreed to the channel. Worked out for that person against the same rules a send uses; nothing is stored (ADR-093), and "in" equals what a send would resolve. The per-recipient delivery half already existed (task-50). Verified by 15 tests, 9 caught mutants (1 equivalent), the suite, the contract and a read of dev recipients.
<!-- SECTION:FINAL_SUMMARY:END -->
