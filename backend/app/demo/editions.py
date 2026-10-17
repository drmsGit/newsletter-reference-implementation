"""The Grathaus editions (task-71): what was sent, and what is ready to send.

The words (subject, preheader, editorial) come from the external model's
`editions.csv`; the stack and the audience are built here. A past edition is
sent through the real path — snapshot, plan, fire with the mock provider —
to a segment of at most 200 (the dev send cap stays 200), then dated back,
so every delivery has its record and every figure agrees (ADR-183,
task-242). Opens and clicks name only what a delivery carried (ADR-182);
the clicks feed the readers' signals as real ones would.
"""
import csv
import io
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class Edition:
    key: str
    brand: str
    name: str
    #: When it was sent; None: a draft, ready to send in the demo.
    sent: datetime | None
    #: The main interest whose readers it went to.
    segment: str
    #: The categories its records and its slot come from.
    categories: tuple[str, ...]


def _on(year, month, day) -> datetime:
    return datetime(year, month, day, 7, 30, tzinfo=timezone.utc)


EDITIONS = [
    Edition("winterstart", "outdoor", "Winterstart 2025", _on(2025, 11, 25), "Wintersport",
            ("Skitouren", "Schneeschuh", "Langlauf", "Lawinenkunde", "Wintersport")),
    Edition("skitouren_einstieg", "outdoor", "Einstieg Skitouren", _on(2026, 1, 13), "Wintersport",
            ("Skitouren", "Lawinenkunde", "Wintersport")),
    Edition("herbstauftakt", "outdoor", "Herbstauftakt", _on(2026, 9, 3), "Wandern",
            ("Tagestouren", "Hüttentouren", "Weitwandern", "Wandern")),
    Edition("huettensaison_finale", "outdoor", "Hüttensaison-Finale", _on(2026, 10, 1), "Wandern",
            ("Hüttentouren", "Klettersteige", "Wandern")),
    Edition("familienherbst", "outdoor", "Familienherbst", _on(2026, 10, 8), "Familie & Kinder",
            ("Familienwandern", "Familie & Kinder", "Tierbeobachtung", "Naturerlebnis")),
    Edition("reparaturwoche", "outdoor", "Reparaturwoche", None, "Nachhaltigkeit",
            ("Reparieren & Second Hand", "Nachhaltigkeit")),
    Edition("kursprogramm_winter", "touren", "Kursprogramm Winter", None, "Wintersport",
            ("Skitouren", "Lawinenkunde", "Schneeschuh", "Wintersport")),
]

#: What the past sends' readers did, as shares of those who received it.
OPEN_RATE, CLICK_RATE = 0.46, 0.14
#: Of the messages sent, how many the provider reports as bounced.
BOUNCE_RATE = 0.01


def read_words(path: Path, problems: list[str]) -> dict[str, dict]:
    """editions.csv: {key: {kind, brand, subject, preheader, editorial}}."""
    if not path.is_file():
        problems.append(f"{path.name}: not found; editions get placeholder words")
        return {}
    raw = path.read_text(encoding="utf-8").lstrip("﻿")
    if '"' not in raw and ("“" in raw or "”" in raw):
        raw = raw.replace("“", '"').replace("”", '"')
    words = {}
    for number, row in enumerate(csv.DictReader(io.StringIO(raw)), start=2):
        key = (row.get("key") or "").strip()
        if not key:
            problems.append(f"{path.name}:{number}: no key, skipped")
            continue
        words[key] = {k: (row.get(k) or "").strip() for k in ("kind", "brand", "subject", "preheader", "editorial")}
    return words


def _words(words: dict, key: str, name: str) -> dict:
    return words.get(key) or {"subject": name, "preheader": "", "editorial": f"Neu bei Grathaus: {name}."}


def _audience(db: Session, name: str, category_id: int, brand_id: int):
    """A rule-based segment: everyone interested in that category. One per
    interest: two editions to the same readers share it."""
    from app.audience.db_models import AudienceGroupDB
    from app.audience.service import add_block, create_group

    existing = db.query(AudienceGroupDB).filter(AudienceGroupDB.brand_id == brand_id,
                                                AudienceGroupDB.name == name).first()
    if existing is not None:
        return existing
    group = create_group(db, name, brand_id=brand_id, description="Grathaus demo segment (task-71)")
    add_block(db, group.id, kind="include", criteria={"categories": [{"category_id": category_id, "min_score": 1}]},
              label=name, brand_id=brand_id)
    return group


