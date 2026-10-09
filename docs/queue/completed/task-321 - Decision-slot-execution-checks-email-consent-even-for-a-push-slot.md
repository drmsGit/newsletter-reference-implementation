---
id: TASK-321
title: Decision-slot execution checks email consent even for a push slot
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 08:01'
updated_date: '2026-10-09 09:00'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Severity: medium. A valid push audience can fail at send time, while direct push decision execution can accept the wrong consent channel. Reachable today.

Evidence: backend/app/decision/service.py:51 calls require_consent with brand and marketing purpose but omits channel. backend/app/recipients/consent.py:374 defaults that parameter to email. The send executes recipient-specific slots at backend/app/delivery/service.py:1038 and rethrows ConsentDenied rather than treating it as an empty pick.

Reproduction: grant marketing consent for push only; create a push variant with a decision slot; execute for that recipient. It is rejected for missing email consent despite valid push consent. This was reproduced in the first review stage. Conversely an email-only recipient can pass this direct decision guard for a push slot.

ADR-163 defines consent independently per channel and purpose; ADR-160's slot execution must enforce that same scope. Derive the channel from the slot's variant and pass it explicitly through the decision consent gate.

Related: task-42's channel/purpose integrity work is relevant; this omitted argument remains outside the otherwise channel-aware send exclusion.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A push decision slot accepts push marketing consent without requiring email consent.
- [x] #2 Email marketing consent alone cannot satisfy a push decision slot.
- [x] #3 An eligible push send with recipient-specific slots completes without a spurious email ConsentDenied.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: promoted from ChatGPT's code review (docs/queue/docs/doc-1, draft-5) by the user's decision, ordered by severity. Claude verified the core evidence against the code the same day: require_consent is called without channel (backend/app/decision/service.py:51), and its channel defaults to DEFAULT_CHANNEL, email (backend/app/recipients/consent.py:379).

2026-10-09: fixed (commit ffb68c8; CI green on 872caab).

Change: execute_decision_slot (backend/app/decision/service.py) reads the slot's variant channel (VariantDB.channel through slot.variant_id) and passes it to require_consent. Before, the channel defaulted to email.

Tests:
- backend/tests/test_slot_consent_channel.py (mine) covers three cases with the real engine, imported before the world fixture replaces it: a push slot accepts push-only consent; email-only consent is refused for a push slot (ConsentDenied); a push send with a personal slot completes. All three failed before the fix: push consent refused, email consent accepted, and the push send raising.
- backend/tests/test_decision_send_pipeline.py (Codex, cherry-picked as 72df52b from codex/regression-tests after review): parametrised over email and push, with the real engine and real channel readiness, a first send delivers an eligible pick; after readiness is removed, the second send mails nothing. This covers task-320 and task-321 end to end.
Mutation check: dropping the channel fails all three of mine. Full suite: 1553 passed (1563 with later work).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A decision slot now checks consent on its own variant's channel. Push-only consent is accepted for a push slot, email-only consent no longer satisfies one, and push sends with personal slots complete. Verified by 3 tests that failed before the fix, Codex's end-to-end email and push pipeline test, a mutation check, the full suite and CI green.
<!-- SECTION:FINAL_SUMMARY:END -->
