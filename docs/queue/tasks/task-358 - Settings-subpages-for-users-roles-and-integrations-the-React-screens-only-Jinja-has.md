---
id: TASK-358
title: >-
  Settings subpages for users, roles and integrations (the React screens only
  Jinja has)
status: To Do
assignee: []
created_date: '2026-10-11 10:01'
labels:
  - frontend
  - backend
dependencies: []
type: feature
ordinal: 209600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** Raised by the user on 2026-10-11 while trying the manager app: user, role and integration administration exist only in the old Jinja UI, and the React client has no screen for any of them. They belong under Settings as subpages, next to General and Brand profiles, not as menu areas of their own: the user's rule of the same day ("a setting part, not an area"), already applied to brand profiles (frontend/src/screens/SettingsLayout.tsx).

**What exists today.**
- Users: /ui/users and its POST forms (backend/app/auth/router.py:215 onwards: invite, activate/deactivate, assign roles). **There are no JSON routes for users at all**; docs/react-screen-inventory.md marks them "no JSON routes".
- Roles: /ui/roles (backend/app/auth/router.py:391 onwards). Same: no JSON routes.
- Integrations: /ui/integrations (backend/app/frontend/router.py:3544), and a JSON router already exists (backend/app/auth/integrations_router.py, GET /integrations at :125, people-only via require_person_with(INTEGRATIONS_MANAGE)). Issuing a key must show the secret exactly once (ADR-166 point 3; the user's note of 2026-10-09: copy once, never revealed again).

**What it needs.**
1. JSON routes for users and roles, people-only, under users.manage, the same rules the Jinja forms apply, through the existing auth service functions (no second copy of the rules). Audit as the forms do.
2. Settings subpages: Users, Roles, Integrations, each a list plus detail, through SettingsLayout's PARTS.
3. A final-design pass first: which fields each screen shows (from the Jinja pages and the interview records), and the one-time secret display for integration keys.

**Related.** task-312 (retiring the Jinja UI names users and roles as the gap blocking it). ADR-150 (permissions and roles), ADR-166 (integrations). Keyboard and layout polish come in their own later session.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Users, roles and integrations are subpages of Settings in the React client
- [ ] #2 Users and roles have people-only JSON routes reusing the auth service rules, audited
- [ ] #3 An integration key's secret is shown once when issued and never again
<!-- AC:END -->
