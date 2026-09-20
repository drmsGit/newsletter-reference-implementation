from sqlalchemy.exc import IntegrityError
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
from app.overrides.db_models import ContentOverrideDB


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


def get_content_record(
    db: Session, content_id: int, *, brand_id: int
) -> ContentRecordDB | None:
    """One content record, **selected** within a brand (ADR-172 points 4-6).

    The brand is part of the query rather than a check after it: a record
    belonging to another brand is not found, rather than found and then
    refused. There is no moment where the row is in hand and something still
    has to remember to say no.

    Keyword-only and without a default, because this function took no brand at
    all until 2026-09-19 and could not be scoped by its callers even when they
    wanted to. A positional would have let an existing argument slide into the
    slot; a default would have reintroduced the thing being removed.
    """
    return (
        db.query(ContentRecordDB)
        .filter(
            ContentRecordDB.id == content_id,
            ContentRecordDB.brand_id == brand_id,
        )
        .first()
    )


# **The category vocabulary is deliberately NOT brand-scoped, and this file is
# therefore deliberately swept in half.** ADR-150's 2026-09-15 addendum: the
# vocabulary is global, and `content_category_assignments` carries no
# `brand_id` because it hangs off `content_records` and is per-brand
# transitively. So `list_categories`, `create_category`, `delete_category` and
# the four relation functions take no brand and must not be "fixed" to take
# one — ADR-172 point 5 refuses new brand columns on exactly this reasoning.
#
# Said here because a sweep that changes ten functions in a file and leaves
# eight alone reads as an oversight to the next person, and the next person
# will be right to check.

# Content lifecycle statuses. Deliberately only two: deactivation exists to stop a
# record being *newly selected* without breaking anything that already references
# it. A richer vocabulary (e.g. "archived") belongs to the general data-lifecycle
# ADR rather than being invented here — see docs/backlog.md.
CONTENT_STATUSES = ("active", "inactive")


#: The channel field groups a caller can claim authority over.
#:
#: **A caller may only clear what it was offering.** That is the whole rule,
#: and it exists because an absent field and a cleared one are indistinguishable
#: otherwise: a screen rendered with push switched off sends no push fields, and
#: rebuilding `content` from what arrived would erase push copy on every edit
#: made while push was off. The Jinja form carries the same signal as
#: `channel_sections_present`; the JSON plane carries it as `groups`.
#:
#: Declared here rather than derived from the channel manifests, which is where
#: it belongs and is not cheap today: the manifests describe modules and their
#: templates, not a flat list of the content keys a channel reads. When that
#: list exists, this table should read from it rather than repeat it.
CONTENT_FIELD_GROUPS: dict[str, tuple[str, ...]] = {
    "email": (
        "headline_medium", "body_medium",
        "button_label", "button_url",
        "image_url", "image_alt",
    ),
    "push": ("push_title", "push_body", "push_image_url", "push_link"),
}

#: Groups where an EMPTY value means "remove the key", not "store an empty one".
#:
#: ADR-161 point 7's rider makes catalogue readiness exactly "push fields not
#: empty", so a stored `""` would leave every record looking push-ready — the
#: difference between "not prepared for push" and "prepared with nothing in
#: it". Email carries no such predicate, so an empty string there is merely an
#: empty string and is stored as written.
#:
#: This asymmetry is deliberate and was preserved rather than tidied when the
#: rule moved out of the router: unifying on "always remove" would be simpler
#: and would change what `create_content` and the render path see, which is a
#: separate decision from where the rule lives.
PRESENCE_SIGNIFICANT_GROUPS = frozenset({"push"})


def merge_content_fields(
    existing: dict | None, incoming: dict, *, groups: list[str],
) -> dict:
    """Merge submitted fields onto stored content, honouring what was offered.

    `groups` names the field groups the caller is authoritative for. A key in a
    group that was not offered is left exactly as it was found; a key in an
    offered group is written, or removed when the group is presence-significant
    and the value is empty. Keys in no group at all are always preserved —
    content is an open dict and a merge must not be a silent schema.

    Pure: takes dicts and returns a new one, so the rule can be tested without
    a database or a request. It was reachable only through a form until
    2026-09-20, which is why a JSON client could not have honoured it.
    """
    merged = dict(existing or {})
    for group in groups:
        fields = CONTENT_FIELD_GROUPS.get(group)
        if fields is None:
            raise ValueError(
                f"'{group}' is not a content field group. Known groups: "
                f"{', '.join(sorted(CONTENT_FIELD_GROUPS))}."
            )
        presence_significant = group in PRESENCE_SIGNIFICANT_GROUPS
        for name in fields:
            if name not in incoming:
                continue
            value = incoming[name]
            if not presence_significant:
                # Stored as written. **Not stripped**, because it was not
                # stripped before this rule moved out of the router and moving
                # a rule is not the moment to change it. Whether email copy
                # should be trimmed is a real question and a separate one.
                merged[name] = value
                continue
            text = value.strip() if isinstance(value, str) else value
            if not text:
                merged.pop(name, None)
            else:
                merged[name] = text
    return merged


