---
id: TASK-208
title: Response models expose less than their tables store — one sweep
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 14:20'
updated_date: '2026-10-03 09:41'
labels:
  - backend
dependencies: []
priority: p1
type: feature
ordinal: 200320
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** **The pattern, named because three is not a coincidence** (Q5): response models routinely expose less than their tables store — `ModuleVariableOut` drops `label` and `envelope`, `PendingActionDetail` drops `subject_type` and `subject_id`, `SendInstance` exposes 8 of 15 columns and none of the three counts. Each was found by asking what a screen needs. **Worth a sweep rather than three one-line fixes**: Phase 0's schema-honesty pass caught bare dicts and did not catch under-exposure.

The instances, as each interview logged them:
- **`PendingActionDetail` does not expose `subject_type` / `subject_id`** (Q4), although `PendingActionDB` stores both — so the client cannot build the link to the thing being decided. Second instance of a defect already seen once, where a response model drops fields the table has. *(Manager Workflow, Cluster 1, gap 6.)*
- `ModuleVariableOut` exposes `name` and `required` only — `modules/router.py:10`. *(Variant Editor, Cluster 2, gap 11.)*

Source: [[Manager Workflow - design interview]] → What Cluster 5 produced (Q5.5) and What Cluster 1 produced, gap 6 (Q1.4); [[Variant Editor - design interview]] → What Cluster 2 produced, gap 11.

**Verified against the code 2026-09-27:**
- `ModuleVariableOut` (`backend/app/modules/router.py:10-12`) carries `name` and `required`; `label` is defined at `backend/app/modules/registry.py:48` and envelope from `:49`.
- `SendInstance` (`backend/app/delivery/models.py:25-33`) omits `brand_id`, `audience_group_id`, `from_address`, `audience_resolution_mode` and the sent/failed/excluded counts (`backend/app/delivery/db_models.py:17,25,28,35,45-47`).
- `PendingActionRow`/`PendingActionDetail` (`backend/app/approvals/models.py:13-59`) omit `payload`, `subject_type`/`subject_id`, `decided_by_type`/`decided_by_id`, `decision_reason` and `execution_error` (`backend/app/approvals/db_models.py:61,79-80,100-106`).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

2026-10-01: SendInstance done as part of task-28 — it now carries from_address, audience_group_id, sent_count, failed_count and excluded_count. ModuleVariableOut and PendingActionDetail remain.

Built 2026-10-03. Named instances: ModuleVariableOut gains label, envelope, type, size, note and concept (`backend/app/modules/router.py`). PendingActionRow gains subject_type/subject_id and decided_by_type/decided_by_id/decision_reason; PendingActionDetail also gains execution_error (detail only) (`backend/app/approvals/models.py`, `router.py`). payload is deliberately NOT exposed (internal arguments; rows are the readable form), and a test pins that. The sweep (an Explore agent over every response_model on the JSON plane) found and fixed: DeliveryExecution.channel/purpose; RecipientDelivery.purpose/exclusion_reason (ADR-163 point 8); AudienceGroup.source_campaign_id; RecipientAddress.is_primary/verified_at. No hash or secret column is exposed anywhere. Deliberately left: brand_id on brand-scoped models, SendInstance.audience_resolution_mode (no longer gates anything, ADR-176), AudienceRuleBlock timestamps, PromptVersion id. Open, raised with the user: RecipientConsentEvent.note (free text, possibly personal data); Snapshot returns artifact_location and render_context. FOUND AND FIXED: GET /recipients/{external_id} had returned 500 for every recipient since 2026-09-16 (619194b made to_recipient take brand_id; get_recipient_by_external_id was not updated). It now takes the working brand, with a regression test. Tests: `backend/tests/test_response_exposure.py` (7), 11 mutants caught after two tests were strengthened to use non-default values (defaults had let 'field exists' pass). Suite 1050 passed, rc=0; schema regenerated, client type-checks, 48 passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Response models now carry what their tables hold and a screen needs: module field metadata, approval subject and decision, execution channel/purpose, delivery exclusion reason, group source campaign, address primary/verified. payload stays hidden on purpose. The sweep found no exposed secrets, and it uncovered GET /recipients/{external_id} returning 500 since 2026-09-16, now fixed. Verified: 7 tests, 11 mutants caught, suite 1050 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
