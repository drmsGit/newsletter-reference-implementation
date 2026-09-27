---
id: TASK-169
title: >-
  `send_send_instance` reads one shared, variant-level snapshot and sends
  identical HTML to every recipient (`delivery/service.py:111-172`) instead of
  resolving per-recipient HTML — even though decisio…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 503300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `send_send_instance` reads one shared, variant-level snapshot and sends identical HTML to every recipient (`delivery/service.py:111-172`) instead of resolving per-recipient HTML — even though decision-slot personalization (ADR-083) already exists in the rendering layer and could resolve different content per recipient within the same variant. Note: providers genuinely don't need campaignId/variantId/snapshotId at all (internal bookkeeping, not the ESP's concern), and variantId being identical across recipients within one send is *correct*, not a gap, when personalization stays inside one variant via decision slots — it would only legitimately differ per recipient in a true split-delivery/A/B scenario, which is the separate "shadow variant" idea already in Needs ADR. Fix scope, narrowed: resolve/render HTML per recipient (reusing existing per-recipient rendering) before handing each recipient their own final HTML to the provider, instead of reusing one shared snapshot for the whole send. Subject/preheader as dedicated provider fields is tracked separately (Campaigns Q4). Source: [[Interview Prep - Delivery, Providers, Recipients]] → Delivery Q2. **Done 2026-07-12** — `send_send_instance` now calls `render_variant_html(mode="send")` per execution (translating the execution's external `recipient_id` to the internal `RecipientDB.id` first), instead of reading one shared snapshot file. Verified live: rendered different HTML for two recipients with different decision resolutions for the same slot (one saw Mallorca content, the other Rome, neither leaked into the other's version), and confirmed the full send pipeline still completes cleanly end-to-end.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 567, section "Done", position 33 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
