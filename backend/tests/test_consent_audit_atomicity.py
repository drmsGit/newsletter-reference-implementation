"""Consent and its actor audit are one transaction (task-340; ADR-153/163)."""
import pytest

from tests import test_render_skip as _render_skip

db = _render_skip.db
world = _render_skip.world


@pytest.mark.parametrize("operation", ["upsert", "crm"])
def test_audit_failure_cannot_leave_an_unaudited_consent_change(db, world, monkeypatch, operation):
    from app.audit import service as audit
    from app.audit.db_models import AuditEventDB
    from app.recipients.db_models import ConsentEventDB, ConsentSyncLogDB
    from tests.test_api_guard import signed_in

    person = world["person"]()
    person_id = person.id
    before_events = db.query(ConsentEventDB).filter_by(recipient_id=person_id).count()
    before_logs = db.query(ConsentSyncLogDB).filter_by(recipient_id=person_id).count()
    called = []
    original = audit.record

    def failed_record(session, action, **kwargs):
        if action == audit.CONSENT_RECORDED:
            called.append(action)
            # Fail after staging the audit too: both writes must roll back.
            original(session, action, **kwargs)
            raise RuntimeError("simulated audit storage failure")
        return original(session, action, **kwargs)

    monkeypatch.setattr(audit, "record", failed_record)
    with signed_in(db) as (client, _token, csrf):
        body = {
            "brand_id": world["brand"].id,
            "consent_status": "opted_out",
        }
        if operation == "upsert":
            body["external_id"] = person.external_id
            url = "/recipients/"
        else:
            body.update(channel="email", purpose="marketing", source="crm")
            url = f"/recipients/{person.external_id}/consent"
        response = client.post(url, headers={"X-CSRF-Token": csrf}, json=body)

    assert response.status_code == 500, response.text
    assert called == [audit.CONSENT_RECORDED]
    db.rollback()
    db.expire_all()
    assert db.query(ConsentEventDB).filter_by(recipient_id=person_id).count() == before_events
    assert db.query(ConsentSyncLogDB).filter_by(recipient_id=person_id).count() == before_logs
    assert db.query(AuditEventDB).filter_by(
        action=audit.CONSENT_RECORDED, subject_type="recipient", subject_id=person_id,
    ).count() == 0
