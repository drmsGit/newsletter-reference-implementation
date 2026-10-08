"""An integration reads what its permission writes (task-53; ADR-166 addendum 2026-10-08).

Every GET resolves to `view`, which every role implies and an integration does
not hold (implying it would hand every integration the recipient list). So an
integration granted `recipients.manage` wrote a recipient and got 403 reading
it back. Decided with the user: a write permission also admits reads of its own
area — only what it writes, not what the platform derives (activity,
memberships, signals, per-recipient results, previews that list people) —
through an explicit table of exact routes, `MACHINE_READS`; a read route not in
it stays behind `view`.
"""
import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.auth.permissions import (
    AUDIENCES_MANAGE, CAMPAIGNS_MANAGE, CONTENT_MANAGE, RECIPIENTS_MANAGE, SENDS_EXECUTE, VIEW,
)
from app.auth.policy import MACHINE_READS
from app.database import SessionLocal
from app.recipients.db_models import RecipientDB
from main import app
from tests.machine import machine

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def someone():
    db = SessionLocal()
    try:
        recipient = db.query(RecipientDB).order_by(RecipientDB.id).first()
        if recipient is None:
            pytest.skip("no recipient in this database")
        return recipient.id, recipient.external_id
    finally:
        db.close()


class TestAWritePermissionReadsItsOwnArea:
    def test_a_crm_connector_reads_back_the_recipients_it_writes(self, someone):
        rid, external_id = someone
        with machine([RECIPIENTS_MANAGE]) as headers:
            assert client.get("/recipients/", headers=headers).status_code == 200
            assert client.get(f"/recipients/{external_id}", headers=headers).status_code == 200
            # Derived about the person: stays behind view.
            for derived in (f"/recipients/{rid}/activity", f"/recipients/{rid}/audience-groups",
                            f"/recipients/{rid}/preferences", "/recipients/consent/drift"):
                assert client.get(derived, headers=headers).status_code == 403, derived

    def test_content_campaigns_and_audiences_read_their_own_and_not_what_is_derived(self):
        with machine([CONTENT_MANAGE, CAMPAIGNS_MANAGE, AUDIENCES_MANAGE]) as headers:
            for own in ("/content/", "/content/categories", "/campaigns/", "/api/audience-groups/"):
                assert client.get(own, headers=headers).status_code == 200, own
            for derived in ("/campaigns/monitoring", "/insight/overview", "/approvals/"):
                assert client.get(derived, headers=headers).status_code == 403, derived

    def test_a_permission_reads_only_its_own_area(self):
        with machine([CONTENT_MANAGE]) as headers:
            assert client.get("/campaigns/", headers=headers).status_code == 403
            assert client.get("/recipients/", headers=headers).status_code == 403

    def test_a_route_not_in_the_table_stays_behind_view(self):
        """Fail closed: a read route nobody listed is not opened by a write grant."""
        with machine([CONTENT_MANAGE, CAMPAIGNS_MANAGE]) as headers:
            assert client.get("/modules", headers=headers).status_code == 403

    def test_a_permission_that_writes_nothing_readable_reads_nothing(self):
        with machine([SENDS_EXECUTE]) as headers:
            assert client.get("/content/", headers=headers).status_code == 403


def test_view_still_reads_everything_it_did(someone):
    rid, _ = someone
    with machine([VIEW]) as headers:
        assert client.get(f"/recipients/{rid}/activity", headers=headers).status_code == 200
        assert client.get("/campaigns/monitoring", headers=headers).status_code == 200
        # A listed route too: view alone admits it, without the area's write permission.
        assert client.get("/recipients/", headers=headers).status_code == 200


def test_every_listed_read_is_a_real_get_route():
    """A typo in the table would silently admit nothing; a removed route would
    leave a stale grant behind. Both show up here."""
    gets = {r.path for r in app.routes if isinstance(r, APIRoute) and "GET" in r.methods}
    assert set(MACHINE_READS) - gets == set()
