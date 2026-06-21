from sqlalchemy.orm import Session

from app.campaigns.db_models import DecisionSlotDB
from app.campaigns.models import DecisionResolution
from app.campaigns.service import create_decision_resolution
from app.content.db_models import (
    ContentCategoryAssignmentDB,
    ContentRecordDB,
)
from app.decision.strategies.base import DecisionStrategy
from app.recipients.db_models import RecipientPreferenceDB
from app.content.service import get_latest_version_for_content

DEFAULT_STRATEGY_CONFIG = {
    "content_score_weight": 1,
    "preference_score_weight": 10,
}

class RecipientTopScoreStrategy(DecisionStrategy):

    def execute(
        self,
        db: Session,
        slot: DecisionSlotDB,
        recipient_id: int | None = None,
    ) -> DecisionResolution:

        if recipient_id is None:
            raise ValueError(
                "recipient_top_score requires recipient_id"
            )

        candidate_filter = slot.candidate_filter or {}
        category_ids = candidate_filter.get("category_ids", [])

        strategy_config = {
            **DEFAULT_STRATEGY_CONFIG,
            **(slot.strategy_config or {}),
        }

        content_score_weight = strategy_config.get(
            "content_score_weight",
            1,
        )

        preference_score_weight = strategy_config.get(
            "preference_score_weight",
            10,
        )

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
                RecipientPreferenceDB.category_id
                == ContentCategoryAssignmentDB.category_id,
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
            raise ValueError(
                "No matching content record found for recipient"
            )

        best_candidate = max(
            candidates,
            key=lambda row: (
                row[1] * content_score_weight
                + row[2] * preference_score_weight
            ),
        )

        content_record = best_candidate[0]
        content_score = best_candidate[1]
        preference_score = best_candidate[2]
        combined_score = int(
            content_score * content_score_weight
            + preference_score * preference_score_weight
        )

        latest_version = get_latest_version_for_content(
            db=db,
            content_record_id=content_record.id,
        )

        return create_decision_resolution(
            db=db,
            decision_slot_id=slot.id,
            recipient_id=recipient_id,
            content_record_id=content_record.id,
            content_version_id=latest_version.id if latest_version else None,
            reason=(
                "Selected by recipient_top_score strategy "
                f"for recipient_id={recipient_id}, "
                f"category_ids={category_ids}, "
                f"content_score={content_score}, "
                f"content_score_weight={content_score_weight}, "
                f"preference_score={preference_score}, "
                f"preference_score_weight={preference_score_weight}, "
                f"combined_score={combined_score}"
            ),
            score=combined_score,
        )