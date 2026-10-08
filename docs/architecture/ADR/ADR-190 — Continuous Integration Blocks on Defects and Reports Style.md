---
type: adr
status: accepted
topic:
  - architecture
  - security
  - operations
  - development
created: 2026-10-08
source:
  - "Decided by the user in chat, 2026-10-08, one question at a time (task-105)"
  - "Ruff and gitleaks measurements, 2026-10-08"
depends_on:
  - "[[ADR-189 — Python Dependencies Are Locked With Hashes]]"
  - "[[ADR-143 — AI-Assisted Development Boundary]]"
---

## Status
Accepted

## Context

**The repository has no CI** (task-105). It is private on GitHub. It had no `.github/`, no CI, no linter, and no dependency or secret scanning. [[ADR-173 — The Manager Client's Runtime Dependencies]] point 4 already booked part of this gap on 2026-09-20. It gave the contract check a script, `npm run check:contract`, but nothing runs it.

**A reference implementation without CI reads as unfinished.** A technical visitor looks for the workflow file first. Without one, the repository reads as a hobby, whatever the tests underneath. task-105 ties this to [[LAUNCH-GATES|launch gate 1]], the positioning gate: how the project reads to the people it is meant for. The source is `CODE_QUALITY_RELEASE_POSITIONING_2026-09-19` §4 and §7.

**The pieces CI needs already exist.**

- [[ADR-189 — Python Dependencies Are Locked With Hashes]] locked the Python dependencies with hashes. Its point 5 says CI scans the lock once task-105 builds CI.
- task-236 added `backend/scripts/check_installed.py`. It fails when what is installed differs from the locks, Python and npm.
- The backend suite builds its own test database. It truncates and reseeds (`backend/tests/conftest.py`). CI therefore needs only an empty Postgres 16 service.
- The client has a type check and build (`npm run build`), tests (`npm run test`) and the contract check.

**Most of what a default linter reports is noise for this code.** Ruff 0.16 with its defaults found 783 findings on 2026-10-08.

- 308 are B008, on FastAPI `Depends()` defaults. That is how FastAPI is meant to be written.
- 189 are import order, and 105 are unused imports.
- The rules that catch real defects found about 14: 12 names defined twice, one unused variable, and one f-string without placeholders. There were no undefined names and no syntax errors.

Making the full default set block would mean roughly 800 fixes before the first green build. That is the cleanup task-105 rules out: checks inform review, they do not trigger a refactor. Making everything report-only was also rejected. A check that never fails is easy to ignore.

**No secret has ever been committed.** A full-history gitleaks scan on 2026-10-08 covered 708 commits and found nothing. `backend/.env` holds a real key. It is git-ignored, so it is never committed and never scanned.

**Enforcement here should be structural.** [[ADR-143 — AI-Assisted Development Boundary]] point 2 says enforcement must be structural, not procedural. "Run the linter before you commit" is a procedure. A build that fails is a structure. Much of this code is written by an assistant, and ADR-143 point 8 holds it to the same bar as a person. CI is where that bar is checked, whoever wrote the change.

The user decided the answer in chat on 2026-10-08, one question at a time.

## Decision

**1. GitHub Actions runs CI on every push and every pull request, and once a week.**
The weekly run exists so that a newly published vulnerability is noticed when nobody pushes. CI runs:

- the backend suite against a Postgres 16 service, in a venv installed from ADR-189's locks with `--require-hashes`;
- the client's type check, build and tests;
- the API contract check;
- `backend/scripts/check_installed.py`;
- the linters, the vulnerability scans and the secret scan.

**2. Linters block on a small set of rules that catch real defects. Everything else is reported and never fails a build.**

- **Ruff blocks on** undefined names (F821), names defined twice (F811), syntax errors, unused variables (F841) and f-strings without placeholders (F541).
- **ESLint blocks on** its recommended rules plus `react-hooks`.
- **`jsx-a11y` warns only.** Its findings feed the keyboard and accessibility session. They are not fixed one by one.
- **Every other finding appears in the log.** Unused imports, import order and style never fail a build.

The existing hits of the blocking set are fixed when it is introduced. Nothing else is refactored. This is task-105's own rule: checks inform review, they do not trigger a refactor.

**3. gitleaks scans every push.**
The full history was scanned once, locally, when this was introduced. It found nothing. If a real secret is ever found, the key is rotated with its provider.

Rewriting git history is a separate decision. It is not needed while the repository is private. It returns when the code moves to the product's own GitHub account.

**4. Dependency vulnerabilities are scanned on every push and weekly.**
pip-audit checks the Python locks. `npm audit` checks the frontend.

- **Only what ships blocks.** That is the runtime Python lock (`backend/requirements.txt`) and the frontend's `dependencies`. Dev tools are reported, not blocking: pytest, pip-tools, Vite and the test libraries, for example.
- **A blocking finding is fixed by upgrading that one package**, under ADR-189 point 5's lock rule.
- **If no fix exists yet, the finding goes on an ignore list.** Each entry has a reason and a date to look again. Nothing is ignored silently.
- **pip-audit and Ruff join the dev lock** (`backend/requirements-dev.in`), under ADR-189.

**5. Python type checking comes later, and gradually.**
mypy is not part of this record. task-105 already says why: a strict mypy over this code today would produce a cleanup nobody asked for.

## Consequences

### Positive

- **A reviewer sees CI.** The workflow file and its runs are the first thing a technical visitor looks for.
- **A defect in the blocking set cannot land.** An undefined name or a function defined twice fails the build, whoever wrote it.
- **Supply-chain drift fails visibly.** `check_installed.py` catches an installed package that is not the locked one.
- **A committed secret fails visibly.** It is caught on the push that introduced it, not on a later audit.
- **Vulnerabilities surface weekly**, even when nobody is working on the code.
- **ADR-170 point 5's promise gets a run.** The contract check becomes a build step, not a convention. That is the shortfall ADR-173 point 4 booked.

### Negative

- **CI costs minutes.** GitHub Actions on a private repository is metered.
- **CI can turn red on a day nobody changed anything.** A vulnerability published overnight fails the weekly run, or the next push. This is the price of point 4, and it is accepted.
- **Report-only findings may be ignored.** They appear in a log that nobody is obliged to read.
- **The blocking set needs deliberate widening.** It starts small on purpose. It only grows if someone decides to grow it.
- **Third-party actions are code we run.** Each action runs with the workflow's access. They are pinned to commit SHAs rather than tags, so a moved tag cannot change what runs. A SHA pin also does not update itself, so a fix in an action arrives only when someone moves the pin.
- **The frontend and backend share one run.** ADR-170's Negative already named this: a slow or flaky client build slows the backend's loop.

## Notes

- **Ruff's measurement is dated.** The 783 findings and the split between them are from 2026-10-08, with Ruff 0.16 defaults. A later Ruff version will count differently. The point is the ratio: about 14 real defects in nearly 800 findings.
- **ESLint is in scope by the user's extension of task-105 on 2026-10-08.** The set is typescript-eslint, `eslint-plugin-react-hooks` and `eslint-plugin-jsx-a11y`. `frontend/package.json` had no ESLint that day. The keyboard and accessibility session that receives `jsx-a11y`'s findings was deferred by the user on 2026-10-05.
- **The contract check needs a running backend.** `npm run check:contract` regenerates the client from `http://127.0.0.1:8000/openapi.json` (`frontend/package.json`). CI must start the API before that step. How is left to the final-design pass.
- **Vulture is not wired in.** task-105 says to run it once by hand for the signal, because in CI it would cry wolf.
- **This is not a promotion path.** [[ADR-143 — AI-Assisted Development Boundary]] point 3 warns that lock-in arises when one provider's CI becomes the only way to promote code. This CI only checks. It deploys nothing. Each check is a command that also runs locally, so moving to another CI host means rewriting the workflow file, not the checks.
- **GitHub Actions is not required to run the platform.** [[ADR-171 — Nothing Required to Run This Platform Is Commercial]] point 1 counts what the platform needs to work. CI is development tooling, so the rule does not apply to it.
- **Rotation follows [[ADR-152 — Secret and Credential Handling]].** Point 3 there makes rotation "update the environment, restart". A leaked key found by point 3 here is replaced with the provider, then rotated the same way.
- **Why the secret scan matters even with `.env` ignored.** ADR-152 point 1 makes the process environment the interface for every credential. A key pasted into code or a test fixture would bypass that. gitleaks catches the paste. `.gitignore` only covers the file.
- **Not a supersession.** ADR-173 point 4 says "this record creates no CI", and that stays true of ADR-173. This record creates it. ADR-189 point 5's "once task-105 builds CI" is fulfilled, not changed.

## Related ADRs

### Depends On
- [[ADR-189 — Python Dependencies Are Locked With Hashes]]
- [[ADR-143 — AI-Assisted Development Boundary]]

### Referenced By
- [[ADR-152 — Secret and Credential Handling]]
- [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]]
- [[ADR-171 — Nothing Required to Run This Platform Is Commercial]]
- [[ADR-173 — The Manager Client's Runtime Dependencies]]
