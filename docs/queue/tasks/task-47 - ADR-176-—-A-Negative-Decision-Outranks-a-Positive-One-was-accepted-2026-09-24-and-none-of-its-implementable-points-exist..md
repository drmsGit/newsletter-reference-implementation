---
id: TASK-47
title: >-
  [[ADR-176 — A Negative Decision Outranks a Positive One]] was accepted
  2026-09-24 and none of its implementable points exist.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-09-27 14:22'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100050
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — an accepted ADR is not implemented, nothing tracked it, and the unbuilt half is the compliance-shaped one. Verified 2026-09-27.** **[[ADR-176 — A Negative Decision Outranks a Positive One]] was accepted 2026-09-24 and none of its implementable points exist.** Its only previous mention anywhere in this file was incidental, so nothing said the work was outstanding — the inverse of a stale entry claiming work is open when it is done, and harder to notice.

  **Point 1 — an exclude block must reach a hand-pinned recipient. Not implemented.** `resolve_audience` (`backend/app/audience/service.py`) still computes `(include_ids - exclude_ids) | pins`; the ADR requires `(include_ids | pins) - exclude_ids`. The function's own docstring still documents the **reversed** 2026-07-26 rule — *"a manual pin … is always included; exclude blocks … never remove a hand-pinned recipient"* — so code and docstring agree with each other and disagree with the accepted decision. **This is a correctness gap with a compliance flavour rather than a missing feature.** The record's argument is that **wrongly including costs more than wrongly omitting** — *"a person who should not have received it and did cannot be un-sent … and is the failure that reaches a supervisory authority"* — and the [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §7 addendum builds on the same mechanism for system-written temporary exclusions. Today a manager's pin still beats an exclusion segment, which is precisely what the decision reverses. **The consent and suppression floor is untouched by this and stays absolute**; only the precedence between two people's intentions changes.

  **Point 4 — sends always re-resolve; `freeze` is removed. Not implemented.** `SendInstanceDB.audience_resolution_mode` (`backend/app/delivery/db_models.py:35`) and `prepare_send_from_audience` (`backend/app/delivery/service.py:202`) both still default to `"freeze"`, and the validator still accepts it — so, in the ADR's own words, *"the mode that should never be used is the one a caller gets by saying nothing"*. `reconcile_executions_to_audience` should become the always-path. **Whether the column is dropped or merely always set is explicitly left as a build question** by the record, so decide it here rather than treating it as settled: dropping it is a hand-written migration in a repo with no Alembic, keeping it is a setting nobody sets.

  **Points 2, 3 and 5 need nothing.** 2 is the principle itself. 3 states a distinction the record deliberately declines to put in the schema. 5's screen rule stands, and its `resolve_audience` default was removed on 2026-09-27 — see that record's dated addendum, which reverses that one clause because the trap point 5 named was subsequently observed as a real push failure rather than a hypothetical.

  **Sequence point 1 before anything that writes exclusion segments automatically**, since [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §7 now routes system suppression through them and expects them to win. **Placed at the end of this section rather than at the top**: ordering here records human priority decisions and this item has not had one.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 132, section "Bugs", position 47 in that section (top = do next). The description is the original entry, verbatim.

Moved to the top of Bugs on 2026-09-27 at the user's direction. Ordering in this queue records human priority decisions, which is why neither this session nor the migration session ranked it when it was created — it sat at the end of Bugs awaiting exactly this call.

The reason it outranks: ADR-176 point 1 is accepted and unimplemented, so `resolve_audience` still computes `(include − exclude) ∪ pins` and an exclude block still cannot remove a hand-pinned recipient. The system does the thing an accepted decision says it must not, and that record's own argument for the precedence is that wrongly including is "the failure that reaches a supervisory authority rather than a retrospective". Point 4 (the `freeze` default) rides along but is not what makes this urgent.

Sequence before anything that writes exclusion segments automatically: the ADR-142 §7 addendum routes system-written temporary suppression through them and expects them to win.

Note for whoever takes it: task-204 fixes only the channel sentence in `resolve_audience`'s docstring. The rest of that docstring still documents the pre-ADR-176 precedence and is **accurate to the code until this task lands** — correcting it earlier would make it describe behaviour that does not exist.
<!-- SECTION:NOTES:END -->
