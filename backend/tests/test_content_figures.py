"""A content record's figures (task-359; ADR-196 addendum 2026-10-16).

Counted per delivery, all time, on read: deliveries that carried the record
(placed in the frame or picked by a slot), clicks on its links, unique
clickers, and its share of all clicks in the deliveries that carried it.
"""
import pytest

from app.campaigns.service import create_module_for_variant
from app.content.kpis import content_figures
from app.content.service import create_content, create_content_version
from app.delivery.db_models import DeliveryExecutionDB
from app.insight.db_models import EngagementEventDB
from tests import test_render_skip as fixtures
from tests.test_api_guard import signed_in

db = fixtures.db
world = fixtures.world


@pytest.fixture
def sent(db, world):
    """One variant: a record placed by hand and a slot that picks the world's
    record. Anna and Ben get it; Anna clicks the placed one twice and the
    picked one once, plus one click on no record; Ben does not click."""
    brand = world["brand"]
    placed = create_content(db, title="t359-placed", brand_id=brand.id, content={
        "headline_medium": "Placed", "button_label": "Go", "button_url": "https://example.com/p"})
    create_content_version(db, content_record_id=placed.id, created_by="test", brand_id=brand.id)
    world["made"]["records"].append(placed.id)
    picked = world["made"]["records"][0]
    variant = world["variant"]()
    create_module_for_variant(db, variant_id=variant.id, module_type="img_left", content_record_id=placed.id,
                              brand_id=brand.id)
    anna, ben = world["person"](picks=True), world["person"](picks=True)
    send, rows = world["send"](variant, [anna, ben])
    assert rows[anna.id][0] == rows[ben.id][0] == "sent", rows
    executions = {e.recipient_id: e for e in db.query(DeliveryExecutionDB).filter_by(send_instance_id=send.id)}
    clicks = [(placed.id, 2), (picked, 1), (None, 1)]
    made = []
    for content_id, times in clicks:
        for _ in range(times):
            event = EngagementEventDB(delivery_execution_id=executions[anna.id].id, event_type="click",
                                      event_data={"content_record_id": content_id} if content_id else {"url": "x"})
            db.add(event)
            made.append(event)
    # A delivered event is no click: it counts in no figure here.
    delivered = EngagementEventDB(delivery_execution_id=executions[anna.id].id, event_type="delivered",
                                  event_data={})
    db.add(delivered)
    made.append(delivered)
    db.commit()
    yield {"brand": brand, "placed": placed.id, "picked": picked, "campaign_id": variant.campaign_id}
    for event in made:
        db.delete(event)
    db.commit()


def test_a_placed_and_a_picked_record_are_counted_per_delivery(db, sent):
    figures = content_figures(db, sent["brand"].id, [sent["placed"], sent["picked"]])
    placed, picked = figures[sent["placed"]], figures[sent["picked"]]
    assert (placed["deliveries"], placed["picked"]) == (2, 0)
    assert (picked["deliveries"], picked["picked"]) == (2, 2)
    assert (placed["clicks"], placed["unique_clickers"]) == (2, 1)
    assert (picked["clicks"], picked["unique_clickers"]) == (1, 1)


def test_the_share_is_of_all_clicks_in_the_deliveries_that_carried_it(db, sent):
    figures = content_figures(db, sent["brand"].id, [sent["placed"], sent["picked"]])
    # Anna's delivery holds four clicks: two on placed, one on picked, one on nothing.
    assert figures[sent["placed"]]["clicks_in_deliveries"] == 4
    assert figures[sent["placed"]]["click_share"] == pytest.approx(0.5)
    assert figures[sent["picked"]]["click_share"] == pytest.approx(0.25)


def test_a_record_never_clicked_has_no_share_rather_than_zero(db, world, sent):
    other = create_content(db, title="t359-unused", brand_id=sent["brand"].id, content={})
    world["made"]["records"].append(other.id)
    assert content_figures(db, sent["brand"].id, [other.id]) == {}


def test_the_record_page_gets_them_overall_and_per_campaign(db, sent):
    with signed_in(db) as (client, _token, _csrf):
        body = client.get(f"/content/{sent['placed']}/performance").json()
    assert body["overall"]["deliveries"] == 2 and body["overall"]["click_share"] == pytest.approx(0.5)
    [campaign] = body["by_campaign"]
    assert campaign["campaign_id"] == sent["campaign_id"] and campaign["figures"]["clicks"] == 2


def test_another_brands_record_is_not_found(db, sent, foreign_brand):
    other = create_content(db, title="t359-foreign", brand_id=foreign_brand.id, content={})
    with signed_in(db) as (client, _token, _csrf):
        response = client.get(f"/content/{other.id}/performance")
    assert response.status_code == 404


def test_a_categorys_records_carry_their_figures(db, sent):
    from app.content.db_models import CategoryDB, ContentCategoryAssignmentDB
    from app.insight.graph import category_detail

    category = CategoryDB(name="t359-category", type="sub")
    db.add(category)
    db.flush()
    db.add(ContentCategoryAssignmentDB(content_id=sent["placed"], category_id=category.id, score=8))
    db.commit()
    try:
        detail = category_detail(db, category.id, brand_id=sent["brand"].id)
        [row] = detail["assigned_content"]
        assert row["figures"]["clicks"] == 2
    finally:
        db.query(ContentCategoryAssignmentDB).filter_by(category_id=category.id).delete()
        db.delete(category)
        db.commit()


def test_another_brand_sees_no_figures_for_this_brands_records(db, sent, foreign_brand):
    assert content_figures(db, foreign_brand.id, [sent["placed"], sent["picked"]]) == {}
