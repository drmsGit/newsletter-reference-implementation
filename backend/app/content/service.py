from app.content.models import ContentRecord, Category, ContentCategoryAssignment


CONTENT_RECORDS = [
    ContentRecord(
        id=1,
        title="Mallorca Beach Walk",
        body="A reusable content record about beach walks in Mallorca.",
    ),
    ContentRecord(
        id=2,
        title="Rome City Weekend",
        body="A reusable content record about a cultural weekend in Rome.",
    ),
    ContentRecord(
        id=3,
        title="Tenerife Nature Escape",
        body="A reusable content record about nature experiences on Tenerife.",
    ),
]


CATEGORIES = [
    Category(id=1, name="Beach", type="main"),
    Category(id=2, name="City", type="main"),
    Category(id=3, name="Nature", type="main"),
]


CONTENT_CATEGORY_ASSIGNMENTS = [
    ContentCategoryAssignment(content_id=1, category_id=1, score=10),
    ContentCategoryAssignment(content_id=2, category_id=2, score=10),
    ContentCategoryAssignment(content_id=3, category_id=3, score=10),
    ContentCategoryAssignment(content_id=3, category_id=1, score=5),
]


def list_content_records() -> list[ContentRecord]:
    return CONTENT_RECORDS


def list_categories() -> list[Category]:
    return CATEGORIES


def list_categories_for_content(content_id: int) -> list[Category]:
    category_ids = [
        assignment.category_id
        for assignment in CONTENT_CATEGORY_ASSIGNMENTS
        if assignment.content_id == content_id
    ]

    return [
        category
        for category in CATEGORIES
        if category.id in category_ids
    ]