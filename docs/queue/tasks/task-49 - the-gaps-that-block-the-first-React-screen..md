---
id: TASK-49
title: the gaps that block the first React screen.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-10-02 13:31'
labels:
  - backend
dependencies: []
type: feature
ordinal: 200200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — the gaps that block the first React screen.** **It said three and there were four.** **~~C1 the brand switcher~~ ✅ DONE 2026-09-20, ~~C15 the CSRF token after a reload~~ ✅ DONE 2026-09-20, C8 planning a send, C2 the settings surface** (`docs/react-screen-inventory.md`). C1 is one route and blocks the shell: `set_session_brand` has no JSON equivalent, so a cookie-authenticated SPA is stuck on whichever brand the session landed on. C8 is the largest capability gap in the product — `prepare_send_from_audience` has exactly one call site and it is the Jinja route, so without it "deliveries" is a read-only list of sends the client cannot create. C2 is not blocking the core loop and is blocking a usable product: there is no `app/settings/router.py` and no `app/ai/router.py`, so the entire settings surface is UI-only. **C15 was invisible to the method that found the others.** C1, C8 and C2 came from reading the API for what it cannot do; C15 came from walking the client's own lifecycle. Every route involved existed and worked — the CSRF token was obtainable only from the `/auth/session/verify` body, so a page reload left a valid session that could not write. `GET /auth/session` now returns it (dated addendum to ADR-168, three mutation-checked tests). **✅ The schema honesty pass is DONE 2026-09-20:** the four bare-dict routes (`process-due`, `process-expired`, `send-test`, `suggest-subject`) **plus the five session routes nobody had listed** — `/auth/session/request` and `/verify` also took `payload: dict = Body(...)`, so the generated client had no types at all for the sign-in flow. Twelve schemas added, none removed, path count unchanged. Two schema renames shipped with it: `RenderedVariant.html` → `artifact_body` (finishing ADR-162 pt 3) and `GET /email-modules` → `GET /modules`.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 146, section "Features", position 2 in that section (top = do next). The description is the original entry, verbatim.

2026-10-02: C8 done. POST /delivery/snapshots/{snapshot_id}/send-instances (backend/app/delivery/router.py plan_send, SendPlanRequest in models.py), tests/test_send_plan_api.py (10 tests, mutation-checked) plus a policy pair in tests/test_auth_policy.py. Rides the existing /delivery/ -> sends.plan entry. Refusals: 404 for a snapshot/audience not in the brand, 409 for an empty or over-cap audience. Not idempotent (ADR-142 §10). C2 (settings/AI routers) remains and is blocked on decisions: settings.manage vs ai.run for prompt publish/model choice, whether settings writes become approvable (ADR-142 §10), channel availability exposure. Found on the way: task-239 (NameError in the two Jinja send routes), fixed.

2026-10-02: C2 done. User decisions: prompt publish and model choice need settings.manage AND ai.run (a future run-time free-text input needs ai.run only, if it enters as input to the prompt, never editing it); settings changes are not approvable (danger zone later for risky ones); settings writes are people only; channel availability readable, not writable. Built: GET /settings (view) and PUT /settings/signals, /send-cap, /ai/spend-cap, /ai/provider, /ai/tasks/{key}/approval, PUT /ai/tasks/{key}/model, POST /ai/tasks/{key}/prompt — app/settings/router.py + models.py; rules in settings.service, shared with the Jinja page, which now also refuses a half-life <= 0, a warning above the hard stop, an unknown provider, an unknown task, and checks ai.run for prompts/models. tests/test_settings_api.py: 19 tests, ten mutants caught. Suite 879 passed. Not done: settings changes are not audited.
<!-- SECTION:NOTES:END -->
