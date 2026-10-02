"""Large demo dataset for presentations + exercising the Category Graph.

Regenerates a rich, varied dataset so the graph shows its full range — nodes of
different sizes, green (positive) / red (negative) / grey (no signal) colouring,
event counts > 0, and edges from category relations + content co-occurrence.
The minimal baseline (`reset_all_data.sql`) stays the clean 3-recipient fixture
the tests rely on; run that to return to baseline.

Deterministic (fixed random seed). Run from the backend/ directory:

    ./venv/bin/python scripts/seed_demo_data.py
"""
import os
import random
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, text

from app.auth.service import ensure_default_brand
from app.campaigns.service import set_envelope_fields
from app.database import SessionLocal, engine
from app.content.db_models import (
    CategoryDB,
    CategoryRelationDB,
    ContentRecordDB,
    ContentVersionDB,
    ContentCategoryAssignmentDB,
)
from app.recipients.db_models import (
    AddressabilityDB,
    ConsentEventDB,
    RecipientDB,
    SignalContributionDB,
)
from app.campaigns.db_models import (
    CampaignDB,
    VariantDB,
    ModuleInstanceDB,
    DecisionSlotDB,
    DecisionResolutionDB,
)
from app.delivery.db_models import SendInstanceDB, DeliveryExecutionDB
from app.snapshots.db_models import SnapshotDB
from app.insight.db_models import EngagementEventDB
from app.insight.service import apply_event_to_signals

# Imported for metadata registration only. SQLAlchemy resolves foreign keys
# against whatever is registered on Base.metadata, and a model class registers
# by being imported — so a module nothing imports leaves its table invisible.
# Without these, SendInstanceDB.audience_group_id cannot resolve audience_groups
# and mapper configuration fails on the first query, which is how this script
# came to be broken before anyone noticed. tests/test_signals.py carries the
# same wall for the same reason.
import app.audience.db_models  # noqa: F401
import app.overrides.db_models  # noqa: F401
import app.providers.db_models  # noqa: F401
import app.settings.db_models  # noqa: F401
import app.auth.db_models  # noqa: F401
import app.ai.db_models  # noqa: F401

random.seed(42)
NOW = datetime.now(timezone.utc)


def _truncate(db):
    db.execute(text("""
        TRUNCATE TABLE
            signal_contributions, engagement_events, delivery_executions,
            content_overrides, decision_resolutions, consent_sync_logs,
            consent_events, recipient_addresses,
            snapshots, send_instances, content_category_assignments,
            content_versions, category_relations, module_instances,
            decision_slots, variants, categories, recipients, campaigns,
            content_records
        RESTART IDENTITY CASCADE
    """))
    db.commit()


# Category design: which ones stay positive (manual + clicks), which are
# "declining" (only negative contributions -> red), which stay untouched (grey).
POSITIVE = ["Beach", "City", "Nature", "Hiking", "Family", "Culture", "Food", "Wellness", "Adventure", "Luxury"]
RED = ["Budget", "Winter"]          # only negative contributions -> red nodes
GREY = ["Nightlife", "Wildlife"]    # content but no signal -> grey nodes
ALL_CATEGORIES = POSITIVE + RED + GREY

RELATIONS = [
    ("Nature", "Hiking"), ("Nature", "Wildlife"), ("Nature", "Adventure"),
    ("City", "Culture"), ("City", "Food"), ("City", "Nightlife"),
    ("Beach", "Family"), ("Beach", "Wellness"), ("Luxury", "Wellness"),
    ("Culture", "Food"), ("Adventure", "Hiking"), ("Family", "Beach"),
    ("Budget", "Family"), ("Winter", "Adventure"), ("Luxury", "City"),
]


BRAND_ID: int | None = None


