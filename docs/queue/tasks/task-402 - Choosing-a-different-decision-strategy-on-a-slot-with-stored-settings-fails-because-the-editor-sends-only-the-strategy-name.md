---
id: TASK-402
title: >-
  Choosing a different decision strategy on a slot with stored settings fails,
  because the editor sends only the strategy name
status: To Do
assignee: []
created_date: '2026-10-17 17:34'
labels:
  - frontend
dependencies: []
type: bug
ordinal: 100100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Surfaced 2026-10-17 by the trailer pre-production checks (a side session's results file, docs/design/trailer/PREPRODUCTION-CHECKS.md section 5.2, with section 9 item 4), run on a scratch database; the user asked for the defects to be queued, not fixed there. Re-checked on main (cf3fab0): read in the code, and the refusal reproduced by calling the real validator on the stock strategies.

**What happens.** In the variant editor a decision slot's Strategy select calls `save.mutate({ decision_strategy: name })` and sends nothing else (frontend/src/screens/SlotSettings.tsx:89-91). `useSaveSlot` turns that into a PATCH with only the changed section (frontend/src/api/resources.ts:1756-1782). The PATCH route fills every section the caller did not send from the stored slot (backend/app/campaigns/router.py:970-977), `update_decision_slot` then validates the merged result against the newly chosen strategy (backend/app/campaigns/service.py:989, `_normalize_for_strategy`), and `_normalize_section` rejects every stored key the new strategy does not declare (backend/app/decision/strategies/base.py:64-78). The manager sees: "Not saved: strategy_config has key(s) not declared by this strategy: ['content_score_weight', 'preference_score_weight']. Allowed: (none — this strategy takes no keys here)". The choice does not stick.

**Who it hits.** The two strategies that ship are enough. `recipient_top_score` declares two weights (backend/app/decision/strategies/recipient_top_score.py:40-), `top_score` declares none (top_score.py:32). Calling `normalize_slot_config` with the stored weights of the first and the second as target is refused; the other direction is accepted, because there is nothing stored to reject and the defaults fill in. So on any slot that stores weights, "choose Top Score" cannot be done in the editor. The checks reported that every slot the demo reset builds stores the two weights. A strategy a developer drops in as one file (trailer scene S14) fails the same way on those slots unless the file happens to declare the same two keys; the checks only got it to save by editing the new file to declare `content_score_weight` and `preference_score_weight`, which is the fix in the wrong place.

**The server is not the defect.** The PATCH route's own comment says the refusal "can fire on a section the caller did not send, when the strategy changed underneath it. That is the right answer: the stored config is genuinely invalid for the new strategy" (router.py:988-992), and `update_decision_slot` says "Switching strategies re-derives the structure" (service.py:987-988). The defect is that the editor offers a choice it cannot complete, and gives the manager no way to say what becomes of the old settings. A fix must not loosen the server's validation for a caller that sends a stale key explicitly.

**The narrow send is pinned on purpose, and by a test that cannot see this.** task-264 made a strategy change send only the strategy and killed the mutant "strategy change resending everything" (docs/queue/completed, task-264 notes). frontend/src/screens/SlotSettings.test.tsx:136-142 asserts the body is exactly `{ decision_strategy: 'top_score' }` against a fetch stub whose stored `strategy_config` is `{ preference_score_weight: 10 }` (line 38-39) and which does not enforce declared keys, so the test is green while the real server refuses. A fix changes that test deliberately; the stub should enforce what the server enforces.

**Options, not decided here.** (a) The editor sends the new strategy's shape along with the name: keep the stored keys the new strategy declares, drop the rest, let defaults fill; the same for `candidate_filter` (both stock strategies declare `category_ids`, a dropped one may not). (b) The server, when a PATCH changes `decision_strategy` and the caller did not send `strategy_config` or `candidate_filter`, re-derives both from the new strategy, keeping compatible keys (what the service comment already claims). Whichever is chosen, something the manager tuned is lost on a switch and a switch back finds defaults; the screen should say so, or keep nothing silently. The raw server message names internal keys; TASK-398 (labels, not internal names) is the wider question and not a duplicate.

Not a duplicate: nothing in the queue or in docs/queue/completed names this; task-144 and task-264 built the declaration and the editor and are the context.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Choosing Top Score on a slot that stores the two weights of Recipient Top Score saves, and the slot then shows no weight fields
- [ ] #2 A strategy dropped in as a single file that declares different settings can be chosen on a slot with stored settings, with no edit to that file
- [ ] #3 What becomes of the settings the new strategy does not declare is stated on screen, and a switch back shows what the screen said it would
- [ ] #4 The server still refuses a key the strategy does not declare when a caller sends it explicitly; its validation is not loosened
- [ ] #5 The SlotSettings client test enforces declared keys in its stub, so it fails without the fix, and the fix is mutation-checked
<!-- AC:END -->
