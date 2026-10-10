---
id: TASK-339
title: The shipped AI subject-line prompt carries a developer's English house style
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 18:43'
updated_date: '2026-10-10 20:47'
labels:
  - backend
dependencies: []
type: feature
ordinal: 200770
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** The one worked example of "the manager owns the prompt" (ADR-140, ADR-141) ships a developer-written editorial style: backend/app/ai/tasks/subject_preheader.py:40-61, DEFAULT_PROMPT. It is in English, and its rules are matters of taste: "No exclamation marks, no 'Discover', no emoji", "Be concrete". It also says "email newsletter". The first thing a manager sees when they open the prompt is someone else's house style, in the wrong language for the German buyer. Business baseline finding P2-H1.

Decided by the user in the 2026-10-09 interview review. The shipped seed keeps only:
- what the code needs, which is the three-option SUBJECT/PREHEADER format the reply is parsed in;
- the technical limits (subject at most 60 characters, preheader at most 90).

The taste rules go. In their place is a clearly marked line for the manager's own house style. The prompt tells the model to write in the language of the content, so a German newsletter gets German suggestions without German being hardcoded.

Final-design pass: check how the default reaches an installation. If it is seeded as a published prompt version, changing the constant affects only new installations; say what happens to an existing version.

Source: docs/business-interview-baseline.md → P2-H1.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The shipped default prompt contains no editorial taste rules, only the parsed format and the 60/90 limits
- [x] #2 It has a marked place for the manager's own house style
- [x] #3 It asks for suggestions in the language of the content
- [x] #4 The reply is still parsed as before
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10, done (commit 69addbc). ADR-140/141; business baseline P2-H1.

DEFAULT_PROMPT now keeps only the 3-option SUBJECT/PREHEADER format the reply is parsed in and the 60/90-character limits. It has a marked 'Your house style:' line ('None set yet. Replace this line in Settings...') and asks for suggestions 'written in the language the content is written in'.

All taste rules removed. That includes 'the preheader must add information, never repeat the subject': it is neither format nor limit, so it went under the decision. The user was told and can ask for it back.

Final-design finding: the default is used only when no prompt version is published (subject_preheader.py, template = published body or DEFAULT_PROMPT; Settings shows the same), so a published version is untouched.

Tests: backend/tests/test_subject_prompt_seed.py, 5 tests. 3 failed first; the limits and parse tests guard what must not change.
Mutations, each caught: a taste rule back, 1 failed; the language replaced with English, 1 failed.
Suite: 1660 passed, Ruff clean. CI green on 69addbc.

Live: the dev DB has a published version 2 ('Version 2 for log test'), which Settings shows, as intended, so the new seed is not visible there.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The shipped AI subject-line prompt is now a neutral seed: only the parsed 3-option format and the 60/90-character limits remain, a marked 'Your house style' line awaits the company's rules, and suggestions come in the language of the content. All developer taste rules are gone. A published prompt version still wins; only installations without one see the new default. Verified by test_subject_prompt_seed.py (failed first, two mutations caught), the full suite (1660), and green CI on 69addbc.
<!-- SECTION:FINAL_SUMMARY:END -->
