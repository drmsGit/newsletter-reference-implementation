---
type: adr
status: accepted
topic:
  - architecture
  - reporting
  - analytics
  - engagement
  - consent
  - campaign
created: 2026-10-11
modified: 2026-10-11
source:
  - "task-58 final-design pass, decided by the user 2026-10-11; absorbs task-360"
depends_on:
  - "[[ADR-020 — Campaign Equals Newsletter]]"
  - "[[ADR-103 — Provider Events Are Normalized Into Internal Events]]"
  - "[[ADR-129 — Correlate Provider Events to Delivery Executions]]"
  - "[[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]"
  - "[[ADR-124 — DWH Is Recommended but Not Mandatory]]"
  - "[[ADR-154 — Erasure and Retention]]"
  - "[[ADR-163 — Per-Channel Consent and Addressability]]"
  - "[[ADR-164 — Channel Feedback and Signals]]"
  - "[[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]]"
  - "[[ADR-195 — A Transactional Send Skips the Opt-In Check, Never Provider Suppression]]"
  - "[[ADR-150 — Tenancy and Access Model]]"
  - "[[ADR-172 — The Working Brand Is Resolved Once and Carried Into Every Query]]"
  - "[[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]"
---

## Status
Accepted

## Context

**Reporting was parked with its shape sketched, not designed.** Queue task-58 was parked by the user on 2026-09-18 with the framing *"we are no analytics platform, you get what you need and an easy way to export everything."* Its sketch was a view that selects a newsletter and/or audience group and shows KPIs with summaries and averages, plus an export to an external BI tool for everything beyond that. Queue task-360, raised on 2026-10-11, asks that choosing a campaign on Monitoring open how it went rather than its editor (`frontend/src/screens/Monitoring.tsx:74`). Its notes already lean towards a collapsible section on the campaign page instead of a new screen. Both were settled in one final-design pass on 2026-10-11.

**What the data model allows.** Verified 2026-10-11:

- **A campaign is one newsletter, with no series entity above it.** [[ADR-020 — Campaign Equals Newsletter]] keeps broader initiatives as metadata or external grouping, and lists "broader marketing initiatives need metadata or external grouping" among its Negative consequences. A campaign reaches an audience group only per send, through `send_instances.audience_group_id`. So "this audience group across campaigns" and "this weekly series" are not things the model holds.
- **Engagement is keyed only by the delivery execution.** `engagement_events` (`backend/app/insight/db_models.py:6-32`) carries `delivery_execution_id` and an `event_type`, nothing else about the person or the send. That is the correlation of [[ADR-129 — Correlate Provider Events to Delivery Executions]] over the normalised vocabulary of [[ADR-103 — Provider Events Are Normalized Into Internal Events]]. A click is one row per provider event: nothing makes clicks unique per recipient. Opens are recorded, but whether they stay is open in task-353 (ePrivacy).
- **A send's counts are already stored.** `send_instances` carries `sent_count`, `failed_count` and `excluded_count` (`backend/app/delivery/db_models.py:49-65`). An uncertain delivery counts with the failures (`backend/app/delivery/service.py:1429-1435`). Each excluded execution records which stage of the exclusion stack dropped it in `exclusion_reason` (`backend/app/delivery/db_models.py:88-98`).
- **Unsubscribes cannot be counted per send today.** An unsubscribe is a `consent_events` row with source `unsubscribe`. The token of [[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]] resolves through the delivery execution, but the consent event it writes keeps no link to that execution or its send (`backend/app/recipients/db_models.py:33-81`). A provider suppression is the same: `suppress_recipient` (`backend/app/recipients/service.py:39-96`) writes a `provider`-sourced consent event, and the webhook that calls it holds the delivery execution (`backend/app/providers/service.py:214-241`) but does not pass it on.

**What exists to look at.** `GET /campaigns/monitoring` (`backend/app/campaigns/router.py:143-162`) gives each campaign's state, with no counts. The Deliveries screens show the stored sent, failed and excluded counts per send. No click, open or bounce figure appears anywhere in the React client.

**What exists to export.** Nothing. There is no export anywhere in the code, and no retention or prune job ([[ADR-154 — Erasure and Retention]], implementation status note). Three records already bound this ground:

- [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]] point 4: the system is operational, not a warehouse. It keeps a bounded retention window, and signal contributions leave through an export boundary to the adopter's DWH (task-85).
- [[ADR-124 — DWH Is Recommended but Not Mandatory]]: cross-channel analytics benefits from an analytical store, and the platform runs without one.
- [[ADR-154 — Erasure and Retention]] point 4a: an erasure must reach whatever the export path feeds, or the export becomes an erasure loophole.

