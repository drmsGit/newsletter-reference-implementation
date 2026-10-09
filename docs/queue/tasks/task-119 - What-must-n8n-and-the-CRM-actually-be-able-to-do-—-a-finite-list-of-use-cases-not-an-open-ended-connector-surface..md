---
id: TASK-119
title: >-
  What must n8n and the CRM actually be able to do — a finite list of use cases,
  not an open-ended connector surface.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-10-09 18:13'
labels:
  - needs-adr
  - backend
dependencies: []
type: decision
ordinal: 300300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
📋 **What must n8n and the CRM actually be able to do — a finite list of use cases, not an open-ended connector surface.** Surfaced 2026-09-18 (user). Sequenced **after [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]**, which both consumers sit behind, and deliberately scoped small: *"automation can be 1-2 use cases (and maybe those won't change for a long time) and crm can be very limited too (get leads and consents, maybe keep track about actions on website like 'downloaded package')"*. **The reason it can be small is that the first adopter is the playbook site itself** — not a living company that constantly changes — so the requirement converges on a fixed list rather than growing. n8n is the named orchestrator because it is well known to the user and German (hosting and GDPR posture); **the CRM is not chosen yet, and choosing it is part of this item.** Note that [[ADR-167 — Anonymous Push Recipients Originate in the Source System]] already made the source system structurally authoritative — *the platform does not admit a recipient the CRM does not own* — so a CRM connection is **the enforcement path for a rule already accepted**, not an optional integration.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 414, section "Needs ADR", position 3 in that section (top = do next). The description is the original entry, verbatim.

2026-10-08 queue cleanup (backlog-sequencer run 3, verified by hand): related since today: task-53 (done 2026-10-08, ADR-166 addendum) lets an integration read back what its write permission covers, through the MACHINE_READS table in backend/app/auth/policy.py. Any finite list of what n8n and the CRM must be able to do can now include reading back recipients, content, campaigns and audiences. Derived data, such as activity and signals, still needs view.

2026-10-09 (interview-review triage, Client Q5): the generated TypeScript client promises only that this checkout's client matches this checkout's server (ADR-170 point 5). Outside integrations get no compatibility promise from it. Whatever contract n8n and the CRM need, including what happens when a response's meaning changes but its shape does not, is part of this task's design.
<!-- SECTION:NOTES:END -->
