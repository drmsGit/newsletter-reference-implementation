---
type: adr
status: accepted
topic:
  - architecture
  - snapshot
  - rendering
  - delivery
  - auditability
created: 2026-10-02
modified: 2026-10-12
source:
  - "task-129 (needs-adr: snapshot storage strategy)"
  - "Code review finding P1-04 (reviewed snapshot does not prove content sent)"
  - "Decided by the user 2026-10-02"
depends_on:
  - "[[ADR-062 — Snapshot Stores Final Render State]]"
  - "[[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]]"
  - "[[ADR-061 — Snapshot Based Final Rendering]]"
  - "[[ADR-128 — Version Content for Auditability and Restoration]]"
  - "[[ADR-162 — Channel Rendering and Artifacts]]"
enables:
  - "[[ADR-053 — Maintain Minimal Delivery Execution History]]"
---

## Status
Accepted

## Context

[[ADR-062 — Snapshot Stores Final Render State]] says a snapshot stores the final render state, and that this state includes the final HTML at minimum. Its 2026-09-12 addendum widened "final HTML" to a package of role-tagged artifacts with a hash over the set. [[ADR-061 — Snapshot Based Final Rendering]] says immutable render snapshots are generated before sending. [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]] separates four things: snapshot state, decision resolution, merge context and the delivery artifact. It allows per-recipient HTML to be dropped, but only if the send-time state stays reconstructable. [[ADR-128 — Version Content for Auditability and Restoration]] says send-time artifacts must be able to reference the content version that was used. [[ADR-162 — Channel Rendering and Artifacts]] point 3 intends a package hash so that a reviewed snapshot proves what was sent. That is code-review finding P1-04, and the hash is not built.

