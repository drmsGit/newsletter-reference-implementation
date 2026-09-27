---
id: TASK-170
title: >-
  `RecipientTopScoreStrategy`'s tie handling (`recipient_top_score.py:69-76`) is
  undisclosed, unintentional pseudo-randomness — `max()` picks whichever tied
  candidate the DB happened to return first, w…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 503400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `RecipientTopScoreStrategy`'s tie handling (`recipient_top_score.py:69-76`) is undisclosed, unintentional pseudo-randomness — `max()` picks whichever tied candidate the DB happened to return first, with no `ORDER BY` and no mention of the tie in `reason`, undermining ADR-085 explainability and risking a permanent, unexplainable bias toward whichever content has a lower ID. Fix: make tie-breaking an explicit, disclosed random selection among tied candidates, and state it in the `reason` string ("tied at score X between N candidates, selected randomly") — honest and auditable rather than hidden. Source: [[Interview Prep - Decision, Overrides, Insight]] → Decision Q7. **Done 2026-07-12** — ties are now detected explicitly and broken with `random.choice`, with the reason string noting "(tied at score X between N candidates, selected randomly)" only when a tie actually occurred. Verified live with a constructed tie: the disclosure appeared correctly; a normal non-tied run stayed clean with no note.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 569, section "Done", position 34 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
