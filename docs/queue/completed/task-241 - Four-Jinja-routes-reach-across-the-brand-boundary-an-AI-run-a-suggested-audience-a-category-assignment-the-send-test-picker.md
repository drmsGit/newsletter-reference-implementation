---
id: TASK-241
title: >-
  Four Jinja routes reach across the brand boundary: an AI run, a suggested
  audience, a category assignment, the send-test picker
status: Done
assignee:
  - '@claude'
created_date: '2026-10-02 17:41'
updated_date: '2026-10-02 17:45'
labels:
  - backend
dependencies: []
priority: p1
type: bug
ordinal: 104050
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found 2026-10-02 by the task-50 read-model sweep, verified against the code the same day. All four are in backend/app/frontend/router.py, the Jinja UI the SPA replaces, and each lacks the brand check ADR-172 requires. (S1) GET /ui/campaigns/{id}?ai_run=N loads any AIRunDB row by id (~R:1196) without checking it targets one of this campaign's variants, so a viewer of a campaign in brand A can read brand B's model output and tokens; ai_runs has no brand column, runs_for_brand in app/ai/service.py already has the scoped join. (S2) POST /ui/campaigns/{id}/suggest-audience looks the campaign up with no brand filter, and create_suggested_group_for_campaign (app/audience/service.py) takes the brand from the campaign, so a manager in brand A can create an audience group in brand B from B's categories. (S3) POST /ui/content/{cid}/categories/{assignment_id}/delete calls delete_category_assignment (app/content/service.py), which has no brand check, and never checks the assignment belongs to cid or cid to the working brand: anyone with content.manage in any brand deletes any brand's assignment by guessing an integer. (S4) _send_test_context lists every brand's variants with campaign names. The send itself is brand-safe. Two further read leaks (recipient detail decisions/deliveries across brands, category detail summing every brand) are fixed with their task-50 rows B10/B20.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Each of S1-S4 has a cross-brand test that fails before the fix
- [x] #2 The brand rule lives in the service where a service is involved (suggested audience, category unassignment, AI run lookup), so a JSON route cannot reopen it
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-02: fixed. S2 create_suggested_group_for_campaign takes brand_id and refuses another brand's campaign (Jinja lookup also scoped). S3 delete_category_assignment(db, content_id, assignment_id, brand_id) joins through the record in the brand. S4 _send_test_context(db, brand_id). S1 correction to the sweep: the template renders a run only under the variant it targeted, so a foreign run never showed in the HTML (proved by pointing the same test at the campaign's own variant, which does render). Fixed anyway with ai.service.run_for_campaign, which the coming C7 JSON read-back needs. tests/test_jinja_brand_crossings.py: 7 tests (page-level for each, service-level for S1-S3); S2-S4 failed before the fix; mutants caught at each layer. Suite 957 passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Suggesting an audience, unassigning a category and the send-test picker no longer reach another brand, with the rule in the service where one is involved; the AI-run lookup is scoped through its campaign. Verified by tests/test_jinja_brand_crossings.py, mutation-checked; full suite 957 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