def update_content_record(
    db: Session,
    content_id: int,
    title: str,
    content: dict,
    description: str | None = None,
    *,
    brand_id: int,
) -> ContentRecord | None:
    # `status` is intentionally not updatable here — editing a record must not be
    # able to silently reactivate it. Use set_content_status().
    record = get_content_record(db, content_id, brand_id=brand_id)
    if record is None:
        return None
    record.title = title
    record.description = description
    record.content = content
    db.commit()
    db.refresh(record)
    return to_content_record(record)


def set_content_status(
    db: Session,
    content_id: int,
    status: str,
    *,
    brand_id: int,
) -> ContentRecord | None:
    """Activate or deactivate a content record.

    Deactivating is the safe alternative to deleting: the record keeps its id, so
    module instances, decision resolutions and snapshots that already point at it
    still render, while the decision strategies (which filter on
    `status == "active"`) stop resolving to it and the module content picker stops
    offering it.
    """
    if status not in CONTENT_STATUSES:
        raise ValueError(
            f"Unknown content status '{status}'. "
            f"Expected one of: {', '.join(CONTENT_STATUSES)}"
        )
    record = get_content_record(db, content_id, brand_id=brand_id)
    if record is None:
        return None
    record.status = status
    db.commit()
    db.refresh(record)
    return to_content_record(record)


def list_content_records(db: Session, *, brand_id: int) -> list[ContentRecord]:
    """Content records for one brand (ADR-150 point 2, ADR-172 point 4).

    **The brand was optional until 2026-09-19 and defaulted to every brand.**
    A forgotten argument did not fail; it returned the whole platform. The
    JSON routers forgot it at every call site, which is how `GET /content/`
    came to serve every brand's records to anybody who could authenticate.

    Callers that genuinely span brands — platform counts, migrations, seeds —
    want `list_all_content_records`, which says so in its name.
    """
    return [
        to_content_record(record)
        for record in db.query(ContentRecordDB)
        .filter(ContentRecordDB.brand_id == brand_id)
        .all()
    ]


def list_all_content_records(db: Session) -> list[ContentRecord]:
    """Every content record, across every brand.

    The escape hatch ADR-172 point 4 owes to the callers that legitimately have
    no working brand: a platform-wide count, a migration, a seed, a test.
    Deliberately ugly to reach for, and counted — `test_brand_boundary.py`
    asserts the set of `list_all_*` functions exactly, so a fourth is an edit
    somebody has to justify rather than a convenience that arrives while
    somebody was fixing something else.

    **Not for routes.** Every request has a working brand (point 1), so a
    router calling this is not a caller that spans brands; it is one that had a
    brand and did not use it. A test asserts no router mentions it.
    """
    return [to_content_record(record) for record in db.query(ContentRecordDB).all()]


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


