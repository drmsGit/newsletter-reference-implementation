"""The approval-inbox demo seed names real actors (2026-10-03).

It used to raise every request as `integration #0` — a stand-in from before
machine principals existed (ADR-166) — and to reject as a 'user' with no id,
so the inbox read "integration #0" and the history "Decided by: user". Now a
named demo integration asks, holding the `sends.execute` grant a real one
would need, and a real person decides.
"""
from app.approvals.db_models import PendingActionDB
from app.auth.db_models import IntegrationDB
from app.database import SessionLocal
from scripts import seed_pending_actions as seed_script


def test_requests_come_from_a_named_integration_and_a_person_decides():
    """Three sent instances besides the draft, so the seed reaches every branch:
    waiting, waiting-but-sent, rejected and expired. With fewer it silently
    skips the rejection, and who decided would go untested."""
    from app.delivery.db_models import SendInstanceDB

    db = SessionLocal()
    extra = []
    made_admin = None
    try:
        # A person must exist to decide. Locally the initial admin from .env is
        # one; CI has no .env, so the test brings its own (found by CI's first
        # run, 2026-10-08) rather than depending on the environment.
        if seed_script._deciding_person(db) is None:
            from app.auth import service as auth
            made_admin = auth.create_user(db, email="seedtest-admin@example.invalid", role_key="admin",
                                          brand_id=auth.ensure_default_brand(db).id)
        template = db.query(SendInstanceDB).filter(SendInstanceDB.status == "sent").first()
        for i in range(2):
            row = SendInstanceDB(brand_id=template.brand_id, snapshot_id=template.snapshot_id,
                                 name=f"seedtest sent {i}", status="sent", provider="mock")
            db.add(row)
            extra.append(row)
        db.commit()
        seed_script.clear(db)
        seed_script.seed(db)
        integration = db.query(IntegrationDB).filter(
            IntegrationDB.name == seed_script.DEMO_INTEGRATION).one()
        rows = db.query(PendingActionDB).filter(
            PendingActionDB.requested_by_type == "integration",
            PendingActionDB.requested_by_id == integration.id).all()
        assert rows, "the seed raised nothing"
        rejected = [r for r in rows if r.status == "rejected"]
        assert rejected, "the seed made no rejection, so who decided goes untested"
        for row in rejected:
            assert row.decided_by_type == "user" and row.decided_by_id is not None, (
                "a rejection with nobody behind it")
        # Holds the grant a real integration needs to ask for a held send.
        # (Asked the way the guard asks it.)
        from app.auth.permissions import SENDS_EXECUTE
        from app.auth.service import has_permission
        assert has_permission(db, integration, SENDS_EXECUTE, brand_id=rows[0].brand_id)
        # --clear removes what it made.
        assert seed_script.clear(db) == len(rows)
        assert db.query(PendingActionDB).filter(
            PendingActionDB.requested_by_id == integration.id,
            PendingActionDB.requested_by_type == "integration").count() == 0
    finally:
        db.rollback()
        seed_script.clear(db)
        for row in extra:
            db.delete(db.merge(row))
        if made_admin is not None:
            from sqlalchemy import text
            for table in ("audit_events", ):
                db.execute(text(f"DELETE FROM {table} WHERE actor_type = 'user' AND actor_id = :u"), {"u": made_admin.id})
            db.execute(text("DELETE FROM role_assignments WHERE user_id = :u"), {"u": made_admin.id})
            db.execute(text("DELETE FROM users WHERE id = :u"), {"u": made_admin.id})
        db.commit()
        db.close()
