---
type: code-module
module: ai
topic:
  - architecture
  - ai
created: 2026-09-18
modified: 2026-09-18
---

# ai

> Part of [[MOC - System Overview]]. Architecture rationale: [[ADR-140 — AI Capability Layer]], [[ADR-141 — In-App Assistive AI Actions]], [[ADR-144 — AI Data and Model Governance]].

## Purpose

The ai module owns **the whole AI capability layer: a registry of discoverable
tasks, the manager-owned prompts those tasks run, the vendor adapters that call
a model, and the token ledger that governs spend**. It implements ADR-140/141's
split literally — the *developer* owns the scaffold (what a task reads, what
shape it returns, its worst-case output ceiling), the *manager* owns the prompt
(versioned in the DB, published, never mutated). Every AI action writes an
`ai_runs` row, **including refused ones**, so the same table is both the audit
trail (ADR-140 §3) and the cost ledger the cap reads (ADR-144 §5). Nothing here
applies its own output: `run_task` returns a proposal and a run id, and a human
applies it.

## Key files
- `backend/app/ai/service.py` (243) — `run_task` orchestration (prompt → gate → adapter → audit), prompt CRUD, ledger reads
- `backend/app/ai/pricing.py` (57) — model rate table, `is_billable`, `cost_usd`. The money *view*; the cap itself is in tokens
- `backend/app/ai/db_models.py` (72) — `AIPromptDB`, `AIRunDB`
- `backend/app/ai/adapters/base.py` (71) — the `AIProvider` ABC, `AIResult`/`AIUsage`, `TokenCountUnavailable`
- `backend/app/ai/adapters/claude.py` (240) — the one real adapter (Anthropic Messages + count_tokens over `httpx`)
- `backend/app/ai/adapters/mock.py` (149) — zero-cost offline adapter, the DEV default
- `backend/app/ai/adapters/factory.py` (44) — `get_ai_provider`; the **governed** provider list
- `backend/app/ai/tasks/registry.py` (96) — mtime-cached task discovery
- `backend/app/ai/tasks/base.py` (44) — `TaskMeta` / `TaskSetting`: what a task declares about itself
- `backend/app/ai/tasks/subject_preheader.py` (170) — the one shipped task

## Public surface
**Service** (`ai/service.py`):
- `run_task(db, task_key, rendered_prompt, max_output_tokens, ...)` → `TaskRun` — `service.py:144`. **The one entry point that spends money.**
- `publish_prompt(db, task_key, body)` — `service.py:58`. Mints version N+1, unpublishes the old one; never mutates a row.
- `get_published_prompt` / `list_prompt_versions` — `service.py:40`, `:49`
- `tokens_used(db)` — `service.py:89`; `spend_to_date(db)` → `{"usd", "unpriced_runs"}` — `service.py:107`

**Registry** (`ai/tasks/registry.py`): `list_tasks()` — `:75`, `get_task(key)` — `:81`, `get_task_module(key)` — `:87`.

**Adapters**: `get_ai_provider(provider_name, model)` — `adapters/factory.py:23`; `AVAILABLE_AI_PROVIDERS = ("mock", "claude")` — `:20`; `DEFAULT_AI_PROVIDER = "mock"` — `:15`.

**Routes:** *none of its own.* The module ships no router — the surfaces live in [[frontend]]: suggest/apply at `frontend/router.py:1465`, `:1503`, and four settings POSTs at `:286`, `:318`, `:336`, `:349`.

## Data model
*Two tables.*
- **`ai_prompts`** (`AIPromptDB`, `db_models.py:31`) — `task_key` + `version` + `body` + `is_published`. Immutable once published. No DB uniqueness on `(task_key, version)` or on "one published per task"; both are enforced in `publish_prompt` only.
- **`ai_runs`** (`AIRunDB`, `db_models.py:47`) — the ledger *and* the audit trail. `status` ∈ `ok | blocked | error`; `prompt_id` is **nullable on purpose** (a run refused before a prompt was found is still recorded); `output_text` holds the suggestion, which is how it survives the POST-redirect without session state.

Neither table has a hand-written migration in `backend/scripts/` — both come from `create_all()` via the import at `backend/main.py:127`.

## Depends on →
- [[settings]] — `get_ai_provider_name`, `get_ai_spend_cap` at module level; `get_task_model` imported **lazily inside `run_task`** (`service.py:162`) to break a cycle
- [[campaigns]] / [[content]] — the subject task reads `VariantDB`, `ModuleInstanceDB`, `ContentRecordDB`

## Depended on by →
- [[frontend]] — every AI surface (9 call sites)
- [[settings]] — imports `AVAILABLE_AI_PROVIDERS` and `MODEL_PRICING` (the latter doubles as the model allow-list)

