---
id: TASK-389
title: A refused Build the variant leaves the envelope and hero saved
status: Done
assignee:
  - '@claude'
created_date: '2026-10-17 10:09'
updated_date: '2026-10-17 10:17'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found by Codex (docs/queue/docs doc-31, its test backend/tests/test_topic_build_refusal.py on origin/codex/regression-tests 0eced93), triaged with the user 2026-10-17: fix now. task-370 promised (ADR-141 addendum 2026-10-17, point 5; backend/app/campaigns/from_topic.py module docstring) that everything is checked before anything is written, so a refused build leaves the variant as it was. That held for the checks build() makes itself (the run, the variant still empty, records still takeable, proposed blocks only), but not for the checks the writes make themselves: the envelope (set_envelope_fields, backend/app/campaigns/service.py:485, refuses an unknown dictionary entry via text_problems, ADR-199) and the editorial module data (_refuse_module_data, service.py:659). build() writes the envelope first and the hero second, so an editorial edited to name an entry the brand does not have ({{unknown}}) is refused with 422 after both are committed: the variant is half built, no longer empty, and the next build is refused. The fix: before any write, run the same validation those writes run — text_problems on the envelope with the envelope manifest, and _refuse_module_data on the editorial module data — so their refusal comes first. Codex test lands with the fix, as its failing test first; its passing companion, backend/tests/test_translation_stale_proposal.py (ADR-200 point 5: taking an older fresh translation keeps a later original change visible), comes in with it.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Bring in both Codex tests; the topic build one fails first. 2. In backend/app/campaigns/from_topic.py, before any write: the envelope through text_problems with the envelope manifest (as set_envelope_fields), the editorial through _refuse_module_data (as create_module_for_variant). 3. Mutation-check, full suite, commit with both tests.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Fixed 2026-10-17 (349c6f8). backend/app/campaigns/from_topic.py runs the editorial through _refuse_module_data (the function create_module_for_variant uses) before the first write. An envelope pre-check was tried and dropped: the envelope is the first write and set_envelope_fields refuses before writing, so it already builds nothing; a new test (a subject naming an unknown entry builds nothing) fails when the envelope write is moved after the hero, which keeps that order honest. Codex tests brought in: backend/tests/test_topic_build_refusal.py (failed before the fix, passes after; removing the pre-check fails it again) and backend/tests/test_translation_stale_proposal.py (passes). Full pytest and Ruff green apart from test_product_name; CI the same: 2173 passed, only test_product_name failing, on the retired name in docs/design from the parallel design commit a4ebdbb.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A refused Build the variant now builds nothing: the editorial is checked before the first write; the envelope, being the first write, already refused cleanly, and a test keeps that order. Codex doc-31 tests brought in. Verified by mutation and the full suite; CI green for this work, red only on the unrelated retired-name check from the design commit.
<!-- SECTION:FINAL_SUMMARY:END -->
