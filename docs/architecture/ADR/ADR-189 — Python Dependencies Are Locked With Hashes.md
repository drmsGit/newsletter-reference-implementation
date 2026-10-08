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
  - "Decided by the user in chat, 2026-10-08, one question at a time (task-235)"
  - "2026-10-01 dependency sweep (task-235, task-236, task-238)"
depends_on:
  - "[[ADR-143 — AI-Assisted Development Boundary]]"
---

## Status
Accepted

## Context

**The backend's dependencies are nine bare names** (task-235). `backend/requirements.txt` lists fastapi, uvicorn, psycopg2-binary, sqlalchemy, jinja2, css-inline, pytest, httpx and python-multipart. It has no versions, no lockfile and no hashes. A fresh install takes whatever PyPI serves that day, plus about twenty transitive packages. Nothing records which ones arrived.

**The frontend already has what the backend lacks.** `frontend/package-lock.json` records every package, each from registry.npmjs.org with an integrity hash. The npm explainer (`docs/implementation/npm.md`) says that lock is "stricter than the backend currently is". It also calls the lock file a security boundary, because installing a package runs code.

**Why it matters: slopsquatting.** A name in a requirements file is installed on trust. An AI assistant can hallucinate a package name, and a person can mistype one. If someone has registered that name, the install brings in their code. This has already happened here by accident. `requirements.txt` read `httpx2` until task-198 fixed it. From 2026-07-03, `httpx2`, `httpcore2` and `truststore` sat installed and unused in the venv. They have since been removed. The name resolved to a real package. It could as easily have resolved to a hostile one.

**This is an AI-assisted-development risk.** [[ADR-143 — AI-Assisted Development Boundary]] point 2 says enforcement must be structural, not procedural. "Check package names carefully" is a procedure. A lock that refuses anything it does not list is a structure.

**Two packages our code imports are not declared.** `pydantic` is imported directly, for example in `backend/app/pagination.py`. `markupsafe` is imported in `backend/app/rendering/service.py`. Both arrive only because another package pulls them in.

**`httpx` is a runtime dependency, not only a test one.** `backend/app/ai/adapters/claude.py` and `backend/app/delivery/providers/resend.py` both import it.

The 2026-10-01 dependency sweep found all of this. The user decided the answer in chat on 2026-10-08, one question at a time.

## Decision

**1. pip-tools writes the lock.**

- Direct dependencies are written by hand in `backend/requirements.in`.
- `pip-compile --generate-hashes` writes `backend/requirements.txt`. Every package gets an exact version and its hashes, transitive ones included. Each carries a `# via` note naming what pulls it in.
- Installing needs plain pip only. An adopter can install without fetching another program first. That matters for a reference implementation meant to be teachable.

**2. Runtime and dev are split.**

- `backend/requirements-dev.in` holds pytest and pip-tools itself, so the lock tool's own version is locked too.
- It is compiled against the runtime lock (`-c requirements.txt`) into `backend/requirements-dev.txt`, also hashed. The two locks therefore cannot disagree on a package they share.
- A deployment installs the runtime lock only.

**3. Every install checks hashes.**
Installs use `pip install --require-hashes`, locally just as much as in CI and deployment. The cost is accepted. Changing a dependency means re-running `pip-compile`. A quick `pip install x` into the venv does not survive the next clean install. That is the point: the earlier stray package slipped in locally.

**4. Directly imported packages are declared.**
`pydantic` and `markupsafe` join the nine in `backend/requirements.in`.

**5. How a lock change is reviewed.**

- A lock change is its own commit, never mixed with feature code. Its message lists what was added, removed or changed.
- Every package new to the lock gets a provenance check before the commit:
  - it exists on PyPI under that exact name;
  - it is established, with a known maintainer;
  - the `# via` notes show which direct dependency pulls it in.
- Upgrades are deliberate, one package at a time (`pip-compile --upgrade-package X`). There is no blanket upgrade without reading the whole diff.
- CI scans the lock for known vulnerabilities once task-105 builds CI.
- Whoever changes the lock does this review. In practice that is mostly the assistant, and the commit shows it to the user.

**6. The first lock records the tested state.**
The first lock holds the versions installed and passing the suite on 2026-10-08. It does not take whatever PyPI serves on the day of the first compile. It is compiled under Python 3.14.

## Consequences

### Positive

- **Installs are reproducible.** Two installs a month apart get the same code, as the frontend already does.
- **A mistyped or hallucinated name can no longer arrive silently.** It has to be written into `requirements.in`, compiled, and committed as a lock change that someone reads.
- **Supply-chain review has a diff to read.** A new transitive package shows up as a new line with a `# via` note, in its own commit.
- **CI scanning has something to scan.** task-105's vulnerability scan needs exact versions, and the lock provides them.
- **The code's real imports match its declared dependencies.** `pydantic` and `markupsafe` no longer depend on another package keeping them.

### Negative

- **Every dependency change costs a compile step and a review.** Adding one package is no longer a one-line edit.
- **Hashes are per version.** On a platform with no matching wheel, the install fails rather than silently building something unverified.
- **The lock is compiled under one Python version.** Another version may need a recompile, because some packages resolve differently by Python version.
- **Someone must keep the lock fresh.** Exact versions do not update themselves. Left alone, the lock ages into known vulnerabilities. Point 5's one-at-a-time upgrades make that work slower, on purpose.
- **A second program enters the development setup.** pip-tools is needed to change the lock, though not to install from it.

## Notes

- **Rejected in brief.** uv writes the same format and is faster. It is a separate program to install and explain, which is the same reason the npm explainer gives for passing over pnpm. Switching later stays cheap, because the output is the same. pip's own `pip lock` and `pylock.toml` were also rejected: the format is still experimental, and pip cannot yet install from it.
- **Hashes check what is in the lock, not what else is installed.** `--require-hashes` does not remove a stray package already sitting in a venv. Catching that is task-236, which was blocked on this record. A clean venv built from the lock is the reliable state.
- **Point 5 makes task-238's check routine.** task-238 is a one-time provenance look at `css-inline` and `annotated_doc`. Point 5 applies the same questions to every package new to the lock.
- **Point 5 is ADR-143 point 8 applied to the lock.** The same review bar holds whoever makes the change. The commit is where the user sees it.
- **Why a hostile package would matter so much here.** [[ADR-152 — Secret and Credential Handling]] point 1 makes the process environment the interface for every credential. Any package installed into that process can read it.
- **This record covers the Python side only.** [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]] names the frontend's own supply chain and lockfile among its costs. That side already has a hashed lock, and npm's practice is described in `docs/implementation/npm.md`, not in an ADR.
- **The first compile must be held to the tested versions.** How that is done is left to the final-design pass before implementation.

## Related ADRs

### Depends On
- [[ADR-143 — AI-Assisted Development Boundary]]

### Referenced By
- [[ADR-152 — Secret and Credential Handling]]
- [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]]
