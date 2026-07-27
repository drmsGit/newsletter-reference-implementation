---
type: code-module
module: audience
topic:
  - architecture
  - audience
created: 2026-07-27
modified: 2026-07-27
---

# audience

> Part of [[MOC - System Overview]]. Architecture rationale: [[MOC - Newsletter Architecture]] (audience/segmentation).

## Purpose

The audience module owns **who a campaign goes to** — audience groups built from
**live rule blocks** plus **manual pins**, resolved on demand into a
consent-gated recipient list. A group is not a frozen member list: it's
`((∪ include blocks) − (∪ exclude blocks)) ∪ (manual pins)`, always re-gated to
consenting recipients. It also owns **content-driven suggestions** — reading a
campaign's content categories to propose targeting blocks a manager can edit.
Engagement-driven targeting is deliberately **parked** behind the automation
workstream.

## Key files
- `backend/app/audience/db_models.py` — `AudienceGroupDB`, `AudienceGroupMemberDB`, `AudienceRuleBlockDB`
- `backend/app/audience/service.py` — `resolve_audience`, criteria search, rule blocks, suggestion/recalculate
- `backend/app/audience/router.py` — the `/api/audience-groups/*` JSON endpoints (note the `/api` prefix)

## Public surface
**Service functions** (`audience/service.py`, selected):
- `resolve_audience(db, group_id)` — **the entry point [[delivery]] calls**: the group's live, consent-gated recipient list
- `list_groups` / `create_group` / `update_group` / `delete_group`
- `list_blocks` / `add_block` / `update_block` / `delete_block` — include/exclude rule blocks
- `find_by_criteria` / `count_for_criteria` — evaluate a criteria payload (language × status × category × min-score) to recipients
- `add_member` / `remove_member` / `get_member_recipient_ids` — manual pins
- `suggest_include_blocks_for_campaign` / `create_suggested_group_for_campaign` / `recalculate_suggested_blocks` — content-driven suggestion (use case 1)

**Routes** (`/api/audience-groups`, tag `audience`): 8 JSON routes — group CRUD + members. (The rich rule-block/suggest UI is driven from [[frontend]].)

## Data model
*Three tables, all owned here.*
- **`audience_groups`** (`AudienceGroupDB`) — name (case-insensitive unique), `source_campaign_id` (set when seeded by "Suggest audience", enables Recalculate).
- **`audience_group_members`** (`AudienceGroupMemberDB`) — **manual pins**; unique `(group, recipient)`.
- **`audience_rule_blocks`** (`AudienceRuleBlockDB`) — `kind` (include/exclude), `criteria` (JSON, same keys as `find_by_criteria`), `source` (manual/suggested).

## Depends on →
- [[recipients]] — resolves + consent-gates recipients (imports `CONSENTING_STATUS`)
- [[content]] — reads content→category assignments to score/suggest
- [[campaigns]] — reads a campaign's content to suggest blocks; `source_campaign_id` FKs a campaign
- [[insight]] — criteria min-score uses live per-category signals

## Depended on by →
- [[delivery]] — `resolve_audience` materializes a send's recipients (and re-resolves for `"rerun"` sends)
- [[frontend]] — the audience-groups UI (rule blocks, suggestions, net-audience preview)

## Invariants & decisions
- **Live rule model, not a frozen list.** Groups re-resolve from blocks every time — a later rule edit changes future sends (unless a send froze its executions). [[delivery]] chooses freeze vs. rerun.
- **Precedence (2026-07-26):** `((includes) − (excludes)) ∪ (pins)`, then consent floor. **A manual pin is always included** — excludes never remove a pin. The **only** exception is the consent floor: a non-consenting recipient is dropped even if pinned.
- **Consent floor is non-negotiable** — hard suppression (bounces/opt-outs) belongs here, not in a regular exclude block.
- **Suggested blocks stay editable/deletable** (same trust model as [[overrides]]); Recalculate is delta-only and preserves manager-tuned thresholds.
- **Audience intelligence is derived, not authoritative** ([[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]]).
- **Engagement-driven use cases are parked** behind [[MOC - Automation Architecture|automation]]; don't propose them as immediate next work.

## ⚠️ Change-impact — if you touch this, also check…
- **`resolve_audience`'s precedence** → [[delivery]] `prepare_send_from_audience` and `reconcile_executions_to_audience` both call it; changing pin/exclude/consent order changes *who gets emailed*. This exact order was a fixed bug (excludes silently dropping pins).
- **The `criteria` JSON keys** → shared by `find_by_criteria`, rule blocks, and the frontend preview; adding a key means updating all three.
- **`source_campaign_id`** → a live-DB `ALTER` was needed to add it; `audience.service` importing it means `app.campaigns.db_models` must also be registered (fine in-app; isolated scripts must import it).
- **The consent floor** → depends on [[recipients]] `CONSENTING_STATUS`; keep it aligned.
