---
id: TASK-74
title: >-
  Couple extended thinking to the output ceiling — enforce the rule instead of
  asserting it.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 202700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** **Couple extended thinking to the output ceiling — enforce the rule instead of asserting it.** Surfaced 2026-08-02 (`/interview-review`, AI Q7). Extended thinking is off by default for a cost-correctness reason: `max_tokens` caps thinking *plus* reply, so a task declaring a 400-token ceiling could spend the whole budget reasoning and return a truncated answer (`claude.py:89-96`). The adapter comment states that a task enabling reasoning must raise its ceiling to match — *"the two must move together"* — but **nothing enforces it**: `thinking` is a constructor argument on the adapter, `max_output_tokens` is a constant in the task file, and no code relates them. The first task that flips thinking on and leaves its ceiling at 400 silently reintroduces the exact failure the default prevents. **Latent, not live** — nothing enables thinking today, which is why this is a guard to add rather than a bug to fix. **Agreed fix: a floor** — refuse, or warn loudly, when thinking is enabled and the declared ceiling is below a sane minimum. **Keep it simple — user's calibration for the whole token-control area (2026-08-02):** the warn/hard-stop pair already exists and today most companies simply notice they have run out; this does not need to be inventive, original or perfect and can adapt over time. Its only job is to buy a reasonable amount of time while automations are running, so someone gets notified, escalates and obtains more budget before the next big prompt lands. Do not gold-plate. Source: [[Interview Prep - AI]] → AI Layer Q7.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 224, section "Features", position 27 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
