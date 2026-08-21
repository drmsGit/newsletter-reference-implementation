---
name: cluster5-audience-decision
description: Results of the 2026-08-21 audience/ + decision/ sweep — the frozen-list-vs-rule-block premise was wrong (they coexist), and ADR-084 settles Cluster 2's max_results question
metadata:
  type: project
---

Cluster 5 (`backend/app/audience/` 672 loc, `backend/app/decision/` 561 loc)
swept 2026-08-21, both read in full. **No dead code in either module.** All 22
audience service functions, all 8 `/api/audience-groups` routes, both
`/decision` routes, both strategies and every `base.py` symbol are reachable.
Zero unused imports.

## The premise that was wrong — settle this, do not re-investigate

**Frozen member lists were NOT superseded by rule blocks. They coexist by
design and both have live writers and readers.**

- `AudienceGroupMemberDB` = the **manual pin** half of the live model.
  Written by `add_member` (UI `frontend/router.py:2769` *and* JSON
  `audience/router.py:56`) and `bulk_add_members` (`frontend/router.py:2827`).
  Read by `get_member_recipient_ids` inside `resolve_audience`.
- `resolve_audience` **needs both**: `(includes − excludes) ∪ pins`, then the
  consent floor.
- **`prepare_send_from_audience`'s `freeze`/`rerun` mode is unrelated** — it
  freezes `DeliveryExecutionDB` rows for one send (ADR-052), never
  `audience_group_members`. Assuming these were the same mechanism is what
  created the premise.
- `docs/backlog.md:71` (A/B split Feature) plans to build **more** on pins:
  *"No new entity needed — reuse the existing pin mechanism."*
- `find_by_criteria` has two live callers and its `exclude_ids` param is passed
  at `frontend/router.py:2799, 2825`.

`docs/architecture/Code/audience.md` omits `bulk_add_members` from its Public
surface list — likely how the residue reading started.

## Confirmed intentional, never flag

- **`top_score.py` / `recipient_top_score.py`** — `pkgutil`-discovered in
  `registry.py:19`, instantiated by `issubclass` inspection, keyed by
  `meta.name`, resolved from the **string** in `DecisionSlotDB.decision_strategy`.
- **`registry.py`'s bare `except Exception` and `importlib.reload`** — both
  deliberate and commented; the reload is the "drop a .py in the directory"
  seam `decision.md` names as a product pillar.
- **`normalize_slot_config`** — no caller in `decision/`; called from
  `campaigns/service.py:302` behind the cycle-breaking lazy import.
- **`random.choice` on score ties** (`recipient_top_score.py:114`) — disclosed
  tie-break per ADR-085, fixed in commit `6b2f402`.
- **`execute_decision_slot`'s consent gate** — belt-and-suspenders; its
  ValueError being swallowed by delivery is `docs/backlog.md` P0-02, already open.
- **`audience/service.py`'s Python email dedupe** — `RecipientDB.email` has no
  unique constraint (deferred decision). Load-bearing, not belt-and-braces.
- **`DEFAULT_CONFIG` in `recipient_top_score.py`** — the `ConfigField` defaults
  reference it, so it is one source of truth, not a duplicate.
- **`AudienceRuleBlockDB.source`** — read by `recalculate_suggested_blocks` and
  the UI badge.
- **No tests exist for `audience/` or `decision/`** — standing risk, not a finding.

## Real and reported 2026-08-21 (not actioned, not in docs/backlog.md)

- **`suggest_include_blocks_for_campaign` computes a `"count"` key no caller
  reads**, at a full audience evaluation each — up to 5 per "Suggest audience"
  and per "Recalculate".
- **`decision_resolutions` (`campaigns/db_models.py:96-106`) has no
  `__table_args__` and no index on any FK** — queried per recipient per slot per
  send from `decision/service.py:65` and `rendering/service.py:317`. The
  missing-constraint gap now reaches the hottest table in the schema. Highest
  value item in the cluster.
- **`_check_type` (`base.py:45-61`) silently accepts anything for an
  unrecognised `ConfigField.type`** — `ok = True` with no `else`. A seam-quality
  defect: the adopter's typo gets no validation despite the docstring promise.
- **`resolve_audience` re-scans the whole recipient table per rule block**, plus
  a settings read and a full contribution scan per block; the group detail page
  then evaluates every block a second time for its count column (folds into
  Cluster 1 #5/#6).
- **`PATCH /api/audience-groups/{id}` nulls `description`** when omitted — binds
  `AudienceGroupCreate`, forwards unconditionally. Same JSON-surface-only drift
  class as Cluster 2's D1/D2.
- **`delete_group` clears members and rule blocks but not
  `SendInstanceDB.audience_group_id`** — its own comment enumerates the FKs and
  misses one. Likely uncaught 500. Unverified.
- **Unused local `added` in `recalculate_suggested_blocks`.**

## ADR-084 settles Cluster 2's open question 3

**ADR-084 is Accepted** and requires multi-result slots plus min items, allowed
*and excluded* categories, content types and fallback content. So
`DecisionSlotDB.max_results` is **not residue and must not be pinned to 1 with
a validator** as Cluster 2 R5 suggested — that would encode a contradiction of
an Accepted ADR. The real gap is that `StrategyResult` holds one
`content_record_id` and `DecisionStrategy.execute` returns `StrategyResult |
None`, so the contract structurally cannot express a multi-pick. Of ADR-084's
six required limits exactly one is implemented (allowed categories, as
`candidate_filter.category_ids`).

## Report drift worth fixing

`docs/architecture/code-slimmer-report.md:376-380, 578` (Cluster 2 Q1) refers to
`resolve_decision`. **No such symbol exists** — it is `execute_decision_slot`
(`decision/service.py:11`). Line numbers are right, symbol name is not.

Method note that paid off: for a "was X superseded by Y" premise, build the
writer/reader table for **both** mechanisms before reading either
implementation, and check whether the supposed successor mode (here `freeze`)
touches the same table at all. It did not.

Related: [[seams-do-not-flag]], [[backlog-already-logged]],
[[cluster2-overrides-campaigns]], [[cluster3-content-rendering]],
[[cluster4-insight-recipients]], [[review-only-never-edit]]
