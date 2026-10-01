---
id: TASK-34
title: 'In `auth/policy.py` order IS semantics, and a reordering fails no test.'
status: Done
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-10-01 21:32'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 103400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P2. The table is right; nothing defends its order.** **In `auth/policy.py` order IS semantics, and a reordering fails no test.** Six narrow/broad prefix pairs are correct only because of the line they sit on, so a broad prefix inserted above a narrow one silently downgrades it. Not hypothetical: the 2026-09-18 `sends.plan` / `sends.execute` split hit exactly this, and moving `/ui/send-instances/` above the dispatch route makes firing a real send require only the permission to *prepare* one. A test pins that one pair; **generalise it to all six.** Second, smaller: `("/ui/brand", VIEW)` is a live prefix collision with `/ui/brands`, harmless today only because brand CRUD lives in `auth_router`, which is not wrapped in `enforce_policy` — an accident rather than a design, and it stops being harmless the day those routes move. The prefix table itself stays: one legible policy that refuses an unclassified write is worth more than per-route decorators, which fail open when forgotten. Source: [[Interview Prep - Auth, Permissions, Machine Principals]] → Q1.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 104, section "Bugs", position 34 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added the general rule the entry asked for: no WRITE_POLICY entry may sit below a prefix of itself (test_policy_prefixes.py). Measured first: there are 15 refining pairs, not six, and all of them were already guarded by per-pair tests — the stale part of the entry. What was unguarded is the next pair: a new narrow entry added below its broad prefix passed all 781 tests, and is now caught only by this rule. The /ui/brand vs /ui/brands collision was already fixed on 2026-09-20 and guarded by the mid-segment check. 784 pass.
<!-- SECTION:FINAL_SUMMARY:END -->
