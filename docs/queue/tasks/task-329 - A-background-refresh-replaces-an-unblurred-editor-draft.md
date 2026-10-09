---
id: TASK-329
title: A background refresh replaces an unblurred editor draft
status: To Do
assignee: []
created_date: '2026-10-09 14:24'
updated_date: '2026-10-09 14:34'
labels:
  - frontend
dependencies: []
type: bug
ordinal: 100300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Severity: moderate (P2). Reachable today. An unsaved local field edit disappears when the server value changes, before any optimistic write check or explicit discard confirmation.

Evidence: frontend/src/components/EditorFields.tsx:32-33 creates local draft state then unconditionally replaces it whenever the value prop changes. frontend/src/main.tsx:21-25 enables query refetch on window focus. frontend/src/screens/ContentDetail.tsx:51 reads the record query and :111-115 passes fetched values into AutosaveField. The same component is used in the composer.

Deterministic proof: /private/tmp/tarrow-client-probe/draft-loss.test.tsx renders the real component with the existing Vitest/jsdom/Testing Library stack. Focus the title, type “My unsaved draft” without blurring, then rerender with another manager's newly saved server value. The input changes to that server value; onSave was never called. Command from frontend: node_modules/.bin/vitest run --config /private/tmp/tarrow-client-probe/vite.config.mjs --configLoader runner. The focused assertion passed. It proves prop-refresh loss; a live browser focus/refetch sequence was not run.

Duplicate check: backlog search for autosave/draft/focus and searches of all open/completed tasks and interview-prep. Completed task-110 and the cef16bf explicit “Load their version” fix cover stale writes and deliberate discard after 409. They do not cover involuntary draft replacement during a read refresh. ADR-180 governs edit conflict behavior; the save-on-blur choice is the Campaign Write Surface final design pass. No fix is proposed here; this is pre-stage evidence, not accepted work.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: promoted from ChatGPT's pre-stage (draft-1, found while preparing the interview questions, docs/queue/docs doc-8) by the user's decision, ordered by severity. Claude verified the core evidence against the code the same day: frontend/src/components/EditorFields.tsx:32-33: useEffect(() => setDraft(value), [value]) replaces the local draft whenever the server value changes, focused or not; refetchOnWindowFocus is on (frontend/src/main.tsx:24).
<!-- SECTION:NOTES:END -->
