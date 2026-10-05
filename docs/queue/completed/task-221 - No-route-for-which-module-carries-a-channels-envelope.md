---
id: TASK-221
title: No route for which module carries a channel's envelope
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 14:20'
updated_date: '2026-10-05 13:55'
labels:
  - backend
dependencies: []
priority: p2
type: feature
ordinal: 200360
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** No route for *"which module carries this channel's envelope"* — `envelope_module_type` is internal. The composer needs it: the envelope is promoted to the top of the composer **by asking `envelope_module_type(channel)`** rather than by knowing a module called `header` is special — and push returns `None`, so the same screen is correct everywhere without a branch.

| # | Gap | Where |
|---|---|---|
| 12 | No route for *"which module carries this channel's envelope"* | `envelope_module_type` is internal |

Source: [[Variant Editor - design interview]] → What Cluster 2 produced, gap 12 (Q2.3).

**Verified against the code 2026-09-27:** `envelope_module_type` (`backend/app/modules/registry.py:208`) is used only internally — `backend/app/frontend/router.py:1063,1200`, `backend/app/campaigns/service.py:393`, `backend/app/campaigns/duplication.py:267`, `backend/app/ai/orchestration.py:76`. The modules router has two routes (`backend/app/modules/router.py:38,46`) and neither exposes it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 GET /modules says which module carries a channel's envelope, computed on the server
- [x] #2 The editor takes its envelope fields from that module and no longer scans every module for envelope fields
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

Done 2026-10-05.
Checked first whether this was still true. Half was stale: the composition already gives has_envelope, envelope_modules and accepted_module_types, all computed with envelope_module_type, so the editor never needed to know that "header" is special. The other half was live: the envelope area scanned every manifest for envelope:true fields (VariantEditor.tsx), which is the "third copy of one derivation" ADR-177 point 8 warns against. It had to, because before a variant's first subject is saved there is no envelope row to read the fields from.
The user chose where to expose it: a carries_envelope flag on GET /modules (and GET /modules/{name}), computed with envelope_module_type. No separate route was added.
- ModuleManifestOut.carries_envelope. The editor now takes its envelope fields from the flagged module.
- Tests: two backend (the list flags exactly envelope_module_type's answer and push none; a single module says so) and one client test (a second module declaring an envelope field does not reach the envelope area). Mutations caught: the flag never true, the flag always true, and the client scanning every module again. Backend 1289 passed; client regenerated, tsc clean, vitest 166 passed.
- Checked live (read-only): email flags only header, push none; variant 4B's envelope shows Subject line and Preheader (inbox preview).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Which module carries a channel's envelope is now exposed on GET /modules (carries_envelope, from envelope_module_type), and the editor reads its envelope fields from that module instead of re-deriving it by scanning every module. The composer's other needs were already met by the composition. Verified by backend and client tests with mutations, both suites and a read-only live check.
<!-- SECTION:FINAL_SUMMARY:END -->
