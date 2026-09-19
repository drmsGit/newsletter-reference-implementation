"""Seed the approval inbox with demo requests, so the screen can be looked at.

Run from `backend/`:

    venv/bin/python scripts/seed_pending_actions.py          # add demo rows
    venv/bin/python scripts/seed_pending_actions.py --clear  # remove them again

**Every row goes through the real service**, so the audit trail behind each one
is genuine and the detail page's History panel shows what actually happened.
Nothing here writes a status directly: a seeded "rejected" request was really
rejected, and a seeded "expired" one really lapsed. Fabricating those states
would make the one screen whose job is to show what happened show something
that did not.

Two consequences worth knowing before clicking:

  * **Approving a seeded request really fires that send.** The demo instances
    below use the mock provider, so nothing leaves the building — but the send
    instance's status does change, and that is the point.
  * The requester is recorded as `integration #0`, which is a stand-in. Once
    the guard rewiring lands, a real machine principal fills that in.
"""

import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.approvals import service as approvals  # noqa: E402
from app.approvals.actions.send_fire import summarise  # noqa: E402
from app.approvals.db_models import PendingActionDB  # noqa: E402
from app.audit.db_models import AuditEventDB  # noqa: E402
from app.auth.service import ensure_default_brand  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.delivery.db_models import SendInstanceDB  # noqa: E402

ACTION = "send.fire_send_instance"
SEED_MARK = "seed"


def _seed_ids(db) -> list[int]:
    return [
        row[0] for row in db.execute(text(
            "SELECT id FROM pending_actions WHERE action_key = :k "
            "AND requested_by_type = 'integration' AND requested_by_id = 0"),
            {"k": ACTION}).all()
    ]


def clear(db) -> int:
    ids = _seed_ids(db)
    if ids:
        db.query(AuditEventDB).filter(
            AuditEventDB.subject_type == approvals.SUBJECT,
            AuditEventDB.subject_id.in_(ids),
        ).delete(synchronize_session=False)
        db.query(PendingActionDB).filter(
            PendingActionDB.id.in_(ids)
        ).delete(synchronize_session=False)
        db.commit()
    return len(ids)


def _request(db, send_instance, brand_id, ttl_seconds=None):
    return approvals.request_approval(
        db, ACTION,
        payload={"send_instance_id": send_instance.id},
        summary=summarise(db, send_instance.id),
        requested_by_type="integration",
        # A stand-in until a real machine principal raises these.
        requested_by_id=0,
        brand_id=brand_id,
        subject_id=send_instance.id,
        ttl_seconds=ttl_seconds,
    )


def seed(db) -> None:
    brand_id = ensure_default_brand(db).id
    instances = (
        db.query(SendInstanceDB)
        .filter(SendInstanceDB.brand_id == brand_id)
        .order_by(SendInstanceDB.id.desc())
        .all()
    )
    if not instances:
        print("No send instances in this brand — nothing to raise requests about.")
        return

    # Prefer a draft instance for the approvable example, so approving it does
    # something rather than being refused as already sent.
    drafts = [i for i in instances if i.status == "draft"]
    others = [i for i in instances if i.status != "draft"]

    made: list[tuple[str, PendingActionDB]] = []

    # 1. Waiting, and genuinely approvable.
    if drafts:
        made.append(("waiting (approvable)", _request(db, drafts[0], brand_id)))

    # 2. Waiting, but the send has already gone out — the case where `describe()`
    #    warns you and approving would be refused. Worth seeing on the screen.
    if others:
        made.append(("waiting (already sent — shows a warning)",
                     _request(db, others[0], brand_id)))

    # 3. Rejected, through the real path so the history reads correctly.
    if len(others) > 1:
        rejected = _request(db, others[1], brand_id)
        approvals.reject(
            db, rejected.id, approver_type="user", approver_id=None,
            reason="Not this week — the offer changed.",
        )
        made.append(("rejected", rejected))

    # 4. Expired, also for real: requested with a one-second life, then swept.
    if len(others) > 2:
        lapsed = _request(db, others[2], brand_id, ttl_seconds=1)
        lapsed.expires_at = approvals.now() - timedelta(minutes=5)
        db.commit()
        approvals.expire_due_pending_actions(db)
        made.append(("expired", lapsed))

    for label, row in made:
        print(f"  #{row.id:<5} {label:<40} {row.summary}")
    print(f"\n{len(made)} request(s) seeded in brand {brand_id}.")
    print("Open /ui/approvals — 'Waiting' by default, 'Decided' for the rest.")
    if not drafts:
        print("\nNote: no draft send instance exists, so nothing here is "
              "approvable without being refused. Create a send in the UI first "
              "and re-run to get one you can actually approve.")


if __name__ == "__main__":
    session = SessionLocal()
    try:
        if "--clear" in sys.argv:
            print(f"Removed {clear(session)} seeded request(s).")
        else:
            clear(session)
            seed(session)
    finally:
        session.close()
