---
id: TASK-310
title: 'Approval logic sits in main.py''s ApprovalRequired handler, owned by no service'
status: To Do
assignee: []
created_date: '2026-10-08 22:45'
labels:
  - backend
dependencies: []
type: chore
ordinal: 205670
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Chore: approval logic sits in an exception handler in `main.py`, which no service owns.** Found by the code-slimmer sweep of 2026-10-08 (D4); location verified by hand.

`_approval_required` (`backend/main.py:519-665`, the handler for `ApprovalRequired`) holds approval logic itself:
- how a held action's subject id is found;
- the check that the subject belongs to the caller's brand;
- how the request is summarised;
- a raw `PendingActionDB` query for an already-open request (around `:625-635`).

None of that is in `backend/app/approvals/service.py`. `main.py` is about 930 lines, much of it handlers.

**What to do.** Move the decision into the approvals service: for example `hold_for_approval(db, exc, principal)`, returning the status code and body. The handler becomes a thin adapter. Tests reach this path over HTTP (`backend/tests/test_approvals.py`, the held-action tests), so they survive the move unchanged.

**Not covered by task-237.** That task audits raw SQL strings and file paths; this is an ownership problem. ADR-142 section 4 governs the inbox.
<!-- SECTION:DESCRIPTION:END -->
