---
id: TASK-342
title: 'Session lengths are fixed in code, though they are company policy'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 18:49'
updated_date: '2026-10-11 12:58'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 201050
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** The absolute session lifetime (12 hours) and the idle timeout (60 minutes) are code constants: SESSION_ABSOLUTE_HOURS and SESSION_IDLE_MINUTES in backend/app/auth/service.py around :51-52. backend/app/settings/service.py has no getter for either. These two are company policy: a works council or an ISO 27001 auditor may require other lengths, and the repo's own rule gives numbers to the company and the mechanism to the product.

Decided by the user in the 2026-10-09 interview review (business baseline P2-B1; recorded in a 2026-10-09 addendum to ADR-151): the two session lengths become company settings, each clamped to a safe range. The attack-resistance numbers stay in code as a stated exception: sign-in code lifetime, guesses, and code-request rate limits. Decided now, built later.

Left to the final-design pass:
- the safe ranges;
- whether a changed length applies to sessions that already exist;
- that the change is audited like other settings (backend/app/settings/audited.py).

Source: docs/business-interview-baseline.md → P2-B1.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Absolute session lifetime and idle timeout are company settings with enforced safe ranges
- [x] #2 Sign-in code lifetime, attempts and request limits remain code constants
- [x] #3 Changing a session length is audited
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Final-design pass 2026-10-11, decided with the user one question at a time (closes the open list of ADR-151's 2026-10-09 addendum):
- D1 Safe ranges: absolute lifetime 1 to 72 hours (default 12); idle timeout 5 to 480 minutes (default 60), and never longer than the absolute lifetime. 5 minutes stays well above the 60-second activity refresh (TOUCH_INTERVAL).
- D2 Existing sessions: a shorter length applies at once to everyone signed in (a session past the new limit ends on its next request); a longer lifetime applies only to sessions started afterwards (nobody's session is silently extended); a longer idle timeout applies at once (it never reaches past a session's lifetime).
- Settled by the addendum already: sign-in code lifetime, guesses and code-request limits stay code constants; the change is audited like other settings.

Where it lands:
1. settings/service.py: keys session_absolute_hours, session_idle_minutes; get_session_lengths(db) -> (hours, minutes) in one query, falling back to the defaults and clamped to the ranges; save_session_lengths(db, hours, minutes) refusing out-of-range or idle longer than the lifetime (SettingsInvalid).
2. auth/service.py: create_session stamps expires_at with the current lifetime; the session check ends a session at min(its stamped expiry, created_at + the current lifetime) (shorter applies now, longer only to new sessions) and checks idle against the current idle timeout. The constants become the defaults only.
3. auth/router.py: the cookie max_age from the current lifetime at sign-in (both sign-in routes).
4. settings router: PUT /settings/session-lengths {absolute_hours, idle_minutes}, people only, settings.manage, audited through audited_settings; the Settings read model carries both and the ranges.
5. Frontend: a "Sign-in sessions" section on Settings, General, with the two numbers, their ranges and a save, in the send-cap section's pattern.
6. Tests: ranges refused; idle longer than the lifetime refused; shortening ends an existing session at once; lengthening does not extend an existing session but does a new one; the idle change applies at once; audited; code-attack constants unchanged; the cookie max_age follows the setting.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09, from writing the ADR-151 addendum: the session constants are at backend/app/auth/service.py:52-53, not :51-52. Facts for the final-design pass:
- TOUCH_INTERVAL is 60 seconds (:905) and is commented as short against the idle timeout, so an idle floor near it would break that.
- The cookie max_age derives from SESSION_ABSOLUTE_HOURS (backend/app/auth/router.py:194 and :663).
- Absolute expiry is stamped into each session row at creation (:892), while idle is checked against the constant on every request (:930). So 'does a change apply to existing sessions' plays out differently for the two.

2026-10-11, built. Commits b2c0bc8 (ADR-151 addendum 2026-10-11) and 9f36608. Before it: Codex doc-17's zero-ceiling batch gap was fixed with its test (5e39bfd), and task-363 was filed at the user's request (measuring an integration-fired send end to end).

Decided with the user (plan D1, D2): ranges 1-72 hours and 5-480 minutes, idle never longer than the lifetime; shorter applies at once, a longer lifetime only to new sessions, a longer idle timeout at once.

Where it landed:
- settings/service.py: SESSION_ABSOLUTE_HOURS_KEY, SESSION_IDLE_MINUTES_KEY, the ranges; get_session_lengths (one query, defaults, clamped on read, idle capped at the lifetime); save_session_lengths (refuses outside the ranges or idle longer than the lifetime).
- auth/service.py: create_session stamps the current lifetime; _session_user ends a session at the earlier of its stamped expiry and its start plus the current lifetime, and checks idle against the current timeout. The constants are now the defaults only.
- auth/router.py: the cookie max_age from the setting at sign-in, both sign-in routes (_cookie_max_age).
- settings router and models: PUT /settings/session-lengths (people only, settings.manage, audited as session_lengths, 422 outside the ranges); the Settings read carries both.
- Frontend: Settings, General gets "Sign-in sessions" with the two numbers, their ranges and what a change does.
- Tests: test_session_lengths.py (17); test_settings_api's audit coverage list gains the route; Settings.test for the section. The cookie test mints its code directly, because the request route's per-client limit is used up by earlier tests in the suite.
- ADR-151 addendum gained one sentence after review: a stored value is still clamped when read.

Verification: backend 1834 passed, Ruff clean; frontend 268 passed, tsc and eslint clean; 8 mutations caught (the cookie one on the JSON sign-in route the test uses). Live check 2026-10-11: Settings, General shows the section with 12 hours and 60 minutes, the ranges and the note; the user's dev values were not changed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Session lengths are company settings: the absolute lifetime (1-72 hours) and idle timeout (5-480 minutes, never longer than the lifetime) are set on Settings, General by a person under settings.manage and audited; a shorter value applies to existing sessions at once, a longer lifetime only to new ones; sign-in code numbers stay code. Decided with the user and recorded in an ADR-151 addendum. Verified by 1834 backend and 268 frontend tests, 8 mutation checks, green CI (9f36608) and a live view of the new section.
<!-- SECTION:FINAL_SUMMARY:END -->
