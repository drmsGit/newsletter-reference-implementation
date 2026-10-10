---
id: TASK-334
title: >-
  Correct six comments and rationale notes the 2026-10-09 interview review found
  stale or missing
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 18:13'
updated_date: '2026-10-10 20:33'
labels:
  - docs
  - frontend
  - backend
dependencies: []
type: docs
ordinal: 200700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Docs]** The 2026-10-09 interview review settled six questions whose only outstanding work is wording. Nothing behaves wrongly; each place below says something false or leaves a reader guessing. Bundled because each is a sentence.

1. Client Q2: frontend/src/api/resources.ts:705-706 (and the same pattern at :911 and :1231) caches module manifests with staleTime: Infinity, commented "do not change under a session". The real boundary is a page reload (or a brand switch, which invalidates everything at session.ts:177). Say so. Revisit with task-55 (keep in POC).
2. Client Q4: frontend/src/api/client.ts:52-55 claims the CSRF token has "exactly one writer, useSession". There are three lifecycle write sites (session.ts:91 load, :141 sign-in, :189 sign-out clears). They cannot disagree because the value is derived from the session token and fixed for the session's life (ADR-168, 2026-09-20 addendum). Reword to "one owner module, three write sites" plus that reason.
3. Client Q5: say in docs/implementation/TypedApiClient.md that the generated client guarantees only that this checkout's client matches this checkout's server (ADR-170 point 5). It promises nothing to an older open tab or to outside integrations; the latter belongs to task-119.
4. CI Q2: backend/scripts/check_installed.py:13-15 exempts every optional lock entry, assuming all are other-platform builds. Add that a missing current-platform binding (rolldown, lightningcss) breaks the frontend build and tests in the same CI run, which is what catches it.
5. CI Q5: write down why the installed-equals-locked check runs on a fresh install (ci.yml:141-148) and not on the tested environments. The test jobs already refuse non-locked installs (--require-hashes at :77, npm ci at :111). The check proves a clean install reproduces the locks, and its main value is the local drift guard task-236 built. It does not attest the post-test environment. Put this in docs/architecture/Code/testing.md.
6. Business P2-A3: backend/app/campaigns/duplication.py:1-8 still quotes "make the manager decide deliberately instead of fast" as the governing premise. Since the Variant Editor interview (Q5.1), duplicating within a campaign is one click; the deliberate wizard remains only for copying into another brand, where content is forked. Reword the docstring to say the friction applies to the cross-brand copy because forking is the risky case.

Source: [[Interview Prep - Since 2026-09-18]] (Client Q2, Q4, Q5; CI Q2, Q5) and docs/business-interview-baseline.md P2-A3.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Each of the six places says what is true, citing the record that settles it
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: a seventh item, from CI Q3. The README tells an adopter that a fork must configure its own required checks: CI in a fork checks that fork's code and enforces nothing by itself (ADR-190, 2026-10-09 addendum).

2026-10-10, done (commit 69e3d3b). All seven items are worded as decided:
- resources.ts manifest caching, Client Q2;
- client.ts CSRF owner and write sites, Client Q4;
- TypedApiClient.md 'What the guarantee covers', Client Q5;
- check_installed.py docstring on this platform's bindings, CI Q2;
- testing.md 'Why the installed-packages check runs on a fresh install', CI Q5;
- duplication.py docstring, P2-A3;
- README on forks setting their own required checks, CI Q3.

No behaviour changes. The full backend suite (1652) passed, including the text-scanning guards, plus Ruff, tsc and ESLint. The CI run for 69e3d3b was cancelled by the next push; run 38083935595 on 5366e90, which contains it, is green.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Seven comments and notes the 2026-10-09 interview review found stale or missing now say what is true, each citing the record that settles it: manifest caching, the CSRF token's write sites, the typed client's guarantee, the optional-package exemption, why the installed-packages check runs on a fresh install, duplication friction, and that a fork sets its own required checks. Wording only. Verified by the full suite including the text guards, and green CI on 5366e90.
<!-- SECTION:FINAL_SUMMARY:END -->
