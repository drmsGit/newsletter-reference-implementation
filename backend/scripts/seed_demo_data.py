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

from sqlalchemy import text

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


def seed():
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
            slot = DecisionSlotDB(
                variant_id=variant.id, name="Main Content Slot",
                decision_type="content_recommendation", decision_strategy="recipient_top_score",
                candidate_filter={"category_ids": pos_ids},
                strategy_config={"content_score_weight": 1, "preference_score_weight": 10}, max_results=1,
            )
            db.add(slot); db.flush()
            db.add_all([
                ModuleInstanceDB(variant_id=variant.id, module_type="hero", position=1, module_data={"headline": f"Edition {ci}"}),
                ModuleInstanceDB(variant_id=variant.id, module_type="img_left", position=2, decision_slot_id=slot.id),
                ModuleInstanceDB(variant_id=variant.id, module_type="cta", position=3, module_data={"button_label": "Explore"}),
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
        snap = SnapshotDB(variant_id=slots[0][1].id, artifact_storage_type="file",
                          artifact_location="/tmp/demo.html", artifact_size=0)
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
            ex = DeliveryExecutionDB(send_instance_id=si.id, recipient_id=r.id, status="sent", provider="mock")
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

        # --- summary ----------------------------------------------------
        print("Demo data seeded:")
        print("  categories:", db.query(CategoryDB).count(), "| relations:", db.query(CategoryRelationDB).count())
        print("  content records:", db.query(ContentRecordDB).count())
        print("  recipients:", db.query(RecipientDB).count())
        print("  campaigns:", db.query(CampaignDB).count(), "| decision resolutions:", db.query(DecisionResolutionDB).count())
        print("  engagement events:", db.query(EngagementEventDB).count())
        print("  signal contributions:", db.query(SignalContributionDB).count())
    finally:
        db.close()


if __name__ == "__main__":
    seed()
