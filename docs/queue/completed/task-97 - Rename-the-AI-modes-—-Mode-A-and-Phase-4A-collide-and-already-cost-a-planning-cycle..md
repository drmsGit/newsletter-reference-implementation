---
id: TASK-97
title: >-
  Rename the AI modes — "Mode A" and "Phase 4A" collide and already cost a
  planning cycle.
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 13:57'
updated_date: '2026-10-08 21:48'
labels:
  - docs
dependencies: []
type: docs
ordinal: 205000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Docs]** **Rename the AI modes — "Mode A" and "Phase 4A" collide and already cost a planning cycle.** Surfaced 2026-08-07 (user). The AI capability layer uses **Mode A / B / C** ([[ADR-141 — In-App Assistive AI Actions]] / [[ADR-142 — Autonomous Workflows and the Automation Boundary]] / [[ADR-143 — AI-Assisted Development Boundary]]) while the roadmap uses **Phase 4A / 4B / 4C**. They are unrelated — Mode A is in-app assistive AI, Phase 4A is deciding the playbook's chapter structure and voice — and the user conflated them, concluding that Phase 4A was finished because the subject-line feature (Mode A) was. That misread a planning session. **Fix: name the modes by function** — Assistive / Autonomous / Development — rather than by letter, in the three ADRs, the roadmap and the backlog. Cheap now, and it removes a trap a playbook *reader* will hit too, since both vocabularies appear in the published material. Note the ADR titles already describe the functions accurately; it is the shorthand "Mode A" that does the damage. Source: user, 2026-08-07.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 275, section "Features", position 50 in that section (top = do next). The description is the original entry, verbatim.

2026-10-08: verified, decided, built (commits 229676d, 4209819, a3d6e0f; CI green on a3d6e0f).

Verified first: the letter shorthand was still everywhere. It appeared in 12 ADRs (all Accepted, in the Decision section of 9), in the playbook, in queue tasks, in three business docs, in two MOCs, and in 7 backend files of code comments and docstrings (two of which feed the OpenAPI text in schema.d.ts).

Decided with the user one question at a time, recorded in the ADR-140 addendum of 2026-10-08 and the playbook decision log:
1. Key plus living files. The modes are Assistive (was A, ADR-141), Autonomous (was B, ADR-142) and Development (was C, ADR-143). Dated records keep the letters, by the user's 2026-10-05 rename rule (the DATED list in backend/scripts/rename_product.py) and the rule that an Accepted Decision is never edited. The ADR-140 addendum is the key. Living files were reworded: the code comments and docstrings, schema.d.ts (regenerated), docs/business BRIEF, ASSUMPTIONS and BETA-SCOPE, and the AI and Security MOCs. Rejected: rewriting the ADRs, the playbook and open tasks; renaming the roadmap phases instead.
2. A guard. backend/tests/test_mode_names.py is built from the product rename's living-file scan: tracked files, is_dated, the text suffixes and ADR-link stripping. It has its own pattern, so hyphenated spellings are caught. docs/business-interview.md, docs/weekly-summary.md and docs/architecture/code-slimmer-report.md joined DATED as records of a date.

Mutation check: 5 of 5 caught. The mutants were a dated record dropped, the letters back in a comment, a hyphenated spelling back in a doc, the pattern narrowed, and dated records scanned. Full suite 1527 passed; Ruff and tsc clean.

Found by CI: the guard reads tracked files only, so it passed locally while test_mode_names.py was untracked, then failed once committed (the file quotes the letters to test its pattern). The file now skips itself by path. A mutation check confirmed that, with the file tracked, the test fails without the skip.

No live check: no behaviour changed. The served text that changed is one HTML comment and two API descriptions, and those are covered by the contract check.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The AI modes are now Assistive, Autonomous and Development in every living file: code comments, the API text, the business docs and the MOCs. The letters can no longer be confused with the roadmap's Phase 4A/4B/4C. Dated records, the ADRs among them, keep the letters by the 2026-10-05 rename rule, and the ADR-140 addendum of 2026-10-08 is the key. A guard test keeps the letters out of living files. Verified by test_mode_names.py (5/5 mutants caught), the full suite (1527 passed) and CI green.
<!-- SECTION:FINAL_SUMMARY:END -->