def list_categories_for_content(
    db: Session, content_id: int, *, brand_id: int
) -> list[Category]:
    """The categories assigned to one record, within a brand.

    The assignment row carries no `brand_id` and does not need one — ADR-150's
    2026-09-15 addendum: it hangs off `content_records`, so which content is
    Beach is already per-brand transitively. ADR-172 point 5 is that principle
    turned into a join: the chain `assignment -> content_record -> brand` is
    walked in the selecting query, so a record in another brand yields an empty
    list exactly as a record with no categories does.
    """
    category_records = (
        db.query(CategoryDB)
        .join(
            ContentCategoryAssignmentDB,
            CategoryDB.id == ContentCategoryAssignmentDB.category_id,
        )
        .join(
            ContentRecordDB,
            ContentRecordDB.id == ContentCategoryAssignmentDB.content_id,
        )
        .filter(
            ContentCategoryAssignmentDB.content_id == content_id,
            ContentRecordDB.brand_id == brand_id,
        )
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

    # Content carries a NOT NULL brand since ADR-150 point 2, so the default
    # brand must already exist. `main.py` calls `bootstrap_auth` before this
    # for that reason — the reverse order was harmless until 2026-09-15 and is
    # now a crash on first boot against an empty database.
    from app.auth.service import ensure_default_brand

    brand_id = ensure_default_brand(db).id

    mallorca = ContentRecordDB(
        title="Mallorca Beach Walk",
        description="A reusable content record about beach walks in Mallorca.",
        content={
            "headline_medium": "Mallorca Beach Walk",
            "body_medium": "A reusable content record about beach walks in Mallorca.",
            "button_label": "Read more",
        },
        status="active",
        brand_id=brand_id,
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
        brand_id=brand_id,
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
        brand_id=brand_id,
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
    brand_id: int,
    description: str | None = None,
) -> ContentRecord:

    record = ContentRecordDB(
        title=title,
        description=description,
        content=content,
        status="active",
        brand_id=brand_id,
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
    *,
    brand_id: int,
) -> ContentCategoryAssignmentDB | None:
    """Assign a category to a content record.

    **The category is not brand-owned and the record is.** The vocabulary is
    global by ADR-150's 2026-09-15 addendum, so `category_id` is checked
    against nothing here; `content_id` is the brand-owned half and is resolved
    through the scoped getter.
    """
    # A score of exactly zero is degenerate/meaningless — "no relevance"
    # should mean no assignment row at all, not a stored zero. (The 0-10
    # range itself is a POC-only convention, not enforced here — that's
    # future config-layer work, Insight Q2.)
    if score == 0:
        raise ValueError("Category assignment score must not be zero — omit the assignment instead")

    if get_content_record(db, content_id, brand_id=brand_id) is None:
        return None

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
    try:
        db.commit()
    except IntegrityError:
        # A concurrent call won the TOCTOU race between the SELECT above and
        # this insert — the unique constraint caught it. Answer exactly as the
        # fast path does, so a caller cannot tell whether it lost a race or
        # simply asked for an assignment that already existed. Same shape as
        # `add_member` in audience/service.py.
        db.rollback()
        return None
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
    *,
    brand_id: int,
) -> ContentVersion | None:
    """Freezes the record's current `content` into an immutable version (ADR-128)."""
    record = get_content_record(db, content_record_id, brand_id=brand_id)
    if record is None:
        return None

    # Read-then-insert, so two concurrent publishes can compute the same next
    # number. The unique constraint now refuses the second rather than storing
    # a duplicate — retry, because the conflict means somebody else published
    # while we were deciding, and their version is simply the earlier one.
    #
    # Bounded rather than a `while True`: a retry that never terminates turns a
    # constraint violation into a hung request. Three attempts is far beyond
    # what a manual publish click can contend with, and if it is ever exceeded
    # the IntegrityError surfaces — which is the honest outcome, because at that
    # point something other than ordinary contention is wrong.
    for attempt in range(3):
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
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            if attempt == 2:
                raise
            continue
        db.refresh(version)
        return to_content_version(version)


def list_versions_for_content(
    db: Session,
    content_record_id: int,
    *,
    brand_id: int,
) -> list[ContentVersion]:
    records = (
        db.query(ContentVersionDB)
        .join(
            ContentRecordDB,
            ContentRecordDB.id == ContentVersionDB.content_record_id,
        )
        .filter(
            ContentVersionDB.content_record_id == content_record_id,
            ContentRecordDB.brand_id == brand_id,
        )
        .order_by(ContentVersionDB.version_number.desc())
        .all()
    )

    return [to_content_version(record) for record in records]


def get_latest_version_for_content(
    db: Session,
    content_record_id: int,
    *,
    brand_id: int,
) -> ContentVersion | None:
    record = (
        db.query(ContentVersionDB)
        .join(
            ContentRecordDB,
            ContentRecordDB.id == ContentVersionDB.content_record_id,
        )
        .filter(
            ContentVersionDB.content_record_id == content_record_id,
            ContentRecordDB.brand_id == brand_id,
        )
        .order_by(ContentVersionDB.version_number.desc())
        .first()
    )

    if record is None:
        return None

    return to_content_version(record)


def delete_content_record(
    db: Session, content_id: int, force: bool = False, *, brand_id: int
) -> bool:
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
    record = get_content_record(db, content_id, brand_id=brand_id)
    if record is None:
        return False

    resolution_count = (
        db.query(DecisionResolutionDB)
        .filter(DecisionResolutionDB.content_record_id == content_id)
        .count()
    )
    override_count = (
        db.query(ContentOverrideDB)
        .filter(ContentOverrideDB.system_content_record_id == content_id)
        .count()
    )
    if resolution_count or override_count:
        raise ContentRecordHasHistoryError(
            f"Content record {content_id} has real history — "
            f"{resolution_count} decision resolution(s), {override_count} content override(s) "
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