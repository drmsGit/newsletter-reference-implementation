---
id: TASK-346
title: The test suite can reach the real Resend and Anthropic APIs
status: Done
assignee:
  - '@claude'
created_date: '2026-10-10 18:59'
updated_date: '2026-10-10 19:11'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100350
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug]** main.py loads backend/.env into the process environment at import (_load_local_env, around :60-95), and many test modules import main, for example via TestClient(app). From then on RESEND_API_KEY and ANTHROPIC_API_KEY are set for the rest of the run.

Both real adapters call the module-level httpx.post:
- backend/app/delivery/providers/resend.py around :68, against RESEND_API_URL (:26);
- backend/app/ai/adapters/claude.py around :139 and :221, against API_BASE (:36).

So any test that plans a send with provider "resend", or runs an AI task with provider "claude", without installing its own fake reaches the real vendor. Nothing in the suite stops it.

It happened on 2026-10-10 while writing task-330's tests. A test planned a send with provider "resend" and did not patch the provider, and two real Resend API calls went out, one per run. Each was a single message to a random ...@example.invalid address, so no person received mail, but Resend accepted both. That breaks the standing rule of no real email in testing.

Decided with the user 2026-10-10: guard first, then task-330. An autouse fixture in backend/tests/conftest.py makes any httpx.post to the two vendor hosts raise and fail the test, whatever .env holds. A test that installs its own fake httpx.post (tests/test_resend.py, tests/test_send_timeout.py, tests/test_ai_claude_adapter.py) overrides the guard, as today. The Anthropic host was added by Claude in the same guard, stated to the user at the time; it costs money per call.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 In every test, httpx.post to api.resend.com raises and fails the test
- [x] #2 In every test, httpx.post to api.anthropic.com raises and fails the test
- [x] #3 Tests that install their own fake httpx.post keep working
- [x] #4 The full suite passes with the guard in place
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10, done (commits 62c327f and 015bfd3).

The guard is an autouse fixture in backend/tests/conftest.py. It wraps httpx.post and raises for api.resend.com and api.anthropic.com (REAL_VENDOR_HOSTS). A test's own monkeypatch of httpx.post replaces it for that test's duration, so the adapter tests in test_resend.py, test_send_timeout.py and test_ai_claude_adapter.py pass unchanged.

Tests: backend/tests/test_no_real_vendor_calls.py.
- Both hosts are refused.
- ResendProvider cannot send.
- The exact send that leaked (provider "resend", nothing faked) now fails loudly.
- A test's own fake still decides.

Red run: done behind a dead proxy (HTTPS_PROXY=http://127.0.0.1:9), so nothing could reach a vendor. 4 failed with ConnectError before the guard.

Mutation (REAL_VENDOR_HOSTS emptied, behind the dead proxy): 4 failed.

Suite: full suite 1618 passed at the guard commit.

CI caught one gap: it has no RESEND_API_KEY, so the adapter returned 'key not set' before the network and the leak test did not raise. Fixed in 015bfd3, where the test sets a fake key, because the leak had a real one. CI is green from ef81dc4.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
No test can reach the real Resend or Anthropic API any more: an autouse guard in backend/tests/conftest.py refuses httpx.post to both hosts whatever .env holds, while tests that fake httpx.post keep working. Filed after two real Resend calls (to @example.invalid) leaked from a task-330 test on 2026-10-10. Verified by test_no_real_vendor_calls.py (red behind a dead proxy, mutation caught), the full suite, and green CI on ef81dc4.
<!-- SECTION:FINAL_SUMMARY:END -->
