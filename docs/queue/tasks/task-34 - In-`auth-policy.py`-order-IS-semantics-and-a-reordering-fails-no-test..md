---
id: TASK-34
title: 'In `auth/policy.py` order IS semantics, and a reordering fails no test.'
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
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
