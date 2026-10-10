---
id: TASK-353
title: 'Discuss: drop open tracking altogether (ePrivacy), so only clicks count'
status: To Do
assignee: []
created_date: '2026-10-10 22:02'
labels:
  - needs-adr
  - backend
dependencies: []
type: decision
ordinal: 300195
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Decision, to discuss]** Should the platform stop offering open tracking altogether, so that only clicks count? Raised by the user 2026-10-10. Nothing is decided; this records the question, the two positions and what each would touch.

**The trigger, as the user put it** (to confirm with legal advice before anything is decided):
- France changed its rules so that tracking in email, open tracking included, needs an opt-in.
- The EU is expected to follow.

**The user's position so far:** a company decides for itself whether it uses opens.

**The new thought:** opens are unreliable anyway, so the platform could say plainly that it does not offer them; only clicks count.

**How opens are used today** (verified 2026-10-10):
- **Collected:** the provider's email.opened webhook event becomes an 'open' engagement event (backend/app/providers/adapters/resend.py around :27-31; providers/service.py around :133-200).
- **Interest signals:** opens are content-tied events (insight/service.py :17), but their default weight is 0.0, 'Apple MPP makes opens noise - off by default' (insight/signals.py :11, :25). A company can raise it in the signal settings.
- **Audience rules:** can select people who 'opened it' (ADR-188; audience/service.py :121, :759; frontend AudienceEngagement.tsx).
- **The tracking pixel is not ours:** the rendered email adds none; it is the provider's open-tracking switch, set per sending domain in Resend.
- **Business record:** the 2026-07-05 triage (finding J1) decided that open, click and conversion all count as positive interest. That still reads as current in the playbook.

**For dropping opens:**
- It is the safe legal default if open tracking needs an opt-in: no consent machinery to build for it.
- Opens are already noise: Apple Mail Privacy Protection pre-fetches images, and bots open mail. The default weight is already 0.
- It simplifies the engagement model and the explanation ('only clicks count').
- It fits 'transparency' and 'control' as differentiators.

**Against, or what it costs:**
- Some adopters rely on open rates for deliverability monitoring and subject-line testing.
- It removes a choice the platform now leaves to the company, which is the user's earlier position.
- It reverses part of J1 (2026-07-05) and ADR-188's 'opened' rule.
- Clicks are tracked too (tracked links); whether click tracking needs consent under the same rules is a question this decision should not leave unasked.

**Options to weigh:**
1. **Keep it as the company's choice.** Today's state: default weight 0, the provider switch is the company's, documented.
2. **Drop opens altogether.**
   - The platform ignores open events from the provider.
   - 'opened' leaves the audience rules.
   - The open weight setting goes.
   - The reference deployment says to switch provider open tracking off.
   - A business decision supersedes J1's open part, and ADR-188 and ADR-164 get addenda.
3. **Opens only with a tracking consent:** a consent purpose 'tracking' (task-134's vocabulary), with opens recorded only for people who gave it. The most correct, and the most to build.

**Related:**
- ADR-164 (channel feedback and signals);
- ADR-188 (engagement in audience rules);
- ADR-163 (consent per purpose);
- task-134 (purpose vocabulary);
- task-305 (complaints as signal);
- docs/reference-deployment.md (provider settings);
- playbook §5, 2026-07-05 (J1).
<!-- SECTION:DESCRIPTION:END -->
