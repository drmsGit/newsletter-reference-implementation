---
id: TASK-201
title: A required-field check before a send fires
status: Done
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-09-28 16:28'
labels:
  - backend
dependencies: []
priority: parked
type: bug
ordinal: 104900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug]** **A required-field check before a send fires** (Q3b). Nothing checks today — `resolve_module_variables` defaults a missing field to `""` and `ModuleVariable.required` is never enforced at render, so an empty push notification ships to a real device. Belongs in Cluster 5's pre-flight.

Source: [[Manager Workflow - design interview]] → What Cluster 2 produced, requirement 1 (Q2.3b). Cluster 5 (Q5.1) placed it: *the system blocks what is broken, and reports what is merely questionable* — an empty required field is broken.

**Verified against the code 2026-09-27:** `resolve_module_variables` (`backend/app/rendering/service.py:257`) falls back to `content.get(var.name, "")` at `:305` and never reads `var.required`; the static path does the same at `:362-369`. `ModuleVariable.required` is declared at `backend/app/modules/registry.py:43` and read only for display (`backend/app/modules/router.py:32`, `backend/app/frontend/router.py:793`).

Related: [[ADR-174 — Channel Readiness Is Asserted, Not Computed]] point 3, [[ADR-177 — A Field Is Defined Once, Required Per Module]]. task-104 is the pre-send checks bundle.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

Done 2026-09-28, scoped to the deterministic half. 666 tests passing, up from 660.

**The check is two checks and only one can block.** The send loop renders per recipient (`delivery/service.py:783`, `mode="send"`), so a slot-bound module's content differs per person — refusing a thousand-recipient send because one person's pick lacks a field would be absurd. That half is a skip and belongs to task-228. ADR-174 point 3 describes the deterministic half: static and content-bound modules, whose answer is the same for everyone.

**`missing_required_fields(db, variant_id)`** in `app/rendering/service.py`. It asks the render path rather than reimplementing it — `resolve_module_variables` for cms modules, and a newly extracted `static_module_variables` for the rest. That extraction is the point, not a tidy-up: a check that rebuilt the module_data/content/override merge itself would drift from what actually ships, which is the failure `CONTENT_FIELD_GROUPS` documents about its own duplicate.

**An unbound module is not a finding, and that falls out** rather than being special-cased — it resolves to no content, so it declares no variables to test. Same answer interview Q1.4 reached independently.

**`UnpublishedContentError` is handed to its own gate.** `create_snapshot_for_variant` already refuses to freeze a variant whose content was never published, so reporting it here would name the wrong cause.

**Enforced in two places, per `base.py`'s own rule that a disabled button is a courtesy and not a control**: `send_fire.describe()` sets `blocked_reason` so the reviewer — the person who can fix it — sees which field; `send_send_instance` refuses.

**Placed before the status transition, and the first attempt was not.** It originally sat after the snapshot lookup, which is after `status = "sending"` — so a refused send was stranded in "sending", unsendable and unretryable. That is the defect this queue already records about that transition being committed ahead of fallible preflight steps, and a new check must not add to it. The test caught it.

**Blast radius, measured not guessed:** four of the dev database's fourteen variants would now be refused — a `cta` with no label pointing nowhere, a `hero` with no headline. The check is right and that data is broken.

**Three tests elsewhere had to stop depending on arbitrary data.** The consent fixture and the draft-send test both picked "the newest" row, which is now often incomplete. Both now build a complete variant when none exists rather than skipping — an earlier version of the fix skipped, which silently disabled five real consent tests, a worse outcome than the failure it avoided.

Six new tests, each mutation-verified: ignoring `required`, treating whitespace as a value, and removing the send-time enforcement each fail the suite.
<!-- SECTION:NOTES:END -->
