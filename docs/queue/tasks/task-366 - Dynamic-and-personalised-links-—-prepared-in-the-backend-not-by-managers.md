---
id: TASK-366
title: 'Dynamic and personalised links — prepared in the backend, not by managers'
status: To Do
assignee: []
created_date: '2026-10-11 19:10'
labels:
  - needs-adr
  - backend
dependencies: []
type: decision
ordinal: 305600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Decision]** Raised by the user on 2026-10-11 while designing the expression dictionary (task-365). That design keeps variables out of links on purpose: a link built from recipient data is a question about tracking and safety, and it needs its own design. In the user's words, companies will need dynamic or personalised links, such as a single-sign-on login link, or a transactional email whose image link carries a dynamic article id. It is "maybe not in the daily business of a manager" and could be prepared in the backend when needed.

**Questions for its design.**
- Who defines a dynamic link: a developer or integrator in the backend, or in a declared link type, rather than a manager in the editor.
- Where its values come from: recipient fields, the transactional payload (task-134 point c wants a global variable solution for arbitrary transactional JSON), or a signed token the platform mints, as for SSO.
- How it fits link tracking: tag_params, the nl_content attribution in `backend/app/rendering/tracking.py`, and https-only URL fields (ADR-194 addenda).
- What the delivery record keeps, so the as-sent reconstruction stays exact (ADR-183).
- Erasure, since a personal URL is personal data (ADR-154).
- Signing and expiry for links that grant access (SSO).

**Related.** task-365, task-134, task-294; ADR-183, ADR-154, ADR-194.
<!-- SECTION:DESCRIPTION:END -->
