---
id: TASK-245
title: >-
  No settings change is audited — the send cap, the AI spend limit and the
  access-control switch included
status: Done
assignee:
  - '@claude'
created_date: '2026-10-03 08:54'
updated_date: '2026-10-03 08:59'
labels:
  - backend
dependencies: []
priority: p1
type: bug
ordinal: 100500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug, accountability]** Found 2026-10-03 while starting the React settings screen. [[ADR-153 — Audit and Accountability]] point 4 sets writes as the audit floor, and no settings write records an audit event:

- JSON (task-49 C2, `backend/app/settings/router.py`): PUT /settings/signals, /settings/send-cap, /settings/ai/spend-cap, /settings/ai/provider, /settings/ai/tasks/{key}/approval, /settings/ai/tasks/{key}/model, and POST /settings/ai/tasks/{key}/prompt. None calls audit.
- Jinja (`backend/app/frontend/router.py`, the six POST /ui/settings* handlers): none calls audit.
- **The access-control switch**, POST /ui/users/enforcement (`backend/app/auth/router.py:450-463`), turns authentication off for everyone through `set_config` and records nothing.

The playbook carried 'settings changes are not audited' as an open decision. It isn't one: ADR-153 already decided it. What these settings control is why it matters: how many recipients one send may reach, how much AI may spend, which tasks auto-apply AI output, and whether access control exists at all. ADR-142's addendum makes no settings change approvable ('whoever holds settings.manage is the authority'), so the audit log is the only after-the-fact accountability these changes have.

Settings are deployment-wide, not brand-owned (`backend/app/auth/policy.py` entry for /settings), so entries carry no brand.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every non-GET settings route on both planes, and the access-control switch, writes an audit event naming the actor, the setting, and the before and after values (a prompt publish records the task and version, not the body)
- [x] #2 A test enumerates the registered settings write routes from the app itself, so a new route without an audit entry fails the suite
- [x] #3 Tests restore or keep every setting's value; the send cap is never raised
- [x] #4 Each new test is mutation-checked
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Governing: ADR-153 point 4 (writes are the floor), ADR-142 addendum (no settings change is approvable, so the audit log is the only accountability), ADR-152 (no secrets in the log).
1. New `backend/app/settings/audited.py`: a context manager audited_settings(request, db, setting, keys=[...]). It reads the named app_config keys before and after and records audit.SETTINGS_CHANGED via record_from_request only if the block succeeded (a refusal writes nothing, so it records nothing). brand_id=None, because settings are deployment-wide. Keys are explicit, never a whole-table diff, so a secret stored in app_config later cannot reach the log. A caller-filled note dict covers what isn't a config key (prompt publish: task + version, never the body).
2. Wrap all 7 JSON writes (`backend/app/settings/router.py`), the 6 Jinja handlers (`backend/app/frontend/router.py`) and the access-control switch (`backend/app/auth/router.py`, setting 'access_control').
3. Tests in `backend/tests/test_settings_api.py`: a guard that enumerates the registered non-GET /settings and /ui/settings routes plus the switch, each with a no-op payload (current values; send cap and access control kept as they are), and asserts one audit row naming the setting. An unknown new route fails it. Plus before/after content, refusal-not-audited, and prompt detail without the body.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-10-03. `backend/app/settings/audited.py`: audited_settings(request, db, setting, keys) records audit.SETTINGS_CHANGED (detail: setting, per-key before/after, plus note) only when the block completes; brand_id=None. It wraps all 7 JSON writes (`backend/app/settings/router.py`), the 6 Jinja handlers (`backend/app/frontend/router.py`) and the access-control switch (`backend/app/auth/router.py`). A prompt publish records task and version, never the body. Tests in `backend/tests/test_settings_api.py` (TestEverySettingsWriteIsAudited): the guard enumerates app.routes, every write is a no-op with current values, and the send cap (200) and access control (on) were confirmed unchanged after the full run. Each test cleans up its own audit rows. Mutation-checked: 8 mutants caught, including a new unaudited route. Two survivors were investigated: one was a malformed mutant (redone, now caught); the other showed db.expire_all() was dead code, and it was removed. The playbook's 'decisions not taken' list is corrected: this was ADR-153 already. Suite 1029 passed, rc=0.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Every settings write on both planes, and the access-control switch, now records who changed which setting, before and after (prompt: task and version, never the body). A guard test enumerates the registered routes, so a future unaudited settings write fails the suite. Verified: 5 tests, 8 mutants caught, suite 1029 passed; send cap and access control untouched.
<!-- SECTION:FINAL_SUMMARY:END -->
