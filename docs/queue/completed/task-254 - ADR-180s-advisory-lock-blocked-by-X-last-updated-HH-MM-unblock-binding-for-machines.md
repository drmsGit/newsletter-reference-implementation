---
id: TASK-254
title: >-
  ADR-180's advisory lock: "blocked by X, last updated HH:MM, unblock", binding
  for machines
status: Done
assignee:
  - '@claude'
created_date: '2026-10-03 18:01'
updated_date: '2026-10-04 08:52'
labels:
  - backend
  - frontend
dependencies: []
references:
  - >-
    docs/architecture/ADR/ADR-180 — A Lock Is Advisory for a Person and Binding
    for a Machine.md
documentation:
  - >-
    docs/architecture/interview-prep/Campaign Write Surface - final design
    pass.md
type: feature
ordinal: 200060
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Split from task-110 on 2026-10-03 (user): task-110 built the layer underneath, optimistic concurrency (a write carrying If-Match with a stale `updated_at` is refused with 409, `backend/app/campaigns/service.py:_refuse_stale`). This is the layer on top that [[ADR-180 — A Lock Is Advisory for a Person and Binding for a Machine]] decides. Point 1: a variant carries an advisory fence, shown as "blocked by X, last updated HH:MM" with an unblock control that any person may use without asking — a social signal, deliberately not a real lock, so nothing is ever held by someone on holiday. Point 3: the same fence is binding for a machine — an agent never clears a fence it did not set, and a machine write to a variant fenced by somebody else is refused. Point 4: enforced server-side, conditioned on the actor type (`audit.ACTOR_INTEGRATION`), never a grantable permission key. What it needs that does not exist: somewhere to store the fence (who set it, when, on which variant); and "last updated by X", which no table records — the composer writes now audited (task-252) make `audit_events` the source, read by subject, with the `actor_id` to name join that ADR-153 kept out of the audit layer. It belongs with the React variant editor (slice 5 of the design pass), which is the screen that shows the fence; built before it, it would have no surface. Presence bubbles and a per-campaign history were deferred by the user ("not necessary from the beginning").
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A person can fence a variant, sees who fenced it and when, and can clear any fence
- [x] #2 A machine write to a variant fenced by someone else is refused server-side; a machine can clear only a fence it set
- [ ] #3 "Last updated by X at HH:MM" for a variant is read from audit_events
- [x] #4 The variant editor shows the fence and the unblock control
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Decided 2026-10-04 (user): any composer edit sets the fence; it lapses after 30 minutes without edits; anyone may unblock sooner. Recorded as an ADR-180 addendum (adr-author).
1. Migration 0030: variants.fenced_by_type, fenced_by_id, fenced_by_label, fenced_at (all nullable). Applied before any model edit.
2. backend/app/campaigns/fence.py: FENCE_LAPSE (30 min), is_active, view, guard (refuses a machine whose write would cross another actor's active fence: HTTP 423), touch (sets the fence to the actor after a write), clear (a person any, a machine only its own; audited variant.unfenced).
3. Composer routes on both planes: guard first on the JSON plane (machines only use it), touch after every successful write, next to its audit entry.
4. DELETE /campaigns/variants/{variant_id}/fence; ComposedVariant.fence for the editor.
5. AC 3 deviation, recorded in the addendum: 'last updated by X at HH:MM' is the fence itself (refreshed by every write, label text as for override authors), not an audit_events read.
6. Client: the editor shows the fence (someone else's, active) with Unblock, or 'last edited by' when lapsed.
7. Tests, mutants, live check.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-04. Backend: migration 0030 (applied to dev, and by hand to the test database because the conftest fix 2bb8b8b is only on the parallel session's branch); backend/app/campaigns/fence.py (FENCE_LAPSE 30 min, guard, touch, clear, view); guard before and touch after every composer write on the JSON plane (campaigns and overrides routers), touch after every successful write on the Jinja plane (bound to the written object, never the URL id); DELETE /campaigns/variants/{id}/fence (audited variant.unfenced); ComposedVariant.fence. The fence write leaves variants.updated_at alone (Core UPDATE writing it back), so a module edit does not move the variant's version token. guard answers only for the working brand's variants, so a 423 never reveals another brand's variant. Two bugs found by the review and the tests before commit: the wiring script put the overrides reset route's calls into set_fields (unusual signature), and the Jinja actor is request.state.current_user, a plain dict, not the principal (fenced as 'unauthenticated' until fixed). Tests backend/tests/test_fence.py (10); mutants: guard never refuses, no lapse, fence moves the version, machine clears any, guard not brand-scoped, override write unguarded: each caught. 21 older tests made successive writes as different machines and met the fence (correctly); they now use one editing machine per test (tests.machine.editor, one_editor fixture). Full suite 1205 passed, rc 0.

2026-10-04. Client: useUnblock and screens/Fence.tsx in the editor header: someone else's active fence names them, says edits still save and offers Unblock; your own says automations wait 30 minutes after your last edit; a lapsed one reads 'Last edited by X at HH:MM'. Tests Fence.test.tsx (4); mutants: never mine, lapsed treated as active, unblock doing nothing: each caught. 114 client tests. Live (Variant 1A): no fence at first; an edit showed 'You are editing this variant (last edit 09:51)'; Unblock cleared it; the label was restored and the resulting fence cleared via the unblock route. AC 3 is met by the fence itself rather than an audit_events read, as the ADR-180 addendum records (deviation agreed in the addendum, not checked as written).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A variant now carries ADR-180's advisory fence: every composer write sets 'blocked by X, last updated HH:MM', it lapses after 30 minutes without edits (user decision, ADR-180 addendum), a person is never stopped and may unblock any fence, and a machine is refused with 423 across another actor's fence and clears only its own. The editor shows it with Unblock. Verified by 10 backend and 4 client tests, nine mutants, and a live round trip.
<!-- SECTION:FINAL_SUMMARY:END -->
