---
id: TASK-344
title: An integration's API key cannot be given an expiry date
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 18:58'
updated_date: '2026-10-11 15:10'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 201060
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** An integration's API key lives until someone revokes it. IntegrationCredentialDB (backend/app/auth/db_models.py around :242) has issue, use and revocation fields but no expiry, and authentication (backend/app/auth/integrations.py around :387) never checks one. A person's session expires twice: 12 hours absolute, 60 minutes idle. So an agency operator who leaves keeps a working key indefinitely unless someone remembers to revoke it. That is the risk ADR-166 itself names; its 2026-10-02 addendum recorded it as a gap.

Decided by the user in the 2026-10-09 interview review (business baseline P2-B2; second 2026-10-09 addendum to ADR-166):
- When a key is issued, the issuer may set an expiry date. Its length is the company's choice.
- The integrations list shows each key's age and expiry.
- An expired key is refused exactly like a revoked one.

Optional, not mandatory, because a mandatory expiry could break an unattended integration overnight. Decided now, built later.

Left to the final-design pass:
- a date or a duration;
- a warning before expiry;
- adding an expiry to an existing key;
- the interaction with rotation (several credentials under one integration).

Source: docs/business-interview-baseline.md → P2-B2.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A key can be issued with an expiry date
- [x] #2 An expired key is refused like a revoked one
- [x] #3 The integrations list shows each key's age and expiry
- [x] #4 A key issued without expiry behaves as today
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Final-design pass 2026-10-11, decided with the user one question at a time (closes the open list of ADR-166's second 2026-10-09 addendum):
- D1 The expiry is set as a duration in days at issue (empty = no expiry); the platform stores the resulting date and the number of days.
- D2 A warning in the app only: a key expiring within 14 days is marked, and so is its integration. No mail (no operator mail exists; task-76).
- D3 An existing key's expiry may be changed: adding one or bringing it forward needs integrations.manage only (it takes power away, like revoking); pushing it later or removing it needs integrations.manage AND every grant the integration has (like issuing). Audited with old and new date.
- D4 Rotation: each key gets its own expiry at issue; the issue form is pre-filled with the number of days the integration's newest key was given.

Where it lands:
1. Migration 0046: integration_credentials.expires_at (nullable) and expires_in_days (nullable).
2. auth/integrations.py: issue_credential(..., expires_in_days) (1 to 3650 days, ValueError otherwise); authenticate refuses an expired key on the revoked path; is_live(credential); set_credential_expiry(_by_person) with the D3 gate; suggested_expiry_days(integration).
3. integrations_router: KeyCreate.expires_in_days; CredentialOut gains expires_at, expires_in_days, expiring_soon; IntegrationOut gains expiring_soon and suggested_expiry_days; live_keys counts unexpired keys; PUT /integrations/{id}/keys/{credential_id}/expiry {expires_in_days: int|null}; audit integration.key_expiry_set {from, to}.
4. Jinja integrations page (frozen route set): its live count excludes expired keys; a key row shows its expiry.
5. Tests: issued with and without expiry; an expired key refused exactly like a revoked one (same answer); live count; the 14-day mark; shortening ungated, lengthening and removing gated; pre-fill from the newest key; bounds.
The React integrations screen is task-358.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09, from the ADR-166 addendum:
- live_keys is counted from revoked_at alone (backend/app/auth/integrations_router.py:106, backend/app/frontend/router.py:3516), so an expired key would show as live unless that changes.
- Adding an expiry to an existing key shortens its life, while changing or removing one lengthens it. The 2026-10-02 addendum leaves reductions ungated, so which gate applies is part of the open 'existing key' question.
- To the caller, an expired key looks the same as a revoked one; only the list tells them apart.

2026-10-11, built. Commits d0bcb51 (ADR-166 addendum 2026-10-11, second) and 40cc737. Before it, Codex doc-16 (c0cd3bf, missed at task-341's start because only the branch tip was checked) and doc-18 (5caf6a5) were integrated: 80e9e1e fixes transactional include rules (they used the marketing opt-in) and exclude rules (they missed a pinned person without an opt-in, ADR-176 point 1).

Decided with the user (D1-D4): days at issue; a 14-day mark in the app, no mail; shortening free, lengthening or removing gated; each key its own expiry, pre-filled from the newest key.

Where it landed:
- Migration 0046: integration_credentials.expires_at, expires_in_days. Applied to dev; existing keys have none.
- auth/integrations.py: EXPIRY_DAYS_RANGE (1-3650), EXPIRING_SOON_DAYS (14), is_live, is_expiring_soon, suggested_expiry_days, issue_credential(expires_in_days), set_credential_expiry(_by_person) with the gate; authenticate refuses an expired key on the revoked path.
- integrations_router: KeyCreate.expires_in_days (422 outside the range); CredentialOut expires_at, expires_in_days, expiring_soon; IntegrationOut expiring_soon, suggested_expiry_days; live_keys counts live keys only; PUT /integrations/{id}/keys/{credential_id}/expiry; audit integration.key_expiry_set {credential_id, from, to}; key_issued records expires_at.
- Jinja integrations page: live count excludes expired keys; a key row says "expired" or "expires <date>".
- Tests: test_key_expiry.py (12).

Verification: backend 1853 passed, Ruff clean; frontend tsc clean (schema regenerated). 8 mutations, all caught. Live check 2026-10-11: after the migration GET /integrations answers with the new fields, the dev keys have no expiry and the live counts are right (n8n 1 of 2, one revoked; webshop 1); the Jinja page renders. The React screen is task-358.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
An integration's key may be issued with an expiry in days (1-3650) or none, as before; an expired key is refused like a revoked one; the list shows expiry, counts only live keys and marks keys expiring within 14 days; an existing key's expiry can be brought forward freely and lengthened or removed only by someone holding every grant; the next key is pre-filled from the newest. Decided with the user and recorded in an ADR-166 addendum. Verified by 1853 backend tests, 8 mutation checks, green CI (40cc737) and a check of the migrated dev keys.
<!-- SECTION:FINAL_SUMMARY:END -->
