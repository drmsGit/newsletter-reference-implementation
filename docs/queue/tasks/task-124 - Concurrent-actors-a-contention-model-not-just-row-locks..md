---
id: TASK-124
title: 'Concurrent actors: a contention model, not just row locks.'
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-10-08 22:25'
labels:
  - needs-adr
  - backend
dependencies: []
type: decision
ordinal: 300800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
📋 **Concurrent actors: a contention model, not just row locks.** **Promoted and broadened 2026-08-02** (`/interview-review`, AI Q4) from the earlier Features item "systemic pattern for concurrency guards", which was scoped to database write races and is superseded by this. The user's framing: *"this should be a general architectural discussion — we will need a systemic concept for this."* **Three distinct sub-problems, and only the first is a locking question.** **(a) Human ↔ human.** Two managers editing the same campaign at the same time. Needs presence ("person A is working in this campaign"), an **unlock** path for when they leave the tab open and go home, and edit-conflict detection — none of which exists anywhere in the project today. **(b) Human ↔ AI — a precedence *policy*, not a mechanism.** The rule the user wants: **if a real person is working on something, AI stands back.** This cannot be derived from database semantics; it is a governance decision about who yields, and it belongs beside [[ADR-140 — AI Capability Layer]]'s "a human can always interfere" posture. **(c) A queue with a log.** Whether write actions route through a queue that records *what was attempted*, so that an action which never fired, or fired and failed, still leaves "when and why" behind. This connects directly to [[ADR-142 — Autonomous Workflows and the Automation Boundary]] (machine actions land in the same action history) and to [[ADR-153 — Audit and Accountability]] (which is the natural home for "attempted but did not run"). **Concrete instances found so far, all symptoms of the same missing concept:** the Overrides Q4 outcome-delta race (`record_outcome_delta`, read-modify-write with no lock); the Delivery Q5 double-send race; and now the **AI spend-cap TOCTOU** — `tokens_used()` reads the ledger, the gate compares, `_record()` writes, with no reservation in between, so two concurrent runs can both pass a gate that only one should (`service.py:193`). Note `send_send_instance` already uses `with_for_update()`, so the project has *one* ad-hoc answer and no convention — which is exactly the problem. **Why it is more urgent than it looked:** AI runs are the most likely thing to actually go concurrent first (Mode B fan-out, or the per-rendering generation option), and the AI instance is the one where losing the race costs *money* rather than consistency. Blast radius there is small and bounded — roughly one racing run's worst case, about a cent — so this is not an emergency, but it is the third instance and the pattern is what needs deciding, not the instance. **Sequencing note:** intersects the Security base (sessions, actors, audit) about to be built — presence and "who holds this" need an authenticated actor to attach to, so there may be real efficiency in designing this alongside rather than after. Source: [[Interview Prep - AI]] → AI Layer Q4; supersedes the earlier item sourced from [[Interview Prep - Delivery, Providers, Recipients]] → Delivery Q5 and [[Interview Prep - Decision, Overrides, Insight]] → Overrides Q4.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 447, section "Needs ADR", position 8 in that section (top = do next). The description is the original entry, verbatim.

2026-10-08 queue cleanup (backlog-sequencer run 3, verified by hand): parts of this are answered. (a) Human against human is decided by ADR-180 (A Lock Is Advisory for a Person and Binding for a Machine) and built with optimistic concurrency (task-110). (b) Human against machine is built as fences (task-254, backend/app/campaigns/fence.py). Still open: (c), the queue with a log, and the AI spend cap check-then-act race (backend/app/ai/service.py:89, tokens_used read before the gate).
<!-- SECTION:NOTES:END -->
