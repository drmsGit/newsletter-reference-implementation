---
id: TASK-314
title: >-
  The consent-drift direction crm_ahead cannot occur under the event model, yet
  the API still offers it
status: To Do
assignee: []
created_date: '2026-10-09 07:22'
labels:
  - needs-adr
  - backend
dependencies: []
type: decision
ordinal: 300180
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Decision: the consent-drift direction `crm_ahead` cannot occur under the event model, yet the API still offers it.** Found on 2026-10-09 while fixing task-307. Filed at the user's request.

**What ADR-163 says.** The 2026-09-12 addendum (point 4) gives drift a direction, because the two cases need opposite corrections:
- **platform_ahead**: something here, usually a bounce or complaint, opted the person out and the CRM has not been told. Relay it outward.
- **crm_ahead**: the CRM asserted something that never took effect here. Re-run the sync.

**Why `crm_ahead` is unreachable now.** Consent is computed from events, and the latest event wins per (recipient, brand, channel, purpose) (`backend/app/recipients/db_models.py:36`). A CRM assertion is itself an event (`source="crm"`). So when the CRM's event is the newest, it *is* the effective state and nothing disagrees. When something newer disagrees, the platform moved after the CRM, which is `platform_ahead`.
- `detect_consent_drift` (`backend/app/recipients/service.py`, after "If the newest event IS the CRM's") concedes this in a comment: a disagreement means the effective event is newer than the CRM's.
- Yet `ConsentDriftDirection.crm_ahead` (`backend/app/recipients/models.py:139`) and the function's docstring still describe it as a live case.
- No test produces it. The only direction test is `test_provider_suppression_shows_as_platform_ahead` (`backend/tests/test_consent_gates.py:624`).

"The CRM said something that never took effect" was a real case in the old model, a mutable `consent_status` column beside a sync log. In the event model, a CRM assertion that fails to take effect leaves no consent event at all, only a failed row in the consent sync log (`ok=False`).

**The options:**
1. **Remove `crm_ahead`.** Drift then has one direction, and the field could go too. This changes ADR-163's addendum point 4, so it needs a dated addendum (adr-author). The API enum changes, so the client types must be regenerated.
2. **Redefine it** as "the CRM's last sync for this cell failed": read from the consent sync log, not the event log. That keeps the two-way distinction ADR-163 wanted, with a source that can actually produce it. It also needs an addendum.
3. **Leave it as documented-unreachable**, with a comment and a test that pins it as unreachable. Cheapest, but the API keeps offering a value it never sends.

Related: task-135 (suppression and opt-out reasons) and task-246 (consent event notes). The same cleanup could name the "latest event wins" ordering once, which task-307's optional step 4 left undone.
<!-- SECTION:DESCRIPTION:END -->
