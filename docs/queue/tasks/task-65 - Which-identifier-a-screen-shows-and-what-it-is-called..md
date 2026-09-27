---
id: TASK-65
title: 'Which identifier a screen shows, and what it is called.'
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - frontend
dependencies: []
type: feature
ordinal: 201800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — FRONTEND DESIGN PASS, and blocked on `VariantDB.channel`. Parked deliberately; do not patch one template at a time.** **Which identifier a screen shows, and what it is called.** Raised by the user 2026-09-16/17 while correcting one label, and the correction went two levels deeper than the label. `campaign_detail.html` showed `Variant {{ variant.id }}` — a global database sequence, so "Variant 981" reads as *the 981st variant* on a system with a handful of campaigns and climbs every time anybody tests anything. Changing it to the campaign id and calling it "Email 981" was **also wrong**: [[ADR-160 — Channel Model and Composition]] point 4 has one campaign carry email, push and social variants, so a campaign id is not an email id. And the user's decisive point: **`Campaign 1048 — Variant A` is accurate and *less* informative** — it drops the one fact a manager needs from that row, which is that this thing is the email.

  **This is blocked on code, not only on design taste.** A label can only say "this is an email" if something at composition level carries a channel, and **nothing does yet**: `VariantDB` has no channel column, and the only `channel` in the schema is `DeliveryExecutionDB.channel` (default `"email"`), a plan-time copy — resolved at send, far too late to label something a manager is still building. [[ADR-160 — Channel Model and Composition]] point 4 ("channel is an attribute on the variant") is **Accepted and unimplemented**, and it is the prerequisite. Until then any label naming a channel is hardcoded, which is exactly the false assertion that produced this entry.

  **ADR-160 already anticipated the display problem and deferred it here.** Its Consequences: a variant now carries two meanings, A/B version *and* channel expression, "which reads awkwardly at `Push A / Push B`. Accepted as a **display** concern to be solved by grouping in the UI, not a model one." So the deferral is the ADR's own; what no ADR gives is a scheme — checked across ADR-160 to 165, identifier and labelling conventions are **not addressed anywhere**.

  **Decide these together rather than one template at a time**, since answering them singly is how the present inconsistency was arrived at: the `#{{ x.id }}` labels on campaigns, modules, executions and recipients (defensible today — there the id *is* what someone would quote); the `f"Content {id}"` / `f"Decision Slot {id}"` page titles; whether a per-campaign index ("Variant 1 of 3") beats any id; and how [[ADR-160 — Channel Model and Composition]] point 7's *"a variant is planned and sent, not a campaign"* should shape the anchor, given the sendable asset is the variant and not the campaign the label currently names. Source: user, 2026-09-16 (the number) and 2026-09-17 (the noun, the missing channel, and the call to park it).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 198, section "Features", position 18 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