def _records_in(db: Session, brand_id: int, category_ids: list[int], *, field: str, exclude: set[int],
                limit: int) -> list[int]:
    """German records of the brand assigned to these categories that fill `field`, best score first."""
    from app.content.db_models import ContentCategoryAssignmentDB, ContentRecordDB

    rows = (db.query(ContentRecordDB.id, ContentRecordDB.content)
            .join(ContentCategoryAssignmentDB, ContentCategoryAssignmentDB.content_id == ContentRecordDB.id)
            .filter(ContentRecordDB.brand_id == brand_id, ContentRecordDB.language == "de",
                    ContentCategoryAssignmentDB.category_id.in_(category_ids))
            .order_by(ContentCategoryAssignmentDB.score.desc(), ContentRecordDB.id).all())
    out = []
    for record_id, content in rows:
        if record_id in exclude or record_id in out or not (content or {}).get(field):
            continue
        out.append(record_id)
        if len(out) == limit:
            break
    return out


def build_edition(db: Session, edition: Edition, words: dict, *, brand_id: int, category_ids: dict[str, int],
                  profile_id: int | None):
    """The campaign: hero, editorial, two image blocks, a slot block of up to
    three picks from the edition's categories; subject and preheader."""
    from app.campaigns.db_models import VariantDB
    from app.campaigns.service import (
        create_campaign, create_decision_slot_for_variant, create_module_for_variant, set_envelope_fields,
    )

    text = _words(words, edition.key, edition.name)
    ids = [category_ids[name] for name in edition.categories]
    campaign = create_campaign(db, name=edition.name, brand_id=brand_id, channel="email",
                               initial_variant_name="Deutsch")
    variant = db.query(VariantDB).filter(VariantDB.campaign_id == campaign.id).one()
    if profile_id is not None:
        variant.brand_profile_id = profile_id
        db.commit()
    set_envelope_fields(db, variant.id, {"subject": text["subject"], "preheader": text["preheader"]},
                        brand_id=brand_id)
    hero = _records_in(db, brand_id, ids, field="headline_hero", exclude=set(), limit=1)
    if hero:
        create_module_for_variant(db, variant_id=variant.id, module_type="hero", content_record_id=hero[0],
                                  brand_id=brand_id)
    create_module_for_variant(db, variant_id=variant.id, module_type="editorial",
                              module_data={"text": text["editorial"]}, brand_id=brand_id)
    blocks = _records_in(db, brand_id, ids, field="headline_medium", exclude=set(hero), limit=2)
    for index, record_id in enumerate(blocks):
        create_module_for_variant(db, variant_id=variant.id, module_type=("img_left", "img_right")[index % 2],
                                  content_record_id=record_id, brand_id=brand_id)
    slot = create_decision_slot_for_variant(
        db, variant_id=variant.id, name="Für Sie ausgewählt", decision_strategy="recipient_top_score",
        candidate_filter={"category_ids": ids}, strategy_config={"content_score_weight": 1,
                                                                 "preference_score_weight": 10},
        max_results=3, brand_id=brand_id)
    create_module_for_variant(db, variant_id=variant.id, module_type=("img_left", "img_right")[len(blocks) % 2],
                              decision_slot_id=slot.id, brand_id=brand_id)
    return campaign, variant


