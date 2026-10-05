---
id: TASK-284
title: Decision slots pick only machine-ready records ready for their channel
status: Done
assignee:
  - '@claude'
created_date: '2026-10-05 18:10'
updated_date: '2026-10-05 18:51'
labels:
  - backend
dependencies:
  - TASK-283
type: feature
ordinal: 200120
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-282 design session (2026-10-05). Recorded in the ADR-174 addendum 2026-10-05 (point 2) and the ADR-179 addendum 2026-10-05 (point 3). Depends on the storage task.

**Today** `candidate_query` (`backend/app/decision/strategies/base.py:176-214`) filters on `status == "active"` (around line 203), the sending brand and `category_ids` only. The candidate count (`backend/app/campaigns/service.py`, `slot_candidate_count`, and `GET /campaigns/decision-slots/{id}/candidates`) uses the same query.

**Decided:** a record is a candidate only if it is machine ready AND marked ready for the slot's channel, the channel of the slot's variant. Put both conditions in `candidate_query`, so the count and every strategy agree. `explain_candidates` (if present) should say why a record was left out ("not machine ready" or "not ready for push").

**The demo seed** (`backend/scripts/seed_demo_data.py`, `create_demo_content_if_empty`) marks its slot content machine ready and ready for email, so the demo still resolves.

**Tests:**
- each condition excludes a record on its own;
- the email backfill keeps today's dev slots resolving;
- a push slot finds nothing until a person marks push readiness.

**What could break:** every test that builds slot candidates without these marks. Their fixtures need the marks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 candidate_query requires machine ready and readiness for the slot's channel; the candidate count agrees
- [x] #2 The demo seed and existing slots keep resolving; a push slot finds nothing until push readiness is marked
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Record the user's answer to the open question (option 1: a slot skips a record that cannot fill its module) as an ADR-174 addendum (adr-author), design-pass decision 9 and the playbook.
2. Tests first (tests/test_slot_candidacy.py): each condition alone excludes; the published version, the latest one, decides; a push slot finds nothing until push is marked; a slot with no module asks no field; the seeded slots still resolve.
3. candidate_query: machine ready, a mark for the slot's channel (the variant's), and an exists() on the latest published version filling every required field of the slot's module(s). One definition of required, shared with readiness_warning (fields_a_record_must_fill).
4. Seed marks its slot content machine ready and ready for email; fixtures that build slot candidates get the marks.
5. Mutation-check, full suite, live read-only check of the dev slots' candidate counts.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
OPEN, ask the user before building (raised 2026-10-05 by the ADR-174 addendum work): ADR-174 Notes (around line 86) leaves open whether a record marked ready but missing a required field is excluded from slot candidacy. As designed, the rule reads the two marks only, so such a record stays a candidate. The send-time required-field check skips slot-bound modules on purpose (backend/app/rendering/frame.py, around 257-258), on the reasoning that a slot pick missing a field should skip that recipient, not block the send. That per-recipient skip is task-228 and is not built. Put the question to the user, with a recommendation, before building this task.

Answer to the OPEN question (user, 2026-10-05): option 1 of 3. A slot also skips a record whose latest published version cannot fill every required field of the slot's module. Recorded: ADR-174 addendum 'A slot passes over a record that cannot fill its module'; Channel Readiness final design pass decision 9; playbook 2026-10-05 entry. Widening task-228 was not chosen.
Judged on the latest published version (what a pick renders, frame._pick_for_slot), so a never-published record is no candidate. A slot bound to no module asks no field but still needs a published version. explain_candidates does not exist, so no 'why left out' text was added; the count is the visible signal.
Required = content.service.fields_a_record_must_fill (required, source content, not envelope), now also used by readiness_warning. Filled = holds a non-whitespace character (SQL ~ '\S'); JSON null or missing key is not filled.
Fixtures updated: test_read_models TestSlotCandidateCount (all four records marked, so status and brand still do the excluding), test_module_states world.
Validation: 12 new tests failed first (10 for the new conditions; 2 pass-before by design); 11 mutants all caught (each condition removed, channel fixed to email, any version not the latest, whitespace counts, draft read instead of version, required ignored, seed without marks / machine ready). Backend 1314 passed. Live, read-only: dev slots 1-4 keep 85 candidates and 5-6 keep 100, the same as under the old rule (migration 0032's backfill covers them); GET /campaigns/decision-slots/{1,5}/candidates on the running server agrees.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Decision slots now pick only records that are machine ready, marked ready for the slot's channel, and whose latest published version fills the slot's module's required fields — all in candidate_query, so every strategy and the candidate count agree. The last condition is the user's answer to the open question (ADR-174 addendum). The demo seed marks its slot content. Verified by 12 new tests (failed first), 11 caught mutants, 1314 backend tests, and an unchanged candidate count on every dev slot.
<!-- SECTION:FINAL_SUMMARY:END -->
