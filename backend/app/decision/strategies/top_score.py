from sqlalchemy.orm import Session

from app.campaigns.db_models import DecisionSlotDB
from app.campaigns.models import DecisionResolution
from app.campaigns.service import create_decision_resolution
from app.content.db_models import (
    ContentCategoryAssignmentDB,
    ContentRecordDB,
)
from app.decision.strategies.base import DecisionStrategy


class TopScoreStrategy(DecisionStrategy):

    def execute(
        self,
        db: Session,
        slot: DecisionSlotDB,
    ) -> DecisionResolution:
        candidate_filter = slot.candidate_filter or {}
        category_ids = candidate_filter.get("category_ids", [])

        query = (
            db.query(ContentRecordDB, ContentCategoryAssignmentDB.score)
            .join(
                ContentCategoryAssignmentDB,
                ContentRecordDB.id == ContentCategoryAssignmentDB.content_id,
            )
            .filter(ContentRecordDB.status == "active")
        )

        if category_ids:
            query = query.filter(
                ContentCategoryAssignmentDB.category_id.in_(category_ids)
            )

        result = (
            query.order_by(
                ContentCategoryAssignmentDB.score.desc(),
                ContentRecordDB.id.asc(),
            )
            .first()
        )

        if result is None:
            raise ValueError("No matching content record found")

        content_record, score = result

        return create_decision_resolution(
            db=db,
            decision_slot_id=slot.id,
            content_record_id=content_record.id,
            reason=f"Selected by top_score strategy for category_ids={category_ids}",
            score=score,
        )