"""Consent drift is computed and answered per brand (task-307).

Consent has been per brand since the ADR-163 addendum of 2026-09-15 — the
latest event wins per (recipient, brand, channel, purpose), as `ConsentEventDB`
says — but the drift report keyed its comparison without the brand and read
every brand's log. Brand B's opt-out was then compared with brand A's CRM
assertion (drift invented), brand B's newer CRM event masked brand A's real
disagreement (drift hidden), and the route answered for every brand at once.
Decided with the user 2026-10-09: the report answers for the working brand,
like every other list (ADR-150 point 2, ADR-172).
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.auth.permissions import VIEW
from app.database import SessionLocal
from app.recipients.db_models import ConsentEventDB, RecipientDB
from app.recipients.service import detect_consent_drift
from main import app
from tests.machine import machine

api = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def someone(db):
    recipient = db.query(RecipientDB).order_by(RecipientDB.id).first()
    if recipient is None:
        pytest.skip("no recipient in this database")
    return recipient


@pytest.fixture
def events(db):
    """Write consent events with explicit, strictly increasing times (newer
    than anything seeded, so they are the latest per cell), and remove them."""
    made: list[int] = []
    base = datetime.now(timezone.utc) + timedelta(days=1)

    def write(recipient_id: int, brand_id: int, status: str, source: str) -> None:
        row = ConsentEventDB(recipient_id=recipient_id, brand_id=brand_id, channel="email",
                             purpose="marketing", status=status, source=source,
                             note=f"task-307 {uuid.uuid4().hex[:6]}",
                             created_at=base + timedelta(minutes=len(made)))
        db.add(row)
        db.commit()
        made.append(row.id)

    yield write
    db.query(ConsentEventDB).filter(ConsentEventDB.id.in_(made)).delete(synchronize_session=False)
    db.commit()


def _drift(db, brand_id: int, recipient_id: int) -> list:
    return [d for d in detect_consent_drift(db, brand_id=brand_id) if d.recipient_id == recipient_id]


def test_another_brands_opt_out_is_not_drift_here(db, someone, events, default_brand, foreign_brand):
    events(someone.id, default_brand.id, "opted_in", "crm")     # A: CRM and platform agree
    events(someone.id, foreign_brand.id, "opted_in", "crm")
    events(someone.id, foreign_brand.id, "opted_out", "provider")  # B: a bounce opted them out

    assert _drift(db, default_brand.id, someone.id) == [], "brand B's opt-out was reported as A's drift"
    [b] = _drift(db, foreign_brand.id, someone.id)
    assert (b.platform_consent_status, b.last_crm_consent_status) == ("opted_out", "opted_in")


def test_another_brands_newer_crm_event_does_not_hide_drift_here(
        db, someone, events, default_brand, foreign_brand):
    events(someone.id, default_brand.id, "opted_out", "crm")    # A: the CRM says no …
    events(someone.id, default_brand.id, "opted_in", "manual")  # … the platform says yes
    events(someone.id, foreign_brand.id, "opted_in", "crm")     # B: newer, and consistent

    [a] = _drift(db, default_brand.id, someone.id)
    assert (a.platform_consent_status, a.last_crm_consent_status) == ("opted_in", "opted_out")
    assert _drift(db, foreign_brand.id, someone.id) == []


def test_the_brand_is_required():
    """Forgetting it is a TypeError, not every brand (ADR-172 point 4)."""
    with pytest.raises(TypeError):
        detect_consent_drift(SessionLocal())


def test_the_route_answers_for_the_working_brand_only(someone, events, default_brand, foreign_brand):
    events(someone.id, foreign_brand.id, "opted_in", "crm")
    events(someone.id, foreign_brand.id, "opted_out", "provider")

    def listed(brand_id: int) -> bool:
        with machine([VIEW], brand_id=brand_id) as headers:
            response = api.get("/recipients/consent/drift?limit=200", headers=headers)
        assert response.status_code == 200, response.text
        return any(item["recipient_id"] == someone.id for item in response.json()["items"])

    assert listed(foreign_brand.id), "the brand with the drift must see it"
    assert not listed(default_brand.id), "another brand's drift was served to this brand"
