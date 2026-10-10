# Tarrow

A vendor-neutral **reference architecture for newsletter and omni-channel
content orchestration**: a playbook of architecture decisions plus a working
reference implementation that proves them. It is meant to be read, taught from
and tailored, not run as a finished product. The decisions are the deliverable;
the code shows they hold up.

**Status: a local proof of concept.** It runs on a developer machine against a
mock email provider by default. Installation, deployment and hosting are
deliberately not started. The name is provisional.

## What is here

| Path | What it is |
|---|---|
| `backend/` | FastAPI modular monolith on Postgres: content, campaigns and variants, decision slots, audiences, consent, delivery, insight, approvals, AI tasks |
| `frontend/` | The manager client: a React single-page app (ADR-170) |
| `backend/app/frontend/`, `backend/app/templates/` | The earlier server-rendered UI, **frozen** — no new routes; the React client replaces it |
| `docs/` | An Obsidian vault: the architecture decision records, the playbook, business context and the work queue |
| `docs/architecture/ADR/` | Architecture decision records — why each part is built the way it is |
| `docs/playbook-strategy.md` | Strategy, the decision log and the roadmap |
| `docs/queue/` | Open and finished work, as Backlog.md tasks (read and written with the `backlog` CLI) |
| `CODE-REVIEW-BRIEF.md` | Read this first if you are reviewing the code |

## Running it locally

You need Docker, Python 3.14 and Node 24.

```bash
docker compose up -d                      # Postgres (database `app`)

cd backend
python3 -m venv venv
venv/bin/pip install --require-hashes -r requirements.txt -r requirements-dev.txt
cp .env.example .env                      # set INITIAL_ADMIN_EMAIL to your address
venv/bin/uvicorn main:app --reload --port 8000
```

The first start builds an empty database from the models and creates the admin
named by `INITIAL_ADMIN_EMAIL`. Sign-in is passwordless: with the default mock
system mail, the sign-in code is written to the API's log. To load demo data:
`venv/bin/python scripts/seed_demo_data.py` (from `backend/`).

```bash
cd frontend
npm ci
npm run dev                               # http://localhost:5173/manager/
```

Nothing commercial is required to run it (ADR-171): email sending and AI both
default to mock providers. Real providers are configured through `.env`.

**Tests:** `cd backend && venv/bin/python -m pytest -q` runs against a test
database of its own, which the suite creates and seeds, and it refuses to touch
the development one. The client: `cd frontend && npm test`.

**CI** (`.github/workflows/ci.yml`, ADR-190) runs the backend suite, the
client's type check, build and tests, the API contract check, lint, the
installed-packages check, known-vulnerability scans and a secrets scan.
Dependencies are installed from hash-locked files (ADR-189). CI fails visibly;
it does not by itself stop a change landing (ADR-190, 2026-10-09 addendum). **A
fork must set up its own required checks**: CI in a fork checks that fork's
code and enforces nothing unless the fork's repository requires it.

## Licence

Not chosen yet; this is an open decision.
