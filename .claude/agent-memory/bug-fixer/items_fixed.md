# Backlog items already implemented

Entries here are done in a worktree branch. If the 🔴 entry is still in
`## Bugs`, that is the un-pruned section, not a second occurrence of the bug —
verify against code before re-implementing.

## Settings signal-weight editor inert (P2, "Corrects a Done claim in this file")

- **Run:** 2026-09-13. First ever bug-fixer run. Outcome: `fixed`.
- **Branch:** `worktree-agent-afd52ccdfdbe71252`. Not committed; left dirty for human review.
- **Entry text verified accurate** against the tree — every cited symbol existed
  and the defect was live. Only drift: the entry cites `recipients/service.py:267`
  for the second `record_contribution` caller; it is actually **:437**. Line
  numbers in this file are hints, confirmed.
- **Fix:** `app/insight/service.py` — `apply_event_to_signals` read the
  module-level `CONTRIBUTION_WEIGHTS` dict at `:92`; now lazily imports
  `get_signal_weights(db)` (mirroring `signals._configured_half_lives` at
  `signals.py:57`) and reads with `.get()` + `raise ValueError`. Dropped
  `CONTRIBUTION_WEIGHTS` from the module-level import, which my change made dead.
- **Shipped in the same change** (the entry required it): `app/templates/settings.html`
  help text no longer claims "Changes apply immediately to computed signals" for
  both editors. Weights are frozen into `base_weight` at write time, so a weight
  change affects only future contributions; a half-life change re-scores the
  whole log on read. **That asymmetry is inherent to ADR-132 §1, not a defect** —
  do not "fix" it later.
- **Test:** `tests/test_signals.py::TestConfigAffectsSignals::test_weight_override_reaches_apply_event_to_signals`.
- The Done-archive entry (Config/settings layer, 2026-07-15) **already carries its
  correction note** ("⚠️ Correction 2026-08-21"). Nothing to append there — and
  `docs/backlog.md` is off limits anyway.

## Webhook signature verification fails open when the secret is absent (P1 security, `docs/backlog.md` line 35)

- **Run:** 2026-09-13 (run 3). Outcome: `fixed`.
- **Branch:** `worktree-agent-a2c2f99fad20b688e`. Left dirty, not committed.
- **Entry was NOT stale.** `providers/adapters/resend.py:65-72` landed exactly —
  second entry in this file whose line numbers still hold (the other is the
  enumeration-oracle one). Both were written by the 2026-08-07 code review;
  that review's line numbers appear to be reliable, unlike older entries.
- **Fix:** `verify_signature()` now returns `False` (+ `logger.error`) when
  `RESEND_WEBHOOK_SECRET` is unset. Two-line behaviour change; the rest of the
  function was already correct (constant-time compare, header presence check).
- **I deliberately added NO dev-bypass flag.** The entry's directive is "fail
  closed"; the "a development bypass must be a deliberate flag" clause
  constrains any bypass, it does not mandate building one. Adding none is the
  strictly conservative reading and needs no naming decision. **If a future run
  is asked to add the flag, that IS a decision** (name, truthy parsing, scope,
  whether it is per-provider) — refuse it unless the human names the flag.
  Precedent if they do: `AUTH_DEV_SHOW_CODE` (`app/auth/service.py:241`) parses
  `{"1","true","yes"}` after strip+lower.
- **The documented local workflow does NOT depend on the fail-open.**
  `docs/how-to-webhooks-engagement.md` step 2 has you copy a real signing secret
  from the Resend dashboard before step 3 sets it. Checked this before changing
  behaviour — that check is what made the flag unnecessary.
- **Doc updates shipped with it** (three files stated the old behaviour verbatim
  and would have misled an operator into an unexplained 401):
  `docs/how-to-webhooks-engagement.md:66`, `docs/architecture/Code/providers.md:59`,
  `docs/architecture/Code/Flow - Engagement to signal.md:55` and `:77`.
  Rule of thumb: prose that *describes the line you changed* is part of the one
  item; anything else is a drive-by.
- **Test:** `backend/tests/test_provider_webhook_signature.py`, 4 cases, no DB
  and no network — pure `monkeypatch` over `os.environ`. Includes a
  correctly-signed positive case so "always return False" cannot pass.
- **Suite:** 161 pass (157 baseline + 4). No DB rows created.

## E1 — hardcoded module-type options in the add-module dropdown (NOT a backlog item; `docs/architecture/code-slimmer-report.md`)

- **Run:** 2026-09-13 (run 4). Outcome: `fixed`.
- **Branch:** `worktree-agent-a52bcd7ea65d0a8c9`. Left dirty, not committed.
- **Source was the code-slimmer report, not `docs/backlog.md`** — first run of that
  shape. The report is 245KB; grep the finding id or a quoted token and read only
  the surrounding ~60 lines. Useful structure: findings are ranked under `## To do`,
  and there is a `## Unverified — the specific checks a human should run` section
  that carries the *preconditions* for the fixes above it. **Read that section for
  your finding before changing anything** — it is where the report parks the
  "check this in the DB first" instructions.
- **Report line numbers landed exactly** (`campaign_detail.html:312-317`,
  edit-form fallback at `:216-222`, `frontend/router.py:699`). This report appears
  as reliable as the 2026-08-07 code review; the older `docs/backlog.md` entries are
  the unreliable ones.
