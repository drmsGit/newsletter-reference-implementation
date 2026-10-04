---
id: TASK-268
title: >-
  GET /content/ finds records by topic: a category filter, title-and-description
  search, score order
status: Done
assignee:
  - '@claude'
created_date: '2026-10-04 10:20'
updated_date: '2026-10-04 10:27'
labels:
  - backend
dependencies: []
type: feature
ordinal: 200030
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-263 design session (2026-10-04, user, one question at a time). It is recorded in the ADR-175 addendum of 2026-10-04 and in the "Choosing a record for a module" section of [[Campaign Write Surface - final design pass]]. The problem: a manager who has only a topic in mind ("something about beaches") cannot find a record to bind, because the bind picker can only match part of a title. This task is the server half. The picker (the next task) and the Content list's category filter (the one after task-267) both build on it.

**What the list route does today.** `GET /content/` (`backend/app/content/router.py:69-80`, calling `page_content_records`, `backend/app/content/service.py:327-341`) takes `q`, `status`, `limit` and `offset`. `q` matches `title` only (`title.icontains`, wildcards escaped, tested in `backend/tests/test_list_filters.py`). Rows come newest first by `id desc`. There is no category filter. The only existing read of "records in a category" is `GET /insight/categories/{id}` (`backend/app/insight/graph.py:187-244`). That read includes inactive records and is not paged, so it is not the picker's route.

**What the decisions require of this route:**
- **Topic is category, read-only, for now** (decision 2). Facets (task-207) join later as a second filter. The route reads category assignments and never writes them.
- **`q` matches title and description**, part-word and any case (decision 3). It does so everywhere `q` is used for content, so the Content list's search widens too, and its label changes in the Content-list task. Body text and full-text search are deferred; Postgres has no search infrastructure here today.
- **"In category X" means direct assignment** (decision 4), the same meaning a decision slot's `candidate_query` gives it (`backend/app/decision/strategies/base.py:176-214`). There is no expansion to child categories, and any future expansion is decided for slots and picker together. The category vocabulary is global and assignments are per brand through `content_records.brand_id` (ADR-150 addendum 2026-09-15), so the filter joins `content_category_assignments` inside the brand's own records. It must not leak another brand's records into the page or the total.
- **Order** (decision 5): with a category, the assignment `score` highest first, then id desc (newest). Text only: id desc, as today. This deliberately differs from top_score's id-asc tie-break; nothing should claim the top row is a slot's pick. The score orders the rows but is not shown on them (decision 6), so the route need not return it unless the picker's final-design pass wants it.
- **The filter applies identically to `items` and `total`** (ADR-185; ADR-175 point 7 and its 2026-10-03 addendum).

**The "not published yet" notice.** The picker shows it on a row (decision 6), and its data lives in `publish_state` (`service.py:45-58`). That function answers "latest version number, and whether the live content differs from it"; nothing published counts as differing, and a send refuses it (`UnpublishedContentError`). Today the list item (`ContentRecord`, `backend/app/content/models.py:23-30`) does not carry it, and computing it per row is one query per record. The task's final-design pass decides the shape: a field on the list item computed in one grouped query, or a cheaper "has a published version" flag. Do not put an N+1 on a paged list.

**Small fix in passing.** The comment at `service.py:339-340` says "The table has no timestamps". The table now has `updated_at` (migration 0029), though still no creation time. Reword it so it stays true.

**Thin demo data.** Seed titles are "{Category} feature #N" (task-71), so topic search will look thin in the demo; that is not a defect of this task. Note also that the demo seed writes a Beach↔Family relation cycle (`backend/scripts/seed_demo_data.py:93-94`), which matters to the picker's dropdown, not to this filter.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 GET /content/ accepts a category filter that returns only the brand's records directly assigned to that category, with total counted under the same filter
- [x] #2 q matches part of the title or the description, any case, wildcards escaped
- [x] #3 With a category, rows are ordered by assignment score descending, then id descending; without one, id descending as today
- [x] #4 A list row carries enough to show "not published yet" without a query per row
- [x] #5 Tests cover brand isolation of the category filter, the order, and that a child category's records are not included
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. ContentListItem(ContentRecord) in backend/app/content/models.py adds latest_version_number (None = never published, so a send would refuse it). This is the picker's "not published yet". "Differs from the latest version" is deliberately left out: binding such a record is fine.
2. In page_content_records, q matches title OR description. category_id joins content_category_assignments: direct only, inside the brand, ordered by score desc then id desc. Latest version comes from one grouped subquery outer-joined into the page query, not N+1.
3. The router gains a category_id query param, an updated q description, and response_model Page[ContentListItem].
4. Reword the "no timestamps" comment.
5. Tests in test_list_filters.py cover: description match; category filter (rows plus total, brand isolation, child not included, order); latest_version_number. Mutation-check each.
6. Regenerate frontend schema.d.ts, then run the client typecheck and tests, and check:contract.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-10-04.
- "Not published yet" = latest_version_number is null on a new ContentListItem row, meaning no version exists and a send refuses the record. It comes from one grouped max(version_number) subquery outer-joined into the page query, not a query per row. "Live differs from latest" was left to the detail route deliberately: binding such a record is fine.
- category_id joins content_category_assignments inside the brand filter. Order with a category: score desc, then id desc.
- The Content screen search now also matches descriptions; its label "Find content by title" stays until task-270 relabels it. useContentList takes no category yet; that is task-269/270.
- 6 new tests in backend/tests/test_list_filters.py (TestContentByTopic). Mutation-checked against 9 mutants, each caught: category filter dropped, score asc, no score order, id-asc tie-break, brand filter dropped, child included, title-only q, q ignored with a category, version dropped.
- Full backend suite: 1217 passed. Client: schema.d.ts regenerated from the live server, tsc -b clean, vitest 125 passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
GET /content/ finds by topic: a category_id filter (direct assignment, brand-scoped, rows and total alike), q over title and description, score-then-newest order with a category, and latest_version_number on each row for the "not published yet" notice without N+1. Verified by 6 new tests mutation-checked against 9 mutants, the full backend suite (1217 passed), and the client typecheck and tests on regenerated types.
<!-- SECTION:FINAL_SUMMARY:END -->
