---
id: TASK-324
title: 'Double opt-in has no entry point: nothing in the platform receives a signup'
status: To Do
assignee: []
created_date: '2026-10-09 11:26'
labels:
  - needs-adr
  - backend
dependencies: []
type: decision
ordinal: 300190
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Decision: double opt-in has no entry point, because nothing in the platform receives a signup.** Split out of task-56 on 2026-10-09 by the user's decision in its interview (ADR-191, Decision point 1): unsubscribe was built first as the compliance gap, and double opt-in became its own task.

**What is already decided.** [[ADR-169 — Operational Flows Are Sequenced Variants, Not a Canvas]] point 1: double opt-in is a route, not a flow: a signed link, a confirmation page and a consent write. ADR-191's mechanics carry over: a per-message random token, a confirm page where only a POST writes, recipient-facing text kept in one place.

**What is not decided: where a signup comes from.** The CRM is the source of truth for who agreed ([[ADR-120 — CRM as Customer Source of Truth]]), and the platform has no signup form or public signup API. The options:
1. **A public signup endpoint** that a company's website form posts to (address, brand, channel and purpose). It creates or finds the recipient, records consent as pending, and sends the confirmation mail. Confirming writes opted_in with source "double_opt_in". The platform then holds consent the CRM did not assert, so it has to be relayed outward (task-135 / task-128).
2. **The CRM does double opt-in itself**, and the platform only receives the confirmed consent through the existing CRM sync. Then no route is needed here at all; ADR-169 point 1 still holds, with the route living in the CRM.
3. **Both**, depending on the company: the endpoint is optional.

**Also open:** which mail carries the confirmation (system mail, with its own transport, task-76, or the marketing provider); what a pending recipient may receive (nothing until confirmed); how long a confirmation link stays valid (unlike unsubscribe, a stale double opt-in link probably should expire); and abuse (a public endpoint that sends mail to any address is a spam relay unless it is rate-limited and sends only the confirmation).

Related: task-56 (unsubscribe, the other half), task-135 (suppression and the CRM relay), task-294 and task-119 (data-in).
<!-- SECTION:DESCRIPTION:END -->
