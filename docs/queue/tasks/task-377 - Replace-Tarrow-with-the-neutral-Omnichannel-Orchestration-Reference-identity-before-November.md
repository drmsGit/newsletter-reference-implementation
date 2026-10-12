---
id: TASK-377
title: >-
  Replace Tarrow with the neutral Omnichannel Orchestration Reference identity
  before November
status: To Do
assignee: []
created_date: '2026-10-12 19:57'
labels:
  - docs
  - backend
  - frontend
dependencies: []
references:
  - docs/business/PRESENTATIONS-2026-11.md
  - product.json
  - backend/scripts/rename_product.py
type: chore
ordinal: 201135
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Diede approved the author-led introduction on 2026-10-12: Diede Slembrouck; Building a communication system you control.; An omnichannel orchestration reference—with a playbook, working code and a live newsletter. Use Omnichannel Orchestration Reference as the neutral project display title, with a corresponding neutral slug (omnichannel-orchestration-reference). Tarrow is discarded as the future brand. README.md:1 and product.json:2-3 still present Tarrow, so the repository front door and runtime identity contradict the new direction. This work belongs before the November agency/potential-pilot presentations (docs/business/PRESENTATIONS-2026-11.md). It is distinct from task-376’s final name/clearance and task-375’s broader positioning work, neither of which needs to finish just to neutralise the discarded brand.

The existing machinery matters: backend/scripts/rename_product.py:11-23 rewrites living tracked files and preserves dated records; :45 excludes business decisions and queue history; :75 discovers tracked files only. Current design/presentation folders are untracked and outlined SVG/PNG logos are not ordinary text replacements. Inventory their current-use surfaces separately while preserving immutable reviewed rounds and P2 benchmark hashes. backend/tests/test_product_name.py:24-61 verifies source/runtime/retired-name consistency; :63-76 verifies renamed-note links. A slug change may sign users out once because the session cookie follows the slug.

The GitHub-facing README should use the author-led framing and accurate omnichannel scope (ADR-165). Live newsletter is intended public-package wording, not proof the own deployment/signup is already operational; label it planned until running. Keep licensing/PoC status accurate. External GitHub description/social preview and repository identity are not updated by text substitution: inventory them and resolve authorised surfaces or report owner actions. Keep repository/local paths, database, volumes and Git history in place unless separately authorised; do not publish confidential naming evidence.

Diede additionally confirmed a conventional neutral design system is enough at this stage. Use readable standard typography and established component patterns, avoiding new custom-letter/logo/rr work or an extensive rebrand. Preserve calm dense layouts, both densities, accessibility/focus/states and labelled system/human semantic cues. Coordinate with task-372 for demo-screen styling rather than duplicate it.

Decision: docs/business/decisions/naming-brand-tarrow.md, 2026-10-12 addenda (confidential, not public PR copy). Naming is a business decision; ADR-165 governs channel-neutral scope. No permanent brand/legal clearance is adopted by the neutral title.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 product.json and active name-driven surfaces consistently use Omnichannel Orchestration Reference and its neutral slug; Tarrow is retained as a retired name.
- [ ] #2 The GitHub-facing README uses the approved author-led introduction and accurate omnichannel scope, with licence/PoC status and planned-versus-live newsletter status explicit.
- [ ] #3 A reviewed dry-run inventory covers tracked files, untracked current-use presentation/design assets and external GitHub identity surfaces; authorised surfaces are aligned and remaining owner actions documented.
- [ ] #4 Active identity assets use conventional typography rather than the discarded Tarrow/rr branding; dated records, ADR titles and immutable reviewed logo/benchmark assets remain preserved.
- [ ] #5 Relevant existing rename/name-source/link and backend/frontend checks pass, active rendered identity surfaces are visually checked, and cookie sign-out implications are documented.
- [ ] #6 The task is linked in November preparation without waiting for a final trademark brand; repository paths, deployed/data state, private evidence and unrelated work remain unchanged; demo styling remains with task-372.
<!-- AC:END -->
