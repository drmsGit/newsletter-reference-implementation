---
id: TASK-292
title: 'The React client has a read-only recipient page: why did this person get this'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-06 18:58'
updated_date: '2026-10-06 19:02'
labels:
  - frontend
dependencies: []
type: feature
ordinal: 200386
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The React client has no recipient page**, so the backend answers to "why did Anna get this" (Manager Workflow interview Q4.5) reach no manager. Filed 2026-10-06 at the user's request, after task-214.

**What the interview decided the page is** ([[Manager Workflow - design interview]] Q4.5, resolution 2026-09-24): look one person up — "why did Anna get this" — **and nothing else. Read-only, with a planned end of life**: it exists because the reasoning lives in this platform, not the CRM ([[ADR-120 — CRM as Customer Source of Truth]] owns the person), and it goes away when a CRM can receive that reasoning. Editing is refused, which keeps [[ADR-126 — Maintain Local Recipient Projection]] honest; the emergency unsubscribe is parked with the GDPR package ([[ADR-154 — Erasure and Retention]]).

**What already exists on the server, to show:**
- the lookup: `GET /recipients/` (paged, search by identifier or address; the client's `useRecipientSearch` in `frontend/src/api/resources.ts` already calls it for the preview's recipient picker);
- `GET /recipients/{id}/activity` (task-50; `backend/app/recipients/service.py`, `recipient_activity`): this brand's last decisions (content, version, score, reason) and deliveries (status, channel, exclusion reason, provider, engagement trace), the affinity profile, this brand's consent grid, and the consent history across brands, labelled;
- `GET /recipients/{id}/audience-groups?channel=` (task-214): the groups that touch the person, in or out, with the reason — per channel, as of now.

**To decide in a short final-design pass, not here:** where it sits in the navigation (a "Recipients" entry with a `g` shortcut, like the others); how the channel is chosen for the groups (the audience screen's pattern: the switched-on channels); the order of the sections; links out to deliveries, campaigns and audience groups. Layout and keyboard polish stay with their own sessions.

**Not in scope:** any write — no edit, no consent change, no unsubscribe.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A manager can look a person up and see their consent, deliveries, decisions and audience groups (per channel, with reasons) for the working brand
- [x] #2 The page writes nothing
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Final-design pass (small, decided in the task): 'Recipients' in the navigation after Audiences, g then r; /recipients (search by identifier or address, paged) and /recipients/:id; sections Consent (this brand), Audience groups (channel chosen as on the audience screen, reasons in words, as of now), Deliveries, Decisions, Interests, Consent history, each linked out; a read-only line saying why.
2. Tests (Recipients.test.tsx): the list searches the server and opens a person; the page says read-only and offers no write; consent with a never-asked cell; groups with reasons, linked, per channel; deliveries, decisions, interests and history linked.
3. resources.ts: useRecipients, useRecipientActivity, useRecipientGroups. Screens Recipients.tsx and RecipientDetail.tsx; route and nav entry.
4. Mutation-check, suite, live read on dev data.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built as planned; no backend change (it reads task-50's activity and task-214's groups). The tests could not run before the screens existed (the imports fail), so the mutation check is the evidence they discriminate: 11 mutants, all caught. Client 196, tsc, contract. Live (read-only, signed in with the dev account): demo-020 shows consent (email opted_in from the seed, push 'Not asked'), 'All demo recipients · In · Matched rule everyone' on email and 'Out · … · Not agreed to push' on push, one delivery, one decision, seven interests, two history events; 'Recipients' sits in the navigation.
Layout and keyboard are left for their sessions. The audience write surface the user raised during this task is filed as task-293 (design first).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The React client has a read-only recipient page: Recipients in the navigation (g then r), a searchable list, and per person their consent for this brand, which audience groups they are in on a chosen channel and why, what was sent, the decisions behind it, their interests and their consent history, each linked to the delivery, content or audience. Nothing on it writes. Verified by 5 tests, 11 caught mutants, 196 client tests and a live read of a dev recipient on email and push.
<!-- SECTION:FINAL_SUMMARY:END -->
