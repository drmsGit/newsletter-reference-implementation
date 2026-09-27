---
id: TASK-8
title: >-
  `brand_id` is a required keyword-only argument on every brand-owned service
  function, and the three genuine spanning callers use `list_all_*()`, whose set
  is asserted exactly.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
  - frontend
dependencies: []
priority: p1
type: bug
ordinal: 100800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug] — P1. DONE 2026-09-20 (ADR-172 point 4).** `brand_id` is a required keyword-only argument on every brand-owned service function, and the three genuine spanning callers use `list_all_*()`, whose set is asserted exactly. Original finding: **a silent cross-brand leak shape, and the React client removes its mitigation.** **`brand_id` defaults to `None` — meaning EVERY brand — on `list_content_records` (`content/service.py:107`), `list_campaigns` (`campaigns/service.py:53`) and `list_audience_groups` (`audience/service.py:31`).** A forgotten argument does not fail; it returns the whole platform. **The same repository made the opposite call twelve files away**: `is_consenting_filter` (`recipients/consent.py:415`) takes brand as a required positional, reasoning explicitly that "forgetting it is a TypeError". The list functions took the fail-open direction for the genuine spanning callers — platform counts, migrations, tests — which a separate `list_all_*()` would have served without giving every other caller a silent default. **Not theoretical:** five detail-by-id routes were unscoped until 2026-09-15, and the module content picker longer than that — its own comment reads *"the audience picker a few lines below was scoped for exactly this reason; this was missed."* **Fix:** required `brand_id` plus explicit `list_all_*()`, converting every entry in the brand change-impact table from a silent leak into an import-time error. **Why now:** the React manager client calls these endpoints directly, rather than through a Jinja route that has already resolved the working brand — so the caller-side mitigation this default has been relying on goes away. Source: [[Interview Prep - Brand Boundary]] → Q2. **Confirmed empirically 2026-09-19** by the router sweep (`docs/react-migration-inventory.md`): the Jinja router passes `brand_id` at 15 call sites and the JSON routers at none, so this is not a default waiting to be forgotten — it has already been forgotten everywhere the SPA will call. Fix it in one pass with the by-id write binding above: same boundary, opposite direction.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 45, section "Bugs", position 8 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