**The code does none of this (verified 2026-10-02).** `send_send_instance` in `backend/app/delivery/service.py` takes only `variant_id` from the snapshot. It then re-renders every recipient from live database state. Nothing of that render is stored: no HTML, no inputs, and no reliable send time, only `updated_at`. The snapshot's HTML file under `storage/snapshots` is an approval preview that is never sent. It is also written non-atomically (task-46): the row is committed with `artifact_location="pending"` and the file is written afterwards, in `create_snapshot_for_variant` in `backend/app/snapshots/service.py`. The snapshot row's `render_context` already exists. Today it holds references per module, not copies of field values, and for push it also holds the inline artifact (decided 2026-09-17, recorded in that function's docstring as not settling the storage question).

Two consequences follow from that.

- **An edit made after approval goes out unreviewed.** The send reads the live variant, so whatever changed between snapshot and send is what the recipients get.
- **"What did recipient X get in send Y" cannot be answered.** Module data, subject and preheader have no history. Non-personalised decision resolutions are overwritten in place (`backend/app/decision/service.py`). Which content version was used is not recorded. Templates and CSS are unversioned files.

task-129 recorded the candidate direction: no full HTML per recipient, but a compact structured record that is re-rendered on demand. The same direction was argued in the privacy interview behind [[ADR-154 — Erasure and Retention]]. Its point 5 says rendered snapshots contain merged personal data, and it calls that "a further argument for reconstructing renders on demand from a structured record rather than persisting per-recipient HTML" (the same point is in `docs/playbook-strategy.md`'s decision log). The strategy file lists snapshot storage as a deferred, open Needs-ADR item. It has no separate decision-log entry for this decision, which the user took on 2026-10-02.

**This is a supersession, not a dated addendum.** It is the second one in this repository; the first was [[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]] superseding [[ADR-001 — Newsletter Architecture Boundaries]] on 2026-09-12. An addendum was considered first, because that is the established way to amend an Accepted record. It cannot do this job. ADR-062's Decision requires that a snapshot store final HTML at minimum, and its Notes make that HTML the source of truth for the snapshot. This record stops storing rendered output at all and makes the structured composition the source of truth. Rewording cannot get there. The Decision itself changes, so ADR-062 is not edited. This record replaces it, and ADR-062's status points here.

Pixel-exact reconstruction was considered and not chosen. It would mean versioning templates and brand CSS, and the user decided that content must be exact while layout is best-effort (point 4). Storing per-recipient HTML was rejected. It is the thing being dropped, and it holds personal data (ADR-154 point 5).

## Decision

**1. A snapshot is a frame: the composition, frozen at snapshot time.**
The frame holds:
- every module's type and position;
- for content-bound and static modules, a **copy** of the final field values: the content version used, the static `module_data`, and the applied override fields;
- for decision-slot modules, the slot reference;
- the envelope (subject and preheader, from the envelope module per [[ADR-162 — Channel Rendering and Artifacts]] point 1), or the push fields;
- a fingerprint of the templates and brand CSS used.

The frame is stored in the snapshot row, in `render_context`. No file is written.

**2. A send renders from the frame, not from the live variant.**
Two things are still decided at send time, on purpose. Per-recipient decision-slot picks are resolved at send time, because that is personalisation. Audience and consent are re-checked at send time ([[ADR-176 — A Negative Decision Outranks a Positive One]] point 4, [[ADR-163 — Per-Channel Consent and Addressability]]). Everything else comes from the frame. An edit made after the snapshot needs a new snapshot before it can be sent. This closes P1-04: the approved composition is what is sent.

**3. Every delivery execution gets a delivery record, written in the send loop.**
The record holds:
- `sent_at`;
- that recipient's decision-slot picks, with a copy of their field values and their content version ids;
- a hash of the rendered output. Per [[ADR-162 — Channel Rendering and Artifacts]] point 3, the hash covers the whole artifact set, not one member.

With the frame, this makes "what content did recipient X get in send Y, as of the send date" answerable exactly.

**4. Fidelity: content exact, layout best-effort.**
Reconstruction re-renders frame plus record with today's templates. It reports two things: whether the template and CSS fingerprint still matches the one used, and whether the re-render's hash equals the sent hash. Templates are not versioned. A layout difference after a template change is reported, never hidden.

**5. HTML snapshot storage is dropped.**
No snapshot files are written. The snapshot preview re-renders from the frame. task-46's non-atomic write disappears with it.

**6. Snapshots made before this change have no frame, and they are not sent.**
They are not live data. A script the user runs drops them, together with the sends anchored to them. In addition, a frameless snapshot is refused at send time. It is never sent from live state.

**7. Not decided here.**
- **Merge context.** No recipient substitution exists yet. When it does, the delivery record must gain the merge context, because [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]] requires it to remain available after delivery.
- **Retention and erasure of delivery records.** These belong to task-136 and [[ADR-154 — Erasure and Retention]].

## Consequences

### Positive
- The approved composition is what is sent. An edit after approval can no longer reach recipients without a new snapshot.
- What each recipient received is reconstructable per send, content exactly, which is what [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]] and [[ADR-128 — Version Content for Auditability and Restoration]] asked for and the code did not provide.
- No HTML files holding personal data are written, so erasure has one less place to reach.
- task-46 dissolves rather than being fixed, because the non-atomic file write no longer exists.
- The two snapshot storage shapes (an email file, an inline push artifact) become one: every channel's frame lives in the row.

### Negative
- Rendering gains a second path. Sending and the snapshot preview render from the frame, while the live editing preview still renders from the variant. Both paths must be kept in step.
- Delivery records grow with sends × decision-slot modules, because each record copies the picked field values.
- Once templates or brand CSS change, the layout of a reconstruction may differ from what was sent. This is reported through the fingerprint and hash comparison, not prevented.
- Existing snapshots, and the sends anchored to them, are lost.

## Notes

- **ADR-061 and ADR-005 are not changed.** [[ADR-061 — Snapshot Based Final Rendering]] asks for an immutable snapshot of the final resolved render state before sending, and the frame is that. It is resolved state, not rendered bytes. [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]] already permits dropping recipient HTML when send-time state stays reconstructable, and this record is that permission being used. Its decision resolutions now survive in the delivery record's copy, even where `backend/app/decision/service.py` overwrites the resolution row in place.
- **ADR-013 is not contradicted.** [[ADR-013 — Content Reference Instead of Content Copy]] governs builder state: a composition references content so that catalog updates reach recurring campaigns. The frame and the delivery record are not builder state. They are records of something that happened, and copying is exactly what keeps them true after the catalog changes.
- **Why copy values when content versions exist.** Content version ids are recorded, as [[ADR-128 — Version Content for Auditability and Restoration]] requires. A copy is still kept, because static `module_data`, override fields and the envelope have no version history of their own.
- **ADR-053 gains its first real implementation.** [[ADR-053 — Maintain Minimal Delivery Execution History]] lists `sentAt` and `contentIds` among delivery history. The delivery record is where they land.
- **ADR-063 parity stays a testing concern.** [[ADR-063 — Rendering Parity Over Rendering Implementation]] holds preview, final rendering and snapshot to the same intended output. The second render path in the Negative list is that parity obligation, made concrete.
- **Where this will need a final-design pass.** Apart from the render itself, the send path's preflight also reads the live variant. `missing_required_fields(db, snapshot.variant_id)` in `send_send_instance` is one example. Each such read must be decided either way before implementation: read from the frame, or deliberately stay live. This record does not decide that.
- **What ADR-062 needs.** Only its status changes, to `Superseded by ADR-183`, in both the frontmatter and `## Status`. Its Decision and its 2026-09-12 addendum stay as written.

