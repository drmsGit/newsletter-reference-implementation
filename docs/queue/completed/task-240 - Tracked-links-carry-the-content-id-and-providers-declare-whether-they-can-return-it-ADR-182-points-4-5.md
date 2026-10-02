---
id: TASK-240
title: >-
  Tracked links carry the content id, and providers declare whether they can
  return it (ADR-182 points 4-5)
status: Done
assignee: []
created_date: '2026-10-02 14:35'
updated_date: '2026-10-02 16:00'
labels:
  - backend
dependencies: []
type: feature
ordinal: 305200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Since 2026-10-02 (task-45, ADR-182) a click credits a content record only when the event names it, so click-driven affinity learning is paused: no rendered link carries a content id yet, and every live webhook click now credits nothing. ADR-102 (accepted) already decided rendering generates tracking metadata including contentId, with providers free to choose the carrier; it was never built. Two parts remain. (1) Rendering puts the content id into each content-bound link, and the provider adapter maps a click payload back to it (Resend reports the clicked URL; other providers use link names or data attributes). (2) Per ADR-101, each provider declares whether it can return a content identifier on a click; a provider without it stays selectable and the provider/settings surface says it has no content-level attribution (ADR-182 point 4). Web tracking as a fallback is less reliable and not designed. Possible ADR-101 addendum listing the new optional capability.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A click on a tracked link in a multi-content email credits exactly the content that link belongs to
- [x] #2 Each provider declares the capability, and the settings read says which providers lack it
- [x] #3 A click on a non-content link (logo, footer) still credits nothing
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-02: built. Carrier: query parameter nl_content (user choice over a redirect endpoint), added in rendering.service.module_html via rendering/tracking.py for content-bound modules only. Resend adapter reads data.click.link (documented shape; not verified against a live event). providers.service drops a named id the delivery record (ADR-183) says was not sent. Capability click_content_attribution on DeliveryProvider (resend True, mock False), listed by GET /settings. Seed content gains button_url. Tests: tests/test_tracked_links.py, test_click_attribution.py additions, an end-to-end test in test_frame.py (delivered link -> Resend webhook -> exactly that content credited); four mutants caught. Suite 950 passed. Not done: ADR-101 addendum listing the capability; adapters for other providers do not exist yet.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Content links carry nl_content=<id>; a Resend click on one credits that content, and only if the recipient's delivery record shows it was in their message. Providers declare whether they can attribute clicks, and the settings read lists it. Verified end to end and mutation-checked; full suite 950 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
