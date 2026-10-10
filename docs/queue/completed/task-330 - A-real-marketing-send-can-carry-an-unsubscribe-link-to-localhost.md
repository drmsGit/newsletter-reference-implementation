---
id: TASK-330
title: A real marketing send can carry an unsubscribe link to localhost
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 18:12'
updated_date: '2026-10-10 19:11'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug]** The unsubscribe link written into every marketing mail is built from PUBLIC_BASE_URL. When that variable is unset, the code silently falls back to the development address: backend/app/subscriptions/service.py:20 sets PUBLIC_BASE_URL_DEFAULT to http://localhost:8000, and :25-26 (public_base_url) applies it without any check of scheme or presence. The URL is built at send time (:48) and the Resend adapter writes it into the List-Unsubscribe headers unchecked (backend/app/delivery/providers/resend.py:61-66).

Why it matters: the link is fixed into each mail when it is sent and can never be corrected afterwards. One deployment that forgets the setting sends every mail of that run with a dead unsubscribe link, both the visible footer and the one-click header. That is exactly the failure ADR-191 chose stored per-message tokens to avoid ("a link in a mail sent last year must still work"). ADR-191's own Negative section already says the base URL "must be configured"; nothing enforces it. Launch gate 10 (docs/business/LAUNCH-GATES.md) was closed on a development live check only.

Decided in the 2026-10-09 interview review (Audience Q6): the real provider refuses a marketing send when PUBLIC_BASE_URL is unset or not https. The mock provider and development stay unaffected, so local work and tests keep the localhost default. Also add the setting to task-55's deployment checklist.

Source: [[Interview Prep - Since 2026-09-18]] → Audience history, delivery safety and recipient unsubscribe, Q6.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A marketing send through a real provider is refused, with a clear reason, when PUBLIC_BASE_URL is unset or not https
- [x] #2 Sends through the mock provider keep working with the localhost default
- [x] #3 task-55 names PUBLIC_BASE_URL as a required deployment setting
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Capability on the adapter (ADR-101, capabilities are explicit): DeliveryProvider.reaches_real_inboxes = True by default; MockProvider sets False. A future adapter is treated as real unless it says otherwise.
2. subscriptions/service.py: public_base_url_problem() returns why the configured PUBLIC_BASE_URL cannot go into a real mail (unset, not https, no host), or None.
3. delivery/service.py send_send_instance: in the read-only pre-send block, after the provider is built and BEFORE the status transition, refuse with ValueError when the provider reaches real inboxes, the channel is email, the send has marketing executions, and the base URL has a problem. The send keeps its status and can be retried once the setting is fixed.
4. Tests first (backend/tests/test_unsubscribe_base_url.py): a stub real provider refused when unset or http, nobody mailed, status unchanged; sent with https and the link uses it; the mock still sends with the localhost default.
5. Mutation-check, full suite, Ruff, commit, CI. task-55 already names the setting (note 2026-10-09).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10, done (commit ef81dc4). Governed by ADR-191 (the base URL must be configured; the 2026-10-09 addendum names this task) and ADR-101 (the capability is explicit).

What changed:
- A new adapter capability, DeliveryProvider.reaches_real_inboxes, is True by default, so a future adapter counts as real until it says otherwise. MockProvider sets it False.
- subscriptions/service.py has public_base_url_problem(). It returns a reason when PUBLIC_BASE_URL is unset, not https, or has no host; otherwise None.
- delivery/service.py send_send_instance refuses with a ValueError in the read-only pre-send block, after the provider is built and BEFORE the status claim. That happens when four things hold together:
  1. the provider reaches real inboxes;
  2. the channel is email;
  3. the send has marketing executions (the only ones footer_for gives a link);
  4. the address has a problem.

Because the refusal comes before the claim, the send keeps its status and can be retried once the setting is fixed. Scheduled and approval-routed sends go through the same function.

Tests: backend/tests/test_unsubscribe_base_url.py, 7 tests. All seven failed first.
- Refused when the address is unset, empty, http, or a host-less https; nobody is mailed and the status stays draft.
- Sent with https, and the link uses it.
- The mock keeps the localhost default.
- A send with no marketing link is not refused.

Mutations, each caught:
- mock claims real: 1 failed;
- no refusal: 4 failed;
- link check always on: 1 failed;
- http accepted: 1 failed.

Suite: 1625 passed. Ruff clean. CI green on ef81dc4.

AC 3: task-55 already names PUBLIC_BASE_URL as a required https setting on a company-owned domain (notes of 2026-10-09).

Two things went wrong while building, both resolved:
1. An early version of the mock test planned a 'resend' send unfaked and made two real Resend calls. That led to task-346 (the guard), built first.
2. A mutation-check backup collided (two files named service.py) and briefly overwrote app/delivery/service.py in the working tree. It was restored from git and the change reapplied, verified by the diff (16 lines) before anything was committed.

No live browser check: checking it needs a Resend-provider send, and whether the dev .env sets PUBLIC_BASE_URL is unknown (never read). A wrong guess could send real mail.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A real marketing send can no longer carry an unsubscribe link to localhost. A provider that reaches real inboxes (new adapter capability; the mock opts out) refuses a marketing email send whose PUBLIC_BASE_URL is unset or not https, before the send is claimed, so it stays retryable once the setting is fixed. Verified by test_unsubscribe_base_url.py (7 tests, failed first, four mutations caught), the full suite (1625), Ruff and green CI on ef81dc4; no live check, because it would need a Resend send.
<!-- SECTION:FINAL_SUMMARY:END -->
