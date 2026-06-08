from sqlalchemy.orm import Session

from app.content.db_models import (
    ContentRecordDB,
    CategoryDB,
    ContentCategoryAssignmentDB,
)
from app.content.models import ContentRecord, Category


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


def list_categories(db: Session) -> list[Category]:
    records = db.query(CategoryDB).all()

    return [
        Category(
            id=record.id,
            name=record.name,
            type=record.type,
        )
        for record in records
    ]


def list_categories_for_content(db: Session, content_id: int) -> list[Category]:
    category_records = (
        db.query(CategoryDB)
        .join(
            ContentCategoryAssignmentDB,
            CategoryDB.id == ContentCategoryAssignmentDB.category_id,
        )
        .filter(ContentCategoryAssignmentDB.content_id == content_id)
        .all()
    )

    return [
        Category(
            id=category.id,
            name=category.name,
            type=category.type,
        )
        for category in category_records
    ]


def create_demo_content_if_empty(db: Session) -> None:
    existing_count = db.query(ContentRecordDB).count()

    if existing_count > 0:
        return

    mallorca = ContentRecordDB(
        title="Mallorca Beach Walk",
        body="A reusable content record about beach walks in Mallorca.",
        status="active",
    )
    rome = ContentRecordDB(
        title="Rome City Weekend",
        body="A reusable content record about a cultural weekend in Rome.",
        status="active",
    )
    tenerife = ContentRecordDB(
        title="Tenerife Nature Escape",
        body="A reusable content record about nature experiences on Tenerife.",
        status="active",
    )

    beach = CategoryDB(name="Beach", type="main")
    city = CategoryDB(name="City", type="main")
    nature = CategoryDB(name="Nature", type="main")

    db.add_all([mallorca, rome, tenerife, beach, city, nature])
    db.commit()

    assignments = [
        ContentCategoryAssignmentDB(content_id=mallorca.id, category_id=beach.id, score=10),
        ContentCategoryAssignmentDB(content_id=rome.id, category_id=city.id, score=10),
        ContentCategoryAssignmentDB(content_id=tenerife.id, category_id=nature.id, score=10),
        ContentCategoryAssignmentDB(content_id=tenerife.id, category_id=beach.id, score=5),
    ]

    db.add_all(assignments)
    db.commit()

def create_content(
    db: Session,
    title: str,
    body: str,
) -> ContentRecord:

    record = ContentRecordDB(
        title=title,
        body=body,
        status="active",
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return ContentRecord(
        id=record.id,
        title=record.title,
        body=record.body,
        status=record.status,
    )

def create_category(
    db: Session,
    name: str,
    type: str = "main",
    parent_category_id: int | None = None,
) -> Category:
    category = CategoryDB(
        name=name,
        type=type,
        parent_category_id=parent_category_id,
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return Category(
        id=category.id,
        name=category.name,
        type=category.type,
        parent_category_id=category.parent_category_id,
    )


def assign_category_to_content(
    db: Session,
    content_id: int,
    category_id: int,
    score: int = 10,
) -> ContentCategoryAssignmentDB:
    assignment = ContentCategoryAssignmentDB(
        content_id=content_id,
        category_id=category_id,
        score=score,
    )

    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return assignment