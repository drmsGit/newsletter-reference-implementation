---
id: TASK-45
title: Click and open attribution guesses one "primary" content record.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 104500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P2, corrupts the signal layer.** **Click and open attribution guesses one "primary" content record.** `_primary_content_id_for_delivery()` (`providers/service.py:100-139`) picks the latest personalized resolution, else the first fixed-content module — it never inspects *which link was clicked*. In a newsletter with four content items, a click on the fourth credits the first, so affinity learning is **systematically wrong** in exactly the multi-content case the product is for. Opens are worse: they are email-level and should not be attributed to any single record. **Fix:** encode module/content id into tracked links and map the clicked URL back to the exact module; treat opens as email-level, or weight them explicitly rather than assigning a primary. Note this quietly degrades every downstream decision, and nothing about it fails visibly. Source: code review 2026-08-07 P2-07. **DIRECTION SET 2026-09-14 (user) — this is a provider-capability question, not a code fix, so it needs an ADR before any implementation.** The user's framing: there is no link traceability today. Attributing a click to content means **the content id has to be carried in the link itself**, and how that is possible is provider-dependent — Salesforce has link names, Selligent has data-attributes, others differ. Since the signal layer already reads customised attributes off an event, this becomes a declared capability in [[ADR-101 — Provider Capabilities Are Explicit]]'s sense: *"can return a custom attribute identifying the content on a click event"*. A provider without it cannot support content-level attribution, and the fallback is web tracking, which the user notes is **less reliable**. **Same shape as [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]**, which already gates provider selection on a capability — so the precedent for refusing a provider that lacks one exists. The open question this does NOT answer is whether lacking it should *block* provider selection outright or merely disable content-level attribution.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 128, section "Bugs", position 45 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
