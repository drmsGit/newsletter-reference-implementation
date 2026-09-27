---
id: TASK-192
title: >-
  In the shipped default configuration the login form is an account-enumeration
  oracle — the one property ADR-151 §2 makes load-bearing.
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
  - frontend
dependencies: []
priority: p1
type: bug
ordinal: 505600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug] — P1, security.** **In the shipped default configuration the login form is an account-enumeration oracle — the one property ADR-151 §2 makes load-bearing.** `auth/router.py:51-81`. Under the default `SYSTEM_MAIL_PROVIDER=mock`: a **known active address** returns a code → `200` rendering `login_verify.html` inline (`:71`); an **unknown or deactivated address** returns `None` → `303` redirect (`:78`). Different status, different body, trivially distinguishable. The neutral-notice *text* is identical in both, which is what makes it look correct, and the docstring at `:58` claims the response is the same either way. **Same root cause as the P0 above** — the `if code:` branch conflates "dev" with "not delivered" — and **0 loc once that is fixed as described**, since the dev branch would then trigger only under an explicit `AUTH_DEV_SHOW_CODE`. **Logged separately because the decision differs:** the P0 is a defect to fix; this in *dev* mode is arguably an acceptable trade. **The question for a human:** is ADR-151 §2's property meant to hold in the demo configuration a prospect is shown, or only in production? Honest options: (a) accept the oracle in dev and say so in the docstring, or (b) gate the dev path behind `AUTH_DEV_SHOW_CODE` only and log the code rather than render it. Do **not** "fix" it by redirecting-then-showing — that breaks the deliberate no-code-in-the-query-string decision documented at `router.py:64-70`, which is a good decision. Source: code-slimmer sweep 2026-08-21, Cluster 6 A4. **DONE 2026-09-13 with the P0 above; this entry's "0 loc" was conditional on that P0 landing first, and the bug-fixer agent refused the item on exactly that ground.** **The question this entry put to a human is answered:** ADR-151 §2's identical-response property holds **everywhere, including the demo configuration** — the dev carve-out was what made the shipped default (`mock`) an oracle. The dev code now goes to the **server log** rather than the screen, so the handler can redirect unconditionally and known/unknown/deactivated/failed-send all produce a byte-identical response. The named anti-fix (redirect-then-show, putting a code in a query string) was not used.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 615, section "Done", position 56 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
