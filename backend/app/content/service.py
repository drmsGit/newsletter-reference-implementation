from sqlalchemy.orm import Session

from app.content.db_models import ContentRecordDB
from app.content.models import ContentRecord


def list_content_records(db: Session) -> list[ContentRecord]:
    records = db.query(ContentRecordDB).all()

    return [
        ContentRecord(
            id=record.id,
            title=record.title,
            body=record.body,
            status=record.status,
        )
        for record in records
    ]


def create_demo_content_if_empty(db: Session) -> None:
    existing_count = db.query(ContentRecordDB).count()

    if existing_count > 0:
        return

    demo_records = [
        ContentRecordDB(
            title="Mallorca Beach Walk",
            body="A reusable content record about beach walks in Mallorca.",
            status="active",
        ),
        ContentRecordDB(
            title="Rome City Weekend",
            body="A reusable content record about a cultural weekend in Rome.",
            status="active",
        ),
        ContentRecordDB(
            title="Tenerife Nature Escape",
            body="A reusable content record about nature experiences on Tenerife.",
            status="active",
        ),
    ]

    db.add_all(demo_records)
    db.commit()