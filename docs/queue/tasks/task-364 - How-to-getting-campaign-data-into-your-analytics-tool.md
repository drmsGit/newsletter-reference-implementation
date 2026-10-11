---
id: TASK-364
title: 'How-to: getting campaign data into your analytics tool'
status: To Do
assignee: []
created_date: '2026-10-11 16:33'
labels:
  - docs
dependencies: []
type: docs
ordinal: 210200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Docs]** Decided by the user on 2026-10-11 in task-58's design pass, recorded in [[ADR-196 — Reporting Is the Campaign's Results Section; Analysis Belongs in the Adopter's Tools]] point 8: the application builds no data export. Getting data into an analytics tool is a full IT task for the adopter, with no configuration screen in the app; the analytics system decides whether it wants CSV, endpoints, or a replica with ETL. This task writes that as a how-to chapter next to docs/how-to-webhooks-engagement.md and docs/how-to-swap-send-provider.md. Its message, in the user's words: if you want analysis in detail, there are better tools for that.

**What the chapter would cover (options, not a build).**
- What the app itself shows: the campaign's results section (ADR-196) and nothing more.
- Where the data lives: delivery_executions, engagement_events (opens, clicks, delivered, bounces, complaints, keyed by delivery), consent_events (with the delivery since 2026-10-11), signal_contributions.
- The ways out: reading the API with a machine credential (ADR-166; note that reporting reads sit behind view, which integrations do not hold, backend/app/auth/policy.py MACHINE_READS), a read replica or database dump with ETL, or taking the provider's webhooks into the warehouse directly.
- ADR-154 point 4a: any per-person export must carry the internal identifier, so an erasure can reach it.
- Retention: nothing is pruned today, but ADR-132 expects a bounded window (task-85, task-136), so history belongs in the warehouse.

**Not in scope.** Promoting the platform with a CRM and n8n setup on the user's website is separate (the user, 2026-10-11). The per-person export of signal contributions stays task-85.

**Related.** task-58 (done), task-85, task-136, ADR-124, ADR-132, ADR-154, ADR-166, ADR-196.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A how-to chapter in docs/ explains the options for getting data into an analytics tool, without building any export
- [ ] #2 It names where the data lives, the erasure obligation of ADR-154 point 4a, and the retention outlook
<!-- AC:END -->
