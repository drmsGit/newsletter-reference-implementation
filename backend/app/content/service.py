from sqlalchemy.orm import Session

from app.campaigns.db_models import ModuleInstanceDB, DecisionResolutionDB
from app.content.db_models import (
    ContentRecordDB,
    CategoryDB,
    CategoryRelationDB,
    ContentCategoryAssignmentDB,
    ContentVersionDB,
)
from app.content.models import ContentRecord, Category, CategoryRelation, ContentVersion
from app.overrides.db_models import OverrideEventDB


class ContentRecordHasHistoryError(Exception):
    """
    Hard block, never bypassable — the content record has real decision or
    override history. Hard-deleting it would corrupt that audit trail, so
    unlike the soft/reassignable relations below, no force flag overrides
    this (consistent with the "never hard-delete anything with historical
    usage" leaning in the still-open data-lifecycle Needs-ADR item).
    """


class HasRelationsError(Exception):
    """Soft block — reassignable relations exist; force=True bypasses."""

    def __init__(self, message: str, counts: dict[str, int]):
        self.counts = counts
        super().__init__(message)


def to_content_record(record: ContentRecordDB) -> ContentRecord:
    return ContentRecord(
        id=record.id,
        title=record.title,
        description=record.description,
        content=record.content or {},
        status=record.status,
    )


def get_content_record(db: Session, content_id: int) -> ContentRecordDB | None:
    return db.query(ContentRecordDB).filter(ContentRecordDB.id == content_id).first()


def update_content_record(
    db: Session,
    content_id: int,
    title: str,
    content: dict,
    description: str | None = None,
) -> ContentRecord | None:
    record = get_content_record(db, content_id)
    if record is None:
        return None
    record.title = title
    record.description = description
    record.content = content
    db.commit()
    db.refresh(record)
    return to_content_record(record)


