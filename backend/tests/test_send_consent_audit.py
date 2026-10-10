"""Every send and every consent change names who did it (task-340, gate 11).

The audit log is the record behind "transparency", but the two events an
auditor asks about first were missing from it: a send fired directly (by a
person, or an integration allowed to send unattended) wrote nothing — only an
approval-routed send logged `send.fired` — and a consent change kept what and
from which source, never who. Decided 2026-10-09 (business baseline P2-D1):
both are audited with their actor before public beta. A recipient's own
unsubscribe stays in the consent history; the recipient is not an audit actor.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.audit.db_models import AuditEventDB
from app.audit.service import ACTOR_INTEGRATION, ACTOR_USER, CONSENT_RECORDED, SEND_FIRED
from app.auth import integrations as ints
from app.auth.db_models import IntegrationCredentialDB
from app.auth.permissions import RECIPIENTS_CONSENT, SENDS_EXECUTE
from app.database import SessionLocal
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.recipients.db_models import ConsentSyncLogDB
from app.snapshots.service import create_snapshot_for_variant
from app.subscriptions.service import unsubscribe
from main import app
from tests import test_render_skip as _render_skip
from tests.machine import machine
from tests.test_api_guard import signed_in

api = TestClient(app, raise_server_exceptions=False)
db = _render_skip.db
world = _render_skip.world


@pytest.fixture
def entries(db):
    """The audit rows a test looks up, removed afterwards."""
    seen: list[int] = []

    def find(action, subject_type, subject_id):
        db.expire_all()
        rows = db.query(AuditEventDB).filter_by(action=action, subject_type=subject_type, subject_id=subject_id).all()
        seen.extend(r.id for r in rows)
        return rows

    find.synced = []        # recipients a CRM sync logged, so their log rows go first
    yield find
    db.rollback()
    db.query(AuditEventDB).filter(AuditEventDB.id.in_(seen)).delete(synchronize_session=False)
    if find.synced:
        db.query(ConsentSyncLogDB).filter(ConsentSyncLogDB.recipient_id.in_(find.synced)).delete(synchronize_session=False)
    db.commit()


def _send(db, world, *, status="draft") -> SendInstanceDB:
    brand = world["brand"]
    snapshot = create_snapshot_for_variant(db, world["variant"](static=True, slots=0).id, brand_id=brand.id)
    world["made"]["snapshots"].append(snapshot.id)
    send = SendInstanceDB(snapshot_id=snapshot.id, brand_id=brand.id, name="task-340", status=status, provider="mock",
                          scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=1) if status == "scheduled" else None)
    db.add(send)
    db.flush()
    world["made"]["sends"].append(send.id)
    db.add(DeliveryExecutionDB(send_instance_id=send.id, recipient_id=world["person"]().id, status="created",
                               provider="mock", channel="email", purpose="marketing"))
    db.commit()
    return send


def _unattended(headers) -> int:
    key_id = headers["Authorization"].split()[1].split(".")[0]
    with SessionLocal() as session:
        credential = session.query(IntegrationCredentialDB).filter_by(key_id=key_id).one()
        ints.set_unattended_sending(session, credential.integration_id, True)
        return credential.integration_id


class TestASendNamesWhoFiredIt:

    def test_a_person_sending_directly(self, db, world, entries):
        send = _send(db, world)
        with signed_in(db) as (client, _token, csrf):
            response = client.post(f"/delivery/send-instances/{send.id}/send", headers={"X-CSRF-Token": csrf})
            me = client.get("/auth/session").json()["user"]["id"]
        assert response.status_code == 200, response.text
        [entry] = entries(SEND_FIRED, "send_instance", send.id)
        assert (entry.actor_type, entry.actor_id) == (ACTOR_USER, me)
        assert entry.detail["via"] == "direct" and entry.detail["outcome"] == "sent"

    def test_an_integration_sending_unattended(self, db, world, entries):
        send = _send(db, world)
        with machine([SENDS_EXECUTE], brand_id=world["brand"].id) as headers:
            integration_id = _unattended(headers)
            response = api.post(f"/delivery/send-instances/{send.id}/send", headers=headers)
        assert response.status_code == 200, response.text
        [entry] = entries(SEND_FIRED, "send_instance", send.id)
        assert (entry.actor_type, entry.actor_id) == (ACTOR_INTEGRATION, integration_id)

    def test_the_old_screens_send_button(self, db, world, entries):
        send = _send(db, world)
        with signed_in(db) as (client, _token, csrf):
            response = client.post(f"/ui/send-instances/{send.id}/send", data={"csrf_token": csrf},
                                   follow_redirects=False)
        assert response.status_code == 303, response.text
        [entry] = entries(SEND_FIRED, "send_instance", send.id)
        assert entry.actor_type == ACTOR_USER and entry.actor_id is not None

    def test_a_scheduled_send_fired_by_the_scheduler(self, db, world, entries):
        send = _send(db, world, status="scheduled")
        with machine([SENDS_EXECUTE], brand_id=world["brand"].id) as headers:
            integration_id = _unattended(headers)
            response = api.post("/delivery/process-due", headers=headers)
        assert response.status_code == 200 and send.id in response.json()["send_instance_ids"], response.text
        [entry] = entries(SEND_FIRED, "send_instance", send.id)
        assert (entry.actor_type, entry.actor_id, entry.detail["via"]) == (ACTOR_INTEGRATION, integration_id, "scheduled")

    def test_a_refused_send_fired_nothing_and_says_nothing(self, db, world, entries):
        send = _send(db, world, status="sent")
        with signed_in(db) as (client, _token, csrf):
            response = client.post(f"/delivery/send-instances/{send.id}/send", headers={"X-CSRF-Token": csrf})
        assert response.status_code == 409
        assert entries(SEND_FIRED, "send_instance", send.id) == []


class TestAConsentChangeNamesWhoMadeIt:

    def test_a_crm_assertion_by_an_integration(self, db, world, entries):
        person = world["person"]()
        entries.synced.append(person.id)
        with machine([RECIPIENTS_CONSENT], brand_id=world["brand"].id) as headers:
            key_id = headers["Authorization"].split()[1].split(".")[0]
            with SessionLocal() as session:
                integration_id = session.query(IntegrationCredentialDB).filter_by(key_id=key_id).one().integration_id
            response = api.post(f"/recipients/{person.external_id}/consent", headers=headers, json={
                "consent_status": "opted_out", "brand_id": world["brand"].id, "source": "crm",
                "channel": "email", "purpose": "marketing"})
        assert response.status_code == 200, response.text
        [entry] = entries(CONSENT_RECORDED, "recipient", person.id)
        assert (entry.actor_type, entry.actor_id) == (ACTOR_INTEGRATION, integration_id)
        assert entry.detail == {"status": "opted_out", "channel": "email", "purpose": "marketing", "source": "crm"}

    def test_a_person_creating_a_recipient_with_consent(self, db, world, entries):
        external_id = f"t340-{uuid.uuid4().hex[:8]}"
        with signed_in(db) as (client, _token, csrf):
            response = client.post("/recipients/", headers={"X-CSRF-Token": csrf}, json={
                "brand_id": world["brand"].id, "external_id": external_id,
                "address": f"{external_id}@example.invalid", "consent_status": "opted_in"})
        assert response.status_code == 200, response.text
        recipient_id = response.json()["id"]
        world["made"]["people"].append(recipient_id)
        [entry] = entries(CONSENT_RECORDED, "recipient", recipient_id)
        assert entry.actor_type == ACTOR_USER and entry.actor_id is not None
        assert "@" not in str(entry.detail), "no email in an audit entry (ADR-153)"

    def test_an_unchanged_assertion_on_create_writes_nothing(self, db, world, entries):
        """create_recipient writes a consent event only when the state changes."""
        person = world["person"]()       # already opted in
        with signed_in(db) as (client, _token, csrf):
            response = client.post("/recipients/", headers={"X-CSRF-Token": csrf}, json={
                "brand_id": world["brand"].id, "external_id": person.external_id, "consent_status": "opted_in"})
        assert response.status_code == 200, response.text
        assert entries(CONSENT_RECORDED, "recipient", person.id) == []

    def test_a_recipients_own_unsubscribe_stays_in_the_consent_history(self, db, world, entries):
        send = _send(db, world)
        from app.delivery.service import send_send_instance

        send_send_instance(db, send.id, brand_id=world["brand"].id)
        db.expire_all()
        execution = db.query(DeliveryExecutionDB).filter_by(send_instance_id=send.id).one()
        assert unsubscribe(db, execution.unsubscribe_token)
        assert entries(CONSENT_RECORDED, "recipient", execution.recipient_id) == []
