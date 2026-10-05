---
id: TASK-278
title: >-
  Category scores are 1 to 10 for every caller, and a score can be changed in
  place
status: Done
assignee:
  - '@claude'
created_date: '2026-10-04 18:25'
updated_date: '2026-10-05 07:40'
labels:
  - backend
dependencies: []
type: feature
ordinal: 200150
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-274 design session (2026-10-04, the user, one question at a time) and recorded in the ADR-080 addendum of 2026-10-04 ([[ADR-080 — Human-governed Taxonomy Before AI Selection]]) and in [[Content Write Surface - final design pass]]. The server half of how a record's categories are edited.

**Score range.** A category score is a whole number from 1 (barely in the category) to 10 (squarely). It is enforced for every caller, and anything else is refused, not clamped. Today:
- `assign_category_to_content` (`backend/app/content/service.py`, around 727-737) refuses only 0; its comment calls 0–10 "a POC-only convention";
- the CSV import clamps to 0–10 (`backend/scripts/import_content_csv.py`);
- the Jinja form allows 1–100 (`backend/app/templates/content_detail.html`, around 339).

Out-of-range scores distort all three readers: top_score ranking, recipient_top_score's weighted sum, and signal contribution `base_weight * (score/10)` (`backend/app/insight/service.py`).

**Existing rows outside 1–10 are reported for a person, never changed silently.** That needs a way to list them, a read-only script for example. Decide the shape in this task's final-design pass.

**Change a score in place.** A new route updates an existing assignment's score, for example `PATCH /content/{id}/assignments/{assignment_id}`. Today the only way is remove and re-add, which briefly takes the record out of the category. Scope it through the record and brand as `DELETE /content/{id}/assignments/{aid}` does (`service.py:700-709`). It needs `content.manage`, and an audit event: task-275 covers the existing writes, and this new one must be audited from the start.

Depends on nothing; task-280 (the React categories section) depends on it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A score outside 1-10 is refused by the API, the Jinja form and the CSV import, none of them clamping
- [x] #2 Existing out-of-range scores can be listed for a person, and nothing changes them automatically
- [x] #3 An existing assignment's score can be changed in place, brand-scoped and audited
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. scripts/migrate_0031_category_score_range.sql: a DO block raising with a list of out-of-range rows if any exist; otherwise ADD CONSTRAINT ck_content_category_assignments_score_range CHECK (score BETWEEN 1 AND 10). Idempotent. Apply with scripts/migrate.py --apply BEFORE any .py edit, while the preview backend reloads.
2. db_models: the same CheckConstraint, so create_all and check_schema agree.
3. models: ContentCategoryAssignmentCreate.score is Field(10, ge=1, le=10); a new ContentCategoryAssignmentScore{score} for PATCH.
4. service: assign refuses outside 1-10; set_assignment_score(db, content_id, assignment_id, score, brand_id) returns the before and after, or None.
5. router: PATCH /content/{id}/assignments/{aid}, brand-scoped through the record (404 otherwise), audited content.category_score_changed {category_id, category, from, to}.
6. Jinja form: score input 1-10.
7. CSV import: parse_categories marks bad scores; main skips and lists them.
8. Tests: API and Jinja range refusals; the PATCH route (change, audit, range, brand 404, unknown 404); the DB constraint refusing a direct insert; the migration refusing and listing a violating row; the CSV import skipping and listing. Mutation-check; full suite; check:contract after regenerating the client.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
From the ADR-080 addendum work (2026-10-04):
- backend/scripts/import_content_csv.py:151-157 writes ContentCategoryAssignmentDB directly and never calls assign_category_to_content, so a range check only in the service misses imported rows. Put the check where both paths pass, or in each.
- ContentCategoryAssignmentCreate.score (backend/app/content/models.py:114-116) has no bounds; the API model should state 1-10 too.
- Open, not decided, to put to the user: parse_categories (import_content_csv.py:72-76) turns an unparseable score ("abc") into 10 with only a printed warning. The decision covers out-of-range values; whether an unparseable one is also refused is the user's call.

Decided with the user 2026-10-05:
- CSV import: a bad score (out of range, or unreadable such as "abc") skips that one assignment, the rest of the row imports, and refused scores are listed at the end; a bare category name still means 10. The user noted this command-line script has no screen and was never discussed before.
- Reporting and enforcement: a database CHECK constraint (score between 1 and 10), added by a migration that refuses and lists any out-of-range rows while they exist, changing nothing. The dev database held none on 2026-10-05: 198 assignments, all scored 5-10.

Built 2026-10-05.
- Migration 0031 (applied to the dev database the same day, before any .py edit, so the reloading backend never met a pending file): a DO block that raises with a list of out-of-range rows ("nothing was changed") if any exist, else adds ck_content_category_assignments_score_range CHECK (score BETWEEN 1 AND 10). The dev database had none. The same CheckConstraint is declared on ContentCategoryAssignmentDB; check_schema agrees.
- SCORE_MIN/SCORE_MAX in content/models.py. ContentCategoryAssignmentCreate.score uses Field(ge=1, le=10), so the API refuses with a 422 field error. New ContentCategoryAssignmentScore.
- service.check_score refuses outside 1-10 (zero included), called before the insert, because the IntegrityError handler would otherwise call a bad score "already assigned".
- set_assignment_score is brand-scoped through the record and returns before and after.
- New route PATCH /content/{id}/assignments/{aid} {score}: 404 outside the brand or unknown, audited content.category_score_changed {category_id, category, from, to}, nothing recorded when the score is unchanged.
- Jinja: the score input is min 1, max 10, step 1.
- CSV import: parse_categories returns (parsed, refused). A bad score skips that assignment and is listed at the end; the clamp is gone; a bare name still means 10; the docstring says so.
- test_read_models: a fixture used score 99 so leaked records would outrank; now 10, the maximum, which keeps that intent.
- Tests: tests/test_category_scores.py (17), covering API range and ends, service, Jinja, the PATCH route (change and audit, same score, range, brand 404, unknown 404), the DB constraint, the migration refusing and listing (run on the test DB inside a rolled-back transaction) and the CSV parse and import report.
- Mutation-checked against 9 mutants, each caught. Backend 1287 passed; client regenerated, tsc clean, vitest 145 passed.
- Incident: the first run hung. The fixture read ids after its commit, which opened a transaction holding a lock that the migration test's ALTER TABLE waited on. Fixed with a rollback at the end of the fixture setup, and commented there.
- Checked live through the React dev proxy on record 65: assigning score 15 gave 422 on the score field, PATCH with score 0 gave 422, and the assignments were unchanged.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Category scores are 1-10 for every caller: a database CHECK (migration 0031, which refuses and lists any bad row rather than changing it), the API (422 field error), the service, the Jinja form, and the CSV import (a bad score skips that assignment and is listed). A score can be changed in place through a new brand-scoped, audited PATCH route. Verified by 17 tests mutation-checked against 9 mutants, the full suite (1287), the contract and a live check that leaves the data unchanged.
<!-- SECTION:FINAL_SUMMARY:END -->
