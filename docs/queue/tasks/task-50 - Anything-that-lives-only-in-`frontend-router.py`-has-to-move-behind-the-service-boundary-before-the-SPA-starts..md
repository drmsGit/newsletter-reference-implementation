---
id: TASK-50
title: >-
  Anything that lives only in `frontend/router.py` has to move behind the
  service boundary before the SPA starts.
status: In Progress
assignee:
  - '@claude'
created_date: '2026-09-27 13:56'
updated_date: '2026-10-02 12:08'
labels:
  - backend
dependencies: []
type: feature
ordinal: 200300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — the precondition for the React build, and the one thing that makes retiring the Jinja UI safe rather than lossy.** **Anything that lives only in `frontend/router.py` has to move behind the service boundary before the SPA starts.** The file is 4,419 lines and was always a verification harness, not the product — [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]] gives it a deletion date, so refactoring it for longevity would be wasted work. What is **not** optional is the audit: every route that validates, orders, defaults, derives a value, sequences a multi-step operation, or makes an authorisation judgement inside the router holds a backend rule in a template layer, and deleting that file deletes the rule. The React client must not be asked to reimplement backend business logic — if it can, so can any other client, and the rule was never enforced. **Do:** sweep the router, classify every write route as (a) presentation only, (b) logic that must move into a service, (c) capability with no JSON equivalent; move the (b) set with tests that pin the behaviour at the service level; close the (c) set as API gaps. Freeze the Jinja UI for new features the same day. **The sweep is done — `docs/react-migration-inventory.md`, 2026-09-19.** 83 routes: **33 presentation, 27 logic-only, 26 capabilities with no JSON route.** Half the file is not presentation. The three that carry a rule rather than a convenience: **the brand boundary on reads exists only here** (15 call sites; `GET /content/`, `GET /content/{id}`, `GET /campaigns/` and `GET /api/audience-groups/` return every brand's rows today, and `get_content_record` (`content/service.py:44`) takes no `brand_id` at all, so it cannot be scoped); **`channel_available` has exactly two call sites, both in this file**, so deleting it deletes the server-side enforcement of ADR-160 point 8; and **`_may_decide` (`frontend/router.py:4167`) is the per-row approval gate** that `auth/policy.py:129` documents as the real one. Raised by `CODE_QUALITY_RELEASE_POSITIONING_2026-09-19` §6, and it is the review's most load-bearing point — though the review saw the router's size and not its contents, and the contents are worse.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 148, section "Features", position 3 in that section (top = do next). The description is the original entry, verbatim.

2026-10-02 audit (subagent sweep, code read for the security items only): the three rules the entry names are already fixed — brand reads (ADR-172, brand_id keyword-only), channel_available (campaigns/service.py), _may_decide (approvals.service.may_decide). Still router-only, ranked: B2/C6/C9/B14 cross-brand duplicate authorisation; B18 push fields written only when non-empty (ADR-161 readiness) vs JSON POST /content/; C14 integrations credentials (secret shown once); B5-B8/C3/C4 settings validation (with C2); task-57 graph brand filter + B26 recipient_count. No guard test exists against new logic landing in frontend/router.py. DONE in this pass: B2/C6/C9 — duplication.require_target_access etc. in campaigns/duplication.py, request.state.principal in the JSON guard, POST /campaigns/{id}/duplicate and POST /content/{id}/duplicate; machines allowed where they hold the grant (user decision). 8 new tests in tests/test_duplication.py, five mutants caught; suite 808 passed. NOT done: B14 (JSON read of which target brands/modes are offered; the SPA would reimplement it). Next: B18, then C14.
<!-- SECTION:NOTES:END -->
