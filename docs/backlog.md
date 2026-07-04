---
type: backlog
topic:
  - project-management
  - backlog
created: 2026-07-04
modified: 2026-07-04
---

# Backlog — Action Items from Interview-Prep Reviews

Granular, prioritized queue of concrete fixes/features decided while working through [[MOC - Interview Prep Baseline]] via the `/interview-review` command. Distinct from the phase-level roadmap in `docs/playbook-strategy.md` §6 (Phase 1-4, strategic/product sequencing) — this is the tactical "what do we act on, in what order" list.

Order within each section is priority order: **top = do next.** New items are inserted at the position matching their priority, not appended to the bottom. Bugs outrank features of similar importance.

## Status legend
- 🔴 To Do
- 🟡 In Progress
- ✅ Done
- ⛔ Won't Do
- 📋 Needs ADR — not actionable yet, blocked on a design decision. Doesn't compete for priority ranking with 🔴 items until it's resolved into one.

## Bugs

- 🔴 **[Bug]** Deleting a category or content record that still has relations (parent/child edges, category assignments) should not silently cascade — raise a confirmation-style error surfacing what it's connected to ("related to N parent(s) / M child(ren) — delete anyway?") so a manager can re-parent/re-assign first if needed. Applies once delete endpoints for content records/categories are built (none exist yet); pairs with the FK/cascade design from Content Q5. Does not cover the harder historical-data question below — see the 📋 Needs ADR item. Source: [[Interview Prep - Content, Campaigns, Audience]] → Content Q6.

- 🔴 **[Bug]** Rendering has no preview-vs-send resolution mode, and static content modules (`ModuleInstanceDB.content_record_id`) have no version-awareness at all — `resolve_content_for_module` always resolves the live, mutable `ContentRecordDB` for static modules regardless of context (`rendering/service.py:196-200,151-188`). Decision-slot content only pins a version if `DecisionResolutionDB.content_version_id` happens to be set — nothing ever auto-resolves "the latest version." Net effect: draft edits to a content record are immediately live everywhere, including active/recurring journeys, with no freeze point. Fix: add a send/snapshot resolution mode that queries the latest `ContentVersionDB` for the record and **raises an error ("contains unpublished content") rather than silently falling back to the live record** if no version exists yet — so managers can't accidentally send/snapshot draft content. Preview/builder mode keeps resolving against the live record (unchanged). Convenience idea: a "publish all" button to freeze every unpublished record in a variant in one step before sending. Depends on / pairs with the content-schema redesign below (once `content` lives on the record, "create version" is the freeze action this error is checking for). Source: [[Interview Prep - Content, Campaigns, Audience]] → Content Q2.

- 🔴 **[Bug]** Two competing category hierarchy mechanisms exist: `CategoryDB.parent_category_id` (leftover from an earlier, wrong implementation) and `CategoryRelationDB` (parent_category_id/child_category_id/relation_type edge table, already what the graph view at `frontend/router.py:1608-1621` actually uses). Fix: drop `CategoryDB.parent_category_id` entirely and consolidate on `CategoryRelationDB` as the single mechanism. Deliberately keep it fully flexible, no new restrictions: a child may have multiple parent relations, and parent-level (main) categories may relate to each other or to children freely — needed for real-world multi-parent taxonomies and for AI-discovered relations later, and adding artificial constraints now isn't necessary. Do add a cycle guard (reject a relation that would create a direct or transitive parent_child loop, e.g. A→B and B→A) since that's a genuine logical contradiction, not a business-flexibility case. Source: [[Interview Prep - Content, Campaigns, Audience]] → Content Q5.

- 🔴 **[Bug]** `get_content_record_by_id` (`content/router.py:43-49`) hand-rolls its own `ContentRecordDB` → `ContentRecord` mapping (plus an unnecessary local re-import of `ContentRecord`) instead of using a shared mapper — duplicates the same mapping already in `list_content_records`/`update_content_record` (`service.py:17-25,28-39`). Fix: extract a `to_content_record(record) -> ContentRecord` helper in `service.py` (mirroring the existing `to_content_version`/`to_category_relation` pattern) and use it in all three places. Small cleanup. Source: [[Interview Prep - Content, Campaigns, Audience]] → Content Q4.

