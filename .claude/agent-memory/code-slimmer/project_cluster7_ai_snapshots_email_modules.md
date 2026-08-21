---
name: cluster7-ai-snapshots-email-modules
description: Cluster 7 sweep — AI-optional boot is definitively NOT a property; residue is one template dropdown; the ai/ seam surfaces that must never be flagged
metadata:
  type: project
---

Swept 2026-08-21. `backend/app/ai/` (746 loc) + `snapshots/` (253) + `email_modules/` (156), all read in full. Report delivered to the session scratchpad, not appended to `docs/architecture/code-slimmer-report.md`.

**Result:** zero unused imports, zero dead functions, zero dead routes, zero orphaned columns, no orphaned schema behind seed SQL. `snapshots/` and `email_modules/` produced no dead code at all. The one piece of genuine residue is in a *template*: `campaign_detail.html:315-317` hardcodes three module-type options after the `list_manifests()` loop; `content_card` has no manifest and renders nothing (`scripts/reset_all_data.sql:147` already records that fix being applied to seed data).

## Settled: AI-optional boot is NOT a requirement — do not re-open

Cluster 1's open call A is answered **no**, with four independent proofs:
- There is **no `anthropic` package anywhere** — `adapters/claude.py:25` uses raw `httpx` against `api.anthropic.com`. Nothing to make optional.
- `main.py:121` imports `app.ai.db_models` at module scope for `create_all`.
- The boot chain is unconditional and module-level: `main.py:145` → `frontend/router.py:28` → `settings/service.py:10` → `ai/adapters/factory.py:10` → `claude.py:25` → `httpx`. The 14 lazy imports in `frontend/router.py` protect nothing that `:28` has not already loaded.
- The factory degrades at **runtime**, correctly: mock default, `ValueError` only on an ungovernable name, missing key handled in `generate`/`count_input_tokens`.

**How to apply:** the 14 lazy imports can be hoisted; no cycle exists (verified the full graph, not just the leaf claim). Do not re-derive this. Corollary worth carrying: the `httpx2` pin in `requirements.txt` is a **boot-blocker**, not a delivery-only bug, because `settings/service.py:10` pulls `httpx` in at startup.

## Confirmed intentional in these three modules — never flag

- `MockAIProvider` and its `canned_response`/`fail` params — deliberate default (ADR-143); its docstring says "not scaffolding to delete later". `imitate_requested_format` (36 loc) is what makes the mock exercise the real parser; `test_ai_subject_task.py:52-71` depends on it.
- `ClaudeProvider.thinking` — always False in `app/`, a written cost-cap decision with a stated future trigger.
- `AIProvider`/`AIResult`/`AIUsage`/`TokenCountUnavailable` — the seam contract.
- `AIRunDB.target_type`/`target_id` written generically, read as if always "variant" — correct today, the seam for ADR-141's second task.
- `SnapshotDB.html_storage_type` always "file" — documented extension point, `docs/backlog.md:158` owns the decision.
- `ModuleManifest.description`, all `/snapshots` and `/email-modules` routes — ADR-142 public surface.
- The four 0-byte `__init__.py` files are package markers, **not** the `providers/adapters/mock.py` case.
- `tokens_used` excluding free providers is deliberate and reasoned in-source.

## What the sweep actually found (open, not yet triaged)

Ledger/gate arithmetic, not architecture: `run_task:207-213` drops `result.usage` on the error branch, so a Claude refusal (HTTP 200 with real billed input tokens) records 0/0; and the gate at `:187-203` never checks `is_billable`, so mock runs are refused once real spend fills the cap. Plus two missing constraints (`ai_prompts` has no uniqueness despite a documented "one published version" invariant; `snapshots.variant_id` unindexed).

**There is no `tests/test_ai_service.py`** — the four AI test files cover adapters, pricing and the parser. `run_task`, the gate, the audit rows and the ledger are untested. That is why `ai/` cleared its interview 8/8 and still had findings.

## Doc gaps

No `docs/architecture/Code/ai.md` (second module without a page, after `auth`). `snapshots.md` and `email_modules.md` are accurate — a change from Clusters 4 and 6, where the pages were stale.

Related: [[seams-do-not-flag]], [[cluster1-frontend-templates]], [[cluster3-content-rendering]], [[cluster5-audience-decision]], [[backlog-already-logged]]
