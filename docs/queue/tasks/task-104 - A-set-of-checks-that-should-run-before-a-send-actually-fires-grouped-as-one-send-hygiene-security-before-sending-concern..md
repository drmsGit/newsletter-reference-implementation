---
id: TASK-104
title: >-
  A set of checks that should run before a send actually fires, grouped as one
  "send hygiene / security before sending" concern.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-09-27 14:20'
labels:
  - backend
dependencies: []
type: feature
ordinal: 205700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — LOW priority, "pre-send safety net" bundle (park for now).** A set of checks that should run before a send actually fires, grouped as one "send hygiene / security before sending" concern. Not important now (POC default provider is mock; the recipient cap + consent floor + Trigger-send confirm already cover the worst accidents), but capture so they're designed together later. Includes: **(1) deduplication** — collapse duplicate recipients within a send (esp. once multiple include blocks / manual pins overlap; `resolve_audience` already dedupes by id, but cross-source email-level dupes from bad imports aren't caught since `RecipientDB.email` has no unique constraint); **(2) double-send protection across re-plans** — planning the same snapshot+audience twice creates two independent send instances; if both trigger, a recipient receives it twice. Needs either a warn-on-duplicate-plan, or the frequency-capping exclude ("not emailed in last N days", itself parked behind automation); **(3) suppression list** — a hard never-send set (past hard bounces, complaints, manual blocklist) applied as a final filter regardless of audience rules, tied to the inbound bounce/complaint→consent work (see the inbound-adapter Feature). These are the "security before sending" layer the user flagged alongside dedup (2026-07-26). Sequence after the send path is otherwise complete; some pieces (frequency cap, suppression from bounces) depend on the parked automation + inbound work. Source: user, 2026-07-26 (campaign→send link session).
  
  - ✅ **[Feature] — the one plugin family that isn't drop-a-file. Done 2026-09-18.** **AI tasks
  need a registry and a generated settings surface.** Noticed by the user
  2026-09-17 while reading the code. `app/ai/tasks/` holds `__init__.py` and
  `subject_preheader.py` and **no registry** — `frontend/router.py:236` imports
  the task module directly and reads `subject_task.TASK_KEY` /
  `subject_task.DEFAULT_PROMPT`, and `settings.html:177` hardcodes a card
  headed "AI prompt — subject & preheader" bound to singular context keys
  (`ai_prompt_body`, `ai_prompt_version`, `ai_prompt_versions`). So tasks only
  *look* drop-a-file because there is exactly one: adding a second needs the
  new `.py`, an import plus three context keys in the router, **and** a
  duplicated card in the template.

  **The user's framing:** replace the hardcoded settings section with an **AI
  task library** that generates one entry per file in `app/ai/tasks/`, with the
  form shape declared in a template stored alongside the file — "so we would
  have a two files per new task solution". Either one template for all tasks or
  one per task; that is the open question.

  **Four precedents to copy, all with the same `_discover` + mtime shape:**
  `decision/strategies/registry.py`, `modules/registry.py`,
  `channels/registry.py`, `rendering/renderers/registry.py`. And the two-files
  target is already the repo's stated standard — [[ADR-160 — Channel Model and Composition]] point 6 chose "a channel manifest plus a provider adapter — two
  files, no config step", for the reason that applies exactly here: "a third
  pattern that needs registering in several places is the one that eventually
  gets registered in two."

  **Interacts with the parked per-task model selection item**, which proposes
  putting model choice "beside the prompt, which is already per-task and
  manager-owned" — that item assumes a per-task settings surface this one would
  build. Sequence them together. **Not urgent** (user). Source: user,
  2026-09-17.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 326, section "Features", position 57 in that section (top = do next). The description is the original entry, verbatim.

2026-09-27: related — task-201 (required-field check before a send fires) and task-228 (post-render per-recipient 'nothing meaningful' skip, whose reason lands with the exclusion reasons).
<!-- SECTION:NOTES:END -->
