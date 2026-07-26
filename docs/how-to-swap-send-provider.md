# How to swap the send provider

*Vendor-neutrality in practice: what it takes to replace Resend with a different ESP (SendGrid, Postmark, Mailgun, Amazon SES, …).*

## TL;DR for the client

**Outbound sending: super fast.** The provider is one class behind a 3-in / 3-out
contract, plus one line in a factory. Swapping ESPs is ~1 new file and a couple of
env vars — an hour of work, no changes to campaigns, variants, recipients, or the
send loop. That is the whole point of the provider layer (ADR-100/105): nothing
above it knows or cares which ESP is used.

**Inbound feedback (opens/clicks/bounces): a bit more work, but isolated.** Only
needed if you want engagement events back from the new provider. It's a separate
adapter surface (webhook endpoint + signature check + event-name mapping) that
does *not* block sending. Parked in this build until DNS verifies — see the last
section.

---

## The outbound adapter — files

All under `backend/app/delivery/providers/`:

| File | Role |
|------|------|
| [`base.py`](../backend/app/delivery/providers/base.py) | The contract. `DeliveryProvider` ABC with one method: `send(recipient_email, subject, html) -> SendResult`. `SendResult` = `{success, provider_message_id, message}`. |
| [`resend.py`](../backend/app/delivery/providers/resend.py) | The real worked example — httpx POST to Resend's API, credentials from env, maps the HTTP response to `SendResult`. Never raises on a send failure; returns `success=False` with the provider's message. |
| [`mock.py`](../backend/app/delivery/providers/mock.py) | No-op provider that always "succeeds" with a fake id. Default when no provider is set. |
| [`factory.py`](../backend/app/delivery/providers/factory.py) | Maps a provider **name string** → provider instance. This is the only place names are wired up. |

That is the entire outbound surface. A provider only ever sees an **email address,
a subject, and rendered HTML** — never campaigns, variants, audience, or DB rows
(ADR-104: audience ownership stays outside the provider).

## How it connects to campaigns / deliveries

The provider sits at the very end of the chain and is chosen by a **name string**,
not a hard-coded import:

```
Campaign → Variant → Snapshot → SendInstance ──(provider="resend")──▶ send loop
                                     │
                                     └─ DeliveryExecution (one per recipient)
                                              │
              render_variant_html(per recipient) ──▶ provider.send(email, subject, html)
                                                              │
                                              status "sent"/"failed" + provider_message_id
```

- The provider name lives on `SendInstanceDB.provider` (a plain string column).
- [`send_send_instance()`](../backend/app/delivery/service.py) does the work: it
  calls `get_provider(send_instance.provider or "mock")` **once**, then loops over
  the send instance's `DeliveryExecution` rows, renders each recipient's HTML, calls
  `provider.send(...)`, and writes `sent`/`failed` + the provider's message id back
  to each execution.
- The UI live-send ([`/ui/send-test`](../backend/app/frontend/router.py)) calls the
  same `get_provider(name).send(...)` directly, defaulting to `"resend"`.

Because selection is by string and the contract is fixed, **nothing above the
factory changes when you swap ESPs.**

## Steps to add / swap a provider

1. **Write the adapter.** New file `backend/app/delivery/providers/<name>.py` with a
   class implementing `DeliveryProvider.send()`. Copy `resend.py` as the template:
   build the ESP's request, read credentials from `os.environ`, map the response to
   `SendResult`. Keep the "never raise on send failure" rule — return
   `success=False` with a message so the send loop records `failed` instead of
   crashing (ADR-086 spirit).

2. **Register it in the factory.** Add one branch to
   [`factory.py`](../backend/app/delivery/providers/factory.py):
   ```python
   if provider_name == "postmark":
       return PostmarkProvider()
   ```

3. **Point sends at it.** Set `provider="<name>"` on new SendInstances, and/or change
   the send-test form default (`provider: str = Form("resend")` in
   `frontend/router.py:139`). Optionally flip the fallback default from `"mock"`.

4. **Add credentials to `backend/.env`** (gitignored): the API key and verified from
   address for the new ESP. Never hard-code secrets.

That's the whole outbound swap. No migrations, no changes to rendering, delivery
tracking, or the UI.

## Inbound feedback (optional, separate)

If you also want opens/clicks/bounces back from the new provider, that's a *different*
adapter — deliberately not built yet in this repo (parked until DNS verifies). The
matching logic already exists: [`ingest_provider_event()`](../backend/app/providers/service.py)
correlates incoming events to a `DeliveryExecution` by `provider_message_id` and
quarantines anything unmatched (ADR-129). To wire a new provider's inbound:

- Add a webhook route that receives the ESP's callbacks.
- Verify the webhook signature (per-provider).
- Normalize the ESP's event-type names to our internal names before calling
  `ingest_provider_event` (ADR-103).

Note: "inbound" here = **webhooks (HTTP callbacks, no DNS)**, not an ESP's
MX/inbound-email receiving feature.

## Why it's cheap — the one-line summary for Tuesday

> Sending is behind a 3-field contract and a name→class factory. New provider =
> one new file + one factory line + env vars, an hour's work, zero changes to
> everything upstream. Getting engagement data *back* from a new provider is a
> separate, larger-but-isolated piece (a webhook adapter) that we've parked.
