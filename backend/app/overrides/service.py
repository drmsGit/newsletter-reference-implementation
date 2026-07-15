from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.campaigns.db_models import ModuleInstanceDB
from app.content.db_models import ContentRecordDB
from app.email_modules.registry import get_manifest
from app.overrides.db_models import ContentOverrideDB
from app.overrides.models import ContentOverrideCreate, OutcomeDeltaUpdate


def _validate_content_record_exists(db: Session, field_name: str, content_record_id: int) -> None:
    exists = (
        db.query(ContentRecordDB.id)
        .filter(ContentRecordDB.id == content_record_id)
        .first()
    )
    if exists is None:
        raise ValueError(
            f"{field_name}={content_record_id} does not reference an existing content record"
        )


def _overrideable_manifest(module: ModuleInstanceDB):
    """A content override needs (a) a module that actually resolves content — a
    content record or a decision slot — and (b) a manifest, so its overridable
    fields are known. A pure module_data module (no content reference) isn't
    content-overridden; its values are edited directly. Applies regardless of
    the manifest's cms flag — a hero/cta that references a content record is
    overridable too."""
    if module.content_record_id is None and module.decision_slot_id is None:
        raise ValueError(
            f"module {module.id} doesn't render a content record or decision slot "
            "— content overrides only apply to modules that resolve content; edit "
            "its module_data directly instead"
        )
    manifest = get_manifest(module.module_type)
    if manifest is None:
        raise ValueError(
            f"module {module.id} (type '{module.module_type}') has no manifest, so "
            "its overridable fields aren't known"
        )
    return manifest


def _validate_field_overrides(manifest, module: ModuleInstanceDB, field_overrides: dict) -> None:
    """Field-override keys must be declared variables of the target module's
    manifest — the same manifest-bound discipline the decision-slot config uses,
    so a typo'd field name is rejected up front instead of silently doing
    nothing at render time."""
    allowed = {v.name for v in manifest.variables}
    unknown = set(field_overrides) - allowed
    if unknown:
        raise ValueError(
            f"field_overrides has key(s) not in the '{module.module_type}' "
            f"manifest: {sorted(unknown)}. Allowed: {sorted(allowed)}"
        )


def create_content_override(db: Session, data: ContentOverrideCreate) -> ContentOverrideDB:
    module = (
        db.query(ModuleInstanceDB)
        .filter(ModuleInstanceDB.id == data.module_instance_id)
        .first()
    )
    if module is None:
        raise ValueError(f"module_instance_id={data.module_instance_id} does not exist")

    manifest = _overrideable_manifest(module)

    if not data.field_overrides:
        raise ValueError(
            "a content override must set field_overrides — the field(s) to change "
            "(e.g. a shorter headline for this send)"
        )
    _validate_field_overrides(manifest, module, data.field_overrides)

    if data.system_content_record_id is not None:
        _validate_content_record_exists(db, "system_content_record_id", data.system_content_record_id)

    override = ContentOverrideDB(
        module_instance_id=data.module_instance_id,
        field_overrides=data.field_overrides,
        system_content_record_id=data.system_content_record_id,
        send_instance_id=data.send_instance_id,
        overridden_by=data.overridden_by,
        reason=data.reason,
        active=True,
    )
    db.add(override)
    try:
        db.commit()
    except IntegrityError:
        # The partial unique index caught an existing active override on this
        # module — a module has a single override state, so reset the current
        # one before adding a new one.
        db.rollback()
        raise ValueError(
            f"module {data.module_instance_id} already has an active override — "
            "reset it before adding a new one"
        )
    db.refresh(override)
    return override


def get_active_content_override(db: Session, module_instance_id: int) -> ContentOverrideDB | None:
    """The single active override on a module, if any — the row rendering
    honors. O(1) via the partial unique index."""
    return (
        db.query(ContentOverrideDB)
        .filter(
            ContentOverrideDB.module_instance_id == module_instance_id,
            ContentOverrideDB.active.is_(True),
        )
        .first()
    )


def reset_content_override(db: Session, override_id: int) -> ContentOverrideDB | None:
    """Reset-to-original (ADR-041): deactivate the override so rendering falls
    back to system-governed content. The row is kept as history so the
    trust-loop comparison and any recorded outcome survive the reset."""
    override = (
        db.query(ContentOverrideDB)
        .filter(ContentOverrideDB.id == override_id)
        .with_for_update()
        .first()
    )
    if override is None:
        return None
    if override.active:
        override.active = False
        override.reverted_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(override)
    return override


def get_content_override(db: Session, override_id: int) -> ContentOverrideDB | None:
    return db.query(ContentOverrideDB).filter(ContentOverrideDB.id == override_id).first()


def list_content_overrides(
    db: Session,
    module_instance_id: int | None = None,
    send_instance_id: int | None = None,
    active: bool | None = None,
) -> list[ContentOverrideDB]:
    q = db.query(ContentOverrideDB)
    if module_instance_id is not None:
        q = q.filter(ContentOverrideDB.module_instance_id == module_instance_id)
    if send_instance_id is not None:
        q = q.filter(ContentOverrideDB.send_instance_id == send_instance_id)
    if active is not None:
        q = q.filter(ContentOverrideDB.active.is_(active))
    return q.order_by(ContentOverrideDB.created_at.desc()).all()


def record_outcome_delta(db: Session, override_id: int, data: OutcomeDeltaUpdate) -> ContentOverrideDB | None:
    # Row lock: two concurrent PATCH calls computing outcome deltas for the
    # same override (e.g. an open-rate job and a click-rate job overlapping)
    # would otherwise both read the same starting outcome_delta and the second
    # commit would silently clobber the first's write.
    override = (
        db.query(ContentOverrideDB)
        .filter(ContentOverrideDB.id == override_id)
        .with_for_update()
        .first()
    )
    if override is None:
        return None

    # Merge incoming keys into the existing dict instead of replacing it —
    # outcome data arrives incrementally (e.g. open-rate today, click-rate a
    # week later) and a wholesale replace would silently drop earlier keys.
    merged = dict(override.outcome_delta or {})
    merged.update(data.outcome_delta)
    override.outcome_delta = merged

    db.commit()
    db.refresh(override)
    return override
