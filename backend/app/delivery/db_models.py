from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, func, text

from app.database import Base


class SendInstanceDB(Base):
    __tablename__ = "send_instances"

    id = Column(Integer, primary_key=True, index=True)
    # ADR-150 points 2 and 9 — the sending brand, and singular by decision.
    #
    # This table already has two paths to a brand: snapshot -> variant ->
    # campaign (snapshot_id is NOT NULL) and audience_group_id. This column is
    # the ARBITER when those disagree, not a third opinion — the send went out
    # as this brand whatever the chain says. Same reasoning as the denormalised
    # channel/purpose below.
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False, index=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="draft")
    provider = Column(String(100), nullable=True)
    # The audience this send targets. Recorded so we know who a send went to
    # (its executions are materialized from the group at prepare time) and can
    # show it on the delivery page. Nullable for legacy/ad-hoc send instances.
    audience_group_id = Column(Integer, ForeignKey("audience_groups.id"), nullable=True)
    # Verified sender for a real (Resend) send, e.g. "News <news@domain.com>".
    # Null = the provider adapter falls back to its RESEND_FROM env default.
    from_address = Column(String(255), nullable=True)
    # **This column records how a send was planned. It no longer gates
    # anything** (ADR-176 point 4, 2026-09-29): every send re-resolves its
    # audience immediately before firing, whatever this says.
    #
    # It is kept rather than dropped because the five rows reading "freeze"
    # were frozen — rewriting them to "rerun" would falsify history to match a
    # decision taken afterwards. Only un-fired rows were backfilled. Dropping
    # it would also be a hand-written migration in a repository with no
    # Alembic, for no behavioural gain.
    #
    # `prepare_send_from_audience` refuses "freeze" by name, so nothing new can
    # be written with it; a reader who sees one is looking at a send planned
    # before that date.
    audience_resolution_mode = Column(String(20), nullable=False, default="rerun")
    # Derived from the child executions once the send finishes, rather than set
    # unconditionally. Persisted rather than computed on read because
    # monitoring, retries and the audit trail all want the number without a
    # GROUP BY, and because a finished send's counts do not change.
    #
    # excluded_count is deliberately separate from failed_count: an excluded
    # recipient is the exclusion stack working (ADR-163 point 7), not a
    # delivery problem, and folding the two together would recreate the lie
    # this field exists to stop.
    # `server_default` as well as `default` (2026-09-29, task-12): the migration
    # that added this NOT NULL column backfilled it with a database default,
    # and the models did not declare one — so the two paths built different
    # schemas. The rule: the database never supplies a default the models
    # do not declare.
    sent_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    failed_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    excluded_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    # Set when a send is scheduled for later (normal calendar-time newsletter
    # scheduling, distinct from AI per-recipient send-time optimization). Status
    # is "scheduled" until it fires. Null = send on manual Trigger.
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DeliveryExecutionDB(Base):
    __tablename__ = "delivery_executions"

    id = Column(Integer, primary_key=True, index=True)
    # Indexed 2026-10-06 (task-296, migration 0036): an audience rule about one
    # send filters deliveries by it — measured 4.76 ms / 2,310 buffers -> 1.62 ms /
    # 384 at 100,000 deliveries.
    send_instance_id = Column(Integer, ForeignKey("send_instances.id"), nullable=False, index=True)
    recipient_id = Column(Integer, ForeignKey("recipients.id"), nullable=False)
    # "created" | "sent" | "failed" | "excluded".
    # "excluded" is not a failure: the recipient was deliberately not sent to,
    # and exclusion_reason says which stage of the ADR-163 point 7 stack
    # dropped them and why. Anything aggregating statuses has to know the
    # difference — an excluded recipient is a correct outcome, a failed one is
    # a problem.
    status = Column(String(50), nullable=False, default="created")
    # Populated only when status == "excluded". The property ADR-163 point 8
    # requires: "why didn't Anna get this?" answerable from the data rather
    # than from whether someone happened to be reading the log.
    exclusion_reason = Column(String(255), nullable=True)
    provider = Column(String(100), nullable=True)
    provider_message_id = Column(String(255), nullable=True, unique=True, index=True)
    # Denormalized at plan time (ADR-163 addendum 2026-09-12, point 1). An
    # inbound bounce/complaint webhook resolves a provider message id to this
    # row and must write a consent event keyed (recipient, channel, purpose) —
    # deriving channel from here would mean execution → send instance →
    # snapshot → variant on every inbound event, the same four-join shape
    # ADR-164 point 9 rejected for SignalContributionDB, and it degrades to
    # unknowable once executions are pruned.
    # **No Python-side default either** (task-42). migrate_0024 dropped the
    # database defaults as fail-open; these two survived it, and that is how a
    # push send's late joiner was planned as an email. A creator that forgets
    # is now a NOT NULL error rather than a silent email.
    channel = Column(String(50), nullable=False)
    purpose = Column(String(50), nullable=False)
    # **What this recipient got** (ADR-183, migration 0027), written in the
    # send loop. With the snapshot's frame it answers "what content did this
    # person receive, as of the send date": `sent_at` (not `updated_at`, which
    # later updates overwrite), `delivery_record` (their decision-slot picks,
    # each with a copy of its values and the content version used, and the
    # frame's template fingerprint), and `artifact_hash` over what was rendered.
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivery_record = Column(JSON, nullable=True)
    artifact_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )