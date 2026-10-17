"""The demo reset (task-71): empty the demo data, keep people and settings,
build Grathaus.

**Kept:** user accounts, roles, grants, sessions and sign-in codes; Settings
(`app_config`, the AI prompts); integrations with their keys and grants; the
audit log (append-only, ADR-153: the reset is one entry in it); the migration
ledger. **Emptied:** every other table, and the image files (ADR-197 addendum
2026-10-17). **Brands:** the default brand is renamed Grathaus Outdoor (its key
stays: the default-brand fallback reads it), Grathaus Touren is added, every
other brand goes with its data and grants.

Built deterministically, so a rehearsal repeats; the content and the
editions' words come from `scripts/demo/` (seed_content_prompt.md). What is
missing there is reported, never invented.
"""
import random
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.demo import catalogue, editions, people

DEMO_DIR = Path(__file__).resolve().parents[2] / "scripts" / "demo"
TOUREN_KEY = "grathaus-touren"
OUTDOOR_NAME, TOUREN_NAME = "Grathaus Outdoor", "Grathaus Touren"

#: Emptied, in one statement: every table but the kept ones. A table missing
#: here that references an emptied one makes the TRUNCATE fail, which is the
#: point — nothing is emptied by CASCADE behind the list's back.
EMPTIED = (
    "signal_contributions", "engagement_events", "provider_event_quarantine", "consent_sync_logs",
    "consent_events", "recipient_addresses", "delivery_executions", "send_instances", "snapshots",
    "content_overrides", "decision_resolutions", "module_instances", "decision_slots", "variants", "campaigns",
    "audience_group_members", "audience_rule_blocks", "audience_groups", "pending_actions", "ai_runs",
    "content_category_assignments", "content_channel_readiness", "content_versions", "category_relations",
    "categories", "content_records", "recipients", "expression_entries", "assets", "brand_profiles",
)
KEPT = (
    "users", "roles", "role_permissions", "role_assignments", "auth_sessions", "login_codes",
    "login_code_requests", "app_config", "ai_prompts", "integrations", "integration_credentials",
    "integration_grants", "integration_auth_failures", "audit_events", "schema_migrations", "brands",
)

LEGAL = {
    "outdoor": {"legal_company_name": "Grathaus Outdoor GmbH (Demo)",
                "legal_address": "Beispielstraße 12\n80331 München",
                "imprint_url": "https://www.grathaus.example/impressum",
                "privacy_url": "https://www.grathaus.example/datenschutz"},
    "touren": {"legal_company_name": "Grathaus Touren GmbH (Demo)",
               "legal_address": "Beispielstraße 12\n80331 München",
               "imprint_url": "https://touren.grathaus.example/impressum",
               "privacy_url": "https://touren.grathaus.example/datenschutz"},
}
UNSUBSCRIBE = {"de": "Abmelden", "en": "Unsubscribe"}


@dataclass
class Outcome:
    problems: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)


def empty(db: Session) -> list[str]:
    """Empty the demo data and every brand but the two Grathaus ones;
    returns the brand keys whose image folders are to go."""
    from app.auth.db_models import BrandDB, RoleAssignmentDB
    from app.auth.service import ensure_default_brand
    from app.auth.db_models import IntegrationGrantDB

    default = ensure_default_brand(db)
    keys = [key for (key,) in db.query(BrandDB.key)]
    db.execute(text(f"TRUNCATE TABLE {', '.join(EMPTIED)} RESTART IDENTITY"))
    gone = [b.id for b in db.query(BrandDB).filter(BrandDB.id != default.id, BrandDB.key != TOUREN_KEY)]
    db.query(RoleAssignmentDB).filter(RoleAssignmentDB.brand_id.in_(gone)).delete(synchronize_session=False)
    db.query(IntegrationGrantDB).filter(IntegrationGrantDB.brand_id.in_(gone)).delete(synchronize_session=False)
    db.query(BrandDB).filter(BrandDB.id.in_(gone)).delete(synchronize_session=False)
    db.commit()
    return keys


def remove_image_files(keys: list[str]) -> None:
    from app.assets.store import get_store

    root = get_store().root
    for key in keys:
        folder = root / key
        # Only a brand's own folder inside the store, never a path a key could stretch.
        if folder.parent == root and folder.is_dir():
            shutil.rmtree(folder)


