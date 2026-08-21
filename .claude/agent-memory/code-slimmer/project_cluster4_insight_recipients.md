---
name: cluster4-insight-recipients
description: Results of the 2026-08-21 insight/ + recipients/ sweep — the RecipientPreferenceDB migration was clean in app/, residue is in scripts/; the real find is an inert settings weight editor
metadata:
  type: project
---

Cluster 4 (`backend/app/insight/` 290 loc, `backend/app/recipients/` 598 loc)
swept 2026-08-21, both read in full. **Swept together deliberately** —
`SignalContributionDB` is declared in `recipients/db_models.py` and driven from
`insight/signals.py`; sweeping either alone yields a false positive.

## The premise that was wrong — settle this, do not re-investigate

`RecipientPreferenceDB` and `PreferenceUpdateLogDB` **do not exist in any
Python in this repo.** Not retired-in-name-only. A repo-wide grep for both
class names plus `recipient_preferences` / `preference_update_logs` returns
zero hits under `backend/app/`. There is no half-migrated read and no second
source of truth. `SignalContributionDB` is unambiguously authoritative: one
writer (`record_contribution`, `insight/signals.py`), many readers
(`insight/signals` ×3, `insight/service` dedup, `frontend/router.py` ×8,
`audience/service.py`, `decision/strategies/recipient_top_score.py`).

**Why this matters:** two earlier sweeps cited evidence pointing the other way
and both citations were misreadings. Correcting them so nobody re-runs it:
- Cluster 3 read `recipients/db_models.py:71-72` as indexing "a live preference
  table". Those are `SignalContributionDB.recipient_id` / `.category_id`.
- Cluster 1 read `frontend/router.py:2503-2504` as computing
  `AVG(PreferenceUpdateLogDB.delta)`. It only *reads* dict keys named
  `avg_delta` / `total_delta`; the real aggregate is
  `func.avg(SignalContributionDB.base_weight)` at `:2291`. **The fossil is the
  variable naming, not the query.** `docs/backlog.md:83` still names the dead
  class — a stale reference a human should correct.
- `docs/backlog.md:250` added a unique constraint to `RecipientPreferenceDB` on
  2026-07-12; the table was dropped 2026-07-15 (`:208`), taking it with it.

**Residue location is inverted from Cluster 2.** Cluster 2 found app columns
kept alive only by seed SQL. Here the app is clean and `backend/scripts/` is
stale.

## Real and reported 2026-08-21 (not actioned, not in docs/backlog.md)

- **The Settings signal-*weight* editor is inert.** `insight/service.py:92`
  reads the module-level `CONTRIBUTION_WEIGHTS`, not `get_signal_weights(db)`.
  Both callers of `record_contribution` pass `base_weight` explicitly, so the
  config-fallback branch (`signals.py:75-82`) has no in-app caller and the
  stored override reaches nothing. Half-lives *do* work (read-time, via
  `_configured_half_lives`). This contradicts the Done claim at
  `docs/backlog.md:206` — whose verification note tested only the half-life
  case. `settings.html:59-60` tells the user weight changes apply immediately.
  3-loc fix. **Highest-value item in the cluster.**
  Inherent limitation to state, not fix: weights freeze into `base_weight` at
  write time, half-lives apply on read. ADR-132 §1 only promises the decay
  constant is re-derivable.
- **`open` events write zero-weight contribution rows.** `open` is in
  `_CONTENT_TIED_EVENT_TYPES` with weight 0.0; `apply_event_to_signals` does not
  short-circuit. `providers/service.py:182-185` has a comment assuming it does.
  Fills the log ADR-132 §4 wants bounded.
- **`backend/scripts/reset_poc_data.sql`** — 121 loc, self-declared incomplete
  draft, zero references anywhere, DELETEs/INSERTs against both dropped tables
  so it aborts on line 15. Superseded by `reset_all_data.sql`. **Genuinely dead
  file.**
- **Unused `UniqueConstraint` import** at `recipients/db_models.py:1` — the
  fossil of the dropped table's constraint. File has no `__table_args__`.
- **`scripts/reset_all_data.sql:163-166`** — stale comment naming
  `PreferenceUpdateLogDB.event_id` as NOT NULL; the successor column
  `SignalContributionDB.event_id` is deliberately nullable.
- **No unique constraint behind the contribution dedup key.**
  `insight/service.py:138-148` is check-then-insert on
  `(recipient_id, category_id, event_id)`. `docs/backlog.md:282` fixed *which*
  columns identify a duplicate, at app level only. The precedent is four lines
  away: `insight/db_models.py:22-26` calls its unique constraint a "safety net
  behind the application-level duplicate check".
