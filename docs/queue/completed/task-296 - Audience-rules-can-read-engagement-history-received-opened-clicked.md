---
id: TASK-296
title: 'Audience rules can read engagement history: received, opened, clicked'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-06 19:59'
updated_date: '2026-10-06 20:44'
labels:
  - backend
dependencies:
  - TASK-295
type: feature
ordinal: 200389
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-293 interview (2026-10-06, with the user); recorded in [[ADR-188 — Audience Rules Are Flat, and May Read Engagement History]] points 4 and 5 and [[Audience Write Surface - final design pass]] decision 7. Closes task-215 (audience criteria cannot express delivery history). Second of four build tasks.

**Build** in `backend/app/audience/service.py` (`find_by_criteria` and the schema from build 1): an engagement field — **what** (received, opened, clicked; "opened" included by the user's decision, the company's call), **which mailing** (a specific send instance, any send of a campaign, any send on the channel), **when** (absolute from/to, or relative: within the last N days / more than N days ago) — reading `DeliveryExecutionDB` (received = a sent execution, by `sent_at`) and `EngagementEventDB` (opened/clicked by `event_type`, `occurred_at`), scoped to the brand's sends. It combines with the other fields in a rule; "did not" is an exclusion rule (point 5), so no negated field. Because it lives in `find_by_criteria`, the arithmetic (task-213), the per-person lookup (task-214) and sends all follow.

**Measure** resolution with engagement rules on the dev data and add indexes where a plan shows a scan (these are the fastest-growing tables; task-106 is the benchmark task).

Tests: each what/which/when, absolute and relative windows, brand isolation, exclusion for "did not", the arithmetic and memberships following; mutation-checked.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A rule can match received, opened or clicked, for a send, a campaign or any send, in an absolute or relative window
- [x] #2 'Did not' works as an exclusion rule; the arithmetic and per-person lookup follow
- [x] #3 Resolution with engagement rules is measured on dev data, indexed where needed
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first (tests/test_audience_engagement.py): received = sent and not bounced (excluded/failed never); opened, clicked; one send, a campaign, any send on the channel, only this brand's; relative and absolute time (whole days); combined with other fields; "did not" as a leave-out rule with the arithmetic and memberships following; invalid engagement refused by field.
2. service.py: CRITERIA_FIELDS gains engagement; _normalise_engagement; _engaged builds the subquery (Ex + Send, bounce anti-join or event join, scope, time); find_by_criteria(engagement=...) and _recipients_for_criteria pass it — so resolution, the arithmetic, memberships and sends follow.
3. Measure at volume on the test database; index where a plan shows a scan.
4. Mutation-check, suite, contract, live check on a scratch audience.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-06, the user: 'received' means handed to the provider and not bounced — excluded and failed deliveries never count, a bounce removes the person, no confirmed 'delivered' required (not every provider reports it).

Choices within the design: one engagement field per rule (several are several rules, ADR-188 point 1); a send or a campaign, never both, neither = any send on the channel being resolved; "to" covers its whole day; relative windows are measured from now (as of now); a send or campaign of another brand matches nobody (the brand filter, not a refusal). A campaign scope reads every channel of the campaign; a specific send is one channel by construction.
Measured 2026-10-06 on the TEST database, rolled back: 100,000 deliveries over 200 sends, 50,000 events. A rule about one send: 4.76 ms / 2,310 buffers -> 1.62 ms / 384 with an index on delivery_executions.send_instance_id (migration 0036, declared on the model). "Received any send in the last 30 days" reads about a third of the rows and scans either way (~18 ms); no index for it. Dev data (40 deliveries, 141 clicks) is too small to measure.
Validation: 19 tests, failing first (the rule check refused 'engagement'); 17 mutants, all caught after two fixture fixes — consent was hiding the brand and channel checks (fred now agreed with this brand too; hank has only a push delivery on a push send). Backend 1435; contract unchanged (criteria stay an open dict on the wire). Live on a scratch audience (deleted after): received any email in 90 days = 8; leaving out who clicked = 2 (6 removed); a contradictory rule refused 422 with its reason.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Audience rules can now read engagement (ADR-188): received (handed to the provider, not bounced), opened or clicked; for one send, any send of a campaign, or any send on the channel; within a fixed or relative period. It combines with the other fields, "did not" is a leave-out rule, and resolution, the arithmetic and the per-person lookup follow. One index (delivery_executions.send_instance_id, migration 0036) makes one-send rules six times cheaper on reads at 100,000 deliveries. Verified by 19 tests, 17 caught mutants, the suite and a live check on a scratch audience.
<!-- SECTION:FINAL_SUMMARY:END -->
