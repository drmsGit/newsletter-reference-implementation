"""How many unsent campaigns a catalogue edit reaches (task-224, ADR-178 point 8).

The composer shows this passively beside a catalogue field: a count of
*unsent* campaigns using the record, the list on demand, no owner names. A
sent campaign is snapshotted and immune, so counting it would overstate the
reach and teach managers to distrust the number. "Sent" is the monitoring
screen's own definition (task-216): a variant whose stage is "sent".
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.permissions import VIEW
from app.campaigns.db_models import CampaignDB, ModuleInstanceDB, VariantDB
from app.content.db_models import ContentRecordDB
from app.delivery.db_models import SendInstanceDB
from app.snapshots.db_models import SnapshotDB
from main import app
from tests.machine import machine

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def world(db, default_brand, foreign_brand):
    record = ContentRecordDB(title="reach", content={}, status="active", brand_id=default_brand.id)
    db.add(record); db.flush()
    made = {"campaigns": [], "snapshots": [], "sends": []}

    def campaign(name, *, brand=default_brand, uses=True, sent=False, variants=1):
        c = CampaignDB(brand_id=brand.id, name=f"{name}-{uuid.uuid4().hex[:4]}")
        db.add(c); db.flush()
        made["campaigns"].append(c.id)
        for _ in range(variants):
            v = VariantDB(campaign_id=c.id, channel="email", name="v", status="draft")
            db.add(v); db.flush()
            db.add(ModuleInstanceDB(variant_id=v.id, module_type="img_left", position=1,
                                    content_record_id=record.id if uses else None))
            if sent:
                s = SnapshotDB(variant_id=v.id)
                db.add(s); db.flush()
                made["snapshots"].append(s.id)
                send = SendInstanceDB(brand_id=brand.id, snapshot_id=s.id, name="n", status="sent")
                db.add(send); db.flush()
                made["sends"].append(send.id)
        db.commit()
        return c

    yield record, campaign
    db.rollback()
    db.query(SendInstanceDB).filter(SendInstanceDB.id.in_(made["sends"])).delete(synchronize_session=False)
    db.query(SnapshotDB).filter(SnapshotDB.id.in_(made["snapshots"])).delete(synchronize_session=False)
    variant_ids = [v.id for v in db.query(VariantDB).filter(VariantDB.campaign_id.in_(made["campaigns"]))]
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id.in_(variant_ids)).delete(
        synchronize_session=False)
    db.query(VariantDB).filter(VariantDB.id.in_(variant_ids)).delete(synchronize_session=False)
    db.query(CampaignDB).filter(CampaignDB.id.in_(made["campaigns"])).delete(synchronize_session=False)
    db.query(ContentRecordDB).filter(ContentRecordDB.id == record.id).delete()
    db.commit()


def _reach(record_id):
    with machine([VIEW]) as headers:
        return client.get(f"/content/{record_id}/unsent-campaigns", headers=headers)


def test_counts_unsent_campaigns_once_each_and_leaves_sent_ones_out(world):
    record, campaign = world
    composing = campaign("composing", variants=2)       # two variants, one campaign
    sent = campaign("sent", sent=True)
    campaign("other", uses=False)                        # does not use the record
    response = _reach(record.id)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["count"] == 1
    assert body["campaigns"] == [{"id": composing.id, "name": composing.name}]
    assert sent.id not in {c["id"] for c in body["campaigns"]}


def test_nothing_but_names_and_ids_is_returned(world):
    record, campaign = world
    campaign("composing")
    [row] = _reach(record.id).json()["campaigns"]
    assert set(row) == {"id", "name"}, "no owners on the composer (ADR-178 point 8)"


def test_another_brands_record_is_not_found(world, foreign_brand, foreign_api):
    record, _ = world
    with foreign_api([VIEW]) as headers:
        assert client.get(f"/content/{record.id}/unsent-campaigns", headers=headers).status_code == 404