def seed(extended: bool = False):
    """The demo dataset. `extended=True` adds what the dev demo needs and the
    test suite deliberately does not (see `_seed_extras`); the suite calls
    `seed()`, so its baseline stays the single-brand fixture."""
    db = SessionLocal()
    try:
        _truncate(db)

        # Content, campaigns and sends carry a NOT NULL brand since ADR-150
        # point 2. `_truncate` deliberately leaves `brands` alone, so the
        # default row survives a reseed — but on a database that has never
        # booted the app there is nothing to survive, hence ensure rather than
        # assume. Everything demo data creates belongs to the one brand: this
        # is a single-brand fixture, and it stays that way so the suite keeps
        # exercising the degenerate case ADR-150 point 4 promises is free.
        global BRAND_ID
        BRAND_ID = ensure_default_brand(db).id

        # --- categories -------------------------------------------------
        cat = {}
        for name in ALL_CATEGORIES:
            ctype = "main" if name in ("Beach", "City", "Nature", "Culture", "Luxury") else "sub"
            c = CategoryDB(name=name, type=ctype)
            db.add(c)
            cat[name] = c
        db.commit()

        for parent, child in RELATIONS:
            db.add(CategoryRelationDB(
                parent_category_id=cat[parent].id,
                child_category_id=cat[child].id,
                relation_type="parent_child",
            ))
        db.commit()

        # --- 100 content records + versions + category assignments ------
        content_ids_by_category = {name: [] for name in ALL_CATEGORIES}
        contents = []
        for i in range(1, 101):
            primary = random.choice(ALL_CATEGORIES)
            title = f"{primary} feature #{i}"
            body = {
                "headline_medium": title,
                "body_medium": f"An editorial piece about {primary.lower()} — issue {i}.",
                "button_label": "Read more",
                # A link to click: without one a content module renders no
                # anchor, so no click can name its content (task-240).
                "button_url": f"https://example.com/stories/{i}",
                "image_url": f"/static/img/demo-{i}.jpg",
            }
            rec = ContentRecordDB(title=title, description=body["body_medium"], content=body,
                                  status="active", brand_id=BRAND_ID)
            db.add(rec)
            contents.append((rec, primary))
        db.commit()

        for rec, primary in contents:
            db.add(ContentVersionDB(content_record_id=rec.id, version_number=1, content=rec.content, created_by="demo"))
            # 1–3 categories: the primary + up to 2 others (co-occurrence -> edges)
            cats = {primary}
            for _ in range(random.randint(0, 2)):
                cats.add(random.choice(ALL_CATEGORIES))
            for cname in cats:
                db.add(ContentCategoryAssignmentDB(content_id=rec.id, category_id=cat[cname].id, score=random.randint(5, 10)))
                content_ids_by_category[cname].append(rec.id)
        db.commit()

        # --- 40 recipients + manual preference contributions ------------
        first = ["Anna", "Jan", "Sophie", "Lars", "Mia", "Tom", "Nora", "Paul", "Lea", "Finn",
                 "Emma", "Noah", "Julia", "Ben", "Clara", "Max", "Ida", "Leon", "Marie", "Elias"]
        langs = ["de", "de", "de", "nl", "fr", "en"]
        recipients = []
        addresses_by_external_id: dict[str, str] = {}
        for i in range(1, 41):
            name = random.choice(first)
            r = RecipientDB(
                external_id=f"demo-{i:03d}",
                language=random.choice(langs),
                attributes={"firstname": name},
                status="active",
            )
            db.add(r)
            # The address is a row, not a column (ADR-163 point 2), so it is
            # carried alongside until the rows are written below.
            addresses_by_external_id[r.external_id] = f"{name.lower()}.{i}@example.com"
            recipients.append(r)
        db.flush()  # assign ids before the consent/address rows reference them

        # Consent is an event per (recipient, channel, purpose), latest wins
        # (ADR-163 point 1), and the address is a row rather than a column on
        # the recipient (point 2). Both are required for a recipient to resolve
        # into an audience at all — consent clears the gate, the address makes
        # them reachable — so a seed that writes neither produces 40 recipients
        # the system correctly refuses to send to.
        for r in recipients:
            db.add(
                ConsentEventDB(
                    recipient_id=r.id,
                    # Consent is per (recipient, BRAND, channel, purpose) —
                    # ADR-163 point 1 as amended for brands. This line was
                    # missing until 2026-09-19, so the seed had been broken
                    # against the schema for as long as `brand_id` was NOT
                    # NULL. Nobody saw it because nobody ran the seed against a
                    # database that did not already have rows in it, which is
                    # exactly what the isolated test database is for.
                    brand_id=BRAND_ID,
                    channel="email",
                    purpose="marketing",
                    status="opted_in",
                    source="seed",
                    note="seed_demo_data.py",
                )
            )
            db.add(
                AddressabilityDB(
                    recipient_id=r.id,
                    channel="email",
                    value={"email": addresses_by_external_id[r.external_id]},
                    status="active",
                    is_primary=True,
                )
            )
        db.commit()

        # manual preferences: 2–5 positive categories each, varied magnitude,
        # occurred_at spread over ~150 days so decay produces size variety.
        for r in recipients:
            for cname in random.sample(POSITIVE, random.randint(2, 5)):
                db.add(SignalContributionDB(
                    recipient_id=r.id,
                    category_id=cat[cname].id,
                    contribution_type="manual",
                    base_weight=float(random.randint(30, 95)),
                    occurred_at=NOW - timedelta(days=random.randint(0, 150)),
                    source="seed",
                ))
        db.commit()

        # negative contributions -> RED nodes (declining interest)
        for cname in RED:
            for r in random.sample(recipients, 18):
                db.add(SignalContributionDB(
                    recipient_id=r.id,
                    category_id=cat[cname].id,
                    contribution_type="unsubscribe",
                    base_weight=float(-random.randint(30, 60)),
                    occurred_at=NOW - timedelta(days=random.randint(0, 90)),
                    source="seed",
                ))
        db.commit()

        # --- 4 campaigns, each a variant + modules + a decision slot -----
        slots = []
        pos_ids = [cat[n].id for n in POSITIVE]
        for ci in range(1, 5):
            camp = CampaignDB(name=f"Demo Campaign {ci}", status="draft", brand_id=BRAND_ID)
            db.add(camp); db.flush()
            variant = VariantDB(campaign_id=camp.id, channel="email",
                                name=f"Variant {ci}A", status="draft")
            db.add(variant); db.flush()
            # Subject and preheader are NOT columns here any more — ADR-162
            # point 1 made them fields of a `header` module, and migration 0012
            # dropped them. This seed still passed them as keyword arguments
            # until 2026-09-19, which nothing noticed because the seed was only
            # ever run against a database that already had its rows.
            set_envelope_fields(db, variant.id, {
                "subject": f"Edition {ci}: picked for you",
                "preheader": "Your personalized selection",
            }, brand_id=BRAND_ID)
            # The hero is a content module, so it needs a record: unbound it
            # rendered hidden (ADR-086). Its own small published record, with
            # the field the hero manifest reads.
            hero_content = {"headline_hero": f"Edition {ci}", "button_label_hero": "Start reading",
                            "button_url": "https://example.com/editions"}
            hero_rec = ContentRecordDB(title=f"Edition {ci} hero", content=hero_content,
                                       status="active", brand_id=BRAND_ID)
            db.add(hero_rec); db.flush()
            db.add(ContentVersionDB(content_record_id=hero_rec.id, version_number=1,
                                    content=hero_content, created_by="demo"))
            slot = DecisionSlotDB(
                variant_id=variant.id, name="Main Content Slot",
                decision_type="content_recommendation", decision_strategy="recipient_top_score",
                candidate_filter={"category_ids": pos_ids},
                strategy_config={"content_score_weight": 1, "preference_score_weight": 10}, max_results=1,
            )
            db.add(slot); db.flush()
            db.add_all([
                ModuleInstanceDB(variant_id=variant.id, module_type="hero", position=1, content_record_id=hero_rec.id, module_data={}),
                ModuleInstanceDB(variant_id=variant.id, module_type="img_left", position=2, decision_slot_id=slot.id),
                # `label` and `url` are the cta manifest's required fields. The
                # seed wrote `button_label` until 2026-10-02, so every demo
                # campaign was refused at send for missing required content.
                ModuleInstanceDB(variant_id=variant.id, module_type="cta", position=3,
                                 module_data={"label": "Explore", "url": "https://example.com/explore"}),
            ])
            slots.append((slot, variant))
        db.commit()

        # decision resolutions: each recipient resolved on slot 1 to a content
        # record in their strongest positive category -> selections spread across
        # categories, driving node size.
        slot1, _ = slots[0]
        for r in recipients:
            sigs = (
                db.query(SignalContributionDB.category_id, SignalContributionDB.base_weight)
                .filter(SignalContributionDB.recipient_id == r.id,
                        SignalContributionDB.category_id.in_(pos_ids))
                .all()
            )
            if not sigs:
                continue
            top_cat_id = max(sigs, key=lambda s: s[1])[0]
            # content records assigned to the top category
            name_by_id = {v.id: k for k, v in cat.items()}
            top_name = name_by_id[top_cat_id]
            candidates = content_ids_by_category.get(top_name, [])
            if not candidates:
                continue
            content_id = random.choice(candidates)
            db.add(DecisionResolutionDB(
                decision_slot_id=slot1.id, recipient_id=r.id, content_record_id=content_id,
                reason=f"top preference match: {top_name}", score=float(random.randint(600, 950)),
            ))
        db.commit()

        # --- engagement: clicks -> click contributions (event_id set) ----
        # A frame, like every snapshot since ADR-183: the composition frozen
        # with its values, which is what a send renders from.
        from app.rendering.frame import build_frame
        from app.snapshots.service import INLINE_LOCATION

        snap = SnapshotDB(variant_id=slots[0][1].id, artifact_storage_type="inline",
                          artifact_location=INLINE_LOCATION, artifact_size=0,
                          render_context=build_frame(db, slots[0][1].id))
        db.add(snap); db.flush()
        si = SendInstanceDB(snapshot_id=snap.id, name="Demo send", status="sent",
                            provider="mock", brand_id=BRAND_ID)
        db.add(si); db.flush()
        db.commit()

        # content whose categories are all positive (keeps red nodes clean)
        pos_name_set = set(POSITIVE)
        clickable = []
        for rec, primary in contents:
            rec_cats = {a.category_id for a in db.query(ContentCategoryAssignmentDB).filter(ContentCategoryAssignmentDB.content_id == rec.id)}
            names = {name_by_id[cid] for cid in rec_cats}
            if names and names.issubset(pos_name_set):
                clickable.append(rec.id)

        event_count = 0
        for r in random.sample(recipients, 32):
            ex = DeliveryExecutionDB(send_instance_id=si.id, recipient_id=r.id, status="sent",
                                     provider="mock", channel="email", purpose="marketing")
            db.add(ex); db.flush()
            for _ in range(random.randint(2, 6)):
                content_id = random.choice(clickable)
                ev = EngagementEventDB(
                    delivery_execution_id=ex.id, event_type="click", provider="mock",
                    provider_event_id=f"evt-{r.id}-{event_count}",
                    event_data={"content_record_id": content_id},
                    occurred_at=NOW - timedelta(days=random.randint(0, 60)),
                )
                db.add(ev); db.flush()
                db.commit()
                try:
                    apply_event_to_signals(db, ev.id)
                except ValueError:
                    pass
                event_count += 1
        db.commit()

        if extended:
            _seed_extras(db, recipients, cat, slots)

        # --- summary ----------------------------------------------------
        print("Demo data seeded:")
        print("  categories:", db.query(CategoryDB).count(), "| relations:", db.query(CategoryRelationDB).count())
        print("  content records:", db.query(ContentRecordDB).count())
        print("  recipients:", db.query(RecipientDB).count())
        print("  campaigns:", db.query(CampaignDB).count(), "| decision resolutions:", db.query(DecisionResolutionDB).count())
        print("  engagement events:", db.query(EngagementEventDB).count())
        print("  signal contributions:", db.query(SignalContributionDB).count())
        if extended:
            from app.audience.db_models import AudienceGroupDB
            from app.auth.db_models import BrandDB

            print("  brands:", db.query(BrandDB).count(),
                  "| audience groups:", db.query(AudienceGroupDB).count())
            print("  sends:", db.query(SendInstanceDB).count(), "| executions with a delivery record:",
                  db.query(DeliveryExecutionDB).filter(DeliveryExecutionDB.delivery_record.isnot(None)).count())
            print("  variants by channel:", dict(
                db.query(VariantDB.channel, func.count(VariantDB.id)).group_by(VariantDB.channel).all()))
    finally:
        db.close()