## Invariants & decisions
- **The spend cap is a pre-call gate, in tokens, not money** (`service.py:177-211`). Worst case = `count_input_tokens() + max_output_tokens`, checked against what's left. Tokens are computable *before* spending; money is reported alongside but never gates (`pricing.py:1-19`).
- **An unverifiable token count is a refusal.** An adapter that cannot count raises `TokenCountUnavailable` and the run is blocked — "a gate built on an unverified number is not a gate" (`adapters/base.py:13-21`).
- **Two opposite defaults, each conservative for its own question** (`pricing.py:9-19`): billability defaults to *billable*, so an unpriced new paid adapter still consumes the cap; cost defaults to *unknown* (`None`) and surfaces as `unpriced_runs` rather than silently counting as $0.
- **Blocked attempts are audited** — every early-return path writes a `status="blocked"` row (`service.py:167`, `:184`, `:201`).
- **Mock traffic never consumes the budget** (`service.py:97-104`) — after day one most rows were mock.
- **Prompts are immutable once published** (`service.py:72-82`), so an audit row pointing at version 3 always resolves to version 3's text.
- **Truncation is surfaced, not swallowed** — `stop_reason == "max_tokens"` becomes the run's message and reaches the manager as a notice. ADR-144's rule: display is not commit.
- **Extended thinking is OFF by default, as a cost decision** (`adapters/claude.py:89-96`) — `max_tokens` bounds thinking *plus* reply, so a 400-token task could burn its ceiling reasoning.
- **A Claude refusal (HTTP 200, empty content) maps to `success=False`** (`claude.py:175-192`), so the UI doesn't describe a decline as a formatting problem. Adapters never raise on generation failure; errors degrade to `AIResult(success=False)`.
- **Providers are an explicit mapping, deliberately not auto-discovered** (`factory.py:3-7`) — which models a deployment may call is governed (ADR-140's kill switch). **Tasks are the opposite**: auto-discovered.
- **A task does not declare its model.** `TaskMeta` declares key, label, prompt, `max_output_tokens`; the *model* is a manager setting resolved inside `run_task` (`service.py:162`). `settings_fields` is a declared-but-unused extension point.
- **Task discovery is drop-a-file** (`tasks/registry.py:31-55`): a module is a task iff it exposes a module-level `META` that is a `TaskMeta`. Filename exclusion was rejected explicitly so helpers self-exclude; one broken task file is logged and skipped, not fatal. Cache invalidates on max mtime of `*.py` in the directory. This is the **fifth** instance of the pattern — see [[decision]] strategies, [[modules]], [[channels]], [[rendering]] renderers.
- **The PII boundary is real**: the task sends only the campaign's own editorial content, nothing recipient-shaped (`subject_preheader.py:13-16`).
- **Model pricing is a hand-maintained vendor fact** with a verification date in the comment (`pricing.py:22-25`). A stale entry shows a wrong total rather than failing.

## ⚠️ Change-impact — if you touch this, also check…
- **Renaming a `TaskMeta.key` orphans prompt history and every past `ai_runs` row** — the key joins the file, `ai_prompts`, `ai_runs` and the `ai_task_models` settings dict. No FK, no migration path (`tasks/base.py:31-33`).
- **`MODEL_PRICING` is doubling as an allow-list** — adding a model there immediately makes it selectable per task (`settings/service.py:198-207`).
- **Adding an adapter needs two edits**: a branch in `get_ai_provider` *and* a name in `AVAILABLE_AI_PROVIDERS`. Omit the second and the settings form silently refuses to save it.
- **Any new adapter must implement `count_input_tokens` truthfully** — returning an estimate quietly converts the cap from a guarantee into a suggestion.
- **The settings ↔ ai import cycle is load-bearing.** `settings/service.py:10` imports the ai factory at module level; `run_task`'s lazy `get_task_model` import exists for this reason. **Do not hoist it.**
- **`REQUESTED_OPTIONS = 3` and the literal "3" in `DEFAULT_PROMPT` are not linked** (`subject_preheader.py:32-38`) — a manager editing the prompt to ask for 5 leaves the code comparing against 3.
- **`run_task` commits per record** with no `commit=False` option (unlike [[audit]]'s `record`) — calling it inside a larger transaction commits that transaction's in-flight work.
- **`ai_runs` has no retention or pruning**, and `tokens_used`/`spend_to_date` are full-table scans in Python on every settings page load and every run.
- **No SQL migration exists for either table** — a Postgres deployment built from `backend/scripts/migrate_*.sql` alone will not have them.
