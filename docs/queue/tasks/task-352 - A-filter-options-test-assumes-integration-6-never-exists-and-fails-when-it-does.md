---
id: TASK-352
title: >-
  A filter-options test assumes integration #6 never exists, and fails when it
  does
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-10 21:41'
updated_date: '2026-10-10 21:50'
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
- [ ] #1 The test no longer depends on any fixed integration or user id being absent
- [ ] #2 It passes alone, in the full suite, and in a -k subset that previously failed
<!-- AC:END -->
