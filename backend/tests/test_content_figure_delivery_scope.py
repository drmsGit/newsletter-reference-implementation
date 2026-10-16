"""Record figures count sent deliveries, not people (task-359; ADR-196)."""
import pytest

from app.campaigns.db_models import CampaignDB
from app.content.kpis import content_figures
from app.delivery.db_models import DeliveryExecutionDB
from app.insight.db_models import EngagementEventDB
from tests.test_content_figures import db, sent, world  # noqa: F401


def test_one_person_in_two_campaigns_counts_twice_and_keeps_the_campaigns_apart(db, world):  # noqa: F811
    person = world["person"](picks=True)
    first_variant, second_variant = world["variant"](), world["variant"]()
    first, _ = world["send"](first_variant, [person])
    second, _ = world["send"](second_variant, [person])
    record_id = world["made"]["records"][0]
    execution = db.query(DeliveryExecutionDB).filter_by(send_instance_id=first.id).one()
    events = [EngagementEventDB(delivery_execution_id=execution.id, event_type="click",
                                event_data={"content_record_id": record_id}) for _ in range(2)]
    db.add_all(events)
    db.commit()
    try:
        overall, campaigns, names = content_figures(db, world["brand"].id, [record_id], by_campaign=True)
        assert overall[record_id] == {
            "deliveries": 2, "picked": 2, "clicks": 2, "unique_clickers": 1,
            "clicks_in_deliveries": 2, "click_share": 1.0,
        }
        per = campaigns[record_id]
        assert set(per) == {first_variant.campaign_id, second_variant.campaign_id}
        assert per[first_variant.campaign_id]["clicks"] == 2
        assert per[first_variant.campaign_id]["unique_clickers"] == 1
        assert per[first_variant.campaign_id]["deliveries"] == 1
        assert per[second_variant.campaign_id] == {
            "deliveries": 1, "picked": 1, "clicks": 0, "unique_clickers": 0,
            "clicks_in_deliveries": 0, "click_share": None,
        }
        assert {cid: names[cid] for cid in per} == {cid: db.get(CampaignDB, cid).name for cid in per}
        assert first.id != second.id
    finally:
        db.rollback()
        for event in events:
            db.delete(event)
        db.commit()


@pytest.mark.parametrize("status", ["failed", "excluded", "uncertain"])
def test_a_non_sent_execution_contributes_neither_content_nor_clicks(db, sent, status):  # noqa: F811
    # The fixture puts every click on one execution and none on the other.
    event = db.query(EngagementEventDB).filter(
        EngagementEventDB.event_type == "click",
        EngagementEventDB.event_data["content_record_id"].as_integer() == sent["placed"],
    ).first()
    execution = db.get(DeliveryExecutionDB, event.delivery_execution_id)
    execution.status = status
    db.commit()
    figures = content_figures(db, sent["brand"].id, [sent["placed"], sent["picked"]])
    for record_id in (sent["placed"], sent["picked"]):
        assert figures[record_id] == {
            "deliveries": 1, "picked": int(record_id == sent["picked"]), "clicks": 0,
            "unique_clickers": 0, "clicks_in_deliveries": 0, "click_share": None,
        }
