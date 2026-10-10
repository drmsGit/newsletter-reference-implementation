---
id: TASK-337
title: Audience date pickers do not say their dates are UTC days
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 18:23'
updated_date: '2026-10-10 20:33'
labels:
  - frontend
dependencies: []
type: feature
ordinal: 200750
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** An engagement rule with an absolute date range ("clicked between 1 and 15 September") counts each date as a UTC day: backend/app/audience/service.py:797-801 builds both boundaries from UTC midnights, and 'to' covers its whole day (task-296). The editor shows plain date inputs with no zone (frontend/src/screens/AudienceEngagement.tsx:148-152). For a manager in Berlin the range is shifted by one or two hours at each end, silently.

Decided with the user in the 2026-10-09 interview review (Audience Q2): keep UTC, and say so where the dates are picked. A company time zone setting stays a later idea. A manager's own browser zone was rejected, because the same saved rule would then mean different people depending on who opens it.

Source: [[Interview Prep - Since 2026-09-18]] → Audience history, delivery safety and recipient unsubscribe, Q2.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The engagement date pickers state that dates are UTC days
- [x] #2 The saved rule and its resolution are unchanged
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10, done (commit 5366e90). AudienceEngagement.tsx: the From and To date fields each carry a React Aria description (Text slot=description): 'A UTC day: it starts at midnight UTC.' and 'A UTC day, included to its end.' Screen readers get it through aria-describedby.

Test: in AudienceEditor.test.tsx, 'says the dates are UTC days' uses toHaveAccessibleDescription. It failed first; with the To note removed it fails again.

Checks: vitest 249, tsc, ESLint, CI green on 5366e90.

Live check: audience 'All demo recipients', new rule form, Between two dates. Both notes showed; the form was cancelled and nothing saved.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The audience date pickers now say their dates are UTC days: From 'starts at midnight UTC', To 'included to its end', attached to each field for screen readers too. Saved rules and their resolution are unchanged. Verified by a new frontend test (failed first, mutation caught), the full frontend checks, green CI on 5366e90, and a live look at an unsaved rule form.
<!-- SECTION:FINAL_SUMMARY:END -->
