from sqlalchemy.orm import Session

from app.campaigns.db_models import DecisionSlotDB
from app.content.db_models import ContentCategoryAssignmentDB, ContentRecordDB
from app.content.service import get_latest_version_for_content
from app.decision.strategies.base import DecisionStrategy, StrategyMeta, StrategyResult
from app.recipients.db_models import RecipientPreferenceDB

DEFAULT_CONFIG = {
    "content_score_weight": 1,
    "preference_score_weight": 10,
}


class RecipientTopScoreStrategy(DecisionStrategy):

    @property
    def meta(self) -> StrategyMeta:
        return StrategyMeta(
            name="recipient_top_score",
            label="Recipient Top Score",
            description=(
                "Combines content score and recipient preference score to pick "
                "the best match per recipient. Weights are configurable via "
                "strategy_config (content_score_weight, preference_score_weight)."
            ),
            requires_recipient=True,
        )

    def execute(
        self,
        db: Session,
        slot: DecisionSlotDB,
        recipient_id: int | None = None,
    ) -> StrategyResult | None:
        if recipient_id is None:
            return None

        candidate_filter = slot.candidate_filter or {}
        category_ids = candidate_filter.get("category_ids", [])

        config = {**DEFAULT_CONFIG, **(slot.strategy_config or {})}
        content_weight = config["content_score_weight"]
        preference_weight = config["preference_score_weight"]

        query = (
            db.query(
                ContentRecordDB,
                ContentCategoryAssignmentDB.score,
                RecipientPreferenceDB.score,
            )
            .join(
                ContentCategoryAssignmentDB,
                ContentRecordDB.id == ContentCategoryAssignmentDB.content_id,
            )
            .join(
                RecipientPreferenceDB,
                RecipientPreferenceDB.category_id == ContentCategoryAssignmentDB.category_id,
            )
            .filter(ContentRecordDB.status == "active")
            .filter(RecipientPreferenceDB.recipient_id == recipient_id)
        )

        if category_ids:
            query = query.filter(
                ContentCategoryAssignmentDB.category_id.in_(category_ids)
            )

        candidates = query.all()
        if not candidates:
            return None

        best = max(
            candidates,
            key=lambda row: row[1] * content_weight + row[2] * preference_weight,
        )

        content_record, content_score, preference_score = best
        combined = float(
            content_score * content_weight + preference_score * preference_weight
        )

        latest_version = get_latest_version_for_content(
            db=db, content_record_id=content_record.id
        )

        return StrategyResult(
            content_record_id=content_record.id,
            content_version_id=latest_version.id if latest_version else None,
            score=combined,
            reason=(
                f"recipient_top_score: recipient={recipient_id}, "
                f"category_ids={category_ids}, "
                f"content_score={content_score}×{content_weight} + "
                f"preference_score={preference_score}×{preference_weight} "
                f"= {combined}"
            ),
        )
