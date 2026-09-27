---
id: TASK-196
title: >-
  The AI suggestion UI withholds what the system already knows: truncation, and
  lost options.
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
  - frontend
dependencies: []
type: bug
ordinal: 506000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug] — low severity.** **The AI suggestion UI withholds what the system already knows: truncation, and lost options.** Surfaced 2026-08-02 (`/interview-review`, AI Q8). Both underlying paths are handled correctly — a `max_tokens` stop is recorded in the audit row as "output hit its ceiling and is truncated" (`service.py:223-227`), and `parse_options` degrades to fewer options rather than raising (`subject_preheader.py:74-98`). **Neither reaches the manager.** (1) The campaign page renders the parsed options and the token count, but not the truncation message — so a manager sees three suggestions with no sign the third may be cut off mid-sentence, and applies one to a real campaign. (2) If the model returns two well-formed options instead of three, two are shown and nothing says one was lost. **Filed as a Bug rather than a Feature because in both cases the information exists and is deliberately withheld from the person acting on it** — the fix is to surface `AIRunDB.message` alongside the options, and to note when fewer options parsed than the prompt requested. Low severity: a truncated *subject line* is short enough that a manager would probably notice, and nothing is committed without a human clicking "Use this". Source: [[Interview Prep - AI]] → AI Layer Q8. **DONE 2026-09-13** in `9d3242d`. `campaign_detail.html:122-132` renders an `ai_notices` block covering both halves — a truncated output, and fewer options than were asked for. It sits **outside** the `ai_suggestions` block deliberately, because a truncation that left nothing parseable still has to be said; putting it inside would have hidden the notice in exactly the worst case.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 623, section "Done", position 60 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
