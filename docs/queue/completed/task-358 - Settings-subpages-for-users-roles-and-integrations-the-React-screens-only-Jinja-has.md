---
id: TASK-358
title: >-
  Settings subpages for users, roles and integrations (the React screens only
  Jinja has)
status: Done
assignee:
  - '@claude'
created_date: '2026-10-11 10:01'
updated_date: '2026-10-16 16:34'
labels:
  - frontend
  - backend
dependencies: []
type: feature
ordinal: 200600
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
- [x] #1 Users, roles and integrations are subpages of Settings in the React client
- [x] #2 Users and roles have people-only JSON routes reusing the auth service rules, audited
- [x] #3 An integration key's secret is shown once when issued and never again
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Final design (2026-10-16), with the user one question at a time:
- Lock-out guards: refused with the reason, deactivating yourself, and any deactivation, role removal or role edit that would leave no active person holding users.manage. In the auth service, so the Jinja forms get them too. Every admin write audited, including creating a user and every role write, which the Jinja forms never logged.
- Four Settings subpages: Users, Roles, Integrations, Brands. Brands: create (key, name), rename, delete (refused while anything belongs to it, as delete_brand does). The access-control switch stays out of React (a development switch).
- An integration key's secret is shown once in a dialog with Copy and "This is the only time it is shown"; closing it forgets it; the list shows only id, label, last use, expiry. Issuing asks a label and an optional expiry.

Shape:
1. backend/app/auth/admin_router.py, prefix /auth (on the _api plane, so BRAND_OWNED "/auth" covers it, its text updated): /auth/users (list, create, active, grants add/remove), /auth/roles (list with permissions and holders, create, permissions, delete), /auth/brands (list, create, rename, delete), /auth/permissions (the catalogue, platform vs brand-scoped). Router-level require_person_with(USERS_MANAGE), GETs included; policy entries for /auth/users, /auth/roles, /auth/brands. Same service functions as the Jinja forms; refusals as 409/422 with the service's words; audits added (USER_CREATED, ROLE_CREATED, ROLE_PERMISSIONS_SET, ROLE_DELETED, BRAND_RENAMED, BRAND_DELETED).
2. Guards in backend/app/auth/service.py (set_active, revoke_assignment, set_role_permissions) raising one refusal the Jinja routes show as ?error=.
3. React: SettingsLayout PARTS gains Users, Roles, Integrations, Brands; list and detail screens; the key dialog; hooks in resources.ts.
4. ADR-150 addendum (guards, audits, JSON admin routes, the switch stays out) and ADR-166 addendum (one-time secret dialog) by adr-author.
5. Tests, mutation checks, live check on scratch users, roles, brands and an integration.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-11, the user set the November 2026 presentations as the focus (docs/business/PRESENTATIONS-2026-11.md): users, roles and integration keys in Settings are on the demo list.

Built 2026-10-16 in two slices; CI green on bd584eb (backend) and ad9bf29 (client and ADR addenda).

Decided with the user, one at a time: refuse deactivating yourself and any change that leaves nobody active with users.manage, and audit every administration write; Brands as their own subpage, the access-control switch stays out of React; an issued key's secret in a dialog with Copy, shown once.

Backend: backend/app/auth/admin.py is the one copy of each administration write and its audit entry, used by the Jinja forms (backend/app/auth/router.py, which now show refusals as ?error=) and the new backend/app/auth/admin_router.py (/auth/users, /auth/roles, /auth/brands, /auth/permissions; people only, users.manage for reads too). Guards in backend/app/auth/service.py (user_managers, AccessLockout) in set_active, revoke_assignment and set_role_permissions. New audit actions: user.created, role.created, role.permissions_set, role.deleted, brand.renamed, brand.deleted. Policy entries for the three write prefixes; the /auth classification names the new routes; the four lists classified as fixed (tens of rows by nature).
Client: Settings gains Users (list, person page), Roles (list, permission editor grouped per brand and everywhere), Integrations (list, page with keys, grants, unattended ceiling, deactivate) and Brands (create, rename, delete after asking). The integration screens use the existing /integrations API unchanged.

Found and fixed during the build: the brand row's label dropped its key from the accessible name, every delete button was called Delete, and an empty brand was deleted on one press; now labelled per brand and asked first. Noted, not changed: there is no route to edit a person's name or email, nor to delete an account (deactivation is the offboarding control, ADR-151 point 5); a deactivated integration still shows its grant and ceiling forms.

Verification: pytest 2096; vitest 340; tsc, build, eslint (no errors), Ruff; mutations: backend nine, client four plus the brand confirmation, all caught (the admin role verified intact after the lock-out mutations); live check: the Users list with real accounts and "you", your own page offering no deactivation, a scratch integration with a key issued (shown once, gone on close), revoked and deactivated, and a scratch brand created and deleted.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Settings has Users, Roles, Integrations and Brands as subpages, over new people-only JSON routes for users, roles and brands that share one copy of each rule and audit entry with the Jinja forms. Nobody can deactivate themselves or leave the installation without anyone who can manage users; every administration write is audited. A new integration key's secret is shown once in a dialog and forgotten when it closes. ADR-150 and ADR-166 addenda. Verified by pytest 2096, vitest 340, mutation checks, a live check and CI.
<!-- SECTION:FINAL_SUMMARY:END -->
