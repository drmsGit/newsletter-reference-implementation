---
id: TASK-139
title: >-
  Config / settings layer (first slice) — the "future config layer" referenced
  across several items (Insight Q2 score bounds, decision-strategy weights, E1
  AI-governance-as-config, ADR-132's "tunable w…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 500300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Feature]** Config / settings layer (first slice) — the "future config layer" referenced across several items (Insight Q2 score bounds, decision-strategy weights, E1 AI-governance-as-config, ADR-132's "tunable weights/half-lives"). **Done 2026-07-15.** Generic DB-backed `AppConfigDB` (key → JSON value; code holds defaults, a row overrides them) + `app/settings/service.py` typed accessors (`get_signal_weights`/`get_half_lives` merging code defaults). `app/insight/signals.py` now reads weights + decay half-lives from config (lazy import to avoid a cycle), so a change applies immediately to computed signals. A Jinja **Settings** page (`/ui/settings`, nav link) lets an admin/BI person edit per-contribution-type base weights + half-lives; blank = code default. **Deliberate line (answers the "should admins edit the decay formula?" question): only *values/toggles* are editable — the decay *model* (exponential half-life) and scoring *logic* stay in code; a different decay model is a plugin/code change, not a setting** (avoids expression-injection/footgun). Verified live: setting `manual` half-life to 0.001d collapsed Anna's Beach signal 90→0, clearing it restored 90. AI-governance guard toggles (read-only vs write; active on content vs campaigns) slot onto this same `AppConfigDB` once AI capabilities exist to consume them — not built now (they'd be inert). Source: user, 2026-07-15 (settings-area discussion). **⚠️ Correction 2026-08-21:** the weight half of this entry never worked — `apply_event_to_signals` reads the module-level `CONTRIBUTION_WEIGHTS` dict, not the merged config, so only the half-life editor is live. The verification note above exercised only the half-life case. Re-opened as a P2 Bug above (code-slimmer sweep, Cluster 4 C1); this entry stays as written per the archive rule.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 507, section "Done", position 3 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
