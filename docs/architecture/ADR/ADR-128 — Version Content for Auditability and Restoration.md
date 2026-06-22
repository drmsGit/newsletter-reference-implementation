---
type: adr
status: accepted
topic:
  - content
  - versioning
  - auditability
  - restoration
  - snapshot
  - approval
created: 2026-06-16
modified: 2026-06-16
---

## Status
Accepted

## Context

The architecture must support dynamic and recipient-aware communication.

Decision Resolutions may select Content Records during send preparation or recipient-specific decision execution.

If a Content Record is changed after a send, the system must still be able to answer:

```text
What exact content did this recipient receive at send time?
```

Referencing only the current Content Record is not sufficient.

The system also needs a way to restore previous content states when a user wants to revert to an earlier version.

## Decision

Content must be versioned.

A Content Record represents the stable identity of a reusable content item.

A Content Version represents a concrete historical state of that content item.

```text
ContentRecord  = identity
ContentVersion = historical state
```

Decision Resolutions and send-time artifacts must be able to reference the Content Version that was used.

### Version Creation

Not every save creates an audit-relevant version.

The architecture distinguishes between draft saves and publish/approve/release actions.

Draft saves update the editable working state.

A new Content Version is created when content becomes sendable. Examples:

- publish
- approve
- release
- mark as production-ready

This avoids creating unnecessary versions for every minor edit while still preserving sendable historical states.

### Immutable Versions

Content Versions are immutable.

An existing Content Version must not be edited after creation.

If an old version should be restored, the system creates a new version based on the old version.

Example:

```text
Version 2 exists.
User wants to restore Version 2.
System creates Version 5 with the content from Version 2.
```

This preserves auditability.

### Approval Workflow

This ADR does not define the full approval workflow.

However, the decision intentionally supports a future approval process.

A future workflow may look like:

```text
Draft
↓
Review
↓
Approved
↓
ContentVersion created
```

The approval process is governance logic and may be defined separately.

## Consequences

### Positive

- enables send-time auditability
- supports recipient-specific decision history
- supports restoration of older content states
- prepares for approval workflows
- avoids permanent dependency on current mutable content
- improves trust in snapshots and delivery history

### Negative

- adds data model complexity
- requires clear version creation rules
- requires additional storage
- requires handling of draft versus published content

## Notes

Snapshots and Decision Resolutions must not depend on mutable content state.

If the platform only stores `content_record_id`, later changes to that record would make historical reconstruction unreliable.

By referencing a Content Version, the system can reconstruct what was actually used at send time.

The platform owns communication history. Content Versions preserve the historical state required for that ownership.

## Related ADRs

### Referenced By

- [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]]
- [[ADR-126 — Maintain Local Recipient Projection]]
- [[ADR-127 — Decision Execution May Use Recipient Context]]
