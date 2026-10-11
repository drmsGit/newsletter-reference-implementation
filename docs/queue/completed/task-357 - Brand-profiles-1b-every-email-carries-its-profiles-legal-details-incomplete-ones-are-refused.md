---
id: TASK-357
title: >-
  Brand profiles 1b: every email carries its profile's legal details; incomplete
  ones are refused
status: Done
assignee:
  - '@claude'
created_date: '2026-10-11 08:59'
updated_date: '2026-10-11 09:58'
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
- [x] #1 Every email frame made from now on freezes its brand profile
- [x] #2 Every email (marketing, transactional, test) carries the profile's legal details; a marketing email also its unsubscribe line with the platform link
- [x] #3 A send is refused while its profile lacks a required field, or its snapshot predates brand profiles
- [x] #4 Deliveries sent before this still reconstruct byte-identically
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Final-design pass 2026-10-11 (checked against the code; one change decided with the user).

User decision: the legal footer markup and its Imprint/Privacy labels per language live in a TEMPLATE FILE, storage/modules/email/_legal_footer.html, not in texts.py. templates_fingerprint hashes every file in the channel directory, so a later edit shows honestly as templates changed; texts.py is not fingerprinted, which is why the legacy footer_html line is frozen forever. The file's addition changes the email fingerprint once, as any new module does; hash_matches for sent deliveries is unaffected because frames below 3 keep footer_html.

1. Frame version 3 (rendering/frame.py): FRAME_VERSION 3, FRAME_VERSIONS (1, 2, 3). build_frame adds brand_profile {id, name, language, kind, values} to email frames, from brand_profiles.service.profile_of_variant (the variant profile, or the brand default when NULL). Push frames carry none.
2. Legal footer (rendering/service.py legal_footer_html, Jinja like module_html, autoescaped): line one legal name and address, then Imprint and Privacy links (Impressum/Datenschutz for de, English otherwise); line two the unsubscribe text, linked to the token URL when there is one, plain when unlinked is asked (test send), absent when the text is empty or the message carries no unsubscribe. The registry skips files whose name starts with an underscore (no orphan-template warning).
3. render_frame: frames of version 3 put legal_footer_html in the footer slot (unsubscribe link from the unsubscribe argument as today, List-Unsubscribe unchanged); frames below 3 keep footer_html exactly. footer_html docstring reworded: frozen forever, and why.
4. Refusal: frame.profile_refusal(frame) -> sentence or None. Email only. Below version 3: made before brand profiles, take a new snapshot (D7). No profile in the frame: same. Missing required fields (structure.missing_fields with the frozen kind and values): names them by label and says to fill the profile, then take a new snapshot (the frame froze the values). Called in send_send_instance pre-claim right after the content check (direct, approval, scheduled and Jinja all pass there) and as blocked_reason in send_fire describe.
5. Test send: the profile is the variant profile, or the brand default without a variant. Incomplete: success False, nothing sent, the fields named. Otherwise the legal footer with the unsubscribe text unlinked and no List-Unsubscribe; render_variant_html gains footer (default empty, so previews are unchanged).
6. Tests: frame v3 freezing (variant profile, NULL reads default, later profile edits do not change the frame), footer content and language labels, unsubscribe linked/plain/absent, escaping, refusal paths (old frame, missing fields; direct and approval describe), test send refused and carrying the footer, a v2 frame still renders byte-identically, a v3 delivery reconstructs to its hash; test_envelope_rename FRAME_VERSION assertion; conftest temp_brand gets a complete default profile.

Not touched: previews (snapshot preview shows the legal line, no unsubscribe line; the live editor preview none), brand.css, the unsubscribe page, push.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-11, built. Commits 06da66e (ADR-194 addendum: the legal footer is a template file) and 0083876.

Decided with the user at the start: the legal footer and its Imprint/Privacy labels live in storage/modules/email/_legal_footer.html (fingerprinted), not texts.py. The registry skips underscore files.

Where it landed:
- rendering/frame.py: FRAME_VERSION 3, FRAME_VERSIONS (1, 2, 3), PROFILE_FRAME_VERSION. build_frame freezes brand_profile {id, name, language, kind, values} on email frames (profile_of_variant: the variant profile or the brand default). render_frame: version 3 renders legal_footer_html; below 3 the legacy footer_html line, unchanged. profile_refusal(frame) gives the sentence for an old frame or a missing required field (by label, and says to take a new snapshot).
- rendering/service.py: legal_footer_html(profile, unsubscribe_url, unsubscribe_unlinked); render_variant_html gained footer (default empty, previews unchanged).
- delivery/service.py: send_send_instance refuses on profile_refusal right after the content check, before the claim. send_test_email uses the variant profile or the brand default; incomplete returns success False naming the fields and sends nothing; otherwise the footer goes with the wording unlinked, no List-Unsubscribe; the plain fallback body carries it too.
- approvals/actions/send_fire.py: the same sentence as blocked_reason.
- subscriptions/texts.py: footer_html docstring now says it is frozen forever and why.
- Tests: test_legal_footer.py (21: freezing, later edits, NULL to default, labels en/de/other, linked/plain/absent unsubscribe, escaping, legacy line byte-for-byte and as a pinned literal, the fingerprint covers the template, refusals incl. push exempt and version-decides, send refused before claim, reviewer told, sent email rebuilds to its hash after a profile change, test send footer and refusal). conftest temp_brand gets a complete default profile (COMPLETE_PROFILE). Updated: test_envelope_rename (version 3; rename compared at version 2), test_frame parity (same footer on both paths), test_channels (a real foreign brand instead of id 999999), test_brand_profile_model (bare brand built directly).

Verification: backend 1747 passed, Ruff clean; 12 mutations, all caught after adding the version-decides test. Live check 2026-10-11 in the browser pane on scratch data (campaign 12, variant 18, snapshot 5, send 7 with no recipients): the snapshot preview ends with the legal footer; the send was refused with 409 naming Legal company name, Address, Imprint link, Privacy link (the dev Default profile is still empty), and stayed draft. Scratch rows removed by id.

Day-one effect, as the description said: every send in dev is refused until each brand's default profile has its legal fields filled, and older snapshots need a new snapshot.

Noticed, not changed: a snapshot preview of an incomplete profile shows the footer with empty name and links (the send is refused anyway). The live editor preview shows no footer.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Slice 1b of brand profiles: frame version 3 freezes each email's brand profile, and every email ends with its legal footer (name, address, Imprint and Privacy links; on marketing the unsubscribe wording as the token link). The footer is a fingerprinted template file (ADR-194 addendum, decided with the user). Sends, approvals and test sends are refused while the frozen profile is incomplete or the snapshot predates profiles; older frames keep the legacy line byte for byte. Verified by 1747 backend tests, 12 mutation checks, green CI (0083876) and a live check on scratch data.
<!-- SECTION:FINAL_SUMMARY:END -->
