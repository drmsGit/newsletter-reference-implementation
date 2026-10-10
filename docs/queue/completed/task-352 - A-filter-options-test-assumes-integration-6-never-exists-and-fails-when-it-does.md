---
id: TASK-352
title: >-
  A filter-options test assumes integration #6 never exists, and fails when it
  does
status: Done
assignee:
  - '@claude'
created_date: '2026-10-10 21:41'
updated_date: '2026-10-10 21:56'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug, test]** backend/tests/test_approvals_list.py, TestFilterOptions.test_it_offers_this_brands_actions_and_requesters_by_name (around :137-168), asserts that a requester which no longer exists is offered 'named honestly': named[('integration', 6)] == 'integration #6'. The rows fixture (around :39-72) hard-codes requested_by_id=6 for that requester and assumes no integration with id 6 exists.

Integration ids in the per-checkout test database keep counting up across tests. Whether id 6 exists depends on which tests ran before, and on what an earlier run left behind. On 2026-10-10 the test failed when only a subset ran (pytest -k 'product or name or mode'): it got 'apitest-f192623f', the name of an existing integration, instead of 'integration #6'. It passed alone and in the full suite.

It is order-dependent, so it can turn CI red by chance. Nothing shipped is affected: the route behaves correctly, and the test's premise is what is wrong.

Suggested direction for whoever fixes it (not decided): use an id that provably does not exist, for example create an integration, note its id and delete it, or take max(id) + a margin. Do not use a fixed number. The fixture's other fixed requester ids (integration 5, users 1 and 2) rest on the same assumption and should be checked the same way.

Found 2026-10-10 while writing docs/design/CONSTRAINTS.md; filed on the user's decision.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The test no longer depends on any fixed integration or user id being absent
- [x] #2 It passes alone, in the full suite, and in a -k subset that previously failed
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10, done (commit 91ee17c).

Reproduced with a throwaway session plugin (scratchpad, not in the repo) that plants integrations 5 and 6 and advances the id sequence. Both name assertions failed: integration #6 in the filter-options test, and integration #5 in the decision-history test, which the entry had flagged as the same assumption.

Fix: the rows fixture creates two integrations and deletes them, and uses their ids. Postgres never reuses a serial id, so they provably name nobody. Tests read the ids from rows[0], rows[3] and rows[4] instead of 5 and 6.

User ids 1 and 2, and integration 99 in the foreign-brand test, stay: their tests do not depend on the id being absent. They are a filter or an 'is not offered' check.

Verified: 9 passed with 5 and 6 planted, alone, and in the -k subset that failed (204 passed). Full suite 1660 passed. Ruff clean. CI green on 91ee17c.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The approvals-list tests no longer assume integrations 5 and 6 don't exist: the fixture now uses ids of integrations it created and deleted, which provably name nobody. It was reproduced by planting integrations 5 and 6 (two name checks failed); with the fix, all 9 pass there, alone and in the subset that failed. Full suite green, and CI green on 91ee17c.
<!-- SECTION:FINAL_SUMMARY:END -->
