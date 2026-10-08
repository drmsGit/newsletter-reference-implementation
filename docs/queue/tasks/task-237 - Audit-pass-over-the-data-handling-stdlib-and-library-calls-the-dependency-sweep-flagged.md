---
id: TASK-237
title: >-
  Audit pass over the data-handling stdlib and library calls the dependency
  sweep flagged
status: To Do
assignee: []
created_date: '2026-10-01 21:26'
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
- [ ] #1 Each text() and DDL() call site is listed with a verdict: bound parameters only, or a finding
- [ ] #2 Jinja autoescape setting and every template-rendering entry point are checked and recorded
- [ ] #3 Every use of random is classified as security-relevant or not
- [ ] #4 The subprocess.run arguments and FileResponse/StaticFiles path sources are confirmed fixed or filed as a bug
- [ ] #5 Any finding becomes its own bug task; none is fixed inside this task
<!-- AC:END -->
