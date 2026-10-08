---
id: TASK-302
title: >-
  End-to-end tests in a real browser with Playwright: a few flows the live
  checks run by hand today
status: To Do
assignee: []
created_date: '2026-10-08 18:59'
labels:
  - frontend
dependencies: []
type: chore
ordinal: 205805
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Nothing tests the platform in a real browser against the real server.** Raised by the user 2026-10-08, together with ESLint, which went to task-105.

**What exists today:**
- The client's screen tests (Vitest and Testing Library, frontend/src/screens/*.test.tsx) run in jsdom against a stub server (stubFetch in frontend/src/test-utils.tsx). They prove a screen's behaviour against the server's contract, and the contract check keeps the types honest. They do not prove that the real API, the real database and the real browser agree.
- The backend suite (pytest) drives the routes through TestClient, without a browser.
- The only real-browser checks are the live checks run by hand in the Claude browser pane at the end of each task, on scratch data (zz-scratch names, deleted afterwards). They have found real defects that the suites missed:
  - the recipient search returning everyone (task-297);
  - a send-only wording on a held request's reply (task-206);
  - a recalculation hint that misdescribed the action (task-297).
  But they are manual and not repeatable.

**Recommended tool: Playwright, not Cypress** (the user agreed 2026-10-08). It fits a Vite client without extra wiring, drives Chromium, Firefox and WebKit, runs headless in CI, and handles the two-origin setup here: the API on :8000, the client on :5173/manager/.

**A few flows, not a coverage target.** Candidates, each one a past live check:
- create an audience, add a rule, see the arithmetic change, delete it (task-297, task-300, task-298);
- an integration's readiness mark held, approved in the inbox, shown on the record page (task-206);
- the content record page: edit a field, mark ready (task-279, task-283);
- sign in with a dev code.

**Questions for the task, not decided here:**
- **Test data.** Today the live checks write scratch rows into the shared dev database and delete them afterwards. An end-to-end run needs a database of its own or a seeded fixture set. This overlaps the isolated test database already named in task-98.
- **Signing in.** Dev sign-in codes go to the API log. A test needs a test-only path, or a seeded session, that cannot exist in a deployment.
- **Sending.** The mock provider only, never Resend, and never raising the dev send cap.
- **Where it runs.** Locally first; in CI once task-105's workflow exists.

**Related:** task-105 (CI, linting), task-98 (test gaps, isolated test database), the keyboard and accessibility session (Playwright can check keyboard paths once that session decides them).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Playwright runs a few end-to-end flows (an audience edited with its arithmetic, a held readiness mark approved) against the real API and client on data of their own
- [ ] #2 Sign-in and test data are handled without anything that could exist in a deployment, and only the mock provider is used
- [ ] #3 It runs locally with one command, and in CI once task-105's workflow exists
<!-- AC:END -->
