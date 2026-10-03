"""Finding one recipient in a segment or a send (2026-10-03).

Decided with the user: no pagination for an audience's reach or a send's
recipients. The 20-recipient sample stays, and a manager looking for someone
specific SEARCHES — by the recipient's identifier or their address on that
channel, case-insensitive, part of either. The search is server-side, so it
works however large the segment is, and it says how many match (ADR-185
point 6: a filter applies to the rows and the count alike).
"""
from fastapi.testclient import TestClient

from app.audience.db_models import AudienceGroupDB
from app.auth.permissions import VIEW
from app.database import SessionLocal
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from app.recipients.consent import address_value
from app.recipients.db_models import AddressabilityDB, RecipientDB
from main import app
from tests.machine import machine

client = TestClient(app, raise_server_exceptions=False)


def _someone_in(db, group_name="Demo send audience"):
    """One reachable member of the seeded group, with their email address."""
    from app.audience.db_models import AudienceGroupMemberDB

    group = db.query(AudienceGroupDB).filter(AudienceGroupDB.name == group_name).one()
    member = db.query(AudienceGroupMemberDB).filter(AudienceGroupMemberDB.group_id == group.id).first()
    recipient = db.get(RecipientDB, member.recipient_id)
    address = db.query(AddressabilityDB).filter(AddressabilityDB.recipient_id == recipient.id,
                                                AddressabilityDB.channel == "email").first()
    return group, recipient, address_value(address, "email")


def _preview(group_id, **params):
    with machine([VIEW]) as headers:
        response = client.get(f"/api/audience-groups/{group_id}/preview",
                              params={"channel": "email", **params}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


class TestSearchingASegment:
    def test_without_a_search_the_sample_is_the_first_twenty_and_says_of_how_many(self):
        db = SessionLocal()
        try:
            group, _, _ = _someone_in(db)
        finally:
            db.close()
        body = _preview(group.id)
        assert len(body["sample"]) == min(20, body["reachable_count"])
        assert body["sample_matching"] == body["reachable_count"]

    def test_by_identifier(self):
        db = SessionLocal()
        try:
            group, recipient, _ = _someone_in(db)
        finally:
            db.close()
        body = _preview(group.id, q=recipient.external_id)
        assert [r["recipient_id"] for r in body["sample"]] == [recipient.id]
        assert body["sample_matching"] == 1
        # The counts describe the segment, not the search.
        assert body["reachable_count"] > 1

    def test_by_part_of_the_address_whatever_its_case(self):
        db = SessionLocal()
        try:
            group, recipient, email = _someone_in(db)
        finally:
            db.close()
        local_part = email.split("@")[0]
        body = _preview(group.id, q=local_part.upper())
        assert recipient.id in [r["recipient_id"] for r in body["sample"]]
        assert all(local_part in (r["address"] or "").lower() or local_part in r["external_id"].lower()
                   for r in body["sample"])

    def test_no_match_is_an_empty_sample_not_an_error(self):
        db = SessionLocal()
        try:
            group, _, _ = _someone_in(db)
        finally:
            db.close()
        body = _preview(group.id, q="nobody-is-called-this")
        assert (body["sample"], body["sample_matching"]) == ([], 0)


class TestSearchingASend:
    def _demo(self, db):
        send = db.query(SendInstanceDB).filter(SendInstanceDB.name == "Demo send").one()
        execution = db.query(DeliveryExecutionDB).filter(
            DeliveryExecutionDB.send_instance_id == send.id).first()
        recipient = db.get(RecipientDB, execution.recipient_id)
        address = db.query(AddressabilityDB).filter(AddressabilityDB.recipient_id == recipient.id,
                                                    AddressabilityDB.channel == "email").first()
        return send, execution, recipient, address_value(address, "email")

    def _executions(self, send_id, **params):
        with machine([VIEW]) as headers:
            response = client.get(f"/delivery/send-instances/{send_id}/executions",
                                  params=params, headers=headers)
        assert response.status_code == 200, response.text
        return response.json()

    def test_by_identifier_and_by_address(self):
        db = SessionLocal()
        try:
            send, execution, recipient, email = self._demo(db)
        finally:
            db.close()
        by_id = self._executions(send.id, q=recipient.external_id, limit=20)
        assert [e["id"] for e in by_id["items"]] == [execution.id] and by_id["total"] == 1
        by_address = self._executions(send.id, q=email.upper(), limit=20)
        assert execution.id in [e["id"] for e in by_address["items"]]
        assert by_address["total"] == len(by_address["items"])

    def test_no_match_counts_zero(self):
        db = SessionLocal()
        try:
            send, _, _, _ = self._demo(db)
        finally:
            db.close()
        body = self._executions(send.id, q="nobody-is-called-this")
        assert (body["items"], body["total"]) == ([], 0)