def _seed_extras(db, recipients, cat, slots) -> None:
    """What the dev demo needs beyond the test baseline (2026-10-02).

    Kept out of `seed()`'s default on purpose: the suite's baseline is a
    single-brand, email-only fixture "so the suite keeps exercising the
    degenerate case ADR-150 point 4 promises is free". Four additions:

      1. an audience group, because planning a send needs one;
      2. a real send of Demo Campaign 2 through `send_send_instance`, so its
         executions carry delivery records and "as sent" answers (ADR-183);
      3. a push variant on Demo Campaign 3, with push content, and push consent
         and device tokens for 15 recipients;
      4. a second brand with its own content, campaign and consent, and an
         admin grant for every admin of the default brand, so duplication,
         the per-brand graph and the grant rules have something to work on.
    """
    from app.audience.service import add_block, create_group
    from app.auth.db_models import BrandDB, RoleAssignmentDB, RoleDB
    from app.campaigns.service import create_module_for_variant, create_variant_for_campaign
    from app.delivery.service import prepare_send_from_audience, send_send_instance
    from app.snapshots.service import create_snapshot_for_variant

    from app.audience.db_models import AudienceGroupDB
    from app.audience.service import add_member

    def group_named(name, description):
        # `_truncate` empties groups through CASCADE today; get-or-create so a
        # change to that list cannot turn a re-seed into a duplicate-name error.
        existing = db.query(AudienceGroupDB).filter(
            AudienceGroupDB.brand_id == BRAND_ID, AudienceGroupDB.name == name).first()
        return existing or create_group(db, name, brand_id=BRAND_ID, description=description)

    # 1. everyone who consents, on the channel a send asks about
    everyone = group_named("All demo recipients", "Every demo recipient with consent (seeded)")
    from app.audience.db_models import AudienceRuleBlockDB

    if db.query(AudienceRuleBlockDB).filter(AudienceRuleBlockDB.group_id == everyone.id).count() == 0:
        add_block(db, everyone.id, kind="include", criteria={}, label="everyone", brand_id=BRAND_ID)

    # 2. a real send: snapshot (a frame), plan, fire — through the real path.
    # To a small pinned sample rather than everyone, so it fits a deployment
    # whose send cap was lowered (a dev database had it at 10): the seed must
    # not change a setting somebody chose.
    sample = group_named("Seed send sample", "Eight pinned demo recipients (seeded)")
    for r in recipients[:8]:
        add_member(db, sample.id, r.id, brand_id=BRAND_ID)
    variant_2 = slots[1][1]
    snapshot = create_snapshot_for_variant(db, variant_2.id, brand_id=BRAND_ID)
    send = prepare_send_from_audience(
        db, snapshot_id=snapshot.id, name="Edition 2 (sent by the seed)",
        audience_group_id=sample.id, provider="mock", brand_id=BRAND_ID,
    )
    send_send_instance(db, send.id, brand_id=BRAND_ID)

    # 3. a push variant, and people who can receive it
    push_content = {"push_title": "Your weekend pick", "push_body": "Three trips we think you'll like.",
                    "push_link": "https://example.com/weekend"}
    push_rec = ContentRecordDB(title="Weekend pick (push)", content=push_content,
                               status="active", brand_id=BRAND_ID)
    db.add(push_rec); db.flush()
    db.add(ContentVersionDB(content_record_id=push_rec.id, version_number=1,
                            content=push_content, created_by="demo"))
    db.commit()
    campaign_3 = slots[2][1].campaign_id
    push_variant = create_variant_for_campaign(db, campaign_3, name="Variant 3 (push)",
                                               channel="push", brand_id=BRAND_ID)
    create_module_for_variant(db, variant_id=push_variant.id, module_type="notification",
                              content_record_id=push_rec.id, brand_id=BRAND_ID)
    for i, r in enumerate(recipients[:15], start=1):
        db.add(ConsentEventDB(recipient_id=r.id, brand_id=BRAND_ID, channel="push",
                              purpose="marketing", status="opted_in", source="seed",
                              note="seed_demo_data.py (extended)"))
        db.add(AddressabilityDB(recipient_id=r.id, channel="push",
                                value={"token": f"demo-token-{i:03d}", "platform": "apns"},
                                status="active", is_primary=True))
    db.commit()

    # 4. a second brand, which `_truncate` leaves in place, so ensure it
    brand_b = db.query(BrandDB).filter(BrandDB.key == "demo-b").first()
    if brand_b is None:
        brand_b = BrandDB(key="demo-b", name="Demo Brand B")
        db.add(brand_b); db.commit()
    admin = db.query(RoleDB).filter(RoleDB.key == "admin").first()
    if admin is not None:
        for assignment in db.query(RoleAssignmentDB).filter(
            RoleAssignmentDB.role_id == admin.id, RoleAssignmentDB.brand_id == BRAND_ID,
        ).all():
            exists = db.query(RoleAssignmentDB).filter(
                RoleAssignmentDB.user_id == assignment.user_id,
                RoleAssignmentDB.role_id == admin.id,
                RoleAssignmentDB.brand_id == brand_b.id,
            ).first()
            if exists is None:
                db.add(RoleAssignmentDB(user_id=assignment.user_id, role_id=admin.id,
                                        brand_id=brand_b.id))
        db.commit()
    b_records = []
    for i, name in enumerate(["Beach", "City", "Food", "Wellness", "Family",
                              "Culture", "Nature", "Luxury", "Hiking", "Adventure"], start=1):
        body = {"headline_medium": f"Brand B: {name} #{i}",
                "body_medium": f"Brand B's take on {name.lower()}.", "button_label": "Read more"}
        rec = ContentRecordDB(title=f"Brand B {name} #{i}", content=body, status="active",
                              brand_id=brand_b.id)
        db.add(rec); db.flush()
        db.add(ContentVersionDB(content_record_id=rec.id, version_number=1, content=body,
                                created_by="demo"))
        db.add(ContentCategoryAssignmentDB(content_id=rec.id, category_id=cat[name].id, score=8))
        b_records.append(rec)
    campaign_b = CampaignDB(name="Brand B newsletter", status="draft", brand_id=brand_b.id)
    db.add(campaign_b); db.flush()
    variant_b = VariantDB(campaign_id=campaign_b.id, channel="email", name="Variant B1", status="draft")
    db.add(variant_b); db.flush()
    db.commit()
    set_envelope_fields(db, variant_b.id, {"subject": "Brand B: this month",
                                           "preheader": "From Demo Brand B"}, brand_id=brand_b.id)
    db.add_all([
        ModuleInstanceDB(variant_id=variant_b.id, module_type="img_left", position=2,
                         content_record_id=b_records[0].id, module_data={}),
        ModuleInstanceDB(variant_id=variant_b.id, module_type="cta", position=3,
                         module_data={"label": "Visit Brand B", "url": "https://example.com/brand-b"}),
    ])
    for r in recipients[:20]:
        db.add(ConsentEventDB(recipient_id=r.id, brand_id=brand_b.id, channel="email",
                              purpose="marketing", status="opted_in", source="seed",
                              note="seed_demo_data.py (extended)"))
    db.commit()


if __name__ == "__main__":
    # The dev demo: the extended set. The test suite calls `seed()` directly.
    seed(extended=True)
