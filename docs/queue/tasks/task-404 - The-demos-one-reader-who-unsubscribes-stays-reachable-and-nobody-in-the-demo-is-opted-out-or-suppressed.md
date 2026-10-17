---
id: TASK-404
title: >-
  The demo's one reader who unsubscribes stays reachable, and nobody in the demo
  is opted out or suppressed
status: To Do
assignee: []
created_date: '2026-10-17 17:34'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Surfaced 2026-10-17 by the trailer pre-production checks (a side session's results file, docs/design/trailer/PREPRODUCTION-CHECKS.md section 1.3, with section 9 item 1), run twice against a demo reset on a scratch database; the user asked for the defects to be queued, not fixed there. Re-checked on main (cf3fab0) by reading the seed. Both flaws are in the demo seed, not in the product's consent logic.

**1. The unsubscribe loses to the opt-in.** `create_readers` writes each reader's email opt-in as a `ConsentEventDB` with no `created_at` (backend/app/demo/people.py:83-90), so it carries the clock of the reset. The editions are sent through the real path and dated back (Familienherbst on 2026-10-08, backend/app/demo/editions.py:47), and the one reader who leaves is written through `record_consent` and then dated `opened_at + 2 minutes`, a past date (editions.py:239-246). Consent is the latest event by `created_at`, then id (backend/app/recipients/consent.py:124-150, and the SQL form at 402-432), so the later opt-in wins and the reader is reachable again. Observed on scratch: the reader who unsubscribed (a different one at each reset, #422 then #533) was in the next send's audience, and the Reparaturwoche send went to them. The demo shows an unsubscribe with no effect, the opposite of what the consent floor promises ([[ADR-163 — Per-Channel Consent and Addressability]], [[ADR-195 — A Transactional Send Skips the Opt-In Check, Never Provider Suppression]], and point 6 of [[ADR-196 — Reporting Is the Campaign's Results Section; Analysis Belongs in the Adopter's Tools]], which is why the seed writes the event through a delivery). It passes its test because backend/tests/test_demo_reset.py:169 only counts that one row with `source="unsubscribe"` exists, not that the reader is unreachable. Any future reset has the same order, because every edition date is fixed in the past and the opt-ins are always written now.

**2. Nobody is opted out or suppressed, so the exclusion counts are zero.** The audience is resolved from consenting readers only, with no consent event meaning no grant (backend/app/audience/service.py:660-700), so the only ones who can show up as left out are readers who have a consent record that is not an opt-in. The seed has none: every reader's latest email event is an opt-in or, for every 25th reader, absent (people.py:83), and those never enter an audience. The one bounce in a hundred is written as a plain engagement event (editions.py:207-212), not through the provider path that suppresses (backend/app/providers/service.py:233 calling `suppress_recipient`, backend/app/recipients/service.py:39), so there is no provider-sourced opt-out either. Observed: every sent campaign records Excluded 0; each audience group's reachability line on the Send screen reads "N of N in this group can be reached on email now"; planning a send for Familie & Kinder gave 123 recipients and fired as 123 sent, 0 excluded. So trailer scene S09 ("who was left out for consent and who for suppression") cannot be drawn from the demo.

**Options for the fix, not decided here.** For 1: date the opt-ins back before the first edition (consistent with how the editions are dated back), or write the unsubscribe at reset time; either leaves the unsubscriber unreachable. For 2: add readers who are members of an audience group but opted out after joining it, and some suppressed the way the webhook does it (the same `suppress_recipient`), so a group's reachability line is below its member count and a send reports a non-zero Excluded with its stage. They must fit the send cap, which the reset reads and never raises, and the segments are tuned to it (people.py MAIN_INTERESTS, editions.py:174-176).

**What a fix disturbs.** The demo's figures are quoted by the trailer brief and storyboard (docs/design/trailer/), and the reset prints a summary line with the unsubscribe (backend/app/demo/reset.py:268). Re-run the checks after the change and correct what those two quote; do not edit them from here.

Not a duplicate: task-71 built the demo and its notes ask for "an unsubscribe" among the believable results; no task in the queue or docs/queue/completed names the order of the two rows.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 After a demo reset the reader who unsubscribed is not reachable: out of the resolved audience of the next send, read through the consent logic and not by counting rows
- [ ] #2 After a reset at least one member of an audience group is opted out and one is suppressed the way the provider webhook does it, so the group reachability line is below its member count and a send reports a non-zero Excluded with its stage
- [ ] #3 No demo segment exceeds the send cap, which stays as it is
- [ ] #4 test_demo_reset asserts all of the above and fails when the old order of the two rows is restored
- [ ] #5 The figures the trailer brief and storyboard quote from the demo are re-read after the change, and the differences are reported to the user
<!-- AC:END -->