- 🔴 **[Bug]** `assign_category_to_content` (`content/service.py:241-257`) has no duplicate check, unlike `audience`'s `add_member` — the same content/category pair can be assigned more than once, creating duplicate rows and duplicate entries in `list_categories_for_content` output. Fix: reject (or upsert) on duplicate `(content_id, category_id)` pairs — no duplicates allowed. Cosmetic/data-hygiene only (no correctness risk beyond a repeated list item), lowest priority of the bugs logged so far. Source: [[Interview Prep - Content, Campaigns, Audience]] → Content Q7.

## Features

- 🔴 **[Feature]** Redesign content schema: move full CMS content fields onto `ContentRecordDB` as a `content` JSON column (same shape as `ContentVersionDB.content`, e.g. `headline_medium`/`body_medium`), so record creation/editing carries the real renderable content directly instead of requiring a separate "create version" step to enter it. Keep `title` (+ short `description`) as metadata columns for catalog listing/filtering. "Create version" becomes a freeze/snapshot action (stand-in for future publish) that copies the record's current `content` into an immutable `ContentVersionDB` row for audit/rollback (ADR-128) — not a "now type your content" step. Also resolves the root cause of the hardcoded `headline_medium`/`body_medium` alias patch in `rendering/service.py` (record and version will finally share one content shape). Source: [[Interview Prep - Content, Campaigns, Audience]] → Content Q1.

- 🔴 **[Feature]** AI/system recommendation layer on top of the (human-governed, per [[ADR-080 — Human-governed Taxonomy Before AI Selection]]) category taxonomy — e.g. "system suggests promoting this to a main category" or "system suggests this relates to category X" based on usage frequency/scoring. Reuses the same propose-don't-impose trust-building pattern already designed for content overrides (`docs/playbook-strategy.md` Decision Log, 2026-06-24) rather than making hierarchy itself emergent/scored (rejected — see Content Q5 addendum). Depends on the Phase 3C signal layer (usage/frequency signals don't exist yet) — future work, not current priority. Source: [[Interview Prep - Content, Campaigns, Audience]] → Content Q5 (addendum).

## Needs ADR (blocked on design decision)

_Not prioritized alongside 🔴 To Do items — these need a decision recorded as an ADR before they're actionable. Move to Bugs/Features once resolved._

- 📋 **Category (and content record) deletion vs. archival policy.** Categories accumulate historical value via preference/engagement scoring (`ContentCategoryAssignmentDB.score`, `RecipientPreferenceDB`) — hard-deleting a category breaks the ability to interpret that historical data (what a past engagement signal even meant). Leaning toward: never hard-delete a category/content record that has any historical usage — **archive** instead. An archived category stops contributing to *new* preference scoring; existing preference influence from it decays naturally over time (same mechanism as the not-yet-built Phase 3C signal decay, [[ADR-112 — Signals Use Time-Based Decay]]) rather than being force-zeroed. Only once a category is fully unused *and* decayed out would actual deletion become safe to consider. Needs a dedicated ADR (none exists today covering archive-vs-delete policy) before implementation — this is tightly coupled to the Phase 3C signal layer design already flagged as open in `docs/playbook-strategy.md` §7. Source: [[Interview Prep - Content, Campaigns, Audience]] → Content Q6 (addendum).

## Won't Do (archive)

_(items moved here keep their original entry text plus a short reason and date)_

## Done (archive)

_(items moved here keep their original entry text plus completion date)_

---
## Related
- [[playbook-strategy]] — §6 Roadmap for phase-level (Phase 1-4) strategic sequencing
- [[MOC - Interview Prep Baseline]] — source of most items logged here
