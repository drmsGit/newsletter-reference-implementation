from sqlalchemy.orm import Session

from app.content.db_models import ContentRecordDB
from app.overrides.db_models import OverrideEventDB
from app.overrides.models import OverrideEventCreate, OutcomeDeltaUpdate


def create_override_event(db: Session, data: OverrideEventCreate) -> OverrideEventDB:
    if data.system_content_record_id == data.override_content_record_id:
        raise ValueError(
            "system_content_record_id and override_content_record_id must differ "
            "— an override that picks the same content as the system isn't an override"
        )

    for field_name, content_record_id in (
        ("system_content_record_id", data.system_content_record_id),
        ("override_content_record_id", data.override_content_record_id),
    ):
        exists = (
            db.query(ContentRecordDB.id)
            .filter(ContentRecordDB.id == content_record_id)
            .first()
        )
        if exists is None:
            raise ValueError(
                f"{field_name}={content_record_id} does not reference an existing content record"
            )

    event = OverrideEventDB(**data.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_override_event(db: Session, override_id: int) -> OverrideEventDB | None:
    return db.query(OverrideEventDB).filter(OverrideEventDB.id == override_id).first()


def list_override_events(
    db: Session,
    module_instance_id: int | None = None,
    send_instance_id: int | None = None,
) -> list[OverrideEventDB]:
    q = db.query(OverrideEventDB)
    if module_instance_id is not None:
        q = q.filter(OverrideEventDB.module_instance_id == module_instance_id)
    if send_instance_id is not None:
        q = q.filter(OverrideEventDB.send_instance_id == send_instance_id)
    return q.order_by(OverrideEventDB.created_at.desc()).all()


def record_outcome_delta(db: Session, override_id: int, data: OutcomeDeltaUpdate) -> OverrideEventDB | None:
    # Row lock: two concurrent PATCH calls computing outcome deltas for the
    # same override (e.g. an open-rate job and a click-rate job overlapping)
    # would otherwise both read the same starting outcome_delta and the
    # second commit would silently clobber the first's write. Same pattern
    # as the Delivery Q5 double-send guard.
    event = (
        db.query(OverrideEventDB)
        .filter(OverrideEventDB.id == override_id)
        .with_for_update()
        .first()
    )
    if event is None:
        return None

    # Merge incoming keys into the existing dict instead of replacing it —
    # outcome data arrives incrementally (e.g. open-rate today, click-rate
    # a week later) and a wholesale replace would silently drop earlier keys.
    merged = dict(event.outcome_delta or {})
    merged.update(data.outcome_delta)
    event.outcome_delta = merged

    db.commit()
    db.refresh(event)
    return event
