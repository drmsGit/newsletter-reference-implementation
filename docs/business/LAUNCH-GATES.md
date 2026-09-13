# Launch gates

What must be true before public beta. Reviewed against commits and
`docs/backlog.md`; not a wish list — each item blocks something specific.

| # | Gate | Blocks | State |
|---|---|---|---|
| 1 | Positioning statement adopted | public beta, Phase 4C write & publish | ❌ open — `POSITIONING.md` |
| 2 | P0 consent defect fixed | any public exposure (compliance) | ✅ done 2026-09-13 — send-time exclusion stack |
| 3 | P0 inbound machine authentication | any public exposure | ❌ open |
| 4 | Auth enforcement flag switched on | any public exposure | 🟡 default is now ON + CSRF done; login rate limiting still missing |
| 4b | Sign-in code disclosure fixed (P0, security) | any public exposure | ✅ done 2026-09-13 — with the enumeration oracle, one change |
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
- **Gate 4 — mostly closed 2026-09-13.** Enforcement now **defaults to ON**, and
  CSRF covers all 62 forms via one router-level dependency beside
  `enforce_policy`, failing closed so a new form without the hidden field is
  refused rather than shipping unguarded.

  The default flipped because its original justification lapsed. The 2026-08-02
  decision shipped it off partly because "system mail defaults to mock, so the
  sign-in code appears on screen" — and the gate-4b fix removed the on-screen
  code that same day, since it was the enumeration oracle. **How to get in:**
  locally the code is in the server log (you cannot be locked out); in
  production it is emailed; if production mail breaks, `AUTH_DEV_SHOW_CODE=true`
  puts it back in the log so you sign in *as yourself* rather than disabling
  access control for everyone. A deactivated sole admin still needs database
  access — stated, not papered over.

  **Still open:** requesting a sign-in code is **not rate-limited**, per address
  or per IP, which ADR-151 §2 requires. Verification attempts are capped at 5
  (`CODE_MAX_ATTEMPTS`); requesting is not capped at all. That is the remaining
  work on this gate and it carries a storage decision — where counters live,
  given in-memory does not survive multiple workers.

- **Gate 4b — ✅ CLOSED 2026-09-13**, together with the P1 enumeration oracle
  that was filed separately. They were the same three lines.

  `deliver_code()` returned False both when the dev path skipped sending and
  when a real send failed, so `request_login_code` could not distinguish them
  and returned the live code in both cases — a deployment with a broken mail
  provider handed a working sign-in code to whoever typed an admin's address.
  The oracle came off the same line: a code was returned only for an existing
  active user, so the handler answered 200-with-code or 303-redirect and gave
  account existence away. `mock` is the default, so both were live in the
  shipped configuration.

  `deliver_code` now returns a tri-state (dev_not_attempted / sent / failed),
  and the handler redirects unconditionally — identical status, location shape
  and body for a known address, an unknown one, a deactivated user and a failed
  send. Two decisions went with it: a failed send shows the same neutral
  response as success (saying "delivery failed" reveals delivery was
  *attempted*, which only happens for real accounts), and the dev code goes to
  the server log rather than the screen, so ADR-151 §2 holds with no dev
  carve-out — the carve-out was what made the default an oracle.

  Five tests, mutation-verified, plus an end-to-end check against the running
  app.
