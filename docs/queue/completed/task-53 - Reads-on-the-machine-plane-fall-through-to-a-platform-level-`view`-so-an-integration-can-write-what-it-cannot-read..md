---
id: TASK-53
title: >-
  Reads on the machine plane fall through to a platform-level `view`, so an
  integration can write what it cannot read.
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 13:56'
updated_date: '2026-10-08 21:13'
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

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An integration's write permission admits reads of exactly the routes listed for it; derived data and unlisted routes stay behind view
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 154, section "Features", position 6 in that section (top = do next). The description is the original entry, verbatim.

Built 2026-10-08, commits 3d65c2e and the ADR commit after it. Asked of the user one at a time, both with the recommendation:
1. A write permission also admits reads of its own area for an integration; no new permission names; read-only permissions later, when a read-only integration exists (reporting, task-58).
2. Only what the permission writes: derived data (activity, memberships, signals, per-recipient results, previews listing people, reporting) stays behind view.
Recorded in ADR-166's addendum of 2026-10-08 (adr-author; corrected once to drop two rows) and a playbook entry.

Where it landed: MACHINE_READS in backend/app/auth/policy.py, exact route templates each admitted by one permission (a new read route stays behind view until listed); the guard in backend/app/auth/dependencies.py asks for the listed permission instead of view for an integration that does not hold view, then checks it as for a write (brand-scoped in the working brand). /settings and /integrations deliberately not listed (found by the adr-author): changing either is person-only, so a machine holding those permissions writes nothing.

Tests: tests/test_machine_reads.py (7; 4 mutants killed, including one table entry removed); tests/test_api_guard.py's "a machine is not given view for free" now uses insight.write, the case its docstring describes. Suite 1515. Live check against the running API as scratch integrations over HTTP: recipients.manage reads the list and one recipient (200), not their activity (403) nor content (403); insight.write cannot list recipients (403).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
An integration can now read back what its permission lets it write - a CRM connector with recipients.manage reads recipients and their consent - without the platform-wide view, and without reaching derived data such as activity, memberships or signals. An explicit route list keeps every new read closed until someone opens it. Decided with the user and recorded in ADR-166's 2026-10-08 addendum; verified by 7 tests (4 mutants killed), the full suite and the running API.
<!-- SECTION:FINAL_SUMMARY:END -->
