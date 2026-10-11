---
id: TASK-313
title: 'No licence is chosen, yet the project calls itself open-source'
status: To Do
assignee: []
created_date: '2026-10-09 07:06'
updated_date: '2026-10-11 20:44'
labels:
  - docs
dependencies: []
type: decision
ordinal: 201130
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Decision: the project has no licence, yet calls itself open-source.** Split out of task-306 on 2026-10-09. The user kept the licence open for now while the rest of the repository's front door was done. `README.md` now says "Not chosen yet; this is an open decision."

**Why it matters.**
- `CLAUDE.md` describes the project as an "open-source newsletter architecture MVP". Without a licence file, nobody outside has rights to reuse the code or the documents.
- The repository is private today (github.com/drmsGit/newsletter-reference-implementation), so nothing is exposed yet. This matters at the first outside reader: an external reviewer, the beta's publication (`docs/business/BETA-SCOPE.md`, Definition A: the playbook and repository are published).

**What the decision has to answer.**
1. **One licence or two.** The code and the playbook/docs are different kinds of work: the published material is the playbook, and the code proves it. Permissive code licences (MIT, Apache-2.0) and documentation licences (CC BY, CC BY-SA) answer different questions. Apache-2.0 also carries a patent grant.
2. **What "teachable and tailorable" needs.** Adopters are meant to copy and adapt the architecture (CLAUDE.md, positioning). A copyleft licence would constrain how they ship what they build from it.
3. **Timing against the name.** The product name is provisional and not legally cleared. The repository is planned to move to the product's own GitHub account once it is (the naming decision's 2026-10-05 entry, `docs/business/decisions/naming-brand-tarrow.md`). Choosing before or after that move changes nothing legally, but the copyright line names a holder.
4. **Third-party content.** The seed content (`backend/scripts/seed_content_chatgpt.csv`) and any assets must be licensable under whatever is chosen.

A business decision, recorded in `docs/business/decisions/`, not an ADR. Then add `LICENSE` (and a docs licence note if two), and update the licence section of `README.md`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A licence decision is recorded in docs/business/decisions/, covering code and docs
- [ ] #2 LICENSE (and a docs licence note if the docs differ) exists, and README.md's licence section names it
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-11, the user set the November 2026 presentations as the focus (docs/business/PRESENTATIONS-2026-11.md): licensing options are what the agencies will ask about first.
<!-- SECTION:NOTES:END -->
