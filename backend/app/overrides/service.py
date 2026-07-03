from sqlalchemy.orm import Session

from app.overrides.db_models import OverrideEventDB
from app.overrides.models import OverrideEventCreate, OutcomeDeltaUpdate


def create_override_event(db: Session, data: OverrideEventCreate) -> OverrideEventDB:
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
    event = get_override_event(db, override_id)
    if event is None:
        return None
    event.outcome_delta = data.outcome_delta
    db.commit()
    db.refresh(event)
    return event
