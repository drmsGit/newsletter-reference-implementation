---
id: TASK-73
title: "Per-task / per-feature model selection \u2014 the direction ADR-144 \u2014 AI Data and Model Governance \u00a72 already documented, now with concrete reasons to build it."
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 202600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Feature] — Done 2026-09-18, the selection half.** **Per-task / per-feature model selection — the direction [[ADR-144 — AI Data and Model Governance]] §2 already documented, now with concrete reasons to build it.** Surfaced 2026-08-02 (user). Today the model is one global setting (Settings → AI model) plus an `ANTHROPIC_MODEL` environment override, so every task calls the same model. ADR-144 §2 already records **per-task model choice as the documented direction**, with the POC deliberately shipping one model plus a "how to add and connect more models" guide — so this is that build, not a new decision. **Why it now has teeth:** tasks differ enormously in what they need. Subject-line generation from supplied content is not frontier reasoning — Haiku 4.5 runs it at roughly a fifth of Opus 5's price ($1/$5 vs $5/$25 per Mtok), which at fan-out scale is the difference between ~$1,800 and ~$9,100 per campaign (see the Mode-A × decision-slot Needs-ADR item). Content enrichment at ingest, outcome analysis, and copy authoring each sit at a different point on the cost/capability curve, and one global setting forces them all to the most expensive one. **Scope to design:** (a) selection **per AI feature**, not globally — the natural home is beside the prompt, which is already per-task and manager-owned (ADR-140 §4), making "prompt + model" one versioned unit; (b) **multi-vendor, not just multi-model** — the user expects deployments to mix providers (one vendor for creative copy, another for flows/agents), which the `AIProvider` adapter already permits but the single global setting forbids; (c) keep the **governed-list** posture — a per-task choice *within* what the deployment has enabled (ADR-140), never free text; (d) decide whether pricing metadata belongs with the model registry (`app/ai/pricing.py` already holds the rates, so per-task selection would let the spend readout attribute cost **per feature**, which is what makes the cheap-model argument checkable rather than theoretical). **Interaction with prompt versioning worth settling at the same time:** if the model becomes part of a task's configuration, changing it should arguably mint a new prompt version — the same prompt on a different model is a different thing, and an audit row resolving to "prompt v3" should resolve to the model it ran on too. `AIRunDB` already records the model per run, so the history exists; the question is whether the *configuration* should version together. Source: user, 2026-08-02. **Built 2026-09-18** alongside the AI task registry, because the task library is where a per-task choice belongs: each card carries a model select over the governed list, `run_task` resolves the task's model and hands it to the adapter, and unset means the deployment default rather than a frozen copy of today's. **The governed list is `MODEL_PRICING`** — a model the platform cannot price is one whose spend cap cannot be checked before the call, which is ADR-144 §5's whole basis. **Two parts of this entry are NOT built and stay open:** (c) attributing spend per feature in the readout, and the prompt-versioning question — whether changing a task's model should mint a new prompt version, since the same prompt on a different model is arguably a different thing. `AIRunDB` already records the model per run, so the history exists either way.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 222, section "Features", position 26 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