**Where the parked sketch is narrowed.** The pass kept the "not an analytics platform" framing and dropped two parts of the sketch. The audience-group selector and the averages are dropped, because the model holds neither a series nor a cross-campaign audience (above). The built export is dropped, because what form it should take is decided by the adopter's analysis system, not by this platform (point 8). Task-360's "what is still missing" view for unsent campaigns is dropped from this record (point 2).

## Decision

**1. The application's one KPI view is a collapsible Results section on the campaign page.**

- **Monitoring keeps linking to the campaign page.** There is no separate results screen.
- **There is no audience-group selector and no multi-campaign selector.**
- **Comparison across campaigns, series or audience groups is the job of the adopter's analytics tool.**

**2. The section appears only once at least one of the campaign's sends has gone out.**

- **Nothing is shown for unsent sends.** Planned and scheduled sends stay on the Deliveries screens.
- **A readiness or "what is missing" check is not part of this.**

**3. One row per variant, summed over all of that variant's sends that went out.** The figures:

- **Recipients:** delivery executions.
- **Sent.**
- **Delivered:** email only. The distinct executions with a delivered event.
- **Failed:** failed plus uncertain, as the stored `failed_count` already counts them.
- **Excluded:** with a breakdown per exclusion stage.
- **Bounced:** the distinct executions with any bounce event. Soft bounces are included.
- **Complaints:** the distinct executions with a complaint event.
- **Total clicks:** click events.
- **Unique clickers:** the distinct executions with at least one click event.
- **Click rate.**
- **Unsubscribes** (point 6).

**4. A campaign line on top, with the totals of the variant rows.**

- **Every click rate is unique clickers over sent,** per variant and for the campaign.
- **The campaign's rate is pooled:** its unique clickers over its sent, not a mean of the variant rates.
- **Sent, not delivered, is the denominator, so email and push compare like for like.** Push has no delivered or open events.

**5. Opens are not shown now, and per-link figures are not here.**

- **Room is kept for opens.** If task-353 keeps opens as a company choice, they join as one more figure. Nothing is built for them by this record.
- **Per-link and per-content figures belong to the content catalogue side** (task-359), not to the campaign's section.

**6. An unsubscribe is attributed to the delivery execution it came through.**

- **`consent_events` gains a nullable `delivery_execution_id`,** a foreign key with `ON DELETE SET NULL`.
- **It is set when the consent event is written through a send's unsubscribe token** ([[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]]). Every row of an "everything from the company" opt-out carries the same execution.
- **It is set when a provider suppression is written from an engagement event** ([[ADR-195 — A Transactional Send Skips the Opt-In Check, Never Provider Suppression]] point 2).
- **A send's unsubscribes are the distinct executions with an unsubscribe-sourced consent event linked to them.** So a repeated click, or an everything opt-out that writes several rows, counts once.
- **Unsubscribes written before this record carry no link and are not counted.** For a send that went out before the attribution existed, the section says so.

**7. Figures are computed on read from the operational tables. Nothing new is stored.**

- **The endpoint is `GET /campaigns/{id}/results`.**
- **It is behind `view`, like every read,** and scoped to the working brand ([[ADR-172 — The Working Brand Is Resolved Once and Carried Into Every Query]]).
- **It is not added to `MACHINE_READS`.** That matches the rule recorded in `backend/app/auth/policy.py:271-273`: reporting stays behind `view`.

**8. No data export is built.**

- **Export for analysis is a full IT task for the adopter.** The analysis system decides whether it wants CSV, endpoints, or a replica with ETL.
- **The application gets no export configuration screen.**
- **The options are documented as a how-to chapter,** in a later docs task. Its message: if you want analysis in detail, there are better tools for that.
- **The per-person export boundary for signal contributions is untouched.** It remains task-85, under [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]].

## Consequences

### Positive

- **One place, and no new screen.** A manager finds how a campaign went on the campaign page, from Monitoring as from anywhere else.
- **The figures cannot drift from the operational data,** because nothing new is stored. A correction to an execution or an event shows at the next read.
- **Unsubscribes become attributable to a send.** Until now they could only be counted per brand.
- **Channels compare like for like.** One click-rate definition holds for email and push, per variant and for the campaign.
- **The platform stays out of the analytics business.** The adopter's own tools do comparison, series and averages, and the export takes the shape those tools want.

### Negative

