---
name: known-exemptions
description: ADR records that are intentionally non-standard — do not re-flag these
metadata:
  type: project
---

## Intentional deviations (do not flag)

### ADR-130 — missing `## Related ADRs`
Explicitly called out in CLAUDE.md as a known intentional deviation. The record is complete otherwise.

### ADR-004, -150, -151, -152, -153, -154 — status: proposed
Six records in `proposed` state. CLAUDE.md says "the six proposed records are all expected." Do not flag these as invalid.

### `## Notes` absent in ~36 records
CLAUDE.md says `## Notes` is optional and that 39 of 75 records use it. Absence is not a deviation.