def brands(db: Session) -> dict[str, int]:
    """The two Grathaus brands; the default brand's admins are admins of both."""
    from app.auth.db_models import BrandDB, RoleAssignmentDB, RoleDB
    from app.auth.service import ensure_default_brand

    outdoor = ensure_default_brand(db)
    outdoor.name = OUTDOOR_NAME
    outdoor.expressions_started_at = None
    touren = db.query(BrandDB).filter(BrandDB.key == TOUREN_KEY).first()
    if touren is None:
        touren = BrandDB(key=TOUREN_KEY, name=TOUREN_NAME)
        db.add(touren)
    touren.name, touren.expressions_started_at = TOUREN_NAME, None
    db.commit()
    admin = db.query(RoleDB).filter(RoleDB.key == "admin").first()
    if admin is not None:
        for (user_id,) in db.query(RoleAssignmentDB.user_id).filter(
                RoleAssignmentDB.role_id == admin.id, RoleAssignmentDB.brand_id == outdoor.id).distinct():
            if not db.query(RoleAssignmentDB.id).filter_by(user_id=user_id, role_id=admin.id,
                                                          brand_id=touren.id).first():
                db.add(RoleAssignmentDB(user_id=user_id, role_id=admin.id, brand_id=touren.id))
        db.commit()
    return {"outdoor": outdoor.id, "touren": touren.id}


def profiles(db: Session, brand_ids: dict[str, int]) -> dict[str, int]:
    """Outdoor: marketing de (default), marketing en, transactional de.
    Touren: marketing de (default), transactional de. {name: id}."""
    from app.brand_profiles.service import TRANSACTIONAL, create_profile, ensure_default_profile

    made = {}
    for brand, brand_id in brand_ids.items():
        default = ensure_default_profile(db, brand_id)
        default.name, default.language = "Newsletter Deutsch", "de"
        default.field_values = {**LEGAL[brand], "unsubscribe_text": UNSUBSCRIBE["de"]}
        db.commit()
        made[f"{brand}:de"] = default.id
        if brand == "outdoor":
            made[f"{brand}:en"] = create_profile(
                db, brand_id, name="Newsletter English", language="en",
                field_values={**LEGAL[brand], "unsubscribe_text": UNSUBSCRIBE["en"]}).id
        made[f"{brand}:transactional"] = create_profile(
            db, brand_id, name="Service-Mails", language="de", kind=TRANSACTIONAL,
            field_values=dict(LEGAL[brand]), allow_transactional=True).id
    return made


def ready_to_demo(db: Session, brand_ids: dict[str, int], profile_ids: dict[str, int], words: dict,
                  category_ids: dict[str, int], records: dict[str, list[int]]) -> list[str]:
    """What the demo is given to work with: an empty variant for Prepare from
    a topic, a push for a store event, the two service mails."""
    from app.campaigns.db_models import VariantDB
    from app.campaigns.service import (
        create_campaign, create_module_for_variant, create_variant_for_campaign, set_envelope_fields,
    )
    from app.content.db_models import ContentRecordDB

    lines = []
    outdoor = brand_ids["outdoor"]
    campaign = create_campaign(db, name="Neue Ausgabe", brand_id=outdoor, channel="email",
                               initial_variant_name="Deutsch")
    lines.append(f"  an empty edition for Prepare from a topic: campaign {campaign.id}")

    pushable = (db.query(ContentRecordDB.id).filter(ContentRecordDB.brand_id == outdoor,
                                                   ContentRecordDB.language == "de",
                                                   ContentRecordDB.id.in_(records["outdoor"]))
                .order_by(ContentRecordDB.id).all())
    push_record = next((rid for (rid,) in pushable
                        if (db.get(ContentRecordDB, rid).content or {}).get("push_title")), None)
    if push_record is not None:
        push = create_campaign(db, name="Testtag im Laden (Push)", brand_id=outdoor, channel="push",
                               initial_variant_name="Push")
        variant = db.query(VariantDB).filter(VariantDB.campaign_id == push.id).one()
        create_module_for_variant(db, variant_id=variant.id, module_type="notification",
                                  content_record_id=push_record, brand_id=outdoor)
        lines.append(f"  a push: campaign {push.id}")

    for key, brand, name in (("bestellbestaetigung", "outdoor", "Bestellbestätigung"),
                             ("buchungsbestaetigung", "touren", "Buchungsbestätigung")):
        text_ = words.get(key) or {"subject": name, "preheader": "", "editorial": f"{name}."}
        mail = create_campaign(db, name=name, brand_id=brand_ids[brand], channel="email",
                               initial_variant_name="Deutsch")
        variant = db.query(VariantDB).filter(VariantDB.campaign_id == mail.id).one()
        variant.brand_profile_id = profile_ids[f"{brand}:transactional"]
        db.commit()
        set_envelope_fields(db, variant.id, {"subject": text_["subject"], "preheader": text_["preheader"]},
                            brand_id=brand_ids[brand])
        create_module_for_variant(db, variant_id=variant.id, module_type="editorial",
                                  module_data={"text": text_["editorial"]}, brand_id=brand_ids[brand])
        lines.append(f"  a service mail: {name}, campaign {mail.id}")

    english = (db.query(ContentRecordDB.id).filter(ContentRecordDB.brand_id == outdoor,
                                                  ContentRecordDB.language == "en").order_by(ContentRecordDB.id)
               .limit(2).all())
    if english:
        two = create_campaign(db, name="Herbst in den Bergen / Autumn in the mountains", brand_id=outdoor,
                              channel="email", initial_variant_name="Deutsch")
        de = db.query(VariantDB).filter(VariantDB.campaign_id == two.id).one()
        en = create_variant_for_campaign(db, two.id, name="English", channel="email", brand_id=outdoor)
        db.query(VariantDB).filter(VariantDB.id == en.id).update({"brand_profile_id": profile_ids["outdoor:en"]})
        db.commit()
        for (english_id,) in english:
            original = db.get(ContentRecordDB, english_id).translation_of_id
            if original:
                create_module_for_variant(db, variant_id=de.id, module_type="img_left", content_record_id=original,
                                          brand_id=outdoor)
            create_module_for_variant(db, variant_id=en.id, module_type="img_left", content_record_id=english_id,
                                      brand_id=outdoor)
        lines.append(f"  a German and an English variant: campaign {two.id}")
    return lines


