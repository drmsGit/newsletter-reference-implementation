---
id: TASK-385
title: >-
  A text with a leading or trailing space shows a false
  somebody-else-changed-this conflict
status: Done
assignee:
  - '@claude'
created_date: '2026-10-16 14:09'
updated_date: '2026-10-16 14:55'
labels:
  - frontend
dependencies: []
type: bug
ordinal: 100300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug]** Found in the live check of task-365 on 2026-10-16. An editor field that saves on blur shows "Somebody else changed this while you were typing" when nobody did, whenever the typed text starts or ends with a space.

How it happens. `AutosaveField` (`frontend/src/components/EditorFields.tsx`) keeps a draft and the stored value it started from (`base`). The server trims envelope text before storing it (`set_envelope_fields` in `backend/app/campaigns/service.py`, "Trimmed here rather than by each caller", task-250), so typing " here is your news" and leaving the field stores "here is your news". When the saved value comes back it differs from the draft (leading space) and from the old base, so the field's own rule (`value !== base && (draft === base || draft === value)` fails) reads it as someone else's change and shows the conflict with "Save mine" / "Use theirs". Reproduced on the subject line of a scratch variant. Module fields trim too (`update_module` stores `value.trim() ? value : null` from the client, which keeps spaces, but the envelope does not).

Why it matters. It tells a manager that a colleague edited their text, which is false and alarming (ADR-180: a person is told, not blocked, and what they are told must be true); "Save mine" then saves the untrimmed text, which the server trims again, and the notice can come back.

Fix to decide in its final-design pass: treat a stored value that equals the draft trimmed as the field's own save (compare trimmed), or trim the draft in the client before saving. Check every caller of `AutosaveField` that the server trims (envelope, content fields, module data), and add a test that types a leading space and leaves the field.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Typing a text with surrounding spaces and leaving the field shows no conflict
- [x] #2 A real change by someone else while typing still shows the conflict
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Fixed 2026-10-16 (commit 1cf951f) in AutosaveField (frontend/src/components/EditorFields.tsx): a returned value equal to the draft apart from surrounding spaces is the field's own save. Chosen over trimming in the client because the server already decides what it keeps (the envelope trims, content keeps some text as written) and the field only has to recognise its own text. Test frontend/src/components/EditorFields.trim.test.tsx: a trimming store takes the text back without a conflict, a real overwrite still shows it; failed first. Mutations: ignoring the trim and taking every value as ours, both caught; trimming only the draft is equivalent while every trimming store returns trimmed text. Live check on the scratch variant: a changed subject typed with surrounding spaces saves with no conflict and the field shows it as stored. vitest 319, pytest 2063, tsc, eslint; CI green on 1cf951f.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A text typed with surrounding spaces no longer shows a false somebody-else-changed-this conflict: the field recognises its own trimmed save, while a real change by someone else still shows. Verified by a failing-first test, mutation checks, a live check and CI on 1cf951f.
<!-- SECTION:FINAL_SUMMARY:END -->
