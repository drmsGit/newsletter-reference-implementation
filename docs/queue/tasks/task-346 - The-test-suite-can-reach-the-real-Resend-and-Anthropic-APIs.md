---
id: TASK-346
title: The test suite can reach the real Resend and Anthropic APIs
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-10 18:59'
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
- [ ] #1 In every test, httpx.post to api.resend.com raises and fails the test
- [ ] #2 In every test, httpx.post to api.anthropic.com raises and fails the test
- [ ] #3 Tests that install their own fake httpx.post keep working
- [ ] #4 The full suite passes with the guard in place
<!-- AC:END -->
