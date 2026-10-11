---
id: TASK-67
title: >-
  Provider choice + real send on the campaign send flow (prepare-send →
  delivery).
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-10-11 20:44'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 200100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** Provider choice + real send on the **campaign send** flow (prepare-send → delivery). Today `send_instance_create` hardcodes `provider="mock"`, so the campaign "Trigger send" never sends real email — only the standalone **Send test** page (`/ui/send-test`, done) does. Add a provider selector (mock/resend) to the send-instance creation, and — before enabling a real campaign send — a **guardrail so it can't blast all recipients by accident** (e.g. a max-recipients cap or an explicit confirm; the demo has 40 recipients and the Resend free tier is 3,000/mo). Also the natural place to finally test the **multi-recipient real send** (3 recipients is enough to prove it). A note banner already points users to Send test from the delivery detail page. Source: user, 2026-07-26 (post-Resend-outbound). **Second reason to build this (2026-07-31, AI-layer interview Cluster 4 / Q19):** this guardrail is also a **Mode-C (AI-assisted development) containment measure**, not just accident prevention. DEV/PROD environment separation does **not** contain outbound email — as long as a DEV environment holds a working send-provider key (which development and testing require), an AI-made change in DEV can still deliver real mail to real people. The mock-provider default, the recipient cap and this guardrail are therefore the *actual* blast-radius limit for Mode C, and should be documented as safety properties rather than as dev conveniences.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 210, section "Features", position 20 in that section (top = do next). The description is the original entry, verbatim.

2026-10-08 queue cleanup (backlog-sequencer run 3, verified by hand, kept by the user's decision): the Jinja half of this entry is built. The hardcoded mock is gone, and the send plan takes a provider, defaulting to mock (backend/app/delivery/models.py:67, SendPlanRequest.provider). The campaign screen offers the choice (backend/app/templates/campaign_detail.html:624). The recipient cap the entry asked for exists: backend/app/settings/service.py:126 get_max_send_recipients, set through backend/app/settings/router.py:151-154, which is audited (task-245).

What remains is a send screen in the React client. Only frontend/src/api/schema.d.ts knows the send-plan route, and no other task covers that screen. The Jinja UI is frozen, so this entry now stands for that screen. Its second reason still holds: the mock default and the cap are the blast-radius limit for AI-assisted development (called Mode C in this dated entry, now Development per the ADR-140 addendum of 2026-10-08), so the React screen must keep both.

2026-10-11, the user set the November 2026 presentations as the focus (docs/business/PRESENTATIONS-2026-11.md). Moved to the head. Widened to the whole flow the demo shows in the React client: freeze a variant for approval (POST /snapshots/variants/{id}, which React never calls), approve, plan the send to an audience, send a test, fire the real send through Resend, and see the signal come back (clicks reaching the campaign's results section, task-58). The webhook needs a public URL for that last step (docs/how-to-webhooks-engagement.md).
<!-- SECTION:NOTES:END -->
