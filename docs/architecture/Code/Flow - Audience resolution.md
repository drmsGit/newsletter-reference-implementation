---
type: code-flow
topic:
  - architecture
  - audience
created: 2026-07-27
modified: 2026-07-27
---

# Flow - Audience resolution

> Part of [[MOC - System Overview]]. How a saved audience group becomes a concrete
> list of people to send to. This is the step [[Flow - Send a campaign]] calls
> first (`prepare_send_from_audience` → `resolve_audience`).

## In one sentence

An audience group is resolved **live** — union its include rule blocks, subtract
its exclude blocks, add back the manually pinned recipients, then drop anyone not
consenting — so the recipient list reflects the rules *and the data* at the moment
you resolve.

## The formula

```
resolve_audience(group) =
    ( (∪ include blocks)  −  (∪ exclude blocks) )  ∪  (manual pins)
    then keep only consent_status == "opted_in"
```

```mermaid
graph TD
    G[Audience group] --> B[Rule blocks]
    G --> P[Manual pins]
    B --> INC[∪ include blocks]
    B --> EXC[∪ exclude blocks]
    INC --> SUB[includes − excludes]
    EXC --> SUB
    SUB --> UNI[∪ manual pins]
    P --> UNI
    UNI --> CF{consent floor:\nopted_in only}
    CF --> OUT[Final recipient list]
```

## Step by step ([[audience]] `resolve_audience`)

1. **Load the blocks.** Each `AudienceRuleBlockDB` carries a `criteria` payload (language × status × category × min-score). `_recipients_for_criteria` evaluates it to a recipient set — a category min-score uses the recipient's **live [[insight]] signal**, so "interested in Hiking ≥ 40" re-evaluates as behavior changes. **It gates on consent for the channel being resolved**, which it did not before 2026-09-29: a push block asked about email consent, so a push-only recipient could not be included at all.
2. **Union the includes.** All `kind="include"` blocks combine with **OR** — stack "interested in Hiking" OR "interested in Food", each editable/counted independently.
3. **Union the pins.** `AudienceGroupMemberDB` manual pins join the include set. They are hand-picked people alongside the rules ("keep both"), and unlike the rules they are stored rows rather than a live query.
4. **Subtract the excludes.** All `kind="exclude"` blocks are unioned and removed from the includes **and the pins together** — so **an exclude block removes a hand-pinned recipient** ([[ADR-176 — A Negative Decision Outranks a Positive One]] point 1, 2026-09-29). This reverses the 2026-07-26 rule, under which pins were added back *after* this step and survived it; the order of steps 3 and 4 is the whole decision.
5. **Apply the consent floor.** The result is filtered to `consent_status == "opted_in"` ([[recipients]] `CONSENTING_STATUS`). A non-consenting recipient is excluded even if pinned (legal, non-negotiable) — and unlike an exclude block this floor is not a precedence question between two people's intentions at all.
6. **Return** the recipient rows (ordered by id).

**What this deliberately does not do: ask whether anybody is reachable.** Until 2026-09-29 step 1 also dropped every recipient with no usable email address. That narrowed *exclude* blocks, which is backwards — dropping somebody from an exclusion puts them back in the audience — so an unaddressable recipient could be pinned in and no exclude block could remove them. Membership now answers *who did the manager mean*; addressability and address deduplication are stage 1 of the send-time exclusion stack, where [[ADR-163 — Per-Channel Consent and Addressability]]'s 2026-09-12 addendum point 3 put them, and where the drop carries a recorded reason instead of a log line. **A screen showing a count runs that stage too** — that addendum's rider — so the group page reports reachable and unreachable separately rather than one number that flatters.

## Where this is used

- [[delivery]] `prepare_send_from_audience` — materialize a send's executions (see [[Flow - Send a campaign]]).
- [[delivery]] `reconcile_executions_to_audience` — **every** send re-resolves *here* just before firing ([[ADR-176 — A Negative Decision Outranks a Positive One]] point 4), so a send can reach a different set than the plan showed.
- [[frontend]] — the group-detail "net audience" preview and the list-page recipient counts.

## Suggestions (use case 1)

A group can be **seeded from a campaign**: [[audience]] `create_suggested_group_for_campaign` reads the campaign's content categories ([[content]] assignments + resolved [[decision]] picks) and creates one `source="suggested"` include block per top category. `recalculate_suggested_blocks` re-derives them delta-only when the campaign's content changes — preserving manager-tuned thresholds and never touching manual blocks/pins. Engagement-driven suggestions are **parked** behind [[MOC - Automation Architecture|automation]].

## Modules this flow passes through

[[audience]] → [[content]] / [[insight]] (criteria evaluation) → [[recipients]] (consent floor). Seeding also reads [[campaigns]].

## ⚠️ Gotchas for a new dev

- **Precedence order is load-bearing.** Pins union *after* excludes subtract. An earlier version put pins into includes before subtracting excludes, so excludes silently dropped pins (group showed 17 instead of 21) — don't reorder.
- **Hard suppression ≠ an exclude block.** Bounces/opt-outs belong on the consent floor so they stay hard against pins. A regular exclude block would be overridden by a pin.
- **Resolution is live, not frozen, and there is no longer a choice about it.** The same group resolves differently next week as signals/consent change, and since [[ADR-176 — A Negative Decision Outranks a Positive One]] point 4 (2026-09-29) every send re-resolves immediately before firing. The `"freeze"` mode that captured a moment is refused; existing rows keep the value because it records how those sends were planned.
- **A group can resolve to 0** — [[delivery]] refuses to plan an empty send.
