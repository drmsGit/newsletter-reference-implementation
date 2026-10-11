---
id: TASK-356
title: The manager app shows the working brand's logo from its default brand profile
status: Done
assignee:
  - '@claude'
created_date: '2026-10-11 08:39'
updated_date: '2026-10-11 11:42'
labels:
  - frontend
  - backend
dependencies:
  - TASK-350
type: feature
ordinal: 200990
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** Slice 5 of 5 of the brand-profile design (ADR-194, 2026-10-11).

The manager app shows the working brand's logo, taken from that brand's default profile, so a manager sees which brand they are working in.

**Only the logo.** The user first decided (question 6) that accent colour, logo and font would come from the default profile, with a contrast guard. After reading the design draft (docs/design/DESIGN.md: 'the manager app is one palette per install, not per brand'), the user narrowed it the same day to the logo only, so that:
- the app keeps one palette and its IBM Plex Sans and Mono fonts per installation;
- the design's colour meanings hold (teal marks what the system chose, ochre what a person pinned);
- a brand accent cannot clash with them.

This replaces task-94's separate web palette idea for the app.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The app shows the working brand's logo from its default profile, and switching brand switches it
- [x] #2 The app's palette and fonts do not change with the brand
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Final-design pass 2026-10-11 (no open question; ADR-194 point 12 as narrowed by the user to the logo only):
1. backend/app/auth/service.py current_brand_summary adds logo and logo_alt, read from the working brand's DEFAULT profile (the setup file's Header fields, task-351). SessionBrand (auth/router.py) gains both, optional. The Jinja pages get the same dict and ignore the keys.
2. frontend Shell: the logo before the brand switcher, alt text from logo_alt or the brand name; nothing when the profile has no logo. Switching brand already refetches the session, so the logo follows.
3. The palette and fonts are not touched: index.css keeps its tokens; only a size rule for the logo.
4. Tests: the session carries the default profile's logo and the other brand's after a switch; the shell shows it, or nothing; no style token changes.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-11, built. Commits a0f7cda and 868033f. Before it, Codex doc-15's attribution defect was fixed with its test (e486157), and ADR-194/ADR-163 got addenda pointing to ADR-195 (376fb48).

Where it landed:
- backend/app/auth/service.py current_brand_summary: logo and logo_alt from the working brand's default profile (the setup file's Header fields), looked up through brand_profiles.service.find_default_profile, which never creates one: reading the session must not write.
- backend/app/auth/router.py SessionBrand: logo, logo_alt (optional).
- frontend Shell: the logo beside the brand switcher, alt from logo_alt or the brand's name; nothing without one. index.css: a size rule only (.shell__logo), no colour or font.
- Tests: test_brand_logo.py (3: the session carries the default profile's logo, switching brand switches it, none without one); Shell.test (the logo, and no image without one).

A slip, corrected: a0f7cda was committed and pushed with one failing test (test_api_guard brand switch): the first version created a default profile on reading the session, and the row blocked the test's brand cleanup. My commit command did not gate on pytest's exit code. 868033f fixes it (lookup only), committed only after a green suite.

Verification: backend 1803 passed, Ruff clean; frontend 267 passed, tsc and eslint clean; 3 mutations caught. Live check 2026-10-11: the dev session carries logo null and logo_alt null for the Default brand, and the top bar is unchanged with no image. A logo was not set on the user's real Default profile; the logo itself is covered by the shell test.

AC #2 (palette and fonts do not change): by construction, nothing but the logo is read from the profile, and no style token changed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Slice 5 of brand profiles: the manager app's top bar shows the working brand's logo from its default profile (session brand logo and logo_alt, looked up without creating anything), switching brand switches it, and nothing else follows the brand: one palette and font set per installation. Verified by 1803 backend and 267 frontend tests, mutation checks, green CI (868033f) and a live check that the session carries the fields and the bar is unchanged without a logo.
<!-- SECTION:FINAL_SUMMARY:END -->
