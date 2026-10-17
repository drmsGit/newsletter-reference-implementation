"""A catalogue module may carry one field typed in the module (task-223).

Variant Editor interview 2.6: an optional heading over a slot-bound module —
"this might be of interest" — that must not render when the slot finds
nothing, so it cannot be a separate heading module. ADR-179's 2026-10-04
addendum: a manifest marks such a field `source: "module"`; the module's
other fields still come from the content or the slot's pick. The field is the
module's own: never overridden, never a catalogue field.

Since 2026-10-15 (task-371, ADR-198 point 5) the heading has left the image
blocks; the retired Single Stack carried it until it was deleted (task-381).
The mechanism is kept (user, 2026-10-17) with no shipped block using it, so
it is tested on a block these tests plant: a catalogue block with a heading
typed in the module, as Single Stack was.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.permissions import CAMPAIGNS_MANAGE, OVERRIDES_MANAGE, VIEW
from app.campaigns.db_models import (
    CampaignDB, DecisionResolutionDB, DecisionSlotDB, ModuleInstanceDB, VariantDB,
)
from app.content.db_models import CategoryDB, ContentRecordDB, ContentVersionDB
from main import app
from tests.machine import editor, machine

client = TestClient(app, raise_server_exceptions=False)
pytestmark = pytest.mark.usefixtures("one_editor", "headed_block")

BLOCK, HEADING = "t381_headed", "t381_heading"
MANIFEST = {
    "label": "Headed block (test)", "channel": "email", "cms": True,
    "variables": [
        {"name": HEADING, "required": False, "source": "module"},
        {"name": "headline_medium", "required": True},
        {"name": "body_medium", "required": False},
    ],
}
TEMPLATE = (f"{{% if {HEADING} %}}<p class=\"module-section-heading\">{{{{ {HEADING} }}}}</p>{{% endif %}}"
            "<h2>{{ headline_medium }}</h2>")


@pytest.fixture
def headed_block(monkeypatch):
    """A block with a field typed in the module, planted for these tests only,
    with its field defined beside the shipped ones."""
    import json

    from app.modules import registry

    shipped = registry.field_definitions()
    monkeypatch.setattr(registry, "field_definitions", lambda: {**shipped, HEADING: {
        "label": "Heading above this module", "concept": "heading", "channel": "email", "type": "text",
        "size": "small"}})
    folder = registry.MODULES_DIR / "email"
    (folder / f"{BLOCK}.json").write_text(json.dumps(MANIFEST))
    (folder / f"{BLOCK}.html").write_text(TEMPLATE)
    registry._registry_mtime = None
    yield
    (folder / f"{BLOCK}.json").unlink(missing_ok=True)
    (folder / f"{BLOCK}.html").unlink(missing_ok=True)
    registry._registry_mtime = None

SHOWN, HIDDEN, ON_RECORD = "Picked for you", "Nobody sees this", "From the catalogue"


@pytest.fixture
def world(db, default_brand):
    b = default_brand.id
    campaign = CampaignDB(brand_id=b, name=f"msf-{uuid.uuid4().hex[:6]}")
    db.add(campaign); db.flush()
    variant = VariantDB(campaign_id=campaign.id, channel="email", name="v", status="draft")
    record = ContentRecordDB(title="r", content={"headline_medium": "Lisbon"}, status="active", brand_id=b)
    empty = CategoryDB(name=f"msf-empty-{uuid.uuid4().hex[:6]}")
    db.add_all([variant, record, empty]); db.flush()
    db.add(ContentVersionDB(content_record_id=record.id, version_number=1, content={"headline_medium": "Lisbon"}))
    picked = DecisionSlotDB(variant_id=variant.id, name="picked", decision_type="content_recommendation",
                            decision_strategy="top_score")
    nothing = DecisionSlotDB(variant_id=variant.id, name="nothing", decision_type="content_recommendation",
                             decision_strategy="top_score", candidate_filter={"category_ids": [empty.id]})
    db.add_all([picked, nothing]); db.flush()
    db.add(DecisionResolutionDB(decision_slot_id=picked.id, recipient_id=None,
                                content_record_id=record.id, reason="r", score=1))
    on_record = ModuleInstanceDB(variant_id=variant.id, module_type=BLOCK, position=1,
                                 content_record_id=record.id, module_data={HEADING: ON_RECORD})
    on_pick = ModuleInstanceDB(variant_id=variant.id, module_type=BLOCK, position=2,
                               decision_slot_id=picked.id, module_data={HEADING: SHOWN})
    on_nothing = ModuleInstanceDB(variant_id=variant.id, module_type=BLOCK, position=3,
                                  decision_slot_id=nothing.id, module_data={HEADING: HIDDEN})
    db.add_all([on_record, on_pick, on_nothing]); db.commit()
    yield {"variant": variant, "on_record": on_record}
    db.rollback()
    from app.overrides.db_models import ContentOverrideDB

    db.query(ContentOverrideDB).filter(ContentOverrideDB.module_instance_id == on_record.id).delete()
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant.id).delete()
    db.query(DecisionResolutionDB).filter(DecisionResolutionDB.decision_slot_id.in_([picked.id, nothing.id])).delete(
        synchronize_session=False)
    db.query(DecisionSlotDB).filter(DecisionSlotDB.variant_id == variant.id).delete()
    db.query(VariantDB).filter(VariantDB.id == variant.id).delete()
    db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
    db.query(ContentVersionDB).filter(ContentVersionDB.content_record_id == record.id).delete()
    db.query(ContentRecordDB).filter(ContentRecordDB.id == record.id).delete()
    db.query(CategoryDB).filter(CategoryDB.id == empty.id).delete()
    db.commit()


def test_the_manifest_says_which_fields_are_typed_in_the_module():
    with machine([VIEW]) as headers:
        manifests = client.get("/modules", params={"channel": "email"}, headers=headers).json()
    block = next(m for m in manifests if m["name"] == BLOCK)
    source = {v["name"]: v["source"] for v in block["variables"]}
    assert source[HEADING] == "module"
    assert source["headline_medium"] == "content"


def test_the_heading_renders_with_its_module_and_hides_with_it(world):
    with machine([VIEW]) as headers:
        body = client.get(f"/rendering/variants/{world['variant'].id}", headers=headers).json()["artifact_body"]
    assert ON_RECORD in body and SHOWN in body
    # The slot that finds nothing is hidden (ADR-086), and its heading with it.
    assert HIDDEN not in body


def test_a_module_typed_field_is_never_overridden(db, world):
    with editor() as headers:
        response = client.put(f"/overrides/modules/{world['on_record'].id}",
                              json={"field_overrides": {HEADING: "Pinned"}}, headers=headers)
    assert response.status_code == 400, response.text


def test_a_catalogue_module_stores_only_its_module_typed_fields(world):
    url = f"/campaigns/modules/{world['on_record'].id}"
    with editor() as headers:
        ok = client.put(url, json={"module_type": BLOCK, "content_record_id": None,
                                   "module_data": {HEADING: "New"}}, headers=headers)
        refused = client.put(url, json={"module_type": BLOCK,
                                        "module_data": {"headline_medium": "Typed over the catalogue"}},
                             headers=headers)
    assert ok.status_code == 200, ok.text
    assert refused.status_code == 422, refused.text


def test_a_module_typed_field_is_not_a_catalogue_field():
    from app.content.service import catalogue_fields, content_field_groups

    assert HEADING not in content_field_groups()["email"]
    assert HEADING not in {f["name"] for f in catalogue_fields()}
