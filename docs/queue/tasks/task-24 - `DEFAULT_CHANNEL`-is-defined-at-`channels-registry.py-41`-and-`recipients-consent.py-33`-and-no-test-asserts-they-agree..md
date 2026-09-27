---
id: TASK-24
title: >-
  `DEFAULT_CHANNEL` is defined at `channels/registry.py:41` and
  `recipients/consent.py:33`, and no test asserts they agree.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
priority: p3
type: bug
ordinal: 102400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P3, one line. Two constants that must move together, and nothing notices if only one does.** **`DEFAULT_CHANNEL` is defined at `channels/registry.py:41` and `recipients/consent.py:33`, and no test asserts they agree.** The duplication is deliberate and stays — the consent constant is the default *cell* in `(recipient, brand, channel, purpose)`, the registry constant is the fallback a composition caller gets, and collapsing them would make the addressability layer import the composition registry, which the channels module's zero-intra-app-imports position exists to prevent. **What is missing is the assertion that two independent decisions currently reach the same answer**, which is the true statement and does not couple the modules. They must change together if push ever becomes a default anywhere. Source: [[Interview Prep - Channels, Audit]] → A-Q7.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 84, section "Bugs", position 24 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
