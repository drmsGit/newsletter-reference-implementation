---
id: TASK-15
title: >-
  The partial unique index does not enforce "one open request per thing" when
  `subject_id` is NULL.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 101500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P2, and it is dormant: it arms itself the day the first subject-less action is registered.** **The partial unique index does not enforce "one open request per thing" when `subject_id` is NULL.** Postgres treats NULLs as distinct in a unique index, so two rows with the same `action_key`, `subject_type=NULL` and `subject_id=NULL` can both sit `pending` and the `IntegrityError` that `request_approval` relies on for idempotence (`approvals/service.py:128-139`) never fires. `subject_id` is nullable on purpose — `db_models.py:74-80` documents it as the ADR-142 §10 settings case — so the model explicitly supports exactly the shape the index silently stops covering, while the index comment claims "one open request per thing" without qualification (`db_models.py:119-137`). **Fix:** decide what identifies a subject-less request. Either uniqueness is per action when there is no subject (`NULLS NOT DISTINCT`, a coalesced expression index, or a second partial index for `subject_id IS NULL`), or subject-less actions carry a caller-supplied idempotency key — and then the action contract has to say so. Do it before the first such action exists, not after. Source: `CODE_REVIEW_2026-09-19` P2-03, verified 2026-09-19.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 66, section "Bugs", position 15 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
