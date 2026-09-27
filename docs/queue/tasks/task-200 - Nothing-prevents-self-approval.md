---
id: TASK-200
title: Nothing prevents self-approval
status: Done
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-09-27 14:42'
labels:
  - backend
dependencies: []
priority: parked
type: bug
ordinal: 104800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug]** **Nothing prevents self-approval** (Q8). `may_decide` checks the action's permission against the request's brand and never compares decider to requester. Safe only while machines requested and could not approve; a hole the moment a person can request.

Source: [[Manager Workflow - design interview]] → What Cluster 5 produced, gap 17 (Q5.8). The same cluster notes a record owed: ADR-168's build note — *"a person firing a send is the approval"* — becomes insufficient once people can request.

**Verified against the code 2026-09-27:** `may_decide` (`backend/app/approvals/service.py:345-377`) checks only `approve_permission`. Nothing in `backend/app/` compares `requested_by_id` with the decider.

Related: [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]].
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

Done 2026-09-27. Fixed per-action rather than globally, and the investigation changed the fix.

**A person can request** — `campaigns/router.py:229` creates a hold with `requested_by_type=ACTOR_USER` — so the task's premise held. But the action it creates is `ai.apply_subject_preheader`, and **for that action the requester approving is the intended flow**: a manager asks the model for a subject, reads it, applies it. ADR-082 wants *a* human to publish, not a second one, and the requester is usually the only human watching. A global decider≠requester rule would have broken it on the day it was written.

`send.fire_send_instance` cannot reach the case at all: a person firing a send **is** the approval (ADR-174 point 4), so no row is held, and a machine cannot approve.

**So the hole was latent, not live** — it opens when a third action is registered where approval is separation of duties rather than review.

**The fix:** `ApprovableAction.requester_may_decide`, required with no default, matching `default_ttl_seconds`'s reasoning that a forgetful module must not get an answer by omission. Either default is wrong: `False` breaks the AI flow, `True` silently reintroduces the hole. `send_fire` declares `False` — the value it would want if a person ever could request one — and `ai_subject_apply` declares `True`.

The condition lives in one helper, `requester_is_decider`, used by both `may_decide` (which gates the button) and `resolve_for_decision` (which writes the sentence). It compares actor **type** as well as id, because `requested_by_id` has no foreign key and a machine's id and a person's id come from different tables. The refusal has its own wording, because the permission sentence would be false here — this person holds the permission.

Six tests, all mutation-verified. One was written only because a mutation run exposed that the first four passed with the gate in `may_decide` disabled: they all went through `resolve_for_decision`, which carries its own check.

660 passing, up from 655.
<!-- SECTION:NOTES:END -->
