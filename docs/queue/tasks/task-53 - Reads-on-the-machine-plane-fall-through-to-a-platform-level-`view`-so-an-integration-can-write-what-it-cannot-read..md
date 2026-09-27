---
id: TASK-53
title: >-
  Reads on the machine plane fall through to a platform-level `view`, so an
  integration can write what it cannot read.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
type: feature
ordinal: 200600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — blocks a CRM connector, and [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]] raised its weight.** **Reads on the machine plane fall through to a platform-level `view`, so an integration can write what it cannot read.** Every GET resolves to `VIEW` (`auth/policy.py`), and `view` is not implied for an integration the way it is for every role — deliberately, since implying it would hand every integration the recipient list. The consequence: an integration granted `recipients.manage` POSTs a recipient successfully and gets a 403 reading one back, and the only remedy available is granting `view`, which is all-or-nothing and platform-level and reopens exactly the exposure the asymmetry protects. **A CRM connector that cannot read back what it wrote cannot reconcile**, so this becomes real the moment the CRM use-case list is written (see the Needs-ADR item on what n8n and the CRM must do). **The asymmetry itself is correct and stays** — what needs deciding is whether machine reads get their own scoped keys instead of falling through. Now sharper because ADR-168 put people on this plane too, so `view` carries two meanings on one set of routes. Source: [[Interview Prep - Auth, Permissions, Machine Principals]] → Q3.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 154, section "Features", position 6 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
