"""A decision slot whose campaign chain does not resolve is an error, not "no content".

task-18. `sending_brand_id` returned `int | None` into parameters annotated
`brand_id: int`. Every caller was safe only by accident: `brand_id == None`
renders as `IS NULL`, the column is NOT NULL, nothing matched, and the consent
check then found no grant for "brand None". And the failure read as the wrong
thing — a slot hidden under ADR-086 as if its strategy had found nothing, or a
consent refusal, for what is actually a data defect.

Each link (slot → variant → campaign → brand) is NOT NULL with a foreign key,
so the chain cannot break in today's schema. These tests construct the broken
case directly, which is the only way to reach it — and the point of the fix is
that brand safety stops depending on that nullability.
"""
from types import SimpleNamespace

import pytest

from app.database import SessionLocal
from app.decision.strategies.base import BrokenCampaignChain, sending_brand_id


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_a_slot_whose_variant_does_not_resolve_raises(db):
    orphan = SimpleNamespace(id=-1, variant_id=-1)

    with pytest.raises(BrokenCampaignChain, match="data defect"):
        sending_brand_id(db, orphan)


def test_it_is_not_a_value_error_so_the_send_loop_cannot_hide_it():
    """The property that matters most, and it is a type. The send loop catches
    ValueError from a slot as "the strategy resolved nothing" and hides the
    slot (ADR-086); ConsentDenied is a ValueError too. A broken chain caught
    there would degrade gracefully into an email missing a module, with nobody
    told why."""
    from app.recipients.consent import ConsentDenied

    assert not issubclass(BrokenCampaignChain, ValueError)
    assert not issubclass(BrokenCampaignChain, ConsentDenied)


def test_a_healthy_slot_resolves_to_an_int(db):
    from app.campaigns.db_models import DecisionSlotDB

    slot = db.query(DecisionSlotDB).first()
    assert slot is not None, "the seeded test database has no decision slot"
    assert isinstance(sending_brand_id(db, slot), int)


def test_the_decision_route_answers_409_not_500(db, monkeypatch):
    """The call site. Without its own branch the router's `except ValueError`
    would not catch this, and it would surface as a server error."""
    import app.decision.service as service
    import app.decision.strategies.recipient_top_score as recipient_top_score
    import app.decision.strategies.top_score as top_score
    from app.auth.permissions import CAMPAIGNS_MANAGE, VIEW
    from app.campaigns.db_models import CampaignDB, DecisionSlotDB, VariantDB
    from tests.machine import machine
    from tests.test_api_guard import client

    row = (
        db.query(DecisionSlotDB.id, CampaignDB.brand_id)
        .join(VariantDB, VariantDB.id == DecisionSlotDB.variant_id)
        .join(CampaignDB, CampaignDB.id == VariantDB.campaign_id)
        .first()
    )
    assert row is not None, "the seeded test database has no decision slot"
    slot_id, brand_id = row
    # With a recipient, `execute_decision_slot` asks for the sending brand to
    # check consent BEFORE the strategy runs — so this reaches the chain lookup
    # whatever the slot's strategy is. Without one, a personalised strategy is
    # refused for the missing recipient first and the test would pass on 400.
    from app.recipients.db_models import RecipientDB

    recipient_id = db.query(RecipientDB.id).order_by(RecipientDB.id).first()[0]

    def broken(db_, slot):
        raise BrokenCampaignChain("chain broken for this test")

    for module in (service, top_score, recipient_top_score):
        monkeypatch.setattr(module, "sending_brand_id", broken)

    with machine([VIEW, CAMPAIGNS_MANAGE], brand_id=brand_id) as headers:
        response = client.post(
            f"/decision/slots/{slot_id}/execute", headers=headers,
            json={"recipient_id": recipient_id},
        )

    assert response.status_code == 409, response.text
    assert "chain broken" in response.json()["detail"]
