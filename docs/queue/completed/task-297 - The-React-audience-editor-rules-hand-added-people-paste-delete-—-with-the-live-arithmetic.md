---
id: TASK-297
title: >-
  The React audience editor: rules, hand-added people, paste, delete — with the
  live arithmetic
status: Done
assignee:
  - '@claude'
created_date: '2026-10-06 19:59'
updated_date: '2026-10-06 21:06'
labels:
  - frontend
dependencies:
  - TASK-295
type: feature
ordinal: 200390
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-293 interview (2026-10-06, with the user); recorded in [[Audience Write Surface - final design pass]] decisions 1, 5, 6, 8, 9, 10 and [[ADR-188 — Audience Rules Are Flat, and May Read Engagement History]]. Third of four build tasks; depends on build 1.

**Build** in `frontend/src/screens/Audiences.tsx` and `AudienceDetail.tsx` (the group's page becomes the editor, no separate edit mode):
- "New audience" on the list (name, description), opening the empty page;
- name and description saving on leaving the field;
- the rules in two sections, **"Who's in"** and **"Leave out"**, with the explanatory line under "Leave out" and the "did not" hint (decision 9); each rule edited in place and saved with **"Save rule"**; language and status chosen from existing values (several allowed), category from `CategoryChoice` with the score (1.0 filled in); "Add a rule";
- the arithmetic (task-213) beside the rules on the chosen channel (first switched-on by default), refreshed after each saved change;
- **hand-added people**: the list with reason, who, when and an exclusion mark; add one with the recipient picker (extract `RecipientChoice` from `frontend/src/screens/Preview.tsx` into a component) and an optional reason; remove one;
- **"Paste people"**: text box, the report, then "Add N";
- **delete** with confirmation, and the 409 shown in place naming the sends;
- **"Suggest from campaign"**, the suggested badge and "Recalculate from campaign" (manual).
Every write states the group's version; "Load their version" on a 409. Layout and keyboard polish stay with their sessions.

Tests per screen convention with a stub server, mutation-checked; a live check on a scratch audience only.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A manager can create an audience and edit its rules and hand-added people, seeing the arithmetic update
- [x] #2 Paste people, delete (with the used-by refusal) and suggest/recalculate work from the page
- [x] #3 Writes state the version; a stale one offers Load their version
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-10-06 (commits b0adc31, 633fbd4, be16e6e).

Server gap closed first: the members list (GET /api/audience-groups/{id}/members) now names each person (external_id) and, when asked with a channel, lists the exclusion rules that leave them out on it (left_out_by), checked for that page's people only through find_by_criteria(only_ids=...) - backend/app/audience/service.py page_members. Without a channel there is no verdict: the consent floor matches nobody then, so the channel guard only saves the queries (equivalent mutant, recorded rather than tested).

Client:
- frontend/src/api/resources.ts: one useAudienceWrite for every write - the group's updated_at read from the cache when the write is sent, one queue per group (scope audience-ID), success awaits the group's re-read so the next write states the new version; rules, members and arithmetic are re-read alongside without holding the queue. Delete drops the cache instead (a deleted group answers 404).
- frontend/src/screens/AudienceDetail.tsx is the editor: name and description autosave (AutosaveField), the channel choice moved up so the hand-added marks and the arithmetic share it, Recalculate from campaign only with a source campaign, Delete with a confirmation; a 409 starting with the server's GroupInUse words is shown as the answer, any other 409 offers Load their version.
- AudienceRules.tsx: Who's in / Leave out, the explanatory line and the did-not hint; each rule a form with Save rule (off until something changed), language and status as checkbox groups from /criteria-values (a value already in the rule stays offered), CategoryChoice with the minimum score filled in at 1.0, the rule name. Criteria the form does not edit (engagement) are kept on save, so task-298 data survives this editor.
- AudiencePeople.tsx: the hand-added table (person linked to the recipient page, reason, who, when, Left out by ... on CHANNEL, Remove), add one with the extracted RecipientPicker (frontend/src/components/RecipientPicker.tsx, also used by the preview) and a reason, Paste people (Check, the report, Add N).
- AudienceCreate.tsx: New audience (n) and Suggest from campaign on the list.

Tests: frontend/src/screens/AudienceEditor.test.tsx, 17, against a stub server that checks If-Match and moves the version on every accepted write; backend test_audience_writes.py gained the members-list test. Mutation check: 20 mutants on the client, all killed after two tests were strengthened - two quick saves in a row (the queue and the awaited re-read had survived when the tests waited between writes) and renaming a rule; the 1.0 default in the draft was redundant (choosing a category fills it) and was simplified away.

Live check, scratch audiences only, both deleted afterwards: created zz-scratch task-297, an include rule (de, 21 match), a hand-add with reason, a leave-out rule marking the hand-add and the arithmetic showing -21 (1 of them added by hand), a stale write (version moved from outside) refused with Load their version which loaded the other text, paste of 4 entries (2 added, 1 already in, 1 not found), two writes back to back both accepted, remove person, remove rule, delete; then Suggest from campaign (Demo Campaign 5), Recalculate, delete. Every write appears in the audit log.

Found in the live check and fixed:
- The recipient search returned everyone once anybody matched: the identifier EXISTS in backend/app/recipients/search.py read recipients again without tying it to the outer row, which the recipients list (task-292) and both pickers query. Aliased; test in tests/test_recipient_search.py, mutation-checked.
- Recalculate applies the difference and keeps tuned suggested rules; the hint said replaces, and a no-change recalculation showed nothing. Reworded, with a done message.

Suites: backend 1437 passed, client 213 passed, build and contract clean. Layout and keyboard handling left to their sessions; no keyboard defect noticed beyond the known ones.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The audience page is now its editor: create, rules under Who's in and Leave out with Save rule, hand-added people with reason and exclusion marks, add one, paste, remove, delete with the used-by refusal, suggest and recalculate; every write states the group's version through one queue, a stale one offers Load their version. The members list gained identifiers and exclusion marks per channel. Verified by 17 stub-server tests (20 mutants killed), the backend members test, both full suites, and a live check on scratch audiences that also found and fixed a recipient search returning everyone.
<!-- SECTION:FINAL_SUMMARY:END -->
