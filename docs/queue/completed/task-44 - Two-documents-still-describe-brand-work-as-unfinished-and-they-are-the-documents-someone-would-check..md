---
id: TASK-44
title: >-
  Two documents still describe brand work as unfinished, and they are the
  documents someone would check.
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 13:56'
updated_date: '2026-10-04 19:14'
labels:
  - docs
dependencies: []
priority: p3
type: bug
ordinal: 104400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P3, stale records in three files.** **Two documents still describe brand work as unfinished, and they are the documents someone would check.** (a) [[ADR-150 — Tenancy and Access Model]]'s implementation-status paragraphs at `:120`, `:132-139` and `:164` describe unenforced brand permissions and a brandless `consent_events`; `:164` says *"Today every permission behaves platform-level."* All three are superseded by code as of 2026-09-18 and none is marked so — unlike `:120`, which does carry a "Superseded by the status below" note, which is the pattern to copy. **Per the ADR rules this is an addendum, not a rewrite of Decision.** (b) `HANDOFF.md:3` says *"Brand scoping step 1 built"* while `:305` and `:311` record steps 2 and 3 as built. Source: `/interview-prep-baseline` 2026-09-18.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ADR-150 says, in a dated addendum, that brand enforcement is built, and every passage still calling it unbuilt is marked superseded
- [x] #2 HANDOFF.md no longer claims only brand step 1 is built
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 126, section "Bugs", position 44 in that section (top = do next). The description is the original entry, verbatim.

Done 2026-10-04.
(a) ADR-150 is still Accepted and its Decision is untouched. Through the adr-author agent:
- an addendum "2026-10-04: implementation status: brand enforcement is built", verified against the code: brand-scoped permissions are checked against the working brand (cb8b5b1, 2026-09-15); consent_events.brand_id is NOT NULL (619194b, 2026-09-16); the JSON routers are guarded (ee01e8a, 2026-09-18); detail-by-id is scoped under ADR-172. No counts.
- a one-line superseded marker on each stale passage, following the 2026-09-14 pattern: the Notes "Known implementation cost" consent claim, the Notes 2026-09-15 "Still unbuilt" paragraph, the 2026-09-15 addendum's "What is not built" paragraph plus its correction's consent sentence, and a fourth found by the agent, Consequences/Negative "ConsentEventDB has no brand column either".
git diff --word-diff shows no words removed.
(b) HANDOFF.md needed nothing: since 2026-10-03 it opens with "Stale since 2026-09-20, do not start a session from this file", and its brand steps 1, 2 and 3 are each marked built.
In passing: BRAND_OWNED["/recipients"] in backend/app/auth/policy.py still called consent capture "the unresolved one", platform-level with the brand taken from the body. It has been brand-scoped and checked against the working brand since ADR-150's 2026-09-20 addendum, so the text now says that. test_brand_boundary 37 passed; full backend suite 1248 passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
ADR-150 gained a dated status addendum (brand enforcement, consent brand, JSON guard and detail scoping all built, each verified with its commit), and each of the four stale passages carries a superseded marker; nothing removed. HANDOFF.md was already marked stale and consistent. The stale BRAND_OWNED["/recipients"] description was corrected too. Full backend suite green.
<!-- SECTION:FINAL_SUMMARY:END -->
