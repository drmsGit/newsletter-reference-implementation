from dataclasses import dataclass
import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.delivery.models import DeliveryExecution, SendInstance, SendInstanceDetail

from app.campaigns.db_models import VariantDB
from app.delivery.exclusion import run_exclusion_stack
from app.delivery.providers.factory import get_provider
from app.recipients.consent import DEFAULT_CHANNEL, DEFAULT_PURPOSE, ConsentDenied
from app.rendering.service import render_variant, render_variant_html
from app.snapshots.db_models import SnapshotDB

logger = logging.getLogger(__name__)


def to_delivery_execution(record: DeliveryExecutionDB) -> DeliveryExecution:
    return DeliveryExecution(
        id=record.id,
        send_instance_id=record.send_instance_id,
        recipient_id=record.recipient_id,
        status=record.status,
        provider=record.provider,
        provider_message_id=record.provider_message_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def create_delivery_execution(
    db: Session,
    send_instance_id: int,
    recipient_id: int,
    status: str = "created",
    provider: str | None = None,
    provider_message_id: str | None = None,
    *,
    brand_id: int,
) -> DeliveryExecution:
    if get_send_instance(db, send_instance_id, brand_id=brand_id) is None:
        raise ValueError(f"SendInstance {send_instance_id} not found")

    execution = DeliveryExecutionDB(
        send_instance_id=send_instance_id,
        recipient_id=recipient_id,
        status=status,
        provider=provider,
        provider_message_id=provider_message_id,
    )

    db.add(execution)
    db.commit()
    db.refresh(execution)

    return to_delivery_execution(execution)


def list_delivery_executions_for_send_instance(
    db: Session,
    send_instance_id: int,
    *,
    brand_id: int,
) -> list[DeliveryExecution]:
    records = (
        db.query(DeliveryExecutionDB)
        .join(SendInstanceDB, SendInstanceDB.id == DeliveryExecutionDB.send_instance_id)
        .filter(
            DeliveryExecutionDB.send_instance_id == send_instance_id,
            SendInstanceDB.brand_id == brand_id,
        )
        .order_by(DeliveryExecutionDB.created_at.desc())
        .all()
    )

    return [to_delivery_execution(record) for record in records]


def get_send_instance(
    db: Session, send_instance_id: int, *, brand_id: int
) -> SendInstanceDB | None:
    """One send instance, selected within a brand (ADR-172 points 4-6).

    `send_instances.brand_id` has been NOT NULL since migration 0007, so this
    is a column comparison rather than a join — the one place on the derived
    plane where the chain is a single hop.
    """
    return (
        db.query(SendInstanceDB)
        .filter(
            SendInstanceDB.id == send_instance_id,
            SendInstanceDB.brand_id == brand_id,
        )
        .first()
    )


def to_send_instance(record: SendInstanceDB) -> SendInstance:
    return SendInstance(
        id=record.id,
        snapshot_id=record.snapshot_id,
        name=record.name,
        status=record.status,
        provider=record.provider,
        scheduled_at=record.scheduled_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
        from_address=record.from_address,
        audience_group_id=record.audience_group_id,
        sent_count=record.sent_count or 0,
        failed_count=record.failed_count or 0,
        excluded_count=record.excluded_count or 0,
    )


def list_send_instances(
    db: Session, *, brand_id: int, limit: int = 50, offset: int = 0,
    status: str | None = None,
) -> list[SendInstance]:
    """Every send in one brand, newest first — the deliveries list (task-28).

    The only way to list sends used to be per snapshot, so a screen had to walk
    campaigns → variants → snapshots → sends itself, which the screen inventory
    names as a thing the SPA must not reimplement. Paged from the start: the
    Manager Workflow interview ruled that a list returning everything does not
    survive real volume. The shared response envelope is task-88's to define;
    this takes the same `limit`/`offset` it will wrap.
    """
    query = db.query(SendInstanceDB).filter(SendInstanceDB.brand_id == brand_id)
    if status:
        query = query.filter(SendInstanceDB.status == status)
    records = (
        query.order_by(SendInstanceDB.created_at.desc(), SendInstanceDB.id.desc())
        .offset(offset).limit(limit).all()
    )
    return [to_send_instance(record) for record in records]


def send_instance_detail(
    db: Session, send_instance_id: int, *, brand_id: int
) -> SendInstanceDetail | None:
    """One send within a brand, with what explains its gap (task-28).

    The stage is the part of `exclusion_reason` before the first colon — the
    stack writes "<stage>: <reason>", so grouping on it counts by stage without
    parsing the free-text reason.
    """
    record = get_send_instance(db, send_instance_id, brand_id=brand_id)
    if record is None:
        return None
    reasons = [
        reason for (reason,) in db.query(DeliveryExecutionDB.exclusion_reason)
        .filter(DeliveryExecutionDB.send_instance_id == record.id)
        .all()
    ]
    by_stage: dict[str, int] = {}
    for reason in reasons:
        if reason:
            stage = reason.split(":", 1)[0].strip()
            by_stage[stage] = by_stage.get(stage, 0) + 1
    return SendInstanceDetail(
        **to_send_instance(record).model_dump(),
        execution_count=len(reasons),
        exclusions_by_stage=by_stage,
    )


def brand_for_snapshot(db: Session, snapshot_id: int) -> int:
    """The sending brand, derived from the campaign being sent (ADR-150 point 9).

    Deliberately NOT taken from the caller's working context. A manager who
    switches brand between building a send and firing it would otherwise send
    brand 1's campaign as brand 2 — the content would be brand 1's, the record
    would say brand 2, and every consequence downstream (point 8's candidate
    scoping, per-brand reporting, and the per-brand consent of Phase 2) would
    follow the wrong one.

    `send_instances.brand_id` is the arbiter of record once written; this is
    where its value comes from.
    """
    from app.campaigns.db_models import CampaignDB, VariantDB
    from app.snapshots.db_models import SnapshotDB

    brand_id = (
        db.query(CampaignDB.brand_id)
        .join(VariantDB, VariantDB.campaign_id == CampaignDB.id)
        .join(SnapshotDB, SnapshotDB.variant_id == VariantDB.id)
        .filter(SnapshotDB.id == snapshot_id)
        .scalar()
    )
    if brand_id is None:
        raise ValueError(
            f"Snapshot {snapshot_id} does not resolve to a campaign, so the sending "
            "brand cannot be determined. Refusing rather than guessing one."
        )
    return brand_id


def create_send_instance(
    db: Session,
    snapshot_id: int,
    name: str,
    status: str = "draft",
    provider: str | None = None,
    scheduled_at=None,
    audience_group_id: int | None = None,
    from_address: str | None = None,
    *,
    brand_id: int,
) -> SendInstance:
    # **The snapshot decides the brand; the caller only proves it may act
    # there.** `brand_for_snapshot` has always been the arbiter of which brand
    # a send belongs to, and that does not change — what is new is refusing a
    # caller who is working in a different one. Reading the brand off the
    # caller instead would let a request in brand A mint a send that renders
    # brand B's snapshot.
    snapshot_brand = brand_for_snapshot(db, snapshot_id)
    if snapshot_brand != brand_id:
        raise ValueError(f"Snapshot {snapshot_id} not found")

    send_instance = SendInstanceDB(
        snapshot_id=snapshot_id,
        brand_id=snapshot_brand,
        name=name,
        status=status,
        provider=provider,
        scheduled_at=scheduled_at,
        audience_group_id=audience_group_id,
        from_address=from_address,
    )

    db.add(send_instance)
    db.commit()
    db.refresh(send_instance)

    return to_send_instance(send_instance)


def _audience_group_in_brand(db: Session, group_id: int, brand_id: int):
    """The audience service's scoped getter, imported where it is used.

    Named locally because `get_group` reads ambiguously in a delivery module —
    there are several kinds of group a send could mean.
    """
    from app.audience.service import get_group

    return get_group(db, group_id, brand_id=brand_id)


def prepare_send_from_audience(
    db: Session,
    snapshot_id: int,
    name: str,
    audience_group_id: int,
    provider: str,
    from_address: str | None = None,
    audience_resolution_mode: str = "rerun",
    scheduled_at=None,
    *,
    brand_id: int,
) -> SendInstanceDB:
    """Materialize a planned send: resolve the audience group to its live
    recipient set (consent-gated) and create one DeliveryExecution per
    recipient, all in status "created". Nothing is sent here. Raises ValueError
    on an empty audience or one exceeding the recipient cap.

    **Every send re-resolves its audience (ADR-176 point 4, implemented
    2026-09-29), and `"freeze"` is refused.** The executions created here are a
    *preview*: the group is re-resolved and reconciled immediately before the
    send fires (`reconcile_executions_to_audience`). A send therefore goes to
    whoever qualifies at the moment it goes out, by construction rather than by
    configuration — which is what makes an exclusion segment written after
    planning actually remove somebody. Under `"freeze"` point 1's precedence
    change would have been true of the resolver and false of the send: a rule
    that reads as a safety and is not one.

    **`audience_resolution_mode` survives as a parameter deliberately**, rather
    than being deleted. Refusing the old value by name says what changed and
    where it is written down; dropping the parameter would greet the same
    caller with `unexpected keyword argument`, which is a fact about Python and
    not about this system. The column it writes is kept for the same reason —
    see `SendInstanceDB.audience_resolution_mode`.

    `scheduled_at` set → status "scheduled" (fires later via
    process_due_scheduled_sends); otherwise "draft" (fires on manual Trigger)."""
    # Imported here rather than at module load to keep the delivery→audience
    # dependency local (audience never imports delivery).
    from app.audience.service import resolve_audience
    from app.settings.service import get_max_send_recipients

    if audience_resolution_mode == "freeze":
        raise ValueError(
            "audience_resolution_mode 'freeze' was removed by ADR-176 point 4: "
            "a send goes to whoever qualifies when it goes out, so consent and "
            "exclusions are current at the only moment that matters. Existing "
            "rows keep the value because they record how those sends were "
            "planned; new ones cannot be created with it."
        )
    if audience_resolution_mode != "rerun":
        raise ValueError("audience_resolution_mode must be 'rerun'")

    # A naive scheduled_at (e.g. from a datetime-local input, local wall-clock)
    # must be made timezone-aware before it hits the timestamptz column —
    # otherwise Postgres reinterprets it in the session TZ and the "<= now()"
    # due-check drifts by the UTC offset. astimezone() attaches the local tz.
    if scheduled_at is not None and scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.astimezone()

    # Resolved against the channel this send will actually go out on. The
    # variant is read once here and used for both the audience gate and the
    # executions' channel, so the two cannot disagree about what is being sent.
    plan_variant = (
        db.query(VariantDB)
        .join(SnapshotDB, SnapshotDB.variant_id == VariantDB.id)
        .filter(SnapshotDB.id == snapshot_id)
        .first()
    )
    plan_channel = plan_variant.channel if plan_variant else DEFAULT_CHANNEL

    # **Both halves are checked against the caller's brand before anything is
    # materialised.** A send binds a snapshot to an audience group, and either
    # one reaching across the boundary produces a send that renders one brand's
    # content to another brand's list. Refused here rather than filtered later,
    # because this function writes one execution per recipient.
    snapshot_brand = brand_for_snapshot(db, snapshot_id)
    if snapshot_brand != brand_id:
        raise ValueError(f"Snapshot {snapshot_id} not found")
    if _audience_group_in_brand(db, audience_group_id, brand_id) is None:
        raise ValueError(f"Audience group {audience_group_id} not found")

    recipients = resolve_audience(db, audience_group_id, channel=plan_channel)
    if not recipients:
        raise ValueError(
            "The selected audience resolves to 0 consenting recipients — nothing to send."
        )

    cap = get_max_send_recipients(db)
    if len(recipients) > cap:
        raise ValueError(
            f"The selected audience has {len(recipients)} recipients, over the send cap of {cap}. "
            "Raise the cap in Settings or narrow the audience."
        )

    send_instance = SendInstanceDB(
        snapshot_id=snapshot_id,
        brand_id=snapshot_brand,
        name=name,
        status="scheduled" if scheduled_at else "draft",
        provider=provider,
        audience_group_id=audience_group_id,
        from_address=from_address or None,
        audience_resolution_mode=audience_resolution_mode,
        scheduled_at=scheduled_at,
    )
    db.add(send_instance)
    db.flush()  # assign send_instance.id before creating child executions

    # **The channel comes off the variant** (ADR-160 point 4), read at plan
    # time because the inbound feedback path depends on the execution row
    # carrying it (ADR-163 addendum point 1) — a bounce arriving weeks later
    # has only this row to say which channel it was about.
    #
    # Written rather than defaulted, which is the point of this change: the
    # column has defaulted to 'email' since it was added, so every execution
    # ever created claimed email whatever it was. Purpose still defaults,
    # because nothing carries one yet.
    for recipient in recipients:
        db.add(
            DeliveryExecutionDB(
                send_instance_id=send_instance.id,
                channel=plan_channel,
                recipient_id=recipient.id,
                status="created",
                provider=provider,
            )
        )

    db.commit()
    db.refresh(send_instance)
    return send_instance


def reconcile_executions_to_audience(db: Session, send_instance: SendInstanceDB) -> None:
    """Re-resolve this send's audience and adjust THIS send's executions.

    **Called for every send since ADR-176 point 4** (2026-09-29), rather than
    only for the sends that asked. It is the mechanism that makes an exclusion
    segment written after planning actually remove somebody.

    **Scoped to one send instance, which answers a question asked on
    2026-09-18**: if two variants of a campaign share an audience group, can
    one send's re-resolution reach the other's executions? It cannot. Every
    query below filters on `send_instance_id`, and nothing here writes to the
    group. The question was originally asked about a "freeze" send and a
    "rerun" one; the modes are gone and the isolation is what mattered.

    The sharper version of that worry is real and answered elsewhere: a push
    that goes out first can *change the world* — someone complains, the provider
    reports it, they are opted out — and a later email send must honour that. It
    does, and by two mechanisms now rather than one. This function drops them,
    and the send-time gate in `send_send_instance` drops them again (ADR-163
    point 7, the P0). **That the gate is now the second line rather than the
    only one is a hazard for its tests, not a reason to remove it**: a send with
    no audience group never reaches this function, so the gate is still the only
    thing standing between an opted-out recipient and a mail.

    Which is also why a separate "audience snapshot" entity is not needed: the
    executions already materialise the audience, and a second mechanism for the
    same thing would be one more place for the two to disagree.

    **What it does:** re-resolve the audience group right before firing and
    reconcile executions — add one for each newly-matching recipient, and drop
    executions for recipients who no longer match *and* haven't sent yet (an
    already-sent execution is history and is left as-is). Enforces the recipient
    cap on the freshly-resolved set. No-op if the send has no audience group.
    """
    if not send_instance.audience_group_id:
        return

    from app.audience.service import resolve_audience
    from app.settings.service import get_max_send_recipients

    # Same channel the executions carry — a "rerun" send re-resolves WHO is
    # targeted, and must ask about the channel it was planned for, or it would
    # reconcile an email audience onto a push send.
    rerun_channel = (
        db.query(DeliveryExecutionDB.channel)
        .filter(DeliveryExecutionDB.send_instance_id == send_instance.id)
        .limit(1)
        .scalar()
    ) or DEFAULT_CHANNEL
    resolved_ids = {
        r.id for r in resolve_audience(
            db, send_instance.audience_group_id, channel=rerun_channel
        )
    }

    cap = get_max_send_recipients(db)
    if len(resolved_ids) > cap:
        raise ValueError(
            f"Re-resolved audience has {len(resolved_ids)} recipients, over the send cap of {cap}."
        )

    existing = (
        db.query(DeliveryExecutionDB)
        .filter(DeliveryExecutionDB.send_instance_id == send_instance.id)
        .all()
    )
    existing_by_recipient = {e.recipient_id: e for e in existing}

    # Drop no-longer-matching that haven't sent.
    for execution in existing:
        if execution.recipient_id not in resolved_ids and execution.status == "created":
            db.delete(execution)

    # Add newly-matching.
    for recipient_id in resolved_ids:
        if recipient_id not in existing_by_recipient:
            db.add(
                DeliveryExecutionDB(
                    send_instance_id=send_instance.id,
                    recipient_id=recipient_id,
                    status="created",
                    provider=send_instance.provider,
                )
            )

    db.commit()


def process_due_scheduled_sends(db: Session) -> list[int]:
    """Fire every scheduled send whose time has arrived. This is the operation a
    scheduler drives — a cron job, worker, or automation platform (n8n) calls it
    on an interval; the architecture just exposes the seam rather than baking in
    a specific scheduler. Returns the ids of the send instances it triggered."""
    due = (
        db.query(SendInstanceDB)
        .filter(
            SendInstanceDB.status == "scheduled",
            SendInstanceDB.scheduled_at.isnot(None),
            SendInstanceDB.scheduled_at <= func.now(),  # DB-side comparison avoids tz drift
        )
        .all()
    )
    triggered = []
    for send_instance in due:
        try:
            # **Not a `list_all_*` case, deliberately.** The SELECT spans
            # brands because a scheduler has no working brand — but each fire
            # already knows its own, from the column `brand_for_snapshot` set
            # when the instance was created. So the sweep hands the send its
            # own brand rather than an escape hatch, and the whitelist of
            # spanning functions stays three entries that all mean the same
            # thing.
            send_send_instance(
                db, send_instance_id=send_instance.id,
                brand_id=send_instance.brand_id,
            )
            triggered.append(send_instance.id)
        except Exception:
            logger.exception("scheduled send failed: send_instance_id=%s", send_instance.id)
    return triggered


def list_send_instances_for_snapshot(
    db: Session,
    snapshot_id: int,
    *,
    brand_id: int,
) -> list[SendInstance]:
    records = (
        db.query(SendInstanceDB)
        .filter(
            SendInstanceDB.snapshot_id == snapshot_id,
            SendInstanceDB.brand_id == brand_id,
        )
        .order_by(SendInstanceDB.created_at.desc())
        .all()
    )

    return [to_send_instance(record) for record in records]


@dataclass
class TestSendResult:
    """What a test send did, for a caller to render."""

    success: bool
    to: str
    provider: str
    provider_message_id: str | None = None
    message: str | None = None
    #: Set when the chosen variant could not be rendered and a plain body went
    #: instead. **Not an error** — the send still happened, and the operator
    #: needs to know they are looking at the fallback rather than their
    #: newsletter. Losing this note would make a failed render look like a
    #: successful preview.
    render_note: str | None = None


def send_test_email(
    db: Session,
    *,
    to: str,
    subject: str,
    provider: str,
    brand_id: int,
    variant_id: int | None = None,
    recipient_id: int | None = None,
) -> TestSendResult:
    """Send one real email, optionally rendering a variant into it.

    Composed in `app/frontend/router.py` until 2026-09-20 (inventory B9) with
    no service function at all — the only remaining item where a client would
    have had to reimplement orchestration rather than call something. Four
    decisions live here:

    **It renders through the EMAIL path on purpose.** This sends an email, so a
    variant of another channel is refused by that path rather than returning an
    empty document. Before the email renderer learned to refuse, a push variant
    rendered as a 252-character empty shell, was mailed to a real address, and
    was reported as a success — because nothing raised, the handler below never
    fired.

    **It renders in SEND mode, not preview mode.** A test send is the one
    action whose entire purpose is "show me what recipients will get", and
    preview mode reads the live, mutable `ContentRecordDB.content` — so an
    unpublished headline edit appeared in the test and the real send shipped
    the last frozen version instead, silently, because a version existed. The
    variant-editor design interview (2026-09-26, question 4.3) settled this:
    a test send shows what would actually be sent at that moment, drift
    included, so a manager notices the drift.

    **A render failure never blocks the send.** The point of this screen is to
    prove the provider path works; a broken variant should not stop an operator
    finding out whether mail leaves the building at all. The fallback body goes
    instead and `render_note` says so.

    **An unknown provider is a failed result, not an exception.** The operator
    typed a name; being told it is wrong is the answer, not a stack trace.

    `brand_id` is required and the variant is resolved through the rendering
    path's own scoped check: the router passed a bare id, so this was a small
    brand gap as well — the same shape B15 had, and for the same reason.
    """
    from app.rendering.renderers.base import RenderedArtifact
    from app.rendering.service import UnpublishedContentError, render_variant_html

    to = to.strip()
    fallback = (
        f"<h1>{subject}</h1>"
        "<p>Test email from the newsletter reference build.</p>"
    )
    render_note = None
    html = fallback

    if variant_id is not None:
        from app.campaigns.service import get_variant

        if get_variant(db, variant_id, brand_id=brand_id) is None:
            render_note = (
                f"Variant {variant_id} is not available here; sent a plain test "
                "body instead."
            )
        else:
            try:
                html = render_variant_html(
                    db, variant_id, recipient_id=recipient_id, mode="send",
                )
            except UnpublishedContentError as error:
                # **Caught ahead of the generic handler, for its message.**
                # Send mode refuses content that has never been frozen, and
                # that refusal is a fact about the variant rather than a
                # renderer hiccup — folding it into "Could not render variant
                # (...)" would hand the operator a vague failure in place of
                # the one thing they can act on. Still sends, still falls back
                # to the plain body: the rule above is unchanged.
                render_note = (
                    f"Content record {error.content_record_id} has never been "
                    "published, so this variant cannot be sent yet — freeze a "
                    "version first. Sent a plain test body instead."
                )
                html = fallback
            except Exception as error:  # never block the send on a render hiccup
                render_note = (
                    f"Could not render variant ({error}); sent a plain test body "
                    "instead."
                )
                html = fallback

    try:
        sent = get_provider(provider).send(
            to, RenderedArtifact.email(html=html, subject=subject),
        )
    except ValueError as error:  # unknown provider
        return TestSendResult(
            success=False, to=to, provider=provider,
            message=str(error), render_note=render_note,
        )

    return TestSendResult(
        success=sent.success,
        to=to,
        provider=provider,
        provider_message_id=sent.provider_message_id,
        message=sent.message,
        render_note=render_note,
    )


def send_send_instance(
    db: Session,
    send_instance_id: int,
    *,
    brand_id: int,
):
    # Row lock + status guard: two concurrent calls both reading "draft"
    # before either commits would otherwise both proceed to send. FOR UPDATE
    # serializes the read-check-write of the status transition itself — the
    # second caller blocks here, then re-reads the row (now "sending"/"sent")
    # once the first commits, and gets rejected below instead of also sending.
    send_instance = (
        db.query(SendInstanceDB)
        .filter(
            SendInstanceDB.id == send_instance_id,
            # **Inside the locked query, not before or after it.** ADR-172
            # point 5 wants the brand in the SELECTING query everywhere; here
            # it matters more than anywhere else, because checking the brand
            # separately would reintroduce exactly the check-then-act window
            # this `FOR UPDATE` exists to close. An instance in another brand
            # is not found, so it is never locked and never sent.
            SendInstanceDB.brand_id == brand_id,
        )
        .with_for_update()
        .first()
    )

    if send_instance is None:
        raise ValueError(
            f"SendInstance {send_instance_id} not found"
        )

    if send_instance.status in ("sending", "sent"):
        raise ValueError(
            f"SendInstance {send_instance_id} is already {send_instance.status} — refusing to send again"
        )

    # **ADR-174 point 3, and this is the enforcement rather than the courtesy.**
    # `send_fire.describe()` shows the same finding so the reviewer can fix it,
    # but a disabled button is not a control: an orchestrator calls this
    # directly and `process_due_scheduled_sends` calls it on a timer.
    #
    # **Before the status transition, deliberately.** The first version of this
    # sat after the snapshot lookup, which is after the line below — and a
    # refused send was left stranded in "sending", unsendable and unretryable,
    # which is the defect `docs/queue` already records about this transition
    # being committed ahead of fallible preflight steps. A new check must not
    # add to it.
    #
    # Before the loop, not inside it: these modules do not depend on who
    # receives the mail, so the answer is the same for every recipient. The
    # per-recipient half — a slot that resolved, for one person, to content
    # missing a field — is a skip rather than a block and is deliberately not
    # here.
    from app.rendering.service import missing_required_fields
    from app.snapshots.db_models import SnapshotDB as _Snapshot

    snapshot = db.query(_Snapshot).filter(
        _Snapshot.id == send_instance.snapshot_id
    ).first()
    if snapshot is None:
        raise ValueError(
            f"Snapshot {send_instance.snapshot_id} not found"
        )
    gaps = missing_required_fields(db, snapshot.variant_id)
    if gaps:
        named = ", ".join(f"{kind}.{field}" for _, kind, field in gaps)
        raise ValueError(
            f"Variant {snapshot.variant_id} is missing required content "
            f"({named}), so this send is refused. An empty required field "
            "reaches the recipient with nothing in it, and the first party "
            "to notice is them."
        )

    # Subject line comes from the variant (recipient-facing copy), not the
    # send_instance.name (an internal label). Fall back to the send_instance
    # name only if the variant has no subject set, so older data still sends.
    variant = (
        db.query(VariantDB)
        .filter(VariantDB.id == snapshot.variant_id)
        .first()
    )
    # Only the fallback. The subject itself rides on the artifact's envelope,
    # filled by the renderer from the envelope module (ADR-162 point 1) — this
    # is what a variant with no envelope copy at all falls back to, and reading
    # `variant.subject` here would read a column nothing writes any more.
    subject = send_instance.name

    # Refused up front if the adapter cannot carry this channel, rather than
    # failing at the vendor with a message about a malformed request.
    provider = get_provider(
        send_instance.provider or "mock",
        from_address=send_instance.from_address,
        channel=variant.channel if variant else DEFAULT_CHANNEL,
    )

    # **Everything above this line only reads, and everything below it is
    # inside the handler** (task-14). The status transition is the claim: once
    # it is committed, every later attempt is refused by the guard above, so an
    # exception that escaped between here and the send loop used to leave the
    # instance in "sending" forever with nothing sent and no route back — and
    # through approvals the request was recorded failed while the send stayed
    # wedged. The snapshot lookup, provider construction and channel
    # validation used to sit after this line; they only read, so they moved
    # above it, and a send they refuse keeps its status and can be retried
    # once the configuration is fixed.
    send_instance.status = "sending"
    db.commit()

    try:
        _deliver_claimed(db, send_instance, snapshot, variant, subject, provider)
    except Exception:
        # Any exception, not just ValueError: a database error in the slot
        # query strands a send exactly as surely as a refused provider.
        # "failed" is retryable — the guard refuses only sending and sent.
        # Rolled back first, because a failed statement leaves the session
        # unable to commit anything; executions already sent were committed
        # one by one inside the loop and are not undone by this.
        db.rollback()
        db.query(SendInstanceDB).filter(
            SendInstanceDB.id == send_instance.id
        ).update({"status": "failed"}, synchronize_session=False)
        db.commit()
        raise


def _deliver_claimed(db: Session, send_instance, snapshot, variant, subject, provider) -> None:
    """Everything `send_send_instance` does after claiming the instance.

    Separate so the caller can wrap ALL of it in one failure handler — the
    property task-14 is about. Nothing here may assume it can leave the parent
    in "sending": the caller moves it to "failed" on any exception.
    """
    send_instance_id = send_instance.id

    # The audience is re-resolved against the group right now, just before
    # sending, so a send reflects who matches at send time — not who matched
    # when it was planned. **Unconditional since ADR-176 point 4**: this was
    # `if audience_resolution_mode == "rerun"`, which meant an exclusion
    # segment written after planning reached the resolver and not the send.
    # A send planned before that date still re-resolves, which is the point —
    # the column records how it was planned, not what it may do.
    #
    # No-op for a send with no audience group: `reconcile_executions_to_audience`
    # returns early, and those executions were never group-derived.
    reconcile_executions_to_audience(db, send_instance)


    # Decision slots on this variant. Rendering only *looks up* an existing
    # resolution per recipient (rendering/service.resolve_content_for_module),
    # so without resolving here a recipient with no prior resolution would get
    # the personalized module hidden — and engagement on it couldn't be
    # attributed. Resolve per recipient at send so they receive their content
    # and we record what they got (DecisionResolutionDB = the audit of it).
    # Per-recipient scope reuses the strategies' existing behavior; the broader
    # segment-vs-person resolution-scope question is the open Needs-ADR item.
    from app.campaigns.db_models import DecisionSlotDB
    from app.decision.service import execute_decision_slot

    decision_slots = (
        db.query(DecisionSlotDB)
        .filter(DecisionSlotDB.variant_id == snapshot.variant_id)
        .all()
    )

    executions = (
        db.query(DeliveryExecutionDB)
        .filter(
            DeliveryExecutionDB.send_instance_id
            == send_instance_id
        )
        .all()
    )

    # THE SEND-TIME GATE (ADR-163 point 7). Run here, immediately before the
    # send loop, for every send without exception.
    #
    # This is the P0 fix. A send materialised its executions at plan time and,
    # before this, never looked at permission again, so a recipient who opted
    # out in between was still mailed.
    #
    # **Re-resolving the audience is not a substitute for this, and since
    # ADR-176 point 4 made re-resolution unconditional it can look like one.**
    # It is not, for two reasons. Re-resolution changes *who is targeted* and
    # this changes *who may be contacted* — different questions that currently
    # agree on consent and do not agree on suppression or addressability. And
    # `reconcile_executions_to_audience` returns early for a send with no
    # audience group, so for those sends this gate is the only thing there is.
    #
    # Set operations, one query per stage, so per-stage attribution costs no
    # N+1 (point 10).
    # Channel and purpose come off the execution rows, which carry both since
    # ADR-163's addendum point 1. Every execution of one send instance shares
    # them, so the first is representative; the defaults cover a send with no
    # executions at all.
    send_channel = executions[0].channel if executions else DEFAULT_CHANNEL
    send_purpose = executions[0].purpose if executions else DEFAULT_PURPOSE

    gate = run_exclusion_stack(
        db,
        {execution.recipient_id for execution in executions},
        # The send instance records the sending brand and is the arbiter of
        # record, so the gate asks about the brand this mail actually goes out
        # as — not the brand whoever pressed the button happens to be viewing.
        send_instance.brand_id,
        channel=send_channel,
        purpose=send_purpose,
    )

    if gate.exclusions:
        logger.warning(
            "send %s: %d of %d recipients excluded at send time — %s",
            send_instance_id,
            len(gate.exclusions),
            len(executions),
            ", ".join(
                f"{exclusion.stage}={sum(1 for e in gate.exclusions if e.stage == exclusion.stage)}"
                for exclusion in {e.stage: e for e in gate.exclusions}.values()
            ),
        )

    for execution in executions:

        # Excluded by the stack above: record why and move on, before any
        # work is done for this recipient. Ordering matters — a recipient
        # who may not be contacted must not have decision slots resolved
        # (that is AI spend on someone who will not be sent to, the cost
        # reason ADR-163 gives alongside the legal one) and must not be
        # rendered.
        if execution.recipient_id not in gate.eligible:
            execution.status = "excluded"
            execution.exclusion_reason = gate.reason_for(execution.recipient_id)
            logger.info(
                "execution %s excluded: recipient %s — %s",
                execution.id,
                execution.recipient_id,
                execution.exclusion_reason,
            )
            db.commit()
            continue

        # Resolve + persist each decision slot for this recipient before
        # rendering, so their personalized content is chosen and recorded.
        for slot in decision_slots:
            try:
                execute_decision_slot(db, slot.id, recipient_id=execution.recipient_id)
            except ConsentDenied:
                # Unreachable in practice — the stack above already excluded
                # every non-consenting recipient, so this is belt and braces
                # behind it. Deliberately NOT swallowed with the rest: a
                # consent refusal arriving here means the gate and the
                # decision layer disagree about who may be contacted, which
                # is a defect to surface rather than a slot to hide.
                raise
            except ValueError:
                # Strategy resolved nothing — the slot renders hidden
                # (ADR-086) and the send continues. This is the ONLY case
                # this handler is for. Before ADR-163 point 8 it also
                # swallowed the consent guard, which is how a compliance
                # defect came to read as a rendering behaviour.
                pass

        # Resolve HTML per recipient rather than reusing one shared
        # variant-level snapshot — decision-slot personalization can
        # resolve different content per recipient within the same
        # variant (ADR-083), so every recipient must get their own
        # rendered HTML, not identical copies of whatever the snapshot
        # happened to freeze for a single (or no) recipient.
        # Through the channel's renderer (ADR-162 point 4), not the email
        # one. An email comes back as HTML with a subject in its envelope;
        # a push comes back as fields. Per recipient rather than reusing
        # the snapshot, because decision-slot personalisation can resolve
        # different content per recipient within one variant (ADR-083).
        artifact = render_variant(
            db=db,
            variant_id=snapshot.variant_id,
            recipient_id=execution.recipient_id,
            mode="send",
        )
        # Subject lives on the variant until ADR-162 point 1 moves it into
        # a header module, so the renderer put it in the envelope. The send
        # instance's name is the fallback it always was.
        if artifact.body is not None and not artifact.envelope.get("subject"):
            artifact.envelope["subject"] = subject

        # Already resolved by stage 1 of the gate, which had to look it up
        # to decide addressability at all. Resolving it again here would
        # reintroduce the per-recipient query the stack exists to avoid,
        # and would let the address that was *checked* differ from the
        # address that is *used*.
        recipient_email = gate.addresses[execution.recipient_id]

        result = provider.send(recipient_email, artifact)

        logger.info(
            "send result: execution_id=%s recipient_id=%s success=%s "
            "provider_message_id=%s message=%s",
            execution.id,
            execution.recipient_id,
            result.success,
            result.provider_message_id,
            result.message,
        )

        execution.status = "sent" if result.success else "failed"
        execution.provider_message_id = (
            result.provider_message_id
        )

        # Commit after each execution — if provider.send() raises mid-batch,
        # executions already sent must not lose their persisted status just
        # because a later one in the loop failed.
        db.commit()

    # Derive the parent status from its children rather than declaring success.
    # This line used to be an unconditional `status = "sent"`, so 100 failed
    # deliveries out of 100 still reported a sent campaign — only an exception
    # escaping the loop marked it failed, and a provider failure returns
    # SendResult(success=False) rather than raising.
    #
    # "excluded" is counted apart from "failed" on purpose: an excluded
    # recipient is the ADR-163 point 7 stack working, not a delivery problem.
    # Folding them together would recreate the same lie one level down.
    counts = {"sent": 0, "failed": 0, "excluded": 0}
    for execution in executions:
        if execution.status in counts:
            counts[execution.status] += 1

    send_instance.sent_count = counts["sent"]
    send_instance.failed_count = counts["failed"]
    send_instance.excluded_count = counts["excluded"]

    if counts["sent"] and counts["failed"]:
        send_instance.status = "partial_failed"
    elif counts["sent"]:
        send_instance.status = "sent"
    elif counts["failed"]:
        send_instance.status = "failed"
    else:
        # Nothing sent and nothing failed: every recipient was excluded, or
        # there were none to begin with. The send did exactly what it should
        # and delivered to nobody — which is neither a success to report green
        # nor a failure to retry, so it gets its own value rather than being
        # rounded to whichever lies less.
        send_instance.status = "no_recipients"

    db.commit()