"""Finding a recipient by identifier or address (2026-10-03).

Decided with the user: an audience's reach and a send's recipients show a
sample, not a paged list, and a manager looking for someone specific searches.
One rule, here, in two forms — Python for a list already resolved (an
audience's reachable set), SQL for one still in the database (a send's
executions) — so the two screens find the same people for the same words.

**The rule:** case-insensitive, part-match, on the recipient's external
identifier OR their address on the channel in question (the email address, a
push token). The address is personal data; the screens already show it beside
each recipient, and it is what a manager actually knows.
"""
from sqlalchemy import exists, or_

from app.recipients.consent import address_key_for
from app.recipients.db_models import AddressabilityDB, RecipientDB


def _needle(q: str | None) -> str | None:
    q = (q or "").strip().lower()
    return q or None


def matches(q: str | None, external_id: str | None, address: str | None) -> bool:
    """The rule over values already in hand. No search matches everyone."""
    needle = _needle(q)
    if needle is None:
        return True
    return needle in (external_id or "").lower() or needle in (address or "").lower()


def clause(q: str | None, recipient_id_column, channel: str):
    """The same rule as a SQL condition on a query that carries a recipient id.

    `exists` rather than a join: a recipient can hold several addresses on one
    channel (a phone and a tablet), and a join would repeat their row once per
    address — wrong for the rows and for the count.
    """
    needle = _needle(q)
    if needle is None:
        return None
    return or_(_by_identifier(needle, recipient_id_column),
               _by_address(needle, recipient_id_column, [channel]))


def clause_any_channel(q: str | None, recipient_id_column):
    """The same rule, matching an address on ANY registered channel — for the
    recipients list, where no channel is in question. Each channel's own
    address key is read, never the JSON as text: searching "email" must not
    match every row because it is a key name."""
    from app.channels.registry import list_channels

    needle = _needle(q)
    if needle is None:
        return None
    channels = [c.name for c in list_channels()]
    return or_(_by_identifier(needle, recipient_id_column),
               _by_address(needle, recipient_id_column, channels))


# `icontains(..., autoescape=True)`: a typed % or _ is a character to find,
# not a wildcard — "50%" finds "50%", not everything starting with "50".

def _by_identifier(needle: str, recipient_id_column):
    return exists().where(RecipientDB.id == recipient_id_column,
                          RecipientDB.external_id.icontains(needle, autoescape=True))


def _by_address(needle: str, recipient_id_column, channels: list[str]):
    return or_(*[
        exists().where(
            AddressabilityDB.recipient_id == recipient_id_column,
            AddressabilityDB.channel == channel,
            AddressabilityDB.value[address_key_for(channel)].as_string()
            .icontains(needle, autoescape=True),
        )
        for channel in channels
    ])
