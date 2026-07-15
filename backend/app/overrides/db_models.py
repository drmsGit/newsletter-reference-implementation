from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    JSON,
    func,
)

from app.database import Base


class ContentOverrideDB(Base):
    """A manager's intentional, logged deviation from what the system produced
    for one module — the *functional* override layer (ADR-040/041), not just an
    audit record. Rendering reads the active override and its field values take
    precedence over the resolved/static content until it is reset.

    An override is **field edits only**: `field_overrides` = {manifest field
    name: value}, e.g. a consistent headline across the personalized picks or a
    shorter copy for this send. Swapping the whole content record is deliberately
    NOT an override — for-all swaps mean "use static content, not a decision
    slot", and segment-targeted swaps ("beach recipients get a special offer")
    belong to the separate guaranteed-placement concept, which suppresses the
    decision slot for matching recipients rather than overriding it here.

    `system_content_record_id` captures which record the edited fields were
    applied to (audit context). `outcome_delta` is filled in retroactively once
    engagement data exists ("did the edited version outperform the original?").

    Deliberately shaped as a reusable spine: a future AudienceOverrideDB (once
    Phase 3B system-suggested audiences exist to deviate from) mirrors the same
    lifecycle — create → active → reset — and the same audit/outcome shape, with
    a different target and payload, rather than a single polymorphic table.
    """

    __tablename__ = "content_overrides"

    id = Column(Integer, primary_key=True, index=True)

    # The render target. A content override always attaches to a concrete
    # module instance (the render unit); the decision slot, if any, is
    # reachable via the module, so it isn't duplicated here.
    module_instance_id = Column(Integer, ForeignKey("module_instances.id"), nullable=False, index=True)

    # Field-level overrides: {manifest_variable_name: value}. Validated at
    # create time against the target module's manifest variables.
    field_overrides = Column(JSON, nullable=True)

    # Which content record the edited fields were applied to / measured against
    # (audit context for the trust loop). Nullable — for a per-recipient
    # personalized module the resolved record varies, so it may be left unset.
    system_content_record_id = Column(Integer, ForeignKey("content_records.id"), nullable=True)

    # Optional: the send whose engagement the outcome_delta is measured against.
    send_instance_id = Column(Integer, ForeignKey("send_instances.id"), nullable=True)

    overridden_by = Column(String(255), nullable=False)
    reason = Column(String(1000), nullable=True)

    # Active overrides drive rendering; reset flips this to False (ADR-041's
    # "used until it is deleted or reset") while keeping the row as history.
    active = Column(Boolean, nullable=False, default=True, server_default="true")
    reverted_at = Column(DateTime(timezone=True), nullable=True)

    # Filled retroactively after send when engagement data is available.
    outcome_delta = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        # An override must actually change something — it carries field edits.
        # (The service also rejects an empty dict; this is the DB-level net.)
        CheckConstraint(
            "field_overrides IS NOT NULL",
            name="ck_content_overrides_changes_something",
        ),
        # At most one *active* override per module — a module has a single
        # override state. History (reset rows) accumulates freely.
        Index(
            "ux_content_overrides_one_active_per_module",
            "module_instance_id",
            unique=True,
            postgresql_where=(active == True),  # noqa: E712
        ),
    )