## Addendum 2026-10-12 — the send flow tests the frame, and its confirmation counts recipients as of now

**Decided with the user on 2026-10-12, one question at a time, for queue task-67: the send flow in the React client, for the November 2026 presentations (`docs/business/PRESENTATIONS-2026-11.md`).** The Decision above is unchanged. This addendum records how the client's send flow stands on it. Point 3 below follows from point 2: the approved composition is what is sent, so a test of that send must show that composition and not the live variant.

1. **Sending a variant is one guided screen per variant, in four steps.**
   - *Freeze and check.* Creates the snapshot, the frame of point 1, and shows what will go out.
   - *Audience, provider and timing.* Plans the send instance from that snapshot.
   - *Test send* (point 3 below).
   - *Confirm and send* (point 4 below).

   Afterwards the screen leads to the delivery and to the campaign's results section ([[ADR-196 — Reporting Is the Campaign's Results Section; Analysis Belongs in the Adopter's Tools]]).
2. **Approval is unchanged.** A person who may fire a send is its approval ([[ADR-174 — Channel Readiness Is Asserted, Not Computed]] point 4). The approvals inbox remains where sends fired by integrations wait ([[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] point 5 and its addenda). No four-eyes rule is added.
3. **A test send renders the frozen snapshot, not the live variant.** It renders as a chosen recipient, with that recipient's stored slot picks (and later their salutation). It uses the snapshot's own subject prefixed "[Test] ", and the provider the send was planned with, and goes to a typed address. Until now `send_test_email` (`backend/app/delivery/service.py` ~801-947) rendered the live variant in send mode and used a typed-in subject, so an edit made after the snapshot showed in the test but not in the send. A test send stays a test, not a delivery: it creates no delivery execution and carries no unsubscribe link and no click tracking. [[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]] is unchanged. The legal footer goes without the link, as the test-send rule of [[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]] says. The old standalone test page keeps its behaviour.
4. **The confirmation before firing shows the recipients as of now.** That number is the audience re-resolved the way the send will count it, by `recipients_now` in `backend/app/delivery/service.py`. Until now only the integration ceiling gate used it. The provider and the sender are shown with it. The old Jinja confirm showed the planned count (`recipient_count` in `backend/app/frontend/router.py` ~2915). That count could differ from who receives the send, because audience and consent are re-checked at send time (point 2). With a real provider the action is spelled out ("Send real email to N people") with a short warning. The recipient cap still refuses anything above it, both at plan and at fire.

**Consequence.** Two test-send behaviours now exist side by side: the flow's, rendered from the frame, and the standalone page's, rendered from the live variant. This is the second render path of the Negative list, reaching test sends.

**No decision-log entry.** `docs/playbook-strategy.md` has no entry for this decision. The reasoning comes from the 2026-10-12 session and task-67.

## Related ADRs

### Depends On
- [[ADR-062 — Snapshot Stores Final Render State]]
- [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]]
- [[ADR-061 — Snapshot Based Final Rendering]]
- [[ADR-128 — Version Content for Auditability and Restoration]]
- [[ADR-162 — Channel Rendering and Artifacts]]

### Enables
- [[ADR-053 — Maintain Minimal Delivery Execution History]]

### Referenced By
- [[ADR-013 — Content Reference Instead of Content Copy]]
- [[ADR-063 — Rendering Parity Over Rendering Implementation]]
- [[ADR-154 — Erasure and Retention]]
- [[ADR-163 — Per-Channel Consent and Addressability]]
- [[ADR-176 — A Negative Decision Outranks a Positive One]]
