# Backlog entries refused or blocked — do not re-derive

## P1 security, login form is an account-enumeration oracle (`docs/backlog.md` line 39)

- **Run:** 2026-09-13. Outcome: `blocked`. No code changed.
- **The entry is NOT stale.** Rare for this file: every cited line number still
  lands exactly — `auth/router.py:51-81` is the POST handler, `:58` the
  docstring claiming an identical response, `:71` the 200 `TemplateResponse`,
  `:78` the 303 `RedirectResponse`. The defect is live in the default config.
- **Blocked on three independent grounds**, any one of which is sufficient:
  1. `app/auth/` is on the protected-paths wall. The invoker named the *item*,
     not the wall, so it stays a wall.
  2. The entry offers "(a) accept the oracle in dev ... or (b) gate the dev path
     behind `AUTH_DEV_SHOW_CODE`" and states "The question for a human". That is
     a decision with the work attached.
  3. The "**0 loc**" claim is **conditional on the P0 (line 27) being fixed
     first**, and the P0 is still open and still live. Do not accept "this is a
     quick zero-cost one" at face value on this entry — see below.
- **Why the 0-loc framing misleads:** `deliver_code` (`app/auth/service.py:252`)
  early-returns `False` on the dev path, and `:276-280` also returns `False` on
  every real delivery failure. `request_login_code` ends
  `return None if delivered else code` (`:310-311`). The two causes are
  indistinguishable to the caller. Until the P0 separates "not attempted (dev)"
  from "attempted and failed", the P1 cannot be fixed by deleting a branch — so
  it is zero-loc only *after* someone else's change lands.
- **ADR-151 is `Proposed`, not `Accepted`.** §2 requires "an identical response
  whether or not the address exists" with **no dev/demo carve-out**. So the
  entry's own framing ("the one property ADR-151 §2 makes load-bearing") is
  right, but the ADR it leans on is not yet decided — which is more reason the
  answer is the human's, not mine.
- **Do not** fix by redirecting-then-showing the code; the entry and the comment
  at `router.py:64-70` both rule that out deliberately, and that is a good
  decision.
- I wrote no test. Any test here has to assert *which* behaviour is correct,
  and that is precisely the undecided question.

## Sequencing note for whoever picks this up

The P0 (line 27) and this P1 (line 39) are **one change to the same function**,
not two. Handing the P1 to an implementer on its own cannot work. The P0 also
lives in `app/auth/` and carries its own undecided sub-question (the recovery
path when real delivery fails), so it is not a bug-fixer item either as written.
