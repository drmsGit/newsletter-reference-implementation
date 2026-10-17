"""The Grathaus readers (task-71): about 1,000 fictional people.

Mostly German-speaking, some English. Every one has a main interest, so the
segments the past editions went to are real audiences; the shares are chosen
so no main interest reaches 200 people, the dev send cap (it stays 200).
Some have no gender or no last name, so both salutations' fallbacks show up
(ADR-199). Addresses are on example.com, which delivers nowhere.

Deterministic: a fixed random seed, so a rehearsal repeats.
"""
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

FEMALE = ["Anna", "Lena", "Sophie", "Marie", "Laura", "Julia", "Katharina", "Lisa", "Hannah", "Lea", "Sarah",
          "Johanna", "Clara", "Theresa", "Franziska", "Verena", "Miriam", "Sabine", "Petra", "Monika", "Andrea",
          "Birgit", "Claudia", "Eva", "Nina", "Carina", "Magdalena", "Christina", "Isabel", "Ronja"]
MALE = ["Lukas", "Jonas", "Maximilian", "Felix", "Tobias", "Florian", "Sebastian", "Simon", "Michael", "Thomas",
        "Andreas", "Stefan", "Markus", "Christian", "Daniel", "Matthias", "Benedikt", "Johannes", "Alexander",
        "Moritz", "Leon", "Paul", "Elias", "Jakob", "Quirin", "Korbinian", "Martin", "Peter", "Georg", "Wolfgang"]
LAST = ["Huber", "Müller", "Schmid", "Wagner", "Bauer", "Maier", "Hofmann", "Fischer", "Weber", "Becker", "Lang",
        "Schneider", "Zimmermann", "Brunner", "Gruber", "Moser", "Berger", "Winkler", "Lechner", "Kaiser", "Fuchs",
        "Wolf", "Graf", "Stadler", "Eder", "Pichler", "Wimmer", "Seidl", "Brandl", "Heigl", "Obermaier",
        "Reiter", "Hartl", "Rauch", "Kellner", "Vogel", "Sommer", "Winter", "Haas", "Lindner"]
ENGLISH_FEMALE = ["Emily", "Olivia", "Grace", "Charlotte", "Amelia", "Ruth", "Hannah", "Chloe"]
ENGLISH_MALE = ["James", "Oliver", "Harry", "George", "Thomas", "William", "Daniel", "Samuel"]
ENGLISH_LAST = ["Smith", "Taylor", "Brown", "Wilson", "Evans", "Walker", "Clarke", "Hughes", "Edwards", "Turner"]

#: Each reader's main interest, and how many have it. Sums to the total; each
#: stays under the send cap, so an edition to one interest fits one send.
MAIN_INTERESTS = {
    "Wandern": 180, "Wintersport": 170, "Klettern": 140, "Familie & Kinder": 130, "Radfahren": 120,
    "Naturerlebnis": 100, "Camping & Trekking": 70, "Sicherheit & Wissen": 50, "Nachhaltigkeit": 40,
}
#: The subcategories a reader of each main interest may also like.
SUBS_OF = {
    "Wandern": ["Tagestouren", "Hüttentouren", "Weitwandern", "Klettersteige", "Familienwandern"],
    "Wintersport": ["Skitouren", "Schneeschuh", "Langlauf", "Lawinenkunde"],
    "Klettern": ["Halle & Bouldern", "Alpinklettern", "Klettersteige"],
    "Familie & Kinder": ["Familienwandern", "Tierbeobachtung"],
    "Radfahren": ["Gravel & Trekking", "Mountainbike"],
    "Naturerlebnis": ["Tierbeobachtung", "Weitwandern"],
    "Camping & Trekking": ["Biwak", "Weitwandern"],
    "Sicherheit & Wissen": ["Erste Hilfe", "Lawinenkunde"],
    "Nachhaltigkeit": ["Reparieren & Second Hand"],
}
TOTAL = sum(MAIN_INTERESTS.values())


def _ascii(value: str) -> str:
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("Ä", "ae"), ("Ö", "oe"), ("Ü", "ue")):
        value = value.replace(a, b)
    return value.lower().replace(" ", "")


def create_readers(db: Session, *, outdoor_id: int, touren_id: int, category_ids: dict[str, int],
                   now: datetime | None = None, rng: random.Random | None = None) -> dict[str, list]:
    """The readers, their consent and addresses, and their stated interests
    (manual contributions, as a preference centre would write them).
    {main interest: [recipient]}."""
    from app.recipients.db_models import AddressabilityDB, ConsentEventDB, RecipientDB, SignalContributionDB

    rng = rng or random.Random(71)
    now = now or datetime.now(timezone.utc)
    mains = [name for name, count in MAIN_INTERESTS.items() for _ in range(count)]
    rng.shuffle(mains)
    by_interest: dict[str, list] = {name: [] for name in MAIN_INTERESTS}
    for i, main in enumerate(mains, start=1):
        english = rng.random() < 0.15
        female = rng.random() < 0.5
        first = rng.choice((ENGLISH_FEMALE if female else ENGLISH_MALE) if english else (FEMALE if female else MALE))
        last = rng.choice(ENGLISH_LAST if english else LAST)
        gender = None if i % 13 == 0 else ("diverse" if i % 47 == 0 else ("female" if female else "male"))
        reader = RecipientDB(external_id=f"grathaus-{i:04d}", language="en" if english else "de", attributes={},
                             first_name=first, last_name=None if i % 19 == 0 else last, gender=gender,
                             status="active")
        db.add(reader)
        db.flush()
        db.add(AddressabilityDB(recipient_id=reader.id, channel="email", status="active", is_primary=True,
                                value={"email": f"{_ascii(first)}.{_ascii(last)}.{i}@example.com"}))
        # Nearly everyone said yes to Outdoor's newsletter; a third to Touren's.
        if i % 25 != 0:
            db.add(ConsentEventDB(recipient_id=reader.id, brand_id=outdoor_id, channel="email",
                                  purpose="marketing", status="opted_in", source="demo",
                                  note="Grathaus demo (task-71)"))
        if i % 3 == 0:
            db.add(ConsentEventDB(recipient_id=reader.id, brand_id=touren_id, channel="email",
                                  purpose="marketing", status="opted_in", source="demo",
                                  note="Grathaus demo (task-71)"))
        # The app users among them: push consent and a device.
        if i % 4 == 0:
            db.add(ConsentEventDB(recipient_id=reader.id, brand_id=outdoor_id, channel="push",
                                  purpose="marketing", status="opted_in", source="demo",
                                  note="Grathaus demo (task-71)"))
            db.add(AddressabilityDB(recipient_id=reader.id, channel="push", status="active", is_primary=True,
                                    value={"token": f"grathaus-device-{i:04d}",
                                           "platform": "apns" if i % 8 == 0 else "fcm"}))
        db.add(SignalContributionDB(recipient_id=reader.id, category_id=category_ids[main],
                                    contribution_type="manual", base_weight=float(rng.randint(55, 95)),
                                    occurred_at=now - timedelta(days=rng.randint(30, 400)), source="demo"))
        for sub in rng.sample(SUBS_OF[main], k=min(len(SUBS_OF[main]), rng.randint(0, 2))):
            db.add(SignalContributionDB(recipient_id=reader.id, category_id=category_ids[sub],
                                        contribution_type="manual", base_weight=float(rng.randint(25, 70)),
                                        occurred_at=now - timedelta(days=rng.randint(10, 300)), source="demo"))
        by_interest[main].append(reader)
        if i % 200 == 0:
            db.commit()
    db.commit()
    return by_interest
