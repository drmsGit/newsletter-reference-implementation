---
id: TASK-47
title: >-
  ADR-176 — A Negative Decision Outranks a Positive One was accepted 2026-09-24
  and none of its implementable points exist.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-09-29 13:33'
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Point 1 — resolve_audience computes ((includes | pins) - excludes), consent floor unchanged. Rewrite the precedence docstring, the inline comment, Code/audience.md, Flow - Audience resolution.md and the 'Manually added — always included' template heading. New test: a pinned recipient an exclude block also catches is absent. Mutation-check by reverting the set operation.
2. Point 4 — keep audience_resolution_mode, refuse 'freeze'. Default flips to 'rerun' in SendInstanceDB and prepare_send_from_audience; the validator rejects 'freeze' naming ADR-176; send_send_instance reconciles unconditionally. Backfill the one un-fired draft only — the five sent rows were frozen and rewriting them would falsify history. No migration (no Alembic, and it buys nothing).
3. Re-point test_consent_gates' P0 test at a group-less send. Removing freeze makes re-resolution drop the opted-out recipient before the send-time gate sees them, so that test would pass for the wrong reason. Add a second test asserting the group-backed path drops them at re-resolution — both mechanisms, separately.
4. Jinja surfaces: drop the resolution select from campaign_detail.html and the Form('freeze') default; rename the 'force add' / 'always included' wording wherever a manager reads it.
Out of scope: point 3 (block kinds, explicitly not expressible), Cluster 4 Q3's return-shape change (separate task).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 132, section "Bugs", position 47 in that section (top = do next). The description is the original entry, verbatim.

Moved to the top of Bugs on 2026-09-27 at the user's direction. Ordering in this queue records human priority decisions, which is why neither this session nor the migration session ranked it when it was created — it sat at the end of Bugs awaiting exactly this call.

The reason it outranks: ADR-176 point 1 is accepted and unimplemented, so `resolve_audience` still computes `(include − exclude) ∪ pins` and an exclude block still cannot remove a hand-pinned recipient. The system does the thing an accepted decision says it must not, and that record's own argument for the precedence is that wrongly including is "the failure that reaches a supervisory authority rather than a retrospective". Point 4 (the `freeze` default) rides along but is not what makes this urgent.

Sequence before anything that writes exclusion segments automatically: the ADR-142 §7 addendum routes system-written temporary suppression through them and expects them to win.

Note for whoever takes it: task-204 fixes only the channel sentence in `resolve_audience`'s docstring. The rest of that docstring still documents the pre-ADR-176 precedence and is **accurate to the code until this task lands** — correcting it earlier would make it describe behaviour that does not exist.

Implemented 2026-09-29 in three commits (fe92188 point 1, 38e163f point 4, 97be0d5 the ADR addendum and playbook entry). 685 tests passing, up from 683.

Point 1: resolve_audience computes ((includes | pins) - excludes). Two tests in test_audience_api.TestExcludeBeatsPin, neither of which existed — the ADR had measured that every pin assertion in the suite was against the consent floor. Both mutation-checked: restoring the old parenthesisation fails the first, dropping pins fails the second.

Point 1's docs: the docstring, docs/architecture/Code/audience.md, Flow - Audience resolution.md, Flow - Send a campaign.md and the 'Manually added — always included' heading on audience_group_detail.html, which now says an exclusion rule still removes these people. frontend/router.py:3629's comment became true without an edit, as ADR-176's Notes predicted.

Point 4, and this is where the build question was decided: THE COLUMN IS KEPT. Five rows read 'freeze' because those sends were frozen; rewriting them would falsify history. Only the one un-fired draft was backfilled, by scripts/migrate_0021_freeze_is_history.py (dry-run default, idempotent, applied — 1 backfilled, 5 left alone deliberately). prepare_send_from_audience refuses 'freeze' by name rather than dropping the parameter, so an old caller is told what changed instead of 'unexpected keyword argument'. send_send_instance now reconciles unconditionally.

The design pass's main finding held: test_consent_gates' P0 test was about to pass for the wrong reason, because its protection WAS the freeze mode. It survives because its fixture's send carries no audience_group_id, so reconcile returns early and the gate is the only thing there is. Verified by mutation both ways — flipping the fixture to 'rerun' changes nothing; neutering the gate fails all four. Docstrings rewritten to say so. Two new tests fire through send_send_instance rather than the reconciler, because the call site is what changed; mutation-checked against restoring the conditional.

Also done: the approval screen's 'Audience resolution' row dropped (it would read 'rerun' on every send) and its rerun warning made unconditional; the Jinja plan form's select removed; delivery_detail's badge relabelled to say how a send was PLANNED.

FOUND, NOT FIXED: task-233. The point-1 test failed against correct code until the fixture recipient was given an email address — a rule block's criteria resolve through _deduplicate_by_address, which drops anyone unaddressable, and pins do not pass through it. Because that helper asks about email addressability whatever channel was requested, a push-only recipient survives an exclusion on a push send. Verified against the dev database. Recorded as a dated addendum on ADR-176 as well as in the queue, because it is a hole in point 1's guarantee rather than an unrelated bug.

task-204 is subsumed: the two stale channel-default sentences were in the docstring this task rewrote, and leaving a known-false sentence in place to respect a task boundary would have been silly.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
ADR-176 points 1 and 4 implemented. resolve_audience computes ((includes | pins) - excludes) so an exclude block removes a hand-pinned recipient; every send re-resolves its audience before firing and 'freeze' is refused by name. The column is kept because five rows record sends that were genuinely frozen; only the one un-fired row was backfilled. Verified by 685 passing tests including four new ones, each mutation-checked, plus a dry-run-then-apply migration. Two findings recorded rather than silently absorbed: task-233 (an exclusion cannot reach an unaddressable recipient, and leaks on push), and that point 4 disabled the protection the ADR-163 P0 test relied on.
<!-- SECTION:FINAL_SUMMARY:END -->
