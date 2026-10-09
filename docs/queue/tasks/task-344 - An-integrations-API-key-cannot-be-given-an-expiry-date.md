---
id: TASK-344
title: An integration's API key cannot be given an expiry date
status: To Do
assignee: []
created_date: '2026-10-09 18:58'
updated_date: '2026-10-09 19:03'
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
- [ ] #1 A key can be issued with an expiry date
- [ ] #2 An expired key is refused like a revoked one
- [ ] #3 The integrations list shows each key's age and expiry
- [ ] #4 A key issued without expiry behaves as today
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09, from the ADR-166 addendum:
- live_keys is counted from revoked_at alone (backend/app/auth/integrations_router.py:106, backend/app/frontend/router.py:3516), so an expired key would show as live unless that changes.
- Adding an expiry to an existing key shortens its life, while changing or removing one lengthens it. The 2026-10-02 addendum leaves reductions ungated, so which gate applies is part of the open 'existing key' question.
- To the caller, an expired key looks the same as a revoked one; only the list tells them apart.
<!-- SECTION:NOTES:END -->
