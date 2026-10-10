---
id: TASK-347
title: Run the reference deployment
status: To Do
assignee: []
created_date: '2026-10-10 20:54'
labels:
  - docs
  - backend
dependencies: []
priority: parked
type: feature
ordinal: 209400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature, parked]** docs/reference-deployment.md describes one honest reference deployment: one box, a reverse proxy in front, the app, PostgreSQL, every environment setting, the API-gateway and egress-proxy seams, and what the adopter is responsible for. It is marked 'designed, not yet run'. task-55 asked for a deployment that is actually run, because only a setup we operate survives follow-up questions. But installation and deployment are deferred by decision at the proof-of-concept stage, so on 2026-10-10 the user chose to write it now and park the running.

When the deployment phase starts, this task:
- runs that setup;
- fills the page's 'Not covered yet' gaps: a container image or install for the application, health checks, logging, a tested backup and restore;
- decides whether the egress proxy can inject the provider credential. Today the Resend adapter refuses to send with an empty RESEND_API_KEY.
- flips the page's status line, after which the positioning may rest on it.

Parked: it must be prioritised before anything else happens to it.
<!-- SECTION:DESCRIPTION:END -->
