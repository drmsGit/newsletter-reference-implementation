---
id: TASK-355
title: 'Transactional brand profiles: an email sent without the opt-in check, guarded'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-11 08:39'
updated_date: '2026-10-11 11:23'
labels:
  - backend
  - frontend
dependencies:
  - TASK-350
type: feature
ordinal: 200985
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** Slice 4 of 5 of the brand-profile design (ADR-194, 2026-10-11).

A brand profile is marked marketing (the default) or transactional. A variant using a transactional profile may go out without opt-in consent. Today every planned send is marketing (task-42), and the send-time exclusion stack checks marketing consent for everyone (ADR-163; backend/app/delivery/exclusion.py).

Choosing a transactional profile on a marketing email would bypass that check, which would be a legal breach made with one dropdown. So, decided by the user:
- Creating a transactional profile, or marking one transactional, needs a separate permission and is audited.
- Choosing a transactional profile on a variant shows a clear 'sent without opt-in check' label and is audited.
- Duplicating a transactional profile keeps it transactional only for someone holding that right; otherwise the copy is marketing.
- A transactional profile may leave the unsubscribe text empty, and then no line is shown. The legal details are still on every email (task-350).

Final-design pass with the consent stage: how a transactional send meets the exclusion stack, which purpose it records (task-134's purpose vocabulary), and what still excludes a recipient (an unaddressable recipient, a hard suppression).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Only a holder of the transactional permission can create or mark a transactional profile; it is audited
- [x] #2 A variant using a transactional profile is sent without the opt-in check, labelled and audited
- [x] #3 Suppressed or unaddressable recipients are still excluded
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Final-design pass 2026-10-11, decided with the user one question at a time. This slice decides the minimum of two open needs-ADR items (task-134 (a), the transactional consent basis, and task-135, suppression); it is recorded as ADR-195 before any code.

Decisions:
- D1 Scope: decide only what this slice needs. A transactional send skips the marketing opt-in check and records purpose "transactional". It still excludes unaddressable recipients and anyone the provider suppressed: a hard bounce or spam complaint recorded for that brand and channel, on any purpose. No new suppression table: the provider-sourced opt-out events already recorded are read as suppression. task-134 (b) reputation streams and (c) modules, and task-135's full model, stay open.
- D2 No unsubscribe line and no one-click header on transactional emails in this slice, even when the profile has wording; the legal details stay. The block-list idea (an unsubscribe that stops transactional mail) stays open.
- D3 A transactional profile is never a brand's default: making one the default, or marking the default transactional, is refused.
- Earlier (design session, ADR-194): a separate permission to create or mark a transactional profile, audited; choosing one on a variant shows a 'sent without opt-in check' label and is audited; duplicating keeps transactional only for a holder of the right, otherwise the copy is marketing; a transactional profile may leave the unsubscribe wording empty.

Where it lands:
1. auth/permissions.py: BRAND_PROFILES_TRANSACTIONAL = "brand_profiles.transactional", brand-scoped; Admin by the preset, not Manager. permission tests updated (18 keys, 10 brand-scoped).
2. recipients/consent.py: TRANSACTIONAL purpose; provider_suppressed_filter(brand_id, channel) and send_floor_filter(brand_id, channel, purpose) (marketing: the opt-in floor; transactional: not provider-suppressed).
3. delivery/exclusion.py: stage 2 runs for marketing only; stage 3 (suppression) gets its first rule, for transactional: provider-suppressed recipients excluded, reason recorded under suppression.
4. audience/service.py resolve_audience / _resolve: the floor by purpose (a purpose argument, default marketing for existing callers). delivery/service.py: a send's purpose from its snapshot's frame (brand_profile.kind, email frames of version 3; marketing otherwise), written on every execution at plan and re-resolution, and used for the audience floor.
5. subscriptions footer_for already gives no link for a non-marketing purpose; the legal footer then has no unsubscribe line. Test send: the wording unlinked only for marketing profiles.
6. brand_profiles service and router: kind transactional on create/update needs the permission (403 without); duplicate keeps it only for a holder; make_default refuses a transactional profile and update refuses marking the default transactional (409); audit details carry the kind. may_mark_transactional on the single read.
7. Variant: choosing a transactional profile is audited with the kind in variant.updated's detail; the composition already reports kind.
8. approvals send_fire describe: a warning that the send goes out without the opt-in check, naming the profile.
9. Frontend: the profile form's kind choice (enabled for holders, otherwise read-only); the variant editor's 'Sent without opt-in check' label and the dropdown option marked transactional.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-11, built. Commits 9da198a (ADR-195) and 68c7f1f.

Decided with the user (plan D1-D3), plus two gaps the ADR author found, both decided the same day and written into ADR-195 before any code:
- Provider suppression applies to EVERY send, marketing too: a dead address is dead either way, and a complaint about any of a brand's mail is a reason not to send it newsletters. Marketing sends exclude a little more than before, never less.
- suppress_recipient records the provider's opt-out even when the cell is already opted out (a complaint after a marketing unsubscribe), unless the provider already suppressed that same cell; otherwise the suppression rule would have nothing to read.
- Kept as it was, said to the user: a marketing bounce on the marketing cell is still recorded under the consent stage, because stage 2 runs first; stages decide the recorded reason, never who is excluded. Suppression shows where the opt-in check would not have caught the person (a bounce on another purpose).

Where it landed:
- auth/permissions.py: brand_profiles.transactional, brand-scoped, Admin by the preset (the dev Admin got it at restart), not Manager.
- recipients/consent.py: TRANSACTIONAL, PROVIDER_SOURCE, provider_suppressed_filter (any provider opt-out for brand and channel, any purpose), send_floor_filter (marketing: opt-in and not suppressed; transactional: not suppressed; any other purpose refused).
- recipients/service.py suppress_recipient: the provider-event rule above.
- delivery/exclusion.py: stage 2 for marketing only; stage 3's first rule for every purpose; an unknown purpose refused.
- audience/service.py resolve_audience/_resolve: the floor by purpose (marketing by default for screens).
- rendering/frame.py send_purpose(frame); delivery/service.py: the purpose from the snapshot at plan, re-resolution, the manual execution route and the send gate; the test send shows the wording unlinked only for marketing profiles.
- brand_profiles: ProfileForbidden (403) without the right on create or when marking; a copy stays transactional only for a holder; make_default and marking the default refused (409); audit details carry the kind; may_mark_transactional on the single read.
- campaigns/router.py: variant.updated records brand_profile_kind. approvals send_fire: a warning naming the profile.
- Frontend: the profile form's Kind choice for holders (read-only with a note otherwise) and a notice on transactional profiles; the variant editor's "Sent without opt-in check" label and a transactional marker on the choice.
- Tests: test_transactional.py (17). Updated: test_brand_profile_api (403 instead of 422), test_permission_split (18 keys, 10 brand-scoped), test_variant_envelope (kind in the audit), frontend tests for the kind choice and the label.

Verification: backend 1795 passed, Ruff clean; frontend 266 passed, tsc and eslint clean; 14 backend mutations (all caught after adding the transactional test-send test) and 2 frontend. Live check 2026-10-11 on scratch data: a transactional profile created as Admin was complete without unsubscribe wording; making it the default was refused with its reason; its screen said what transactional means and offered the Kind choice; on a scratch variant the editor showed "Sent without opt-in check"; the audit recorded created with kind transactional and variant.updated with brand_profile_kind transactional. Scratch profile deleted through the API, campaign rows removed by id. The send path itself (purpose, floors, suppression, no unsubscribe) is covered by tests, not run live, to avoid sending to dev recipients.

Open, as ADR-195 says: task-134 (b) reputation streams and (c) modules; task-135's full suppression model, including lifting a provider suppression; what an unsubscribe on transactional mail writes. ADR-195 Notes suggest dated addenda to ADR-194 (points 1 and 10 now narrower) and ADR-163 (stage 3 has a rule); not written.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Slice 4 of brand profiles: a transactional profile's sends record purpose transactional, skip the marketing opt-in check at planning, re-resolution and send time, and carry no unsubscribe line; provider suppression (hard bounce, complaint) now leaves people out of every send, and a complaint after an unsubscribe is still recorded. Creating or marking one needs brand_profiles.transactional, copies stay transactional only for holders, it is never the default, and choosing one is labelled, audited and flagged to the approver. Decided with the user as ADR-195. Verified by 1795 backend and 266 frontend tests, 16 mutation checks, green CI (68c7f1f) and a live check on scratch data.
<!-- SECTION:FINAL_SUMMARY:END -->
