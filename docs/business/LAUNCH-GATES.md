# Launch gates

What must be true before public beta. Reviewed against commits and
`docs/backlog.md`; not a wish list — each item blocks something specific.

| # | Gate | Blocks | State |
|---|---|---|---|
| 1 | Positioning statement adopted | public beta, Phase 4C write & publish | ❌ open — `POSITIONING.md` |
| 2 | P0 consent defect fixed | any public exposure (compliance) | ✅ done 2026-09-13 — send-time exclusion stack |
| 3 | P0 inbound machine authentication | any public exposure | ❌ open |
| 4 | Auth enforcement flag switched on | any public exposure | 🟡 built, ships off |
| 4b | Sign-in code disclosure fixed (P0, security) | any public exposure | ❌ open — found 2026-08-21 |
| 5 | Real provider integration proven | the "no lock-in" claim | ✅ done — Resend, live, verified domain |
| 6 | Inbound engagement loop proven | the signal-layer claim | ✅ done — signed webhooks, end-to-end |
| 7 | Security model designed + base built | Phase 4C | ✅ ADR-150–154; base built, proposed status |
| 8 | Playbook structure decided (4A) | 4C | 🟡 started in Cowork |
| 9 | 2–3 client cases mapped to the pillars (4B) | 4C | ❌ open |

## The three that actually block exposure
Gates 2, 3 and 4 are the ones where "we launched" and "we were fine" come
apart. From the 2026-08-07 external review:

- **Gate 2 — ✅ CLOSED 2026-09-13.** A frozen audience was consent-gated at plan
  time and never again, and the decision layer's consent guard was swallowed by
  a bare `except ValueError` in `delivery/service.py`, so a compliance defect
  read as a rendering behaviour.

  Fixed in the shape ADR-163 §7/§8 prescribes — which is why that cluster was
  settled first. `app/delivery/exclusion.py` runs an ordered stack
  (addressability → consent → suppression → frequency) immediately before the
  send loop, **for every resolution mode including `freeze`**, and records *why*
  each recipient was excluded on the execution row. Re-resolving the audience
  was explicitly not the fix: that is what `rerun` mode does and it changes who
  is *targeted*. Freezing targeting must never freeze permission to contact.

  Stage 3 (suppression) is named, ordered and empty by construction — a bounce
  is currently written as a consent event with `source="provider"`, so stage 2
  catches it, and the suppression data model is still an open Needs-ADR item.
  Stage 4 (frequency) is post-POC per ADR-161 §8.

  `ConsentDenied` is now re-raised rather than swallowed; the bare
  `except ValueError` survives only for its one legitimate case, a strategy
  resolving nothing (ADR-086).

  The regression test the 2026-08-07 review ranked first — send-time consent
  revocation — ships with the fix and is mutation-verified: removing the gate
  fails it. The P1 beside it in the same function (a send reporting `sent` when
  every delivery failed) is fixed in the same pass.

  *Historical note, kept because it was wrong and was acted on:* an earlier
  version of this entry claimed `app/database.py`'s engine-at-import made four
  test modules uncollectable. It does not — the suite collects and passes. The
  real constraint is that several tests need a live seeded Postgres, which is
  the isolated-test-DB Needs-ADR item.
- **Gate 3** — the JSON API routers are deliberately unguarded; that is machine
  authentication, scoped as a Mode B prerequisite. It was raised to P0 because
  it blocks public exposure, not just Mode B.
- **Gate 4** — the enforcement mechanism covers every UI page but ships off
  until a deployment has signed in once. Fine locally, not for anything public.
- **Gate 4b** — a failed sign-in-code delivery prints the live six-digit code
  into the requester's browser, so an unauthenticated visitor who names an
  Admin's address gets a working code whenever the mail provider fails
  (`auth/service.py:310-311` → `auth/router.py:63-76`). Found by the
  code-slimmer sweep 2026-08-21, missed by the external review, ~3 loc to fix
  plus a decision about the admin lockout path. Two related auth defects are
  logged with it: `+`-addressed accounts cannot sign in at all once a real
  provider is configured, and the default configuration makes the login form an
  account-enumeration oracle — the one property ADR-151 §2 makes load-bearing.

## Rules
- A gate moves to ✅ only with something checkable behind it — a commit, a
  verified live run, an adopted file. "Designed" is not "done"; gate 7 is
  deliberately split that way.
- Update this file when a gate moves, not at review time.
