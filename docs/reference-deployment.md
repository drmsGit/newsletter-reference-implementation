---
type: reference
status: designed, not yet run
created: 2026-10-10
---

# Reference deployment

> **Status: designed, not yet run (2026-10-10).** This page answers "how do you
> host this, how do you secure access, what servers" — but nobody operates this
> setup yet. Installation and deployment are deferred by decision at the current
> proof-of-concept stage (task-55, decided with the user 2026-10-10). Until it is
> run, **no positioning claim may rest on it** ([[POSITIONING]] rule 2: only what
> is demonstrable in the repo). What it states about the application itself is
> checked against the code as of this date; what it states about the box around
> it is a design.

**This is deliberately not an ADR.** How an adopter fills the process environment
is infrastructure, and [[ADR-152 — Secret and Credential Handling]] point 1
exists so the architecture never has to know. An ADR would turn our hosting
choice into a commitment and invite adopters to inherit it instead of using what
they already operate.

**The claim is the seam, not the product.** The platform holds no secrets of its
own and reads everything from the process environment, so a company injects them
with whatever it already runs. That sentence carries further with a security
reviewer than any vendor name.

## The shape: one box

One server, a reverse proxy in front, one database. That is defensible and
survives follow-up questions, which a stack nobody operates would not.

| Part | What it is | Notes |
|---|---|---|
| Reverse proxy | Terminates TLS, forwards to the app | Any proxy you already run. It must **overwrite** `X-Forwarded-For` if `TRUST_PROXY_HEADERS` is on (see below). |
| Application | One FastAPI process (`uvicorn main:app`) | Serves the JSON API, the React manager client at `/manager` (built into `frontend/dist`), the older Jinja screens, the public unsubscribe page (`/unsubscribe/{token}`) and the provider webhook. |
| Database | PostgreSQL 16 | Holds everything, including consent evidence and the audit log, so its backups are a compliance matter, not only an operational one. |

Everything the application needs from outside arrives through the environment.
It refuses to start while a database migration is pending
(`schema_migrations.assert_no_pending_migrations`, called at startup in
`main.py`); a person applies migrations with `scripts/migrate.py --apply`
([[ADR-181 — A Database Records Which Migrations It Has Had]]).

### Traffic in and out

- **In, from people:** the manager client, the Jinja screens, and recipients
  opening unsubscribe links.
- **In, from machines:** integrations (n8n, a CRM) with an API key
  ([[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]); the email
  provider's signed webhook (`POST /provider/webhooks/resend`, verified with
  `RESEND_WEBHOOK_SECRET`); and whatever triggers scheduled sends.
- **Out:** the email provider (`api.resend.com`) and, if AI is switched on, the
  model provider (`api.anthropic.com`). Nothing else.

### Scheduled sends

The platform has no scheduler of its own; something you already run calls
`POST /delivery/process-due` on an interval — a cron job, a worker, n8n. It acts
for one brand per call (declare it with `X-Brand`), so a company with several
brands calls it once per brand, with an integration key allowed to send
unattended. Each send it fires is audited with that integration as actor
(task-340).

## The environment

Names only; how they are filled is yours ([[ADR-152 — Secret and Credential Handling]]).
The application never writes these and never shows a secret's value; Settings
only says whether a key is configured.

