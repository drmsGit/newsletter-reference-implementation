---
id: TASK-148
title: >-
  Rendering has no preview-vs-send resolution mode, and static content modules
  (`ModuleInstanceDB.content_record_id`) have no version-awareness at all —
  `resolve_content_for_module` always resolves the…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 501200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** Rendering has no preview-vs-send resolution mode, and static content modules (`ModuleInstanceDB.content_record_id`) have no version-awareness at all — `resolve_content_for_module` always resolves the live, mutable `ContentRecordDB` for static modules regardless of context (`rendering/service.py:196-200,151-188`). Decision-slot content only pins a version if `DecisionResolutionDB.content_version_id` happens to be set — nothing ever auto-resolves "the latest version." Net effect: draft edits to a content record are immediately live everywhere, including active/recurring journeys, with no freeze point. Fix: add a send/snapshot resolution mode that queries the latest `ContentVersionDB` for the record and **raises an error ("contains unpublished content") rather than silently falling back to the live record** if no version exists yet — so managers can't accidentally send/snapshot draft content. Preview/builder mode keeps resolving against the live record (unchanged). Depends on / pairs with the content-schema redesign below (once `content` lives on the record, "create version" is the freeze action this error is checking for). Source: [[Interview Prep - Content, Campaigns, Audience]] → Content Q2. **Done 2026-07-12** — `render_variant_html`/friends take a `mode="preview"|"send"`; send mode raises `UnpublishedContentError`, surfaced as a 409 (API) and an alert banner (UI). Verified live: blocked a snapshot on an unpublished record with the correct message. The "publish all" convenience-button idea is carried forward as its own Feature.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 525, section "Done", position 12 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
