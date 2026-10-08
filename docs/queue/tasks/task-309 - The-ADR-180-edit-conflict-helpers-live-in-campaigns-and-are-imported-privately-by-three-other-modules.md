---
id: TASK-309
title: >-
  The ADR-180 edit-conflict helpers live in campaigns/ and are imported
  privately by three other modules
status: To Do
assignee: []
created_date: '2026-10-08 22:45'
labels:
  - backend
dependencies: []
type: chore
ordinal: 205660
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Chore: the ADR-180 edit-conflict helpers live in `campaigns/`, and three other modules import its private functions.** Found by the code-slimmer sweep of 2026-10-08 (D3); imports verified by hand.

**What is shared from where.**
- `IF_MATCH` and the private `_expected` are defined at `backend/app/campaigns/router.py:80-99` and imported by `content/router.py:12`, `audience/router.py:31` and `overrides/router.py:14`.
- `StaleWrite` and `refuse_stale` are defined in `backend/app/campaigns/service.py` and imported by three routers. The services import them inside functions (`content/service.py:317`, `audience/service.py:87`, `overrides/service.py:180`) to avoid a circular import.
- `_stale` is defined twice: `campaigns/router.py:100` and `audience/router.py:54`.

ADR-180 (A Lock Is Advisory for a Person and Binding for a Machine) is platform-wide; only its first user was campaigns. No ADR says where the helpers must live.

**What to do.** Move them to `backend/app/concurrency.py`, beside `backend/app/pagination.py`, which is the same kind of cross-cutting helper. Make `_expected` public under a real name, drop the duplicate `_stale`, and remove the function-local imports. The existing optimistic-concurrency tests (task-110 and the content, audience and override edits) cover the move.
<!-- SECTION:DESCRIPTION:END -->