- **Two missing FK indexes:** `engagement_events.delivery_execution_id` and
  `signal_contributions.event_id` (a `ForeignKey` does not create an index).
  Every other FK in both modules has `index=True`.
- **`detect_consent_drift` N+1** — loads all of `consent_sync_logs`, then one
  `RecipientDB` query per recipient. No UI, no test.
- **`apply_event_to_signals` commits once per category** (`record_contribution`
  commits internally) — a mid-loop failure leaves an event partially applied,
  and the dedup guard makes the retry produce a different signal.
- **`_configured_half_lives` hits `app_config` on every signal read** — bundle
  into P2-04, do not raise alone. Do NOT copy `_load_brand_css`'s bare
  `lru_cache`; it would break the Settings page.
- **"Preference" vocabulary outlived the model** — `RecipientPreference*`,
  `create_recipient_preference`, `PreferenceUpdateResult.applied_deltas`, the
  `/preferences` routes. Renaming routes/response models is an ADR-142 break;
  only internal names are fair game. Lowest-value item.

## Decide, don't delete (Cluster 2 R5 shape)

- **`CONTRIBUTION_WEIGHTS["unsubscribe"]` / `HALF_LIFE_DAYS["unsubscribe"]`** —
  no producer anywhere; `insight/service.py:15-16` says unsubscribe is handled
  on the consent path by design. But `settings.html` renders a row per weight
  key, so an admin can edit a weight that can never fire. **Direct tension with
  ADR-132 §3**, whose Decision table lists `unsubscribe` as a contribution type.
- **`ConsentSyncLogDB.applied`** — hardcoded `True` at its only writer; no path
  produces `False`.
- **`suppress_recipient`'s `reason` parameter** — accepted, never used, passed
  by its one caller. It is the signature stub for `docs/backlog.md:186`
  (suppression + opt-out reason model). Do not delete.
- **ADR-132 §4 retention window / DWH export** — unimplemented, but **already
  `docs/backlog.md:81`**. Not a new finding.

## Confirmed live / intentional, never flag

- **All 3 `/insight` routes and all 8 `/recipients` routes.** ADR-142 public
  surface. `detect_consent_drift` and `list_consent_sync_logs` have no UI at
  all — an API-surface fact, not death.
- **`recipients/router.py` route ordering is correct** and its comment is
  accurate. Do not sort this router.
- **The `recipients` ⇄ `insight` cycle is real.** `insight/signals.py:19`
  imports `recipients.db_models` at module level, so `recipients/service.py:259,
  282` import `insight.signals` function-locally. Same class as Cluster 2's
  campaigns/overrides cycle, not Cluster 1's style choice.
- **`SignalContributionDB` living in `recipients/`** — documented quirk with
  change-impact notes on both module pages.
- **`validate_recipient_attributes`'s 14-substring deny-list** — ADR-126
  enforcement, argued in the comment.
- **`ConsentSyncLogDB.external_id` denormalization** — deliberate, commented.
- **`EngagementEventDB.occurred_at` vs `created_at`** — decay basis vs record
  time, not duplication.
- **`uq_engagement_events_provider_event`'s NULL behaviour** — Postgres
  confirmed, guards only provider-sourced rows, exactly as commented.
- **The ten `# noqa: F401` imports in `tests/test_signals.py:29-38`** — they
  register table metadata so the FK resolves when the file runs alone.
  Deleting them makes the suite order-dependent.
- **`providers/service.py:100-139` `_primary_content_id_for_delivery`** guessing
  one primary content record — **already `docs/backlog.md:35`**, P2. Largest
  correctness risk touching `insight/`, already logged.

## Method notes that paid off

- When a sweep brief asserts a table was dropped, **grep the class name across
  `backend/` first and settle it in one command** before reasoning from earlier
  reports. Two prior sweeps' "counter-evidence" was variable naming.
- Trace a config value end to end — key → setter → getter → **the line that
  actually uses it at write time**. `get_signal_weights` had two readers and
  neither was a writer of anything. Grepping the getter name alone would have
  said "live".
- For partial-migration residue, grep `backend/scripts/` **separately**: a
  stale `.sql` with zero references is invisible to any app-level sweep.

Related: [[seams-do-not-flag]], [[backlog-already-logged]],
[[cluster2-overrides-campaigns]], [[cluster3-content-rendering]],
[[review-only-never-edit]]
