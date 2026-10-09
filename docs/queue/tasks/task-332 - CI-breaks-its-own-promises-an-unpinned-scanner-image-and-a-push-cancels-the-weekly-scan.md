---
id: TASK-332
title: >-
  CI breaks its own promises: an unpinned scanner image, and a push cancels the
  weekly scan
status: To Do
assignee: []
created_date: '2026-10-09 18:12'
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
- [ ] #1 The gitleaks image is referenced by sha256 digest, tag noted in a comment
- [ ] #2 A push to main during a scheduled run does not cancel the scheduled run
- [ ] #3 CI stays green
<!-- AC:END -->