def send_and_date(db: Session, edition: Edition, variant, *, brand_id: int, category_id: int,
                  cap: int, rng: random.Random) -> dict:
    """Send it to its segment through the real path, date it back, add what
    the readers did. Refuses a segment over the send cap rather than raising it."""
    from app.audience.service import resolve_audience
    from app.campaigns.db_models import CampaignDB, VariantDB
    from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
    from app.delivery.service import prepare_send_from_audience, send_send_instance, sent_content_ids
    from app.insight.db_models import EngagementEventDB
    from app.insight.service import apply_event_to_signals
    from app.recipients.consent import record_consent
    from app.snapshots.db_models import SnapshotDB
    from app.snapshots.service import create_snapshot_for_variant

    group = _audience(db, f"Interesse: {edition.segment}", category_id, brand_id)
    size = len(resolve_audience(db, group.id, "email"))
    if size > cap:
        raise RuntimeError(f"{edition.name}: its segment has {size} readers, over the send cap of {cap}; "
                           "the cap is not raised — reduce the segment (app/demo/people.py MAIN_INTERESTS)")
    snapshot = create_snapshot_for_variant(db, variant.id, brand_id=brand_id)
    send = prepare_send_from_audience(db, snapshot_id=snapshot.id, name=edition.name, audience_group_id=group.id,
                                      provider="mock", brand_id=brand_id)
    send_send_instance(db, send.id, brand_id=brand_id)

    sent_on = edition.sent
    # Created a week before, last changed when it went out: the list and the
    # campaign page show the edition's own dates, not the day of the reset.
    dated = {"created_at": sent_on - timedelta(days=6), "updated_at": sent_on}
    db.query(CampaignDB).filter(CampaignDB.id == variant.campaign_id).update(dated, synchronize_session=False)
    db.query(VariantDB).filter(VariantDB.id == variant.id).update(dated, synchronize_session=False)
    db.query(SnapshotDB).filter(SnapshotDB.id == snapshot.id).update({"created_at": sent_on},
                                                                    synchronize_session=False)
    db.query(SendInstanceDB).filter(SendInstanceDB.id == send.id).update(
        {"created_at": sent_on, "updated_at": sent_on}, synchronize_session=False)
    executions = db.query(DeliveryExecutionDB).filter(DeliveryExecutionDB.send_instance_id == send.id).all()
    for execution in executions:
        execution.created_at = execution.updated_at = sent_on
        if execution.sent_at is not None:
            execution.sent_at = sent_on
    db.commit()

    opens = clicks = 0
    unsubscribed = None
    for execution in executions:
        if execution.status != "sent":
            continue
        # What the provider reports for each message, as a real one does by
        # webhook: delivered, or now and then a bounce. The mock reports
        # nothing, so without this the campaign showed 0 delivered.
        reported = "bounce" if rng.random() < BOUNCE_RATE else "delivered"
        db.add(EngagementEventDB(
            delivery_execution_id=execution.id, event_type=reported, provider="mock",
            provider_event_id=f"grathaus-{reported}-{execution.id}", event_data={},
            occurred_at=sent_on + timedelta(seconds=rng.randint(5, 240))))
        db.commit()
        if reported == "bounce":
            continue
        carried = sorted(sent_content_ids(db, execution) or set())
        if rng.random() >= OPEN_RATE:
            continue
        opened_at = sent_on + timedelta(hours=rng.randint(1, 72))
        events = [("open", opened_at, None)]
        if carried and rng.random() < CLICK_RATE / OPEN_RATE:
            for _ in range(rng.randint(1, 2)):
                events.append(("click", opened_at + timedelta(minutes=rng.randint(1, 30)), rng.choice(carried)))
        for event_type, at, content_id in events:
            event = EngagementEventDB(
                delivery_execution_id=execution.id, event_type=event_type, provider="mock",
                provider_event_id=f"grathaus-{event_type}-{execution.id}-{opens + clicks}",
                event_data={"content_record_id": content_id} if content_id else {}, occurred_at=at)
            db.add(event)
            db.flush()
            db.commit()
            if event_type == "click":
                clicks += 1
                try:
                    apply_event_to_signals(db, event.id)
                except ValueError:
                    pass
            else:
                opens += 1
        # One reader of the family edition leaves, through this delivery (ADR-196 point 6).
        if edition.key == "familienherbst" and unsubscribed is None and len(events) == 1:
            consent = record_consent(db, execution.recipient_id, "opted_out", brand_id, source="unsubscribe",
                                     channel="email", purpose="marketing", note="Grathaus demo (task-71)",
                                     delivery_execution_id=execution.id)
            consent.created_at = opened_at + timedelta(minutes=2)
            db.commit()
            unsubscribed = execution.recipient_id
    return {"sent": sum(1 for e in executions if e.status == "sent"), "opens": opens, "clicks": clicks,
            "unsubscribed": unsubscribed}
