"""A slot's ranked set of picks (task-109; ADR-084 addendum 2026-10-11).

A slot shows up to N records, so what a decision stores is a set: one row per
pick, sharing a `pick_set`, each with its `rank`. **Every reader goes through
here**, because "the latest row" stopped being the answer the moment a set had
more than one: it would be the last-written pick, not the set.

The order readers have always used is kept: the recipient's own set if there
is one, else the slot's global one.
"""
from sqlalchemy.orm import Session

from app.campaigns.db_models import DecisionResolutionDB


def _latest_row(db: Session, slot_id: int, recipient_id: int | None) -> DecisionResolutionDB | None:
    query = db.query(DecisionResolutionDB).filter(DecisionResolutionDB.decision_slot_id == slot_id)
    query = (query.filter(DecisionResolutionDB.recipient_id == recipient_id) if recipient_id is not None
             else query.filter(DecisionResolutionDB.recipient_id.is_(None)))
    return query.order_by(DecisionResolutionDB.created_at.desc(), DecisionResolutionDB.id.desc()).first()


def set_of(db: Session, row: DecisionResolutionDB) -> list[DecisionResolutionDB]:
    """The whole set `row` belongs to, first pick first. A row from before
    sets is a set of one."""
    if row.pick_set is None:
        return [row]
    return (db.query(DecisionResolutionDB)
            .filter(DecisionResolutionDB.decision_slot_id == row.decision_slot_id,
                    DecisionResolutionDB.pick_set == row.pick_set)
            .order_by(DecisionResolutionDB.rank, DecisionResolutionDB.id).all())


def own_set(db: Session, slot_id: int, recipient_id: int | None) -> list[DecisionResolutionDB]:
    """The latest set stored for exactly this recipient (None: the global one)."""
    row = _latest_row(db, slot_id, recipient_id)
    return set_of(db, row) if row is not None else []


def latest_pick_set(db: Session, slot_id: int, recipient_id: int | None) -> list[DecisionResolutionDB]:
    """What the slot shows this recipient: their own latest set, else the
    slot's global one. Empty when nothing was ever resolved."""
    if recipient_id is not None:
        found = own_set(db, slot_id, recipient_id)
        if found:
            return found
    return own_set(db, slot_id, None)
