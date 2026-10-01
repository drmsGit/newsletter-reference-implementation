---
id: TASK-234
title: >-
  A recipient-independent decision strategy is executed once per recipient per
  send
status: To Do
assignee: []
created_date: '2026-09-29 18:29'
updated_date: '2026-10-01 20:54'
labels:
  - backend
dependencies: []
priority: p3
type: chore
ordinal: 304200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Chore] — found 2026-09-29 while measuring task-11's candidate indexes, and it is why one of them was refused.** `top_score` declares `requires_recipient=False` (`backend/app/decision/strategies/top_score.py`): its answer depends on the slot, the brand and the catalogue, never on who is receiving. But the send loop calls `execute_decision_slot(db, slot.id, recipient_id=...)` for every execution (`backend/app/delivery/service.py:820`), and `execute_decision_slot` runs `strategy.execute` **before** it discovers the result is shared — it only then maps the recipient to `None` (`effective_recipient_id`, `backend/app/decision/service.py:71`) and looks up the one shared resolution row. So the strategy's query — a join of `content_records` and `content_category_assignments` with a sort — runs once per recipient per slot, and returns the same answer every time.

**Why it surfaced as an index question.** task-11 measured `content_category_assignments (category_id)` at 0.201 ms → 0.029 ms with no buffer saving, on a structural table that stays small. That is nothing once per send and real once per recipient: 0.2 ms × 500,000 recipients is about 100 s of identical queries per slot per send. **An index would have hidden the multiplier rather than removed it**, which is why migration 0023 records the candidate as refused and points here.

**Shape of the fix, not decided:** resolve a recipient-independent slot once per send and reuse the result for every recipient in it — a per-send cache keyed by slot, or resolving such slots before the recipient loop. Must keep the existing semantics that a shared resolution row is updated in place rather than duplicated (`decision/service.py:91`), and must not change when a personalised strategy (`requires_recipient=True`) is evaluated. **Unverified:** whether any other strategy with `requires_recipient=False` has side effects per call that callers rely on.
<!-- SECTION:DESCRIPTION:END -->