def list_content_records(db: Session) -> list[ContentRecord]:
    records = db.query(ContentRecordDB).all()

    return [to_content_record(record) for record in records]


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
        description="A reusable content record about beach walks in Mallorca.",
        content={
            "headline_medium": "Mallorca Beach Walk",
            "body_medium": "A reusable content record about beach walks in Mallorca.",
            "button_label": "Read more",
        },
        status="active",
    )
    rome = ContentRecordDB(
        title="Rome City Weekend",
        description="A reusable content record about a cultural weekend in Rome.",
        content={
            "headline_medium": "Rome City Weekend",
            "body_medium": "A reusable content record about a cultural weekend in Rome.",
            "button_label": "Read more",
        },
        status="active",
    )
    tenerife = ContentRecordDB(
        title="Tenerife Nature Escape",
        description="A reusable content record about nature experiences on Tenerife.",
        content={
            "headline_medium": "Tenerife Nature Escape",
            "body_medium": "A reusable content record about nature experiences on Tenerife.",
            "button_label": "Read more",
        },
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
    content: dict,
    description: str | None = None,
) -> ContentRecord:

    record = ContentRecordDB(
        title=title,
        description=description,
        content=content,
        status="active",
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return to_content_record(record)

def create_category(
    db: Session,
    name: str,
    type: str = "main",
) -> Category:
    category = CategoryDB(
        name=name,
        type=type,
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return Category(
        id=category.id,
        name=category.name,
        type=category.type,
    )


def to_category_relation(record: CategoryRelationDB) -> CategoryRelation:
    return CategoryRelation(
        id=record.id,
        parent_category_id=record.parent_category_id,
        child_category_id=record.child_category_id,
        relation_type=record.relation_type,
        created_at=record.created_at,
    )


def _would_create_cycle(db: Session, parent_category_id: int, child_category_id: int) -> bool:
    """
    True if adding parent_category_id -> child_category_id would close a
    direct or transitive parent_child loop — i.e. parent_category_id is
    already reachable by walking down existing child edges starting at
    child_category_id. Multi-parent taxonomies stay fully allowed; only an
    actual cycle is rejected.
    """
    if parent_category_id == child_category_id:
        return True

    visited: set[int] = set()
    stack = [child_category_id]

    while stack:
        current = stack.pop()
        if current == parent_category_id:
            return True
        if current in visited:
            continue
        visited.add(current)

        children = (
            db.query(CategoryRelationDB.child_category_id)
            .filter(CategoryRelationDB.parent_category_id == current)
            .all()
        )
        stack.extend(row[0] for row in children)

    return False


def create_category_relation(
    db: Session,
    parent_category_id: int,
    child_category_id: int,
    relation_type: str = "parent_child",
) -> CategoryRelation:
    if relation_type == "parent_child" and _would_create_cycle(db, parent_category_id, child_category_id):
        raise ValueError(
            f"Relating category {parent_category_id} as parent of {child_category_id} "
            "would create a parent_child cycle"
        )

    relation = CategoryRelationDB(
        parent_category_id=parent_category_id,
        child_category_id=child_category_id,
        relation_type=relation_type,
    )

    db.add(relation)
    db.commit()
    db.refresh(relation)

    return to_category_relation(relation)


def list_category_relations(db: Session) -> list[CategoryRelation]:
    records = db.query(CategoryRelationDB).all()

    return [to_category_relation(record) for record in records]


def list_parent_relations_for_category(
    db: Session,
    child_category_id: int,
) -> list[CategoryRelation]:
    records = (
        db.query(CategoryRelationDB)
        .filter(CategoryRelationDB.child_category_id == child_category_id)
        .all()
    )

    return [to_category_relation(record) for record in records]


def list_child_relations_for_category(
    db: Session,
    parent_category_id: int,
) -> list[CategoryRelation]:
    records = (
        db.query(CategoryRelationDB)
        .filter(CategoryRelationDB.parent_category_id == parent_category_id)
        .all()
    )

    return [to_category_relation(record) for record in records]


def delete_category_relation(db: Session, relation_id: int) -> bool:
    relation = db.query(CategoryRelationDB).filter(CategoryRelationDB.id == relation_id).first()
    if relation is None:
        return False
    db.delete(relation)
    db.commit()
    return True


def delete_category_assignment(db: Session, assignment_id: int) -> bool:
    assignment = db.query(ContentCategoryAssignmentDB).filter(ContentCategoryAssignmentDB.id == assignment_id).first()
    if assignment is None:
        return False
    db.delete(assignment)
    db.commit()
    return True


def assign_category_to_content(
    db: Session,
    content_id: int,
    category_id: int,
    score: int = 10,
) -> ContentCategoryAssignmentDB | None:
    # A score of exactly zero is degenerate/meaningless — "no relevance"
    # should mean no assignment row at all, not a stored zero. (The 0-10
    # range itself is a POC-only convention, not enforced here — that's
    # future config-layer work, Insight Q2.)
    if score == 0:
        raise ValueError("Category assignment score must not be zero — omit the assignment instead")

    existing = (
        db.query(ContentCategoryAssignmentDB)
        .filter(
            ContentCategoryAssignmentDB.content_id == content_id,
            ContentCategoryAssignmentDB.category_id == category_id,
        )
        .first()
    )
    if existing is not None:
        return None

    assignment = ContentCategoryAssignmentDB(
        content_id=content_id,
        category_id=category_id,
        score=score,
    )

    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return assignment


def to_content_version(record: ContentVersionDB) -> ContentVersion:
    return ContentVersion(
        id=record.id,
        content_record_id=record.content_record_id,
        version_number=record.version_number,
        content=record.content,
        created_by=record.created_by,
        created_at=record.created_at,
    )


def create_content_version(
    db: Session,
    content_record_id: int,
    created_by: str | None = None,
) -> ContentVersion | None:
    """Freezes the record's current `content` into an immutable version (ADR-128)."""
    record = get_content_record(db, content_record_id)
    if record is None:
        return None

    latest_version = (
        db.query(ContentVersionDB)
        .filter(ContentVersionDB.content_record_id == content_record_id)
        .order_by(ContentVersionDB.version_number.desc())
        .first()
    )

    next_version_number = (
        latest_version.version_number + 1
        if latest_version
        else 1
    )

    version = ContentVersionDB(
        content_record_id=content_record_id,
        version_number=next_version_number,
        content=record.content or {},
        created_by=created_by,
    )

    db.add(version)
    db.commit()
    db.refresh(version)

    return to_content_version(version)


def list_versions_for_content(
    db: Session,
    content_record_id: int,
) -> list[ContentVersion]:
    records = (
        db.query(ContentVersionDB)
        .filter(ContentVersionDB.content_record_id == content_record_id)
        .order_by(ContentVersionDB.version_number.desc())
        .all()
    )

    return [to_content_version(record) for record in records]


def get_latest_version_for_content(
    db: Session,
    content_record_id: int,
) -> ContentVersion | None:
    record = (
        db.query(ContentVersionDB)
        .filter(ContentVersionDB.content_record_id == content_record_id)
        .order_by(ContentVersionDB.version_number.desc())
        .first()
    )

    if record is None:
        return None

    return to_content_version(record)


def delete_content_record(db: Session, content_id: int, force: bool = False) -> bool:
    """
    Deleting a content record that still has relations must not silently
    cascade. Decision-resolution / override history is a hard block (never
    force-deletable — that data stays put, per the data-lifecycle Needs-ADR
    leaning). Category assignments, versions, and module instances are
    reassignable relations: without force, this raises HasRelationsError
    with counts so a manager can re-parent/re-assign first; with force=True,
    assignments and versions are cascade-deleted and any module instance
    pointing at this record has content_record_id cleared (the module slot
    survives as empty rather than campaign structure being destroyed).
    """
    record = get_content_record(db, content_id)
    if record is None:
        return False

    resolution_count = (
        db.query(DecisionResolutionDB)
        .filter(DecisionResolutionDB.content_record_id == content_id)
        .count()
    )
    override_count = (
        db.query(OverrideEventDB)
        .filter(
            (OverrideEventDB.system_content_record_id == content_id)
            | (OverrideEventDB.override_content_record_id == content_id)
        )
        .count()
    )
    if resolution_count or override_count:
        raise ContentRecordHasHistoryError(
            f"Content record {content_id} has real history — "
            f"{resolution_count} decision resolution(s), {override_count} override event(s) "
            "— and can never be deleted, only its future use prevented."
        )

    assignment_count = (
        db.query(ContentCategoryAssignmentDB)
        .filter(ContentCategoryAssignmentDB.content_id == content_id)
        .count()
    )
    version_count = (
        db.query(ContentVersionDB)
        .filter(ContentVersionDB.content_record_id == content_id)
        .count()
    )
    module_count = (
        db.query(ModuleInstanceDB)
        .filter(ModuleInstanceDB.content_record_id == content_id)
        .count()
    )

    if (assignment_count or version_count or module_count) and not force:
        raise HasRelationsError(
            f"Content record {content_id} is related to {assignment_count} category "
            f"assignment(s), {version_count} version(s), and used by {module_count} "
            "module instance(s) — delete anyway?",
            counts={
                "category_assignments": assignment_count,
                "versions": version_count,
                "module_instances": module_count,
            },
        )

    db.query(ContentCategoryAssignmentDB).filter(
        ContentCategoryAssignmentDB.content_id == content_id
    ).delete()
    db.query(ContentVersionDB).filter(
        ContentVersionDB.content_record_id == content_id
    ).delete()
    db.query(ModuleInstanceDB).filter(
        ModuleInstanceDB.content_record_id == content_id
    ).update({ModuleInstanceDB.content_record_id: None})

    db.delete(record)
    db.commit()
    return True


def delete_category(db: Session, category_id: int, force: bool = False) -> bool:
    """
    Same confirmation-guard shape as delete_content_record, scoped to a
    category's relations: content assignments and parent/child hierarchy
    edges. Categories have no direct decision/override history of their own
    (that history references content records, not categories), so there's
    no hard-block case here — force=True always suffices.
    """
    category = db.query(CategoryDB).filter(CategoryDB.id == category_id).first()
    if category is None:
        return False

    assignment_count = (
        db.query(ContentCategoryAssignmentDB)
        .filter(ContentCategoryAssignmentDB.category_id == category_id)
        .count()
    )
    relation_count = (
        db.query(CategoryRelationDB)
        .filter(
            (CategoryRelationDB.parent_category_id == category_id)
            | (CategoryRelationDB.child_category_id == category_id)
        )
        .count()
    )

    if (assignment_count or relation_count) and not force:
        raise HasRelationsError(
            f"Category {category_id} is related to {assignment_count} content "
            f"assignment(s) and {relation_count} parent/child relation(s) — delete anyway?",
            counts={
                "content_assignments": assignment_count,
                "category_relations": relation_count,
            },
        )

    db.query(ContentCategoryAssignmentDB).filter(
        ContentCategoryAssignmentDB.category_id == category_id
    ).delete()
    db.query(CategoryRelationDB).filter(
        (CategoryRelationDB.parent_category_id == category_id)
        | (CategoryRelationDB.child_category_id == category_id)
    ).delete()

    db.delete(category)
    db.commit()
    return True