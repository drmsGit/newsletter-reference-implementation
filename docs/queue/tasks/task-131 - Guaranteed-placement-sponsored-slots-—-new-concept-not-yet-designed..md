---
id: TASK-131
title: 'Guaranteed placement / sponsored slots — new concept, not yet designed.'
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-09-27 14:29'
labels:
  - needs-adr
  - backend
dependencies: []
type: decision
ordinal: 301500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
📋 **Guaranteed placement / sponsored slots — new concept, not yet designed.** Surfaced 2026-07-05 while resolving the personalization-weighting question (Decision Q-adjacent, `recipient_top_score.py` defaults). A content slot that sits *outside* personalization ranking entirely: sales flags an item as "will show no matter what" (usually one-off, last-minute), or a partner contract guarantees minimum placement on an ongoing basis. Deliberately distinct from the override mechanism above — different trigger (a business/contractual guarantee, not a one-off editorial judgment call) and often a different owner (sales/partnerships, not the person building the email). Needs its own design before implementation — not yet scoped as an ADR or a feature. **This also subsumes the segment-targeted-content case** ("everyone gets the decision result, except recipients in category X get content record Y" — e.g. beach recipients get a special beach offer). That was briefly considered as a category-scoped *override* ("Case 2") during the override redesign and deliberately **dropped** (2026-07-15) in favor of doing it here: model it as a guaranteed placement plus a simple if/else — **a recipient who qualifies for the guaranteed placement doesn't render the decision slot at all** — rather than a second override case. Open question to settle as part of this: what defines a recipient being "in" the target segment (top preference vs. any preference over a threshold). Source: `docs/playbook-strategy.md` Decision Log, 2026-07-05, item 5; `docs/business-interview-baseline.md` §M1.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 463, section "Needs ADR", position 15 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
