import random

from sqlalchemy.orm import Session

from app.campaigns.db_models import DecisionSlotDB
from app.content.db_models import ContentCategoryAssignmentDB, ContentRecordDB
from app.content.service import get_latest_version_for_content
from app.decision.strategies.base import ConfigField, DecisionStrategy, StrategyMeta, StrategyResult
from app.insight.signals import operational_signals_for_recipient

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
            candidate_filter_fields=[
                ConfigField(
                    name="category_ids",
                    type="list[int]",
                    default=[],
                    description="Restrict candidates to these category IDs (empty = all).",
                ),
            ],
            config_fields=[
                ConfigField(
                    name="content_score_weight",
                    type="number",
                    default=DEFAULT_CONFIG["content_score_weight"],
                    description="Weight applied to the content's own category score.",
                ),
                ConfigField(
                    name="preference_score_weight",
                    type="number",
                    default=DEFAULT_CONFIG["preference_score_weight"],
                    description="Weight applied to the recipient's preference score.",
                ),
            ],
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

        # The recipient's operational preference signals (decay-weighted over the
        # contribution log, ADR-132), keyed by category. The decision layer
        # consumes signals, not raw events (ADR-111).
        signals = operational_signals_for_recipient(db, recipient_id)

        query = (
            db.query(
                ContentRecordDB,
                ContentCategoryAssignmentDB.score,
                ContentCategoryAssignmentDB.category_id,
            )
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

        # Only categories the recipient actually has a signal for count — same
        # as the old inner join against a preference row, but now the "score" is
        # the decayed signal.
        candidates = [
            (content_record, content_score, signals[category_id])
            for (content_record, content_score, category_id) in query.all()
            if category_id in signals
        ]
        if not candidates:
            return None

        def candidate_score(row):
            return row[1] * content_weight + row[2] * preference_weight

        top_score = max(candidate_score(row) for row in candidates)
        tied = [row for row in candidates if candidate_score(row) == top_score]

        # Ties are broken by an explicit, disclosed random choice rather than
        # silently taking whichever row the DB happened to return first
        # (undisclosed bias toward lower content IDs) — the reason string
        # says so, so the pick stays auditable (ADR-085).
        best = random.choice(tied) if len(tied) > 1 else tied[0]
        tie_note = (
            f" (tied at score {top_score} between {len(tied)} candidates, selected randomly)"
            if len(tied) > 1
            else ""
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
                f"= {combined}{tie_note}"
            ),
        )