| Variable | Needed | What it is |
|---|---|---|
| `DATABASE_URL` | yes | Postgres connection string. The code's default is the local development database; never rely on it. |
| `PUBLIC_BASE_URL` | yes, for real sends | The public https address recipients reach. **A domain the company owns**, not an agency's host: every mail sent carries unsubscribe links to it for good. A real send refuses to go out without it, or with a non-https value (task-330). |
| `RESEND_API_KEY`, `RESEND_FROM` | for real email | The sending credential and default sender. |
| `RESEND_WEBHOOK_SECRET` | for engagement and bounces | Verifies the provider's webhook signature. |
| `SYSTEM_MAIL_PROVIDER`, `SYSTEM_MAIL_FROM` | yes | How sign-in codes reach people. `mock` writes codes to the server log, which is for development only. |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | only if AI is used | The model credential and model. |
| `INITIAL_ADMIN_EMAIL` | first start | The first administrator; read once, never re-grants. |
| `TRUST_PROXY_HEADERS` | behind a proxy | Off by default. Turn on only where your proxy **overwrites** `X-Forwarded-For`; otherwise a visitor can mint a new identity per request and the sign-in rate limits stop counting. |
| `AUTH_COOKIE_INSECURE` | never in production | Drops `Secure` from the session cookie, for plain-http development only. |
| `AUTH_DEV_SHOW_CODE` | never in production | Shows sign-in codes on screen, for development only. |
| `API_DOCS` | optional | Whether the API documentation is public. |

## Access and security, as built

- **People** sign in with an emailed one-time code; sessions expire after 12
  hours, or 60 minutes idle ([[ADR-151 — Authentication and Sessions]]). The
  session cookie is `HttpOnly`, `SameSite=Lax` and `Secure` by default. The
  session lengths will become company settings (task-342).
- **Machines** use an API key per integration, with grants per brand
  ([[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]). Keys do
  not expire yet; an optional expiry date is decided and queued (task-344).
- **Everything is same-origin.** The client and the API share one address, so
  there is no cross-origin access to configure
  ([[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]]).
- **Rate limits inside the app** cover sign-in code requests and guesses, and
  failed machine authentication. Successful machine calls have no budget inside
  the app — that belongs to the gateway (below). What the app does bound is mail:
  held sends need a person's approval, and every send is capped by the recipient
  limit.

## The two seams larger adopters ask about

### An API gateway in front

Where TLS, **rate and request limits**, IP allowlists and a WAF live. A
per-integration request budget belongs here, **keyed on the API key** (business
baseline P2-G2, decided 2026-10-09). The app needs nothing from it but correct
forwarding; if the gateway sets `X-Forwarded-For`, it must overwrite it.

### An egress proxy behind

Where outbound traffic is allowlisted (the two hosts above and nothing else) and
logged in one place. **The strong version** lets the proxy inject the provider
credential, so the application holds no key at all. That is a seam, not a
working setup: today the Resend adapter refuses to call out when
`RESEND_API_KEY` is empty, so credential injection would need either a
placeholder value or a small change to the adapter. Not designed further yet.

## What the adopter is responsible for

These follow from decisions already taken; the platform cannot do them for you.

- **Keeping unsubscribe links working.** A token never expires, but the link only
  works while `PUBLIC_BASE_URL` stays reachable and the delivery record it points
  to still exists. Moving hosts means keeping the old address answering; pruning
  old delivery records must keep the unsubscribe lookup working for a minimum
  period ([[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]]
  addendum 2026-10-09; the period is set in task-136). Erasing a person on
  request also stops their old links, which is not decided yet.
- **Security checks after handoff.** A fork's CI checks that fork's code. Its
  owner — the company, or the agency if their contract says so — runs the checks
  against the deployed version, reads the weekly vulnerability scan, and acts on
  it. We maintain the reference, not forks (business interview BF-CI1).
- **Required checks.** CI fails visibly; it does not stop a change landing unless
  the fork's repository requires the checks
  ([[ADR-190 — Continuous Integration Blocks on Defects and Reports Style]]
  addendum 2026-10-09).
- **Backups.** Consent evidence and the audit log live in the database. A backup
  you have never restored is not a backup.
- **Consent law.** Built for EU consent rules: no recorded opt-in, no marketing
  (business baseline P2-E1). A deployment under other law changes that in its
  fork, knowingly.

## Not covered yet

- A container image or install script for the application. Only the development
  database has a `docker-compose.yml`.
- Health checks, log shipping, monitoring.
- A tested backup and restore.
- Running any of this. When it is run, this page's status line changes and the
  gaps above get answers.
