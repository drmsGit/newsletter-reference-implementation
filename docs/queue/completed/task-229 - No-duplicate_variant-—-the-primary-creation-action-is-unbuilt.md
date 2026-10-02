---
id: TASK-229
title: No duplicate_variant — the primary creation action is unbuilt
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 14:20'
updated_date: '2026-10-02 19:46'
labels:
  - backend
dependencies: []
priority: p1
type: feature
ordinal: 200310
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** **Duplication is primary and does not exist.** `duplicate_campaign` and `duplicate_content_record` are built; there is no `duplicate_variant`, and 5.1 made it the primary creation action. 5.6 settles that it **reuses** the campaign machinery rather than reimplementing a subset — narrower (same-brand only), not parallel.

| # | Gap | Where |
|---|---|---|
| 27 | No `duplicate_variant` — the primary creation action is unbuilt | `campaigns/duplication.py` |
| 29 | A context-sensitive `content_mode` default (`KEEP` within a campaign) | build-time |

Gap 29 only applies once gap 27 exists, so they are one piece of work.

Source: [[Variant Editor - design interview]] → What Cluster 5 produced, gaps 27 and 29 (Q5.1, 5.6).

**Verified against the code 2026-09-27:** `backend/app/campaigns/duplication.py` defines `content_modes_for` (`:105`), `duplicate_campaign` (`:127`), `duplicate_content_record` (`:384`) and `summarise_source` (`:415`); no `duplicate_variant` anywhere in `backend/app/`. Gap 29 is partial: `content_modes_for` returns `[KEEP, LAYOUT]` within one brand and `backend/app/templates/campaign_duplicate.html:131` pre-selects the first, but `duplicate_campaign` has no server-side default — `content_mode` is required (`duplication.py:133`).

Related: task-113 (duplication must carry active overrides).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Final-design pass, 2026-10-02. Governing: ADR-013 (+2026-09-16 addendum), ADR-150 point 2, ADR-160 points 4-5, ADR-162 point 1, ADR-172 point 6, ADR-153, ADR-021. Interview: Variant Editor Q5.1, 5.2, 5.6.
1. Extract the per-variant body of duplicate_campaign (`backend/app/campaigns/duplication.py`: slots as prepared spots, modules renumbered with the envelope at 0, content binding via _target_content_id, url_carriers) into one helper both callers use. That is 5.6's 'reuse the machinery, not a subset'. duplicate_campaign's behaviour is unchanged; the existing 39 tests in `backend/tests/test_duplication.py` guard it.
2. Add duplicate_variant(db, variant_id, brand_id, target_campaign_id=None, name=None, content_mode=None), same-brand only. The source variant and the target campaign must both be in the working brand; otherwise it answers as absent. Modes are content_modes_for(same, same) = KEEP | LAYOUT, and COPY is refused. Channel is carried, status forced to draft, name defaults to '<name> (copy)', one commit.
3. Gap 29 default (DECISION, user): KEEP when the target is the source's own campaign (A/B arms), LAYOUT when it is another campaign (the weekly case, Q5.2). An explicit content_mode always wins.
4. Route POST /campaigns/variants/{variant_id}/duplicate (body: target_campaign_id?, name?, content_mode?) -> 201. It falls under the existing '/campaigns/' policy entry = campaigns.manage, so no new policy line. 404 when outside the brand, 409 for a refused mode. Audit event variant.duplicated with the report as detail (ADR-153 provenance, no copied_from column).
5. Not touched: Jinja (frozen), the React screen, task-113 overrides (SCOPE DECISION, user).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

Decided by the user 2026-10-02: (1) the default content_mode depends on the target. KEEP within the source's own campaign, LAYOUT into another campaign; an explicit mode wins. (2) Override carry-over stays in task-113, done right after, through the shared helper this task extracts.

Built 2026-10-02. `_copy_variant_into` (`backend/app/campaigns/duplication.py`) is now the one place a variant is copied, and duplicate_campaign calls it. The 39 pre-existing duplication tests pass unchanged. Added `duplicate_variant` + `default_variant_mode` + `DuplicationNotFound`, and the route POST /campaigns/variants/{variant_id}/duplicate (`backend/app/campaigns/router.py`), which resolves to campaigns.manage via the existing '/campaigns/' policy entry. Audit action variant.duplicated (`backend/app/audit/service.py`). 8 tests in `backend/tests/test_duplication.py` (TestDuplicatingAVariant, TestDuplicatingAVariantOverJson). Mutation-checked: 9 mutants. The first run let one survive: dropping the source-brand check was masked by the target check. Added the case it exposed, where brand B pulls brand A's variant into its own campaign and KEEP would bind A's content; that mutant is now caught. Full suite 1002 passed, rc=0. Not done here: active overrides (task-113), the React screen, and schema.d.ts regeneration (next client change).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
duplicate_variant built, same-brand only, reusing the campaign copy machinery through one shared helper. The default content mode depends on the target (KEEP in the own campaign, LAYOUT elsewhere; decided by the user). JSON route POST /campaigns/variants/{id}/duplicate, audited. Verified: 8 new tests, each rule mutation-checked; full suite 1002 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
