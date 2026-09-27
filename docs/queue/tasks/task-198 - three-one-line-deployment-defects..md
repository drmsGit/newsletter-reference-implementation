---
id: TASK-198
title: three one-line deployment defects.
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 506200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug] — P2, three one-line deployment defects.** **(a)** `requirements.txt` line 8 reads **`httpx2`**, but the application imports `httpx` — a fresh install either fails or pulls an unintended package, which is why the reviewer could not collect the test suite. **(b)** `DATABASE_URL` is **hard-coded with a password** in `app/database.py:4`, breaking deployment portability and normalising a credential-in-source pattern in a reference implementation people are meant to copy; read it from the environment with an explicit dev default. **(c)** The session cookie sets `HttpOnly` and `SameSite=Lax` but **not `Secure`** (`auth/router.py:98-103`), so a reachable HTTP path would transmit the session token in clear; set it in normal deployments and make local HTTP the explicit exception. Grouped because each is a few characters, but (a) blocks anyone reproducing the build. Source: code review 2026-08-07 P2-09, P2-08, P2-01. **DONE 2026-09-13, all three.** **(a)** `requirements.txt:8` reads `httpx` and **(b)** `app/database.py:9` reads `DATABASE_URL` from the environment with an explicit dev default, both in `cd36abe`. **(c)** the session cookie now sets `secure=cookie_secure()`, defaulting **on**. **The exception is explicit and it is not theoretical:** a `Secure` cookie is not sent over plain HTTP, and while Chrome and Firefox treat `http://localhost` as a trustworthy origin and send it anyway, Safari historically does not — a developer there would watch sign-in loop back to the login form with nothing to read. `AUTH_COOKIE_INSECURE=true` is for exactly that, and startup logs a warning naming it so it is never silent. Mutation-checked three ways, including inverting the env check — which would have made every deployment insecure while two of the three tests still passed, because both set the variable explicitly; the third test exists to pin the default's direction.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 628, section "Done", position 62 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
