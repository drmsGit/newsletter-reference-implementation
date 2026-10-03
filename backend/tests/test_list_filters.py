"""Server-side filters on the lists that exist today (2026-10-03).

Manager Workflow interview requirement 5 asks for server-side filtering on
every list; ADR-175 point 7 requires it and ADR-185 point 6 binds it: **a
filter applies to the rows and the total alike**. Decided with the user: this
round covers fields that already exist — facets (ADR-175's main filter for
content and campaigns) are their own work.

- content: title search, and status (`active` / `inactive`, a real vocabulary)
- campaigns: name search only — `CampaignDB.status` is set at creation and
  never moves (task-216), so filtering on it would mislead; a campaign's real
  state is the monitoring screen's
- audience groups: name search (ADR-175 point 5: search and paging, no facets)
- recipients: identifier or address search, on any channel
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth import service as auth
from app.auth.permissions import RECIPIENTS_MANAGE, VIEW
from app.database import SessionLocal
from main import app
from tests.machine import machine

client = TestClient(app, raise_server_exceptions=False)
TAG = f"filt{uuid.uuid4().hex[:6]}"


def _get(path, perms=(VIEW,), **params):
    with machine(list(perms)) as headers:
        response = client.get(path, params={"limit": 200, **params}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def made():
    """Two content records, two campaigns and two groups wearing TAG, one of
    each 'inactive' or differently named, so a filter that is ignored fails."""
    from app.audience.db_models import AudienceGroupDB
    from app.campaigns.db_models import CampaignDB
    from app.content.db_models import ContentRecordDB

    db = SessionLocal()
    brand = auth.ensure_default_brand(db).id
    rows = [
        ContentRecordDB(title=f"{TAG} Alpine Hiking", content={}, status="active", brand_id=brand),
        ContentRecordDB(title=f"{TAG} alpine skiing", content={}, status="inactive", brand_id=brand),
        CampaignDB(name=f"{TAG} Spring Launch", status="draft", brand_id=brand),
        CampaignDB(name=f"{TAG} autumn", status="draft", brand_id=brand),
        AudienceGroupDB(name=f"{TAG} Families", brand_id=brand),
        AudienceGroupDB(name=f"{TAG} singles", brand_id=brand),
    ]
    db.add_all(rows)
    db.commit()
    yield rows
    db.rollback()
    for row in rows:
        db.delete(db.merge(row))
    db.commit()
    db.close()


class TestContent:
    def test_title_search_is_part_and_any_case_and_counts_only_matches(self, made):
        body = _get("/content/", q=f"{TAG} ALPINE")
        assert {r["title"] for r in body["items"]} == {f"{TAG} Alpine Hiking", f"{TAG} alpine skiing"}
        assert body["total"] == 2

    def test_status_narrows_and_combines_with_search(self, made):
        body = _get("/content/", q=TAG, status="inactive")
        assert [r["title"] for r in body["items"]] == [f"{TAG} alpine skiing"]
        assert body["total"] == 1

    def test_an_unknown_status_is_refused_not_ignored(self, made):
        with machine([VIEW]) as headers:
            response = client.get("/content/", params={"status": "archived"}, headers=headers)
        assert response.status_code == 422


class TestCampaigns:
    def test_name_search(self, made):
        body = _get("/campaigns/", q="spring launch")
        mine = [r for r in body["items"] if r["name"].startswith(TAG)]
        assert [r["name"] for r in mine] == [f"{TAG} Spring Launch"]
        assert body["total"] == len(body["items"])


class TestAudienceGroups:
    def test_name_search(self, made):
        body = _get("/api/audience-groups/", q=f"{TAG} fam")
        assert [r["name"] for r in body["items"]] == [f"{TAG} Families"]
        assert body["total"] == 1


class TestRecipients:
    def test_by_identifier_or_address_on_any_channel(self):
        from app.recipients.consent import address_value
        from app.recipients.db_models import AddressabilityDB, RecipientDB

        db = SessionLocal()
        try:
            address = db.query(AddressabilityDB).filter(AddressabilityDB.channel == "email").first()
            recipient = db.get(RecipientDB, address.recipient_id)
            email = address_value(address, "email")
        finally:
            db.close()
        perms = (VIEW, RECIPIENTS_MANAGE)
        by_id = _get("/recipients/", perms=perms, q=recipient.external_id)
        assert recipient.id in [r["id"] for r in by_id["items"]]
        by_address = _get("/recipients/", perms=perms, q=email.upper())
        assert [r["id"] for r in by_address["items"]] == [recipient.id]
        assert by_address["total"] == 1
        nobody = _get("/recipients/", perms=perms, q="nobody-is-called-this")
        assert (nobody["items"], nobody["total"]) == ([], 0)


def test_a_typed_wildcard_is_a_character_not_a_wildcard(made):
    """`%` and `_` are what SQL LIKE uses as wildcards; typed into a search
    box they mean the character. Unescaped, '%' would match every record."""
    assert _get("/content/", q="%")["total"] == 0
    assert _get("/recipients/", perms=(VIEW, RECIPIENTS_MANAGE), q="_")["total"] == 0
