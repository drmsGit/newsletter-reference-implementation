---
id: TASK-329
title: A background refresh replaces an unblurred editor draft
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 14:24'
updated_date: '2026-10-09 17:15'
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

2026-10-09, fixed (commit 7a56adc). Verified the entry first: frontend/src/components/EditorFields.tsx:33 replaced the draft whenever the value prop changed.

Found while designing the fix: saves read the record version from the query cache at send time (frontend/src/api/resources.ts:985, useSaveContentRecord). Merely keeping the draft would therefore let the blur save carry the refreshed version and silently overwrite the other manager's change, the stale write task-110 guards against.

Decided with the user 2026-10-09 (recommended option, refined by the user): keep the typing and say so. Because the case is rare, leaving the field must not save over theirs; the manager checks and chooses.

The user asked whether the existing "someone is working on this" notice already covers this. It does not: the Fence notice (frontend/src/screens/Fence.tsx:41) exists only in the variant editor. It appears only once the other person's edit has landed, so whoever was already typing never saw it. Content records, audiences, slot settings and catalogue modules have no such notice. Governing record: ADR-180 (a person is told, not blocked), plus the save-on-blur choice in the Campaign Write Surface final design pass. No new ADR; logged in docs/playbook-strategy.md section 5 (2026-10-09).

What changed, AutosaveField only:
- It keeps base, the stored value the draft started from, adjusted during render rather than in an effect.
- The draft follows a new stored value when nobody has typed (draft === base), or when the new value equals the draft (its own save coming back).
- Otherwise there is a conflict. The typing stays, and a notice (role=alert) shows their value. Blur saves nothing.
  - "Save mine" acknowledges theirs and saves the draft, so it knowingly overwrites.
  - "Use theirs" takes their value.
- The task-261 onLeave hand-off still runs before the conflict check, since it writes to the catalogue rather than over theirs.
- "Load their version" after a 409 is unaffected: it remounts the page (ContentDetail.tsx generation key).

Tests: frontend/src/components/EditorFields.test.tsx, six tests; five failed on the old code. The sixth, an untouched field follows the stored value, pins existing behaviour.

Mutation check: all four mutations are caught.
- With the blur conflict guard removed, 1 test fails.
- With the old always-follow sync, 5 fail.
- Without the own-save-returns clause, 3 fail.
- Without Save mine acknowledging theirs, 1 fails.

Full vitest: 233 passed. tsc and eslint clean.

Live browser check NOT done yet: the browser pane was signed out, and reading a sign-in address from the users table or the transcript was refused by the permission classifier. Pending a sign-in by the user in the pane.

2026-10-09 live check, browser pane signed in by Claude with the user's go-ahead, scratch content record 120 'task-329 scratch'.
- Typed 'My unsaved draft' into Title without leaving the field.
- Changed the title to 'Their new title' through the API, as a second manager.
- Fired the app's real refetch-on-focus path. The pane was hidden, so visibilityState was forced to visible and visibilitychange dispatched on window, where TanStack Query listens.

Result:
- The heading refetched to 'Their new title'.
- The field kept 'My unsaved draft' and stayed focused, and the notice with Save mine / Use theirs appeared.
- Clicking outside the field left the stored title as 'Their new title' (nothing saved).
- Save mine stored 'My unsaved draft', and the notice went away.

CI green on 7a56adc.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A background refresh no longer replaces what a manager is typing. AutosaveField remembers the stored value its draft started from. An untouched field still follows the stored value, and its own save still settles it. When someone else's value arrives under typing, the typing stays, a notice shows their value, and leaving the field saves nothing; the manager chooses Save mine or Use theirs (decided with the user 2026-10-09, in line with ADR-180, logged in the playbook). Verified by six new tests in EditorFields.test.tsx (five failed first, four mutations all caught), the full vitest suite (233), tsc, eslint, green CI on 7a56adc, and a live check on scratch record 120.
<!-- SECTION:FINAL_SUMMARY:END -->