def run(db: Session, *, content_dir: Path | None = None, images_dir: Path | None = None,
        send_cap: int | None = None) -> Outcome:
    """The whole reset. Commits as it goes; a failure leaves a partial demo,
    which the next run empties again."""
    from app.expressions.service import entries_of
    from app.settings.service import get_max_send_recipients

    content_dir = content_dir or DEMO_DIR / "content"
    images_dir = images_dir or DEMO_DIR / "images"
    out = Outcome()
    rng = random.Random(71)

    remove_image_files(empty(db))
    brand_ids = brands(db)
    profile_ids = profiles(db, brand_ids)
    for brand_id in brand_ids.values():
        entries_of(db, brand_id, start=True)
    category_ids = catalogue.create_tree(db)

    read = catalogue.read_all(content_dir)
    out.problems += read.problems
    if not read.rows:
        out.problems.append(f"no content rows in {content_dir} (batch-*.csv, english.csv)")
    alts: dict[str, str] = {}
    for row in read.rows:
        if row.image and row.image_alt and row.language == "de":
            alts.setdefault(row.image, row.image_alt)
    assets = catalogue.upload_images(db, images_dir, brand_ids, alts, out.problems)
    records = catalogue.create_records(db, read.rows, brand_ids, category_ids, assets)
    out.lines.append(f"  records: {len(records['outdoor'])} Outdoor, {len(records['touren'])} Touren; "
                     f"images: {len({k for _b, k in assets})}")

    readers = people.create_readers(db, outdoor_id=brand_ids["outdoor"], touren_id=brand_ids["touren"],
                                    category_ids=category_ids, rng=rng)
    out.lines.append(f"  readers: {sum(len(v) for v in readers.values())}")

    words = editions.read_words(content_dir / "editions.csv", out.problems)
    cap = send_cap or get_max_send_recipients(db)
    for edition in sorted(editions.EDITIONS, key=lambda e: (e.sent is None, e.sent or 0)):
        brand_id = brand_ids[edition.brand]
        _campaign, variant = editions.build_edition(db, edition, words, brand_id=brand_id,
                                                    category_ids=category_ids,
                                                    profile_id=profile_ids.get(f"{edition.brand}:de"))
        if edition.sent is None:
            out.lines.append(f"  draft: {edition.name}")
            continue
        figures = editions.send_and_date(db, edition, variant, brand_id=brand_id,
                                         category_id=category_ids[edition.segment], cap=cap, rng=rng)
        out.lines.append(f"  sent {edition.sent:%Y-%m-%d}: {edition.name} — {figures['sent']} delivered, "
                         f"{figures['opens']} opens, {figures['clicks']} clicks"
                         + (", 1 unsubscribe" if figures["unsubscribed"] else ""))
    out.lines += ready_to_demo(db, brand_ids, profile_ids, words, category_ids, records)
    from app.audit import service as audit

    audit.record(db, audit.DEMO_RESET, actor_type=audit.ACTOR_SYSTEM,
                 detail={"records": {b: len(ids) for b, ids in records.items()},
                         "readers": sum(len(v) for v in readers.values()), "problems": len(out.problems)})
    return out
