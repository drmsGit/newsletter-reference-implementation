---
id: TASK-93
title: >-
  Initial interest from subscription context (DOI), + cold-start via trackable
  fixed content.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 204600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — Initial interest from subscription context (DOI), + cold-start via trackable fixed content.** Surfaced 2026-07-26 (user). Two linked ideas about how a *new* recipient gets their first interest signals, so they're not stuck with an empty profile: **(1) Subscription-context seeding.** When someone subscribes via the website's **double-opt-in (DOI)** flow, the company can pass parameters that "give context" — which topic/page they subscribed from, a chosen interest, campaign source, etc. On recipient create, translate those into initial declared `manual` contributions (the same mechanism used to seed the `ds@` demo recipient with Hiking). This means a new subscriber can start with a real, sourced interest instead of a blank slate — no arbitrary seeding. Needs: a documented parameter contract on the recipient-create/DOI path and the mapping to categories. **(2) Cold-start via trackable fixed content.** Confirmed product behavior: a recipient with **no** interest correctly sees **no recommended/personalized content** (the decision slot resolves nothing → hidden). But the email still contains fixed/editorial content — *as long as that fixed content is linked to real content records (with category assignments)*, a click on it attributes categories and **builds the recipient's first interest**, so recommendations appear "after a while". Today the demo's fixed hero/CTA are plain `module_data` (untracked), so nothing to attribute; a real setup links fixed content to content records. Consider: (a) encourage/allow fixed modules to reference content records; (b) make click attribution consider *all* content in the email, not just the primary resolved pick (`_primary_content_id_for_delivery` currently returns one). Both are the "how does a profile bootstrap" story and pair with the signal layer (ADR-132). Source: user, 2026-07-26 (webhook engagement session). **Update 2026-07-31 (AI-layer interview, Cluster 3 / Q17): second reason to build this.** Cold-start is now the *only* case where a per-email AI suggestion clearly earns its keep (the per-send 5% challenger was dropped — see the shadow-variant item), so the subscription-context parameters are what give a brand-new recipient their first *Anhaltspunkt* before the welcome-cycle suggestion button and the anti-bubble/exploration feature (above) take over.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 262, section "Features", position 46 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
