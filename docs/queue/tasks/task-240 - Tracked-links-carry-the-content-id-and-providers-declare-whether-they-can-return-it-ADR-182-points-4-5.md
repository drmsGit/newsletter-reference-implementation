---
id: TASK-240
title: >-
  Tracked links carry the content id, and providers declare whether they can
  return it (ADR-182 points 4-5)
status: To Do
assignee: []
created_date: '2026-10-02 14:35'
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
- [ ] #1 A click on a tracked link in a multi-content email credits exactly the content that link belongs to
- [ ] #2 Each provider declares the capability, and the settings read says which providers lack it
- [ ] #3 A click on a non-content link (logo, footer) still credits nothing
<!-- AC:END -->