- **Precondition checked and clean:** `SELECT module_type, COUNT(*) FROM
  module_instances GROUP BY 1` → `cta 4, hero 5, img_left 10, img_right 1`. **No
  `content_card` rows in the dev DB**, so removing the option strands nothing.
  If a future run needs DB access: the dev `.env` has **no `DATABASE_URL`** — the
  live value is `database.py`'s own fallback,
  `postgresql://newsletter_user:newsletter_password@localhost:5432/newsletter`,
  and the main venv has **no `python-dotenv`**. Connect with SQLAlchemy against
  that literal URL.
- **Fix:** deleted three hardcoded `<option>` lines (`hero`, `content_card`, `cta`)
  after the `module_templates` loop in the *add*-module `<select>`. `hero`/`cta`
  were duplicates of what `list_manifests()` yields; `content_card` has no manifest
  (`storage/email_modules/` holds cta, hero, img_left, img_right, single_stack).
  The *edit*-module select at `:216-222` was already correct and **was deliberately
  left alone** — its `{% if module.module_type not in types %}` fallback is what
  keeps an orphan row selectable and must not be "tidied" to match.
- **Test:** `backend/tests/test_campaign_module_options.py`, 3 cases, **no DB and no
  network**. Extracts the one add-module `<select>` from the template with a regex,
  renders it standalone via `jinja2.Environment.from_string` against real
  `list_manifests()`, asserts the option values equal the manifest names exactly.
  Re-adding the three lines fails all three. **Template-fragment rendering is a
  cheap, DB-free way to test a Jinja defect — reuse this shape.**
- **Gotcha:** `backend/app/` has **no `__init__.py`**, so `import app; app.__file__`
  is `None` and `Path(app.__file__)` raises `TypeError` at collection. Anchor
  template paths on a real module instead (`Path(registry.__file__).parent.parent`).
- **Suite:** 160 pass (157 baseline + 3).
- ADR-162 §5 (Accepted) states the governing principle in words — a misfiled or
  absent manifest must not surface as "a manager being offered a module that cannot
  render" — but it is about the future channel directories and does not govern this
  template directly. Cite it as principle, not as authority.

## Harness note (run 4)

The `Edit`/`Write` tools and multi-part Bash commands are **blocked from writing
outside the worktree** in this harness, which collides with the definition's
"write memory to the main checkout". What worked: write the block to the
scratchpad with `Write`, then one plain Bash append (`cat <scratch> >> <memory
path>`) with no `cd` and no heredoc. Do that from the start next run.

## AI suggestion UI withholds truncation and lost options (`docs/backlog.md` line 43, 🔴 low)

- **Run:** 2026-09-13 (run 5). Outcome: `fixed`. Worktree `agent-a9c5fa83a52fa50ee`.
- **Entry was NOT stale.** Every cited symbol still lands: `ai/service.py:223-227`
  is still the `message=("output hit its ceiling and is truncated" if
  result.stop_reason == "max_tokens" else None)` on the ok-path `_record`, and
  `parse_options` is still exactly `tasks/subject_preheader.py:74-98`.
- **The defect was one branch in `frontend/router.py`:** the campaign-detail
  read-back used `row.message` **only** in the `else` (non-ok) arm as `ai_error`.
  On `status == "ok"` the message was dropped on the floor, so a `max_tokens`
  truncation never reached the page.
- **Fix (3 files):** `REQUESTED_OPTIONS = 3` + a pure `option_notices(options,
  run_message)` in `app/ai/tasks/subject_preheader.py`; router builds
  `ai_notices` on the ok path and passes it in the context; `campaign_detail.html`
  renders the notices in an `alert-warning`, **outside** the `{% if ai_suggestions %}`
  block so a truncation that left nothing parseable is still said.
- **Two decisions I made (entry left them open), both stated in the report:**
  (1) the run message is surfaced **verbatim** — consistent with how the router
  already surfaces `row.message` verbatim as `ai_error`; (2) the "requested" count
  is a constant in the **dev-owned scaffold**, not parsed out of the
  manager-owned prompt body. Caveat: if a manager edits the Settings prompt to
  ask for 5, `REQUESTED_OPTIONS` does not follow. Flagged as the unverified line.
- **Test:** 8 cases appended to `tests/test_ai_subject_task.py`, **no DB, no
  network**. Five pure `option_notices` cases, three that render the notice block
  extracted from `campaign_detail.html` by regex through a standalone
  `jinja2.Environment` (the run-4 template-fragment shape — it keeps working,
  reuse it). Falsified in both halves: `if False and run_message` → 3 fail;
  `if False and 0 < len(...)` → 2 fail; deleting the template block → 3 fail.
  All restored.
- **Deliberately not touched:** the `ai_error` wording "The model replied, but not
  in the requested format." (it can now be misleading when the true cause is
  truncation — but both lines render together, so the manager sees the cause);
  `parse_options` itself; `ai/service.py` (the audit side was already correct).
- **ADR-144 (accepted)** is the governing record — "If a running task hits its own
  output ceiling, the **partial result is still shown** (display ≠ commit), never
  silently discarded." ADR-140 §3 (the run row is the source of truth for what was
  offered) is why the notice is read back off the row rather than held in session.
