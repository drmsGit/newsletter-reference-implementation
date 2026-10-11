"""A zero unattended ceiling holds even an empty scheduled send (ADR-166)."""
from app.auth.permissions import SENDS_EXECUTE, VIEW
from app.delivery.db_models import SendInstanceDB
from tests.machine import machine
from tests.test_unattended_ceiling import _pending, api
from tests.test_unattended_ceiling import db, fired, sends  # noqa: F401


def test_zero_ceiling_holds_an_empty_due_send_on_repeated_sweeps(db, sends, fired):  # noqa: F811
    send = sends(0, scheduled=True)
    with machine([VIEW, SENDS_EXECUTE]) as headers:
        for _ in range(2):
            response = api.post("/delivery/process-due", headers=headers)
            assert response.status_code == 200, response.text
            assert send.id in response.json()["held_send_instance_ids"]
            assert send.id not in response.json()["send_instance_ids"]
            assert fired == []
            assert len(_pending(db, send.id)) == 1
            db.expire_all()
            assert db.get(SendInstanceDB, send.id).status == "scheduled"
