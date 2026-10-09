---
id: TASK-237
title: >-
  Audit pass over the data-handling stdlib and library calls the dependency
  sweep flagged
status: Done
assignee:
  - '@claude'
created_date: '2026-10-01 21:26'
updated_date: '2026-10-09 07:25'
labels:
  - backend
dependencies: []
type: chore
ordinal: 200700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🟠 **[Chore] — four read-only checks the 2026-10-01 dependency sweep could not settle from the import list alone.** Each is a "confirm" and not a known defect; file a bug task for anything found, and do not fix inside this task. **(1) Raw SQL:** every call site of `sqlalchemy.text` and `sqlalchemy.DDL` (SQLAlchemy is imported in 85 files) — confirm no user-derived value is interpolated into the SQL string instead of bound. **(2) Template escaping:** the Jinja2 `Environment` (imports `Environment, BaseLoader`, plus `Jinja2Templates`) — confirm autoescape is on wherever recipient or manager text reaches HTML, and that no user-supplied string is ever rendered as a template (server-side template injection). Also the `markupsafe.Markup` / `escape` use in one file. **(3) Randomness:** the project imports `random` as well as `secrets`, `hmac` and `hashlib` — confirm `random` never produces a login code, session token, unsubscribe token or anything else an attacker benefits from guessing. **(4) Subprocess:** `app/schema_migrations.py:212` calls `subprocess.run` at migration time — confirm the arguments are fixed and never built from request data or an environment value an outsider can set; no `shell=True` or `os.system` was found. Also `FileResponse` and `StaticFiles` serve files from disk: confirm no path is built from user input. Related: the five `importlib.import_module` sites (`schema_migrations.py:171`, `ai/tasks/registry.py:41`, `rendering/renderers/registry.py:34`, `decision/strategies/registry.py:30`, `approvals/actions/registry.py:34`) import only local modules found by scanning our own directories, so they are a repository-write-access question and not a dependency one.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Each text() and DDL() call site is listed with a verdict: bound parameters only, or a finding
- [x] #2 Jinja autoescape setting and every template-rendering entry point are checked and recorded
- [x] #3 Every use of random is classified as security-relevant or not
- [x] #4 The subprocess.run arguments and FileResponse/StaticFiles path sources are confirmed fixed or filed as a bug
- [x] #5 Any finding becomes its own bug task; none is fixed inside this task
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09 audit, read-only. No finding, so no bug task (AC #5). This follows ADR-190's addendum of 2026-10-08, which measured Ruff's bandit rules and left the SQL strings (S608) and random to review.

(1) Raw SQL. Outside the tests there are 18 text()/DDL() sites in app/, scripts/ and main.py:
- Constant SQL with no interpolation:
  - backend/app/schema_compare.py:56, :67, :72 and :90 (catalogue reads);
  - server defaults in auth/db_models.py:84, recipients/db_models.py:161-162, delivery/db_models.py:63-65 and campaigns/db_models.py:95;
  - approvals/db_models.py:165 (a partial-index WHERE clause);
  - audit/db_models.py:103 and :111 (the append-only trigger DDL);
  - scripts/seed_demo_data.py:70 (TRUNCATE).
- f-strings in backend/app/schema_compare.py:166, :167 and :183 (DROP and CREATE DATABASE). They interpolate `scratch`, which is the configured database name plus "_schemacheck", so it is operator configuration, quoted as an identifier, and Postgres cannot bind a database name. Safe.
- Other raw paths:
  - backend/app/schema_migrations.py:203 executes migration file contents from the repository's scripts/ directory. This is a repository-write question. It is reachable only via scripts/migrate.py; the app never calls apply_pending.
  - backend/scripts/drop_stale_test_databases.py:82 runs DROP DATABASE "{name}", where the names come from pg_database, filtered by the test prefix, and the dev name is refused. It is a CLI script. Safe; a name containing a double quote would break the quoting, but only someone with database access could create one.
- The tests have 126 text()/DDL() lines. The interpolated ones substitute table or column names from literal lists in the test files themselves, with values bound as :u parameters. They never ship.

(2) Template escaping.
- The rendering environment sets autoescape=True (backend/app/rendering/service.py:32).
- _jinja.from_string (service.py:364) renders only module templates: get_template_html reads MODULES_DIR/{channel}/{name}.html after get_manifest finds a registered (channel, name) in the registry dict (backend/app/modules/registry.py:393-427). A made-up name never reaches the filesystem, and no user text is ever compiled as a template.
- render_rich_text (service.py:50-61) escapes everything first, then adds only <strong>, <br> and http(s) links. The URL and label are already escaped, so an attribute cannot be broken, and javascript: URLs do not match the pattern.
- Jinja2Templates (backend/app/frontend/router.py:151, backend/app/auth/router.py:44, backend/main.py:298) uses Starlette's select_autoescape() (starlette/templating.py:95), which is on for .html. Every file in app/templates is .html, and there is no |safe or Markup in any template.
- backend/app/modules/registry.py:285 is a parse-only Environment (noqa S701, ADR-190 addendum). It never renders.

(3) Randomness. random appears once in app code: backend/app/decision/strategies/recipient_top_score.py:103, a tie-break among equally scored content items. Not security-relevant, since predicting it gains nothing. The demo seed (scripts/seed_demo_data.py) is deterministic by design (random.seed(42)). Every secret comes from secrets or os.urandom:
- the sign-in code: auth/service.py:786, secrets.randbelow;
- the session token: :876, token_urlsafe;
- the login-code salt: :92, os.urandom;
- integration key ids and keys: auth/integrations.py:35 and :48.

(4) Subprocess and files.
- The only subprocess.run is backend/app/schema_migrations.py:212: [sys.executable, str(path), "--apply"] with the path from the migrations directory listing, cwd fixed and no shell. It is reachable only from scripts/migrate.py.
- File serving: FileResponse(SPA_INDEX) (backend/main.py:868) serves one fixed path. StaticFiles(directory=SPA_DIR / "assets") (main.py:850) is a fixed directory, and Starlette refuses paths outside it.
- Other file reads are constants or registry scans of repository directories. The one with a variable segment, backend/app/rendering/frame.py:59 (templates_fingerprint, MODULES_DIR / channel), takes a channel from a variant, and a variant only accepts a channel that exists on disk and is enabled (_refuse_unavailable_channel, backend/app/campaigns/service.py:26, ADR-160 point 8).
- The importlib.import_module sites import only modules found by scanning our own directories, a repository-write question, as the entry said.

CODE-REVIEW-BRIEF.md was updated: the open-issue bullet for this task is gone, and the deliberate table now explains the f-string SQL.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Audited every raw-SQL site, every template-rendering entry point, every use of random, and the subprocess and file-serving paths. No finding: no request data reaches a SQL string, a template source, a subprocess argument or a file path; autoescape is on wherever text becomes HTML; and every secret comes from secrets or os.urandom. Per-site verdicts are in the notes, and the review brief is updated.
<!-- SECTION:FINAL_SUMMARY:END -->
