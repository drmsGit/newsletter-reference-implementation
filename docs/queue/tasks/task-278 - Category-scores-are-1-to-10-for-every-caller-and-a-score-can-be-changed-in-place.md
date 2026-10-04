---
id: TASK-278
title: >-
  Category scores are 1 to 10 for every caller, and a score can be changed in
  place
status: To Do
assignee: []
created_date: '2026-10-04 18:25'
updated_date: '2026-10-04 18:26'
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
- [ ] #1 A score outside 1-10 is refused by the API, the Jinja form and the CSV import, none of them clamping
- [ ] #2 Existing out-of-range scores can be listed for a person, and nothing changes them automatically
- [ ] #3 An existing assignment's score can be changed in place, brand-scoped and audited
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
From the ADR-080 addendum work (2026-10-04):
- backend/scripts/import_content_csv.py:151-157 writes ContentCategoryAssignmentDB directly and never calls assign_category_to_content, so a range check only in the service misses imported rows. Put the check where both paths pass, or in each.
- ContentCategoryAssignmentCreate.score (backend/app/content/models.py:114-116) has no bounds; the API model should state 1-10 too.
- Open, not decided, to put to the user: parse_categories (import_content_csv.py:72-76) turns an unparseable score ("abc") into 10 with only a printed warning. The decision covers out-of-range values; whether an unparseable one is also refused is the user's call.
<!-- SECTION:NOTES:END -->
