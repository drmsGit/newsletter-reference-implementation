---
id: TASK-312
title: Retiring the frozen Jinja UI is undecided — no ADR records when or how it goes
status: To Do
assignee: []
created_date: '2026-10-09 07:02'
updated_date: '2026-10-09 07:03'
labels:
  - needs-adr
  - frontend
  - backend
dependencies: []
type: decision
ordinal: 305500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Decision: when and how the frozen Jinja UI is retired. No ADR or task records it.** Filed 2026-10-09 under task-306, decided with the user: the review brief says plainly that the React client replaces the Jinja UI, that the Jinja UI is frozen by a test, and that its retirement is not scheduled. The open question lives here so it is not only a sentence in a brief.

**What exists.** ADR-170 decides the React SPA as the manager client; it does not decide the end of the server-rendered UI. task-50 froze that UI for new features "the day the migration audit was done", and `backend/tests/test_jinja_freeze.py` enforces the freeze. It pins the exact set of `/ui` routes and everything in `backend/app/frontend/router.py`. Its docstring says it outright: "No ADR records the retirement or a date". The test is built to shrink: a frozen route that no longer exists fails the test, so the list can only get shorter.

**What it costs to keep.**
- `backend/app/frontend/router.py` is about 4,000 lines; `backend/app/templates/` holds the pages.
- The code-slimmer sweep of 2026-10-08 (finding D5) found no writes held only by Jinja: every write goes through a service. But it found two places where the planes differ. `deliveries_list` recounts "sent" per send while the delivery service stores `sent_count`, so the two screens can disagree. `_may_configure_ai` re-implements a permission rule that also lives in `backend/app/settings/router.py`.
- Every duplicate between a Jinja route and a JSON route is a rule that can drift. task-63's leftover duplication (`PUSH_CONTENT_FIELDS` and its agreement test) goes only when Jinja goes.

**What has to be decided:**
1. **The exit condition.** Which Jinja screens have no React equivalent yet, and which must exist before Jinja can go? Known gaps: the campaign send screen (task-67), and sign-in, users and roles, which `backend/app/auth/router.py` serves under `/ui`. An inventory of every frozen route against the React routes is the first step; `docs/react-migration-inventory.md` is a dated starting point.
2. **Whether to retire it whole or screen by screen.** Screen by screen fits the shrinking freeze test. All at once is simpler to reason about.
3. **The server-rendered sign-in, users and roles pages.** The React client signs in through its own JSON routes (`/auth/session/...` in `backend/app/auth/router.py`), so the `/ui/login` page is Jinja-only. User and role management under `/ui` need React screens, or a decision that they stay a platform-admin page, before Jinja can go.
4. **Record it** as an ADR, through the adr-author agent: a decision about the end of the second plane, which ADR-170 left open.
<!-- SECTION:DESCRIPTION:END -->
