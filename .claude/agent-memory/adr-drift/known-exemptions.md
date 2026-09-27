---
name: known-exemptions
description: ADR records that are intentionally non-standard — do not re-flag these
metadata:
  type: project
---

## Intentional deviations (do not flag)

### ADR-130 — missing `## Related ADRs`
Explicitly called out in CLAUDE.md as a known intentional deviation. The record is complete otherwise.

### Proposed-status records — STALE, re-verify every sweep
CLAUDE.md / the adr-conventions skill have at different times said "six
proposed records" (ADR-004, -150, -151, -152, -153, -154) then "two"
(ADR-152, ADR-166, per the skill dated 2026-09-15). As of the 2026-09-27
sweep, **zero** records carry `status: proposed` — ADR-152 (modified
2026-09-18) and ADR-166 (modified 2026-09-19) have both since moved to
`accepted`. Do not trust any document's stated count of proposed records;
grep `^status: proposed` across the directory each sweep instead. This is
now the third count in this line's short history (6 → 2 → 0), so treat the
number as volatile rather than re-checking against a cached value.

### `## Notes` absent in ~36 records
CLAUDE.md says `## Notes` is optional and that 39 of 75 records use it. Absence is not a deviation.
