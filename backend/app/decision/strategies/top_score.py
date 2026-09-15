from sqlalchemy.orm import Session

from app.campaigns.db_models import DecisionSlotDB
from app.content.db_models import ContentCategoryAssignmentDB, ContentRecordDB
from app.content.service import get_latest_version_for_content
from app.decision.strategies.base import ConfigField, DecisionStrategy, StrategyMeta, StrategyResult, sending_brand_id


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

        query = (
            db.query(ContentRecordDB, ContentCategoryAssignmentDB.score)
            .join(
                ContentCategoryAssignmentDB,
                ContentRecordDB.id == ContentCategoryAssignmentDB.content_id,
            )
            .filter(ContentRecordDB.status == "active")
            # ADR-150 point 8: a decision slot resolves ONLY the sending
            # brand's content. Safe by construction — widening it is the
            # configurable filter point 10 defers, not this default. A slot
            # whose campaign chain is broken resolves nothing rather than
            # every brand's content, because an unknown brand is not "any".
            .filter(ContentRecordDB.brand_id == sending_brand_id(db, slot))
        )

        if category_ids:
            query = query.filter(
                ContentCategoryAssignmentDB.category_id.in_(category_ids)
            )

        result = query.order_by(
            ContentCategoryAssignmentDB.score.desc(),
            ContentRecordDB.id.asc(),
        ).first()

        if result is None:
            return None

        content_record, score = result
        latest_version = get_latest_version_for_content(
            db=db, content_record_id=content_record.id
        )

        return StrategyResult(
            content_record_id=content_record.id,
            content_version_id=latest_version.id if latest_version else None,
            score=float(score),
            reason=f"top_score: highest scored content in category_ids={category_ids}",
        )
