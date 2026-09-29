"""Backfill `audience_resolution_mode` on un-fired sends — ADR-176 point 4.

**Only sends that have not gone out are touched.** A send that already fired
*was* frozen: its executions were fixed at plan time and that is what happened.
Rewriting those rows to `"rerun"` would edit history to agree with a decision
taken afterwards, which is the same error as rewriting a dated ADR citation.
They keep the value, and `SendInstanceDB`'s comment says why a reader will
still see it.

An un-fired send is different: it is a plan, and under point 4 it will
re-resolve when it fires whatever the column says. Leaving it reading "freeze"
would describe behaviour it does not have.

Idempotent and dry-run by default; `--apply` commits.

    venv/bin/python scripts/migrate_0021_freeze_is_history.py
    venv/bin/python scripts/migrate_0021_freeze_is_history.py --apply
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Imported for the side effect: `send_instances` carries foreign keys to tables
# these modules define, and SQLAlchemy resolves them at flush time. A dry run
# never flushes, so without this an --apply run dies where the dry run passed —
# which is exactly how migration 0020 failed on 2026-09-28.
import app.audience.db_models  # noqa: E402,F401
import app.auth.db_models  # noqa: E402,F401
import app.campaigns.db_models  # noqa: E402,F401
import app.snapshots.db_models  # noqa: E402,F401
from app.database import SessionLocal  # noqa: E402
from app.delivery.db_models import SendInstanceDB  # noqa: E402

# Statuses a send can hold before anything has left the machine. Anything else
# — sending, sent, failed, partial — describes an attempt that happened, and
# how its audience was resolved is a fact about that attempt.
UNFIRED = ("draft", "scheduled")


def main() -> int:
    apply = "--apply" in sys.argv
    db = SessionLocal()
    try:
        stale = (
            db.query(SendInstanceDB)
            .filter(
                SendInstanceDB.audience_resolution_mode == "freeze",
                SendInstanceDB.status.in_(UNFIRED),
            )
            .order_by(SendInstanceDB.id.asc())
            .all()
        )
        history = (
            db.query(SendInstanceDB)
            .filter(
                SendInstanceDB.audience_resolution_mode == "freeze",
                SendInstanceDB.status.notin_(UNFIRED),
            )
            .count()
        )

        for send in stale:
            print(f"  send {send.id} ({send.status}) {send.name!r}: freeze -> rerun")
            if apply:
                send.audience_resolution_mode = "rerun"

        print(f"\n{len(stale)} un-fired send(s) to backfill.")
        print(
            f"{history} fired send(s) left reading 'freeze' on purpose — that "
            "is how they were planned and it is true."
        )
        if apply:
            db.commit()
            print("\nApplied.")
        else:
            print("\nDry run. Re-run with --apply to commit.")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
