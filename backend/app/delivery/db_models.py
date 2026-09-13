from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from app.database import Base


class SendInstanceDB(Base):
    __tablename__ = "send_instances"

    id = Column(Integer, primary_key=True, index=True)
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
    # How the audience is resolved into recipients:
    #   "freeze" — executions are fixed at plan time (a snapshot of the group).
    #   "rerun"  — the group is re-resolved immediately before the send fires and
    #              executions are reconciled (add newly-matching, drop no-longer-
    #              matching that haven't sent). Mirrors Salesforce's send-time
    #              audience re-evaluation.
    audience_resolution_mode = Column(String(20), nullable=False, default="freeze")
    # Derived from the child executions once the send finishes, rather than set
    # unconditionally. Persisted rather than computed on read because
    # monitoring, retries and the audit trail all want the number without a
    # GROUP BY, and because a finished send's counts do not change.
    #
    # excluded_count is deliberately separate from failed_count: an excluded
    # recipient is the exclusion stack working (ADR-163 point 7), not a
    # delivery problem, and folding the two together would recreate the lie
    # this field exists to stop.
    sent_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    excluded_count = Column(Integer, nullable=False, default=0)
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
    send_instance_id = Column(Integer, ForeignKey("send_instances.id"), nullable=False)
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
    channel = Column(String(50), nullable=False, default="email")
    purpose = Column(String(50), nullable=False, default="marketing")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )