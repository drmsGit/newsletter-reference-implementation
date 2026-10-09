---
id: TASK-330
title: A real marketing send can carry an unsubscribe link to localhost
status: To Do
assignee: []
created_date: '2026-10-09 18:12'
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
- [ ] #1 A marketing send through a real provider is refused, with a clear reason, when PUBLIC_BASE_URL is unset or not https
- [ ] #2 Sends through the mock provider keep working with the localhost default
- [ ] #3 task-55 names PUBLIC_BASE_URL as a required deployment setting
<!-- AC:END -->