- **No cross-campaign comparison in the application.** There are no averages over a weekly series and no view per audience group. An adopter without an analytics tool has the campaign page and nothing more.
- **Old campaigns' figures will shrink once retention pruning arrives** (task-136, task-85), because they are computed on read. Keeping them needs aggregates written before rows are pruned. That must be decided with the retention policy. An erasure has the same effect on a smaller scale: [[ADR-154 — Erasure and Retention]] point 2 removes a person's delivery executions and engagement events, and its Negative consequences already accept that historical volumes shift.
- **Unsubscribes before 2026-10-11 are not attributed,** so a send that went out before then undercounts them.
- **Bounced includes soft bounces,** so it overstates permanent failures.
- **Unique counting is per delivery execution.** A person who received two sends of the same variant counts twice in that variant's row.
- **Click rate over sent, not delivered, slightly understates email engagement.**
- **Opens are absent until task-353 decides.**

## Notes

- **Not a supersession, and no record's Decision is edited.**
  - [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]] point 4's export boundary for contributions stands. Point 8 above concerns export for analysis, which ADR-132 did not decide.
  - [[ADR-164 — Channel Feedback and Signals]] point 3 sends aggregate results to a human-read reporting view, never to the decision path. The Results section reads only per-recipient engagement events. Where aggregate metrics would be shown, once ingested, is not decided here; their ingestion is not built (ADR-164, Notes).
  - [[ADR-020 — Campaign Equals Newsletter]] said grouping stays flexible "for reporting and analytics". Point 1 places that grouping in the adopter's tool.
- **The how-to chapter carries ADR-154's obligation.** Point 4a of [[ADR-154 — Erasure and Retention]] requires any export path to carry the internal identifier so a downstream deletion is possible. Since the adopter builds the export (point 8), the chapter has to say so.
- **`ON DELETE SET NULL` fits ADR-154 point 6.** When an erasure removes a person's delivery executions, the minimised consent record it keeps survives, with its link emptied.
- **No change to the integration read rule.** The playbook decision log entry of 2026-10-08, "An integration reads what its permission writes" (`docs/playbook-strategy.md` §5), said read-only permissions could come "when a read-only integration exists (reporting, task-58)". This record builds no export, so task-58 does not bring one. Reporting stays behind `view`, as that entry's point 2 and the 2026-10-08 addendum to [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] already have it.
- **No decision-log entry for this pass.** `docs/playbook-strategy.md` §5 has none. The reasoning above is from task-58's parked description, task-360's description and notes, and the user's answers of 2026-10-11.
- **Queue tasks.**
  - **task-58:** the parked reporting item this record settles.
  - **task-360:** Monitoring opening a results overview. Absorbed into point 1. Its "what is missing" half for unsent campaigns is not carried (point 2).
  - **task-353:** whether open tracking stays (point 5).
  - **task-359:** content and category KPIs, where per-link figures belong (point 5).
  - **task-85:** the DWH export boundary for signal contributions (point 8), and one of the two prunes that will shrink computed figures.
  - **task-136:** the general retention policy, which must decide whether aggregates are kept before pruning.

## Related ADRs

### Depends On
- [[ADR-020 — Campaign Equals Newsletter]] — no series entity; a campaign reaches an audience group only per send.
- [[ADR-103 — Provider Events Are Normalized Into Internal Events]] — the event vocabulary the figures count.
- [[ADR-129 — Correlate Provider Events to Delivery Executions]] — every event is keyed to an execution, which is what "distinct executions" counts.
- [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]] — operational, not a warehouse; the export boundary for contributions, untouched.
- [[ADR-124 — DWH Is Recommended but Not Mandatory]] — analysis belongs in an analytical store the platform does not require.
- [[ADR-154 — Erasure and Retention]] — erasure must reach exports (4a); pruning and erasure shrink computed figures.
- [[ADR-163 — Per-Channel Consent and Addressability]] — the consent events that gain the execution link, and the exclusion stages the breakdown shows.
- [[ADR-164 — Channel Feedback and Signals]] — aggregates live in reporting rather than the decision path.
- [[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]] — the token whose execution an unsubscribe is now linked to.
- [[ADR-195 — A Transactional Send Skips the Opt-In Check, Never Provider Suppression]] — the provider suppression that also records its execution.
- [[ADR-150 — Tenancy and Access Model]] — reads behind `view`, scoped to a brand.
- [[ADR-172 — The Working Brand Is Resolved Once and Carried Into Every Query]] — the working brand the endpoint is scoped to.
- [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] — its 2026-10-08 addendum keeps reporting behind `view`; this record adds nothing to `MACHINE_READS`.
