---
id: TASK-258
title: 'The variant editor, catalogue fields and overrides (slice 6)'
status: To Do
assignee: []
created_date: '2026-10-03 18:27'
labels:
  - frontend
dependencies: []
documentation:
  - >-
    docs/architecture/interview-prep/Campaign Write Surface - final design
    pass.md
type: feature
ordinal: 200058
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Slice 6 of [[Campaign Write Surface - final design pass]], the client half, after its backend tasks. ADR-178 in the composer: a catalogue-bound module shows its record's fields, and typing edits the record (point 1); "Override here" converts one field, which then shows the catalogue value it covers (points 2, 4); reset per field, and per module with a confirmation (point 6); a passive count of unsent campaigns using the record, clickable to the list, no owner names (point 8, task-224); an optional reason as presets with free text behind Other (point 9; user 2026-10-03: "Shorter for this send", "Different tone for this audience", "Out of date for this campaign", "Legal or compliance", Other); no outcome_delta (point 10); none of it on a slot-bound module (point 5). Plus D5 (user 2026-10-03): "changed since last published — sends still use version N" with one-click Publish. And binding an unbound catalogue module to a record, by searching the content list.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A catalogue-bound module shows its record's fields; editing one saves to the record on blur with its version
- [ ] #2 Override here converts one field; the covered catalogue value stays visible; typing saves the override with the module version
- [ ] #3 Reset one field, and reset the module after a confirmation
- [ ] #4 The unsent-campaign count is shown beside catalogue fields and opens the list
- [ ] #5 An unpublished edit is said, with a Publish button
- [ ] #6 An unbound catalogue module can be bound to a record found by title
- [ ] #7 A reason can be given as a preset or Other text
<!-- AC:END -->
