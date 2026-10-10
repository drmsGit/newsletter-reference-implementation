---
id: TASK-332
title: >-
  CI breaks its own promises: an unpinned scanner image, and a push cancels the
  weekly scan
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 18:12'
updated_date: '2026-10-10 19:50'
labels:
  - docs
dependencies: []
type: bug
ordinal: 100600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug]** Two one-line gaps in .github/workflows/ci.yml, both found in the 2026-10-09 interview review.

1. Pinning (CI Q1). ci.yml:14-16 explains that third-party actions are pinned by commit hash so a moved tag cannot change what runs (ADR-190). The secret scanner, the one step that reads the whole git history, is still pulled by tag: ci.yml:177 runs ghcr.io/gitleaks/gitleaks:v8.30.1. Decided: pin it by @sha256 digest, with the tag kept in a comment, matching the actions convention.

2. Cancellation (CI Q4). ci.yml:29-31 groups runs by ref with cancel-in-progress: true, and the weekly schedule (:23-24, Mondays 06:00 UTC) runs on main, where every push lands. A push during the weekly vulnerability scan silently cancels it, and a cancelled scan is easy to mistake for a quiet week. The weekly run exists precisely for weeks without pushes. Decided: the scheduled run is never cancelled, for example by adding github.event_name to the concurrency group, or by not cancelling for schedule.

Who watches the weekly result stays open (keep in POC). The repo is labelled docs here only because CI has no area label of its own.

Source: [[Interview Prep - Since 2026-09-18]] → CI and dependency verification, Q1 and Q4.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The gitleaks image is referenced by sha256 digest, tag noted in a comment
- [x] #2 A push to main during a scheduled run does not cancel the scheduled run
- [x] #3 CI stays green
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10, done (commit 8eb7fb6), ADR-190.

- gitleaks runs from ghcr.io/gitleaks/gitleaks@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f, the v8.30.1 image index read anonymously from ghcr's registry API. The tag is kept in a comment.
- The concurrency group is ci-ref-event_name, so a push still cancels an older run for the same ref but never the scheduled one.
- The workflow header now names the image pinning too.

Tests: backend/tests/test_ci_workflow.py reads the file as text and checks three things: every action is pinned to a 40-hex commit, every docker image to a sha256 digest, and the concurrency group includes github.event_name. The last two failed before the edit; the actions check already passed.

CI run 38081134728: all four jobs green. The log shows the scanner pulling the digest-pinned image and its job passing.

Not verifiable in CI: that a Monday scan survives a concurrent push. The test checks the setting, not GitHub's behaviour.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
CI keeps both of its promises now: the secret scanner runs from its v8.30.1 image digest rather than a movable tag, and scheduled runs have their own concurrency group, so a push to main can no longer cancel the weekly scan. A new test, backend/tests/test_ci_workflow.py, pins both plus the actions' commit pinning (it failed on the two problems first). Verified by green CI on 8eb7fb6, whose log shows the scanner pulling the pinned image.
<!-- SECTION:FINAL_SUMMARY:END -->
