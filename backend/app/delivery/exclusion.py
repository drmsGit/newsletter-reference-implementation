"""The send-time exclusion stack (ADR-163 point 7).

Four ordered stages, run immediately before an artifact is handed to a
provider. Every stage answers one question about one recipient, and a recipient
who fails any stage is excluded **with the reason recorded** — which is the
whole point, and the property whose absence made the open P0 read as a
rendering behaviour rather than a compliance defect (point 8).

    1. addressability — is there a valid address for this channel?
    2. consent        — is there a grant for this (channel, purpose)?
    3. suppression    — hard bounce, complaint, manual blocklist
    4. frequency      — post-POC (ADR-161 point 8)

**Why this exists at all.** Consent is checked when an audience is resolved,
but a `freeze` send materialises its executions at plan time and then never
looks again. Someone who opts out between planning and sending is still mailed.
Re-resolving the audience is not the fix — that is what `rerun` mode does, and
it changes *who is targeted*, which a frozen send deliberately does not want.
The fix is to re-check *permission* without re-checking *targeting*: freezing
targeting must never freeze permission to contact.

**Order is a performance decision, not a correctness one (point 9).** All four
stages are ANDed, so the order never changes who is excluded — only how many
rows reach the later, more expensive stages. The intuition that consent should
come first is right for email and probably wrong for push: on email everyone
has an address and some opted out, so consent is the selective filter; on push
few people have a live token at all while most who installed granted
permission, so addressability is. Most-selective-first is therefore
channel-dependent and is deliberately **not** hardcoded as universal. The order
below is the documented default for email.

**Stages are set operations, not per-recipient loops (point 10).** Each stage
takes the surviving set and returns a smaller one; the difference is the
exclusion, recorded in bulk. That keeps per-stage attribution without the N+1
the send path is already flagged for.
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.recipients.consent import (
    DEFAULT_CHANNEL,
    DEFAULT_PURPOSE,
    is_consenting_filter,
    resolve_emails,
)
from app.recipients.db_models import RecipientDB

# Stage names, recorded verbatim on the execution row so "why didn't Anna get
# this?" is answerable from the data rather than from a log line.
STAGE_ADDRESSABILITY = "addressability"
STAGE_CONSENT = "consent"
STAGE_SUPPRESSION = "suppression"
STAGE_FREQUENCY = "frequency"


@dataclass(frozen=True)
class Exclusion:
    """One recipient, dropped by one stage, for one stated reason."""

    recipient_id: int
    stage: str
    reason: str


class ExclusionStackResult:
    """What survived, what did not, and the address for each survivor.

    The addresses come back because stage 1 had to resolve them anyway —
    making the caller resolve them a second time would reintroduce exactly the
    per-recipient query this stack exists to avoid.
    """

    def __init__(
        self,
        eligible: set[int],
        addresses: dict[int, str],
        exclusions: list[Exclusion],
    ):
        self.eligible = eligible
        self.addresses = addresses
        self.exclusions = exclusions

    def reason_for(self, recipient_id: int) -> str | None:
        for exclusion in self.exclusions:
            if exclusion.recipient_id == recipient_id:
                return f"{exclusion.stage}: {exclusion.reason}"
        return None


def run_exclusion_stack(
    db: Session,
    recipient_ids: set[int],
    *,
    channel: str = DEFAULT_CHANNEL,
    purpose: str = DEFAULT_PURPOSE,
) -> ExclusionStackResult:
    """Run the four stages over a set of recipients.

    Returns the survivors, their resolved addresses, and one `Exclusion` per
    dropped recipient. Never raises for an excluded recipient — exclusion is an
    ordinary outcome, and a stack that raised would make the common case an
    exception path.
    """
    exclusions: list[Exclusion] = []
    surviving = set(recipient_ids)

    if not surviving:
        return ExclusionStackResult(set(), {}, exclusions)

    # --- Stage 1: addressability ------------------------------------------
    # One query for the whole set. A recipient with no active address on this
    # channel is not reachable, which is a different fact from having refused
    # contact — hence a different stage and a different recorded reason.
    addresses = resolve_emails(db, sorted(surviving))
    unaddressable = surviving - set(addresses)
    for recipient_id in sorted(unaddressable):
        exclusions.append(
            Exclusion(
                recipient_id,
                STAGE_ADDRESSABILITY,
                f"no active address on the {channel} channel",
            )
        )
    surviving -= unaddressable

    # --- Stage 2: consent --------------------------------------------------
    # The latest (recipient, channel, purpose) event must be a grant. This is
    # the stage that closes the P0: it runs at send time, so an opt-out
    # recorded after the audience was frozen is seen.
    if surviving:
        consenting = {
            row.id
            for row in db.query(RecipientDB.id)
            .filter(
                RecipientDB.id.in_(sorted(surviving)),
                is_consenting_filter(channel, purpose),
            )
            .all()
        }
        withdrawn = surviving - consenting
        for recipient_id in sorted(withdrawn):
            exclusions.append(
                Exclusion(
                    recipient_id,
                    STAGE_CONSENT,
                    f"no grant for ({channel}, {purpose})",
                )
            )
        surviving -= withdrawn

    # --- Stage 3: suppression ----------------------------------------------
    # Named, ordered, and currently empty by construction — not forgotten.
    #
    # Suppression has no store of its own yet; the data model is an open
    # Needs-ADR item. Today a hard bounce or spam complaint is written as a
    # consent event with source="provider", so stage 2 above already catches
    # it. Inventing a suppression table here would pre-empt a decision that is
    # deliberately still open, and a second mechanism for the same fact is the
    # kind that gets checked in one place and forgotten in the other.
    #
    # When that item is decided, this is where it plugs in — and because the
    # stack is ordered and each stage records its own reason, a recipient
    # dropped for suppression will be distinguishable from one who simply never
    # granted consent, which is a distinction the current single-status model
    # cannot make.

    # --- Stage 4: frequency ------------------------------------------------
    # Post-POC by explicit decision (ADR-161 point 8). The platform owns
    # cross-channel capping because nothing else can see across channels, but
    # the numbers belong to the adopting company and the mechanism is not
    # built. Named here so the stack's shape matches the record.

    return ExclusionStackResult(surviving, addresses, exclusions)
