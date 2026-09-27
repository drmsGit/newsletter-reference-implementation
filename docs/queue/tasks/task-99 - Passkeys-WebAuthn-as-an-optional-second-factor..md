---
id: TASK-99
title: Passkeys / WebAuthn as an optional second factor.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 205200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — ON HOLD pending the user's own research (2026-08-02).** **Passkeys / WebAuthn as an optional second factor.** The *shape* is already decided in [[ADR-151 — Authentication and Sessions]] §6: passkeys are an **additive layer, never a replacement**, because a passkey must be enrolled and recovered and that path is the email code — so the code flow stays mandatory underneath either way. **Deferred deliberately:** a six-digit code with a short TTL, single use and attempt limiting is adequate for now, and passkeys are a nice-to-have rather than a gap. The user wants to survey the options before choosing. **Finding that shaped the deferral:** `webauthn 3.0.0` installs cleanly on Python 3.14, but it is not one package — it pulls `cryptography`, `pyOpenSSL`, `cbor2`, `cffi`, `pyasn1`, `pyasn1_modules` and `pycparser`, so seven transitive dependencies land on a deliberately nine-line `requirements.txt`, one of them carrying compiled extensions. Worth weighing against the **Cyber Resilience Act** obligations noted in [[ADR-152 — Secret and Credential Handling]]: SBOM and vulnerability handling make a compiled crypto dependency something to adopt deliberately rather than incidentally. Assessment if it goes ahead: `webauthn` is the standard Python implementation and `cryptography` is about as well-maintained as Python packages get, so the objection is posture rather than risk. **Also still open from ADR-151:** step-up authentication for destructive actions, for which an enrolled passkey would be an attractive factor. Source: user, 2026-08-02.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 279, section "Features", position 52 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
