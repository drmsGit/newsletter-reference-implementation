---
id: TASK-155
title: >-
  `_load_brand_css` (`rendering/service.py`) re-reads and re-inlines `brand.css`
  from disk on every single render with no caching — becomes O(recipients)
  redundant work if `render_variant_html` is call…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 501900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `_load_brand_css` (`rendering/service.py`) re-reads and re-inlines `brand.css` from disk on every single render with no caching — becomes O(recipients) redundant work if `render_variant_html` is called per-recipient (already planned, see the Delivery Q2 personalization fix). Fix: cache the CSS text (e.g. `functools.lru_cache` or module-level cache). Cheap, low-risk fix regardless of the pending MJML migration (Email Modules Q1) — raw-HTML templates keep needing Python-side inlining even after MJML lands, since ADR-131 keeps raw HTML as a permanent escape hatch, not just a stopgap; this just applies to fewer templates long-term. Source: [[Interview Prep - Snapshots, Rendering, Email Modules]] → Rendering Q2. **Done 2026-07-12** — `@lru_cache(maxsize=1)`.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 539, section "Done", position 19 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
