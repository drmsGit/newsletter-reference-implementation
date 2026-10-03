from sqlalchemy.orm import Session

from app.campaigns.db_models import DecisionSlotDB
from app.content.db_models import ContentCategoryAssignmentDB, ContentRecordDB
from app.content.service import get_latest_version_for_content
from app.decision.strategies.base import (
    ConfigField, DecisionStrategy, StrategyMeta, StrategyResult, candidate_query, sending_brand_id,
)


class TopScoreStrategy(DecisionStrategy):

    @property
    def meta(self) -> StrategyMeta:
        return StrategyMeta(
            name="top_score",
            label="Top Score",
            description=(
                "Selects the highest-scored content record across all "
                "candidates in the allowed categories. No recipient context needed."
            ),
            requires_recipient=False,
            candidate_filter_fields=[
                ConfigField(
                    name="category_ids",
                    type="list[int]",
                    default=[],
                    description="Restrict candidates to these category IDs (empty = all).",
                ),
            ],
            config_fields=[],
        )

    def execute(
        self,
        db: Session,
        slot: DecisionSlotDB,
        recipient_id: int | None = None,
    ) -> StrategyResult | None:
        candidate_filter = slot.candidate_filter or {}
        category_ids = candidate_filter.get("category_ids", [])

        # Resolved once and reused: it filters the candidates below AND scopes
        # the version lookup further down, which must agree with it. Two calls
        # would be two chances for them to disagree.
        brand_id = sending_brand_id(db, slot)

        query = candidate_query(db, slot, brand_id=brand_id)

        result = query.order_by(
            ContentCategoryAssignmentDB.score.desc(),
            ContentRecordDB.id.asc(),
        ).first()

        if result is None:
            return None

        content_record, score, _category_id = result
        latest_version = get_latest_version_for_content(
            db=db, content_record_id=content_record.id, brand_id=brand_id
        )

        return StrategyResult(
            content_record_id=content_record.id,
            content_version_id=latest_version.id if latest_version else None,
            score=float(score),
            reason=f"top_score: highest scored content in category_ids={category_ids}",
        )
