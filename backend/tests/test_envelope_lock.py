"""A variant edit and its envelope copy commit as one (task-322).

`update_variant` checked the version token under a row lock, then committed
the rename — releasing the lock — and only then wrote the envelope (subject,
preheader) with a second commit. A second editor could slip in between, write
its envelope with a token that had seen the rename, and be silently overwritten
when the first resumed: the lost update ADR-180 point 2's version check exists
to stop. Found by the external review of 2026-10-09. The rename and the
envelope now commit together under the lock.
"""
import threading
import uuid

from app.campaigns import service as campaigns
from app.campaigns.db_models import VariantDB
from app.database import SessionLocal
from app.rendering.service import envelope_fields_for_variant
from tests import test_render_skip as _render_skip

db = _render_skip.db
world = _render_skip.world


def test_a_second_editor_is_never_silently_overwritten(db, world, monkeypatch):
    variant = world["variant"]("email", static=True, slots=0)
    brand = world["brand"].id
    t0 = db.query(VariantDB.updated_at).filter(VariantDB.id == variant.id).scalar()

    a_in_envelope, b_done = threading.Event(), threading.Event()
    real = campaigns.set_envelope_fields
    a_thread: dict = {}

    def pausing(db_, variant_id, fields, **kwargs):
        if threading.current_thread() is a_thread.get("t"):
            a_in_envelope.set()
            b_done.wait(timeout=2)
        return real(db_, variant_id, fields, **kwargs)

    monkeypatch.setattr(campaigns, "set_envelope_fields", pausing)
    outcome: dict = {}

    def editor(name, subject, token_from):
        session = SessionLocal()
        try:
            token = token_from(session)
            campaigns.update_variant(session, variant.id, name, {"subject": subject, "preheader": "p"},
                                     brand_id=brand, expected_updated_at=token)
            outcome[name] = "accepted"
        except campaigns.StaleWrite:
            session.rollback()
            outcome[name] = "refused"
        finally:
            session.close()

    a = threading.Thread(target=editor, args=("A", "from A", lambda s: t0))
    a_thread["t"] = a
    a.start()
    assert a_in_envelope.wait(timeout=5)

    def b_token(session):     # B reads the version as it stands now
        return session.query(VariantDB.updated_at).filter(VariantDB.id == variant.id).scalar()

    b = threading.Thread(target=editor, args=("B", "from B", b_token))
    b.start()
    b.join(timeout=1)
    b_done.set()
    a.join(timeout=10)
    b.join(timeout=10)

    check = SessionLocal()
    try:
        subject = envelope_fields_for_variant(check, variant.id, "email").get("subject")
    finally:
        check.close()
    assert outcome["A"] == "accepted"
    if outcome["B"] == "accepted":
        assert subject == "from B", "B's accepted envelope was silently overwritten by A, which never saw it"
    else:
        assert subject == "from A"


def test_a_failed_envelope_write_leaves_no_half_committed_rename(db, world, monkeypatch):
    import pytest

    variant = world["variant"]("email", static=True, slots=0)
    before = variant.name

    def fails(*args, **kwargs):
        raise RuntimeError("module write refused")

    monkeypatch.setattr(campaigns, "set_envelope_fields", fails)
    session = SessionLocal()
    try:
        with pytest.raises(RuntimeError):
            campaigns.update_variant(session, variant.id, "renamed", {"subject": "x"}, brand_id=world["brand"].id)
        session.rollback()
    finally:
        session.close()
    check = SessionLocal()
    try:
        assert check.query(VariantDB.name).filter(VariantDB.id == variant.id).scalar() == before
    finally:
        check.close()
