---
id: TASK-357
title: >-
  Brand profiles 1b: every email carries its profile's legal details; incomplete
  ones are refused
status: To Do
assignee: []
created_date: '2026-10-11 08:59'
labels:
  - backend
dependencies:
  - TASK-350
type: feature
ordinal: 200972
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** Slice 1b of the brand-profile design (ADR-194, final-design pass of 2026-10-11 recorded on task-350). It switches enforcement on after task-350 (1a) has made profiles exist and fillable.

- **Frame version 3:** build_frame (backend/app/rendering/frame.py) freezes the variant's profile, or the brand default when it is NULL, as brand_profile {id, name, language, kind, values} in email frames. FRAME_VERSIONS becomes (1, 2, 3).
- **render_frame:**
  - Version 3 frames get legal_footer_html (new, in backend/app/subscriptions/texts.py). Line one is the legal name and address, then the Imprint and Privacy links with built-in labels per language (en/de, fallback en). Line two, only when the unsubscribe text is set, is that text as the link to the token URL.
  - Older frames keep footer_html exactly as today. footer_html and FOOTER_STYLE must never change, because texts.py is not in templates_fingerprint, so any change silently breaks hash_matches for every sent delivery. Its docstring is reworded to say so.
- **Test sends** (send_test_email, delivery/service.py around :762): render_variant_html gains a footer argument. A test send carries the live profile's legal footer, with the unsubscribe text unlinked and no List-Unsubscribe header, and is refused (success=False, naming the fields) while the profile lacks a required field.
- **Send refusal:**
  - missing_profile_fields_in_frame(frame) is called in send_send_instance's read-only pre-claim block, right after the content check. It refuses a frame below version 3 ('made before brand profiles; take a new snapshot', D7), a frame without a profile, and a missing required field (legal name, address, imprint URL and privacy URL always; unsubscribe text on marketing).
  - The same check is the advisory blocked_reason in approvals/actions/send_fire.py describe. Direct, approval, scheduled and Jinja sends all pass through it.
- **Tests:** test_envelope_rename.py's FRAME_VERSION == 2 assertion; frame and unsubscribe tests; already-sent deliveries must still reconstruct byte-identically.

The user's dev data on day one: every send of an existing campaign is refused until that brand's default profile has its legal fields filled, and planned sends holding an older snapshot need a new snapshot.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every email frame made from now on freezes its brand profile
- [ ] #2 Every email (marketing, transactional, test) carries the profile's legal details; a marketing email also its unsubscribe line with the platform link
- [ ] #3 A send is refused while its profile lacks a required field, or its snapshot predates brand profiles
- [ ] #4 Deliveries sent before this still reconstruct byte-identically
<!-- AC:END -->
