import random

from sqlalchemy.orm import Session

from app.campaigns.db_models import DecisionSlotDB
from app.content.service import get_latest_version_for_content
from app.decision.strategies.base import (
    ConfigField, DecisionStrategy, StrategyMeta, StrategyResult, best_per_record, candidate_query,
    sending_brand_id,
)
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

    def rank(
        self,
        db: Session,
        slot: DecisionSlotDB,
        recipient_id: int | None = None,
        *,
        limit: int = 1,
        exclude: frozenset[int] = frozenset(),
    ) -> list[StrategyResult]:
        if recipient_id is None:
            return []

        candidate_filter = slot.candidate_filter or {}
        category_ids = candidate_filter.get("category_ids", [])

        # Resolved once and reused: it filters the candidates below AND scopes
        # the version lookup further down, which must agree with it.
        brand_id = sending_brand_id(db, slot)

        config = {**DEFAULT_CONFIG, **(slot.strategy_config or {})}
        content_weight = config["content_score_weight"]
        preference_weight = config["preference_score_weight"]

        # The recipient's operational preference signals (decay-weighted over the
        # contribution log, ADR-132), keyed by category. The decision layer
        # consumes signals, not raw events (ADR-111).
        signals = operational_signals_for_recipient(db, recipient_id)

        query = candidate_query(db, slot, brand_id=brand_id)

        # Only categories the recipient actually has a signal for count — same
        # as the old inner join against a preference row, but now the "score" is
        # the decayed signal.
        candidates = [
            (content_record, content_score, signals[category_id])
            for (content_record, content_score, category_id) in query.all()
            if category_id in signals
        ]
        if not candidates:
            return []

        def candidate_score(row):
            return row[1] * content_weight + row[2] * preference_weight

        # Ties are ordered at random rather than by whichever row the database
        # returned first (an undisclosed bias toward lower content ids), and the
        # reason says so, so a pick stays auditable (ADR-085). Shuffling first
        # and then sorting stably keeps that random order inside each tie.
        random.shuffle(candidates)
        candidates.sort(key=candidate_score, reverse=True)
        ties: dict[float, int] = {}
        for row in candidates:
            ties[candidate_score(row)] = ties.get(candidate_score(row), 0) + 1

        picks = []
        for content_record, content_score, preference_score in best_per_record(
                candidates, lambda row: row[0].id, exclude, limit):
            combined = float(content_score * content_weight + preference_score * preference_weight)
            tied = ties[content_score * content_weight + preference_score * preference_weight]
            tie_note = (
                f" (tied at score {combined} between {tied} candidates, ordered randomly)"
                if tied > 1 else ""
            )
            latest_version = get_latest_version_for_content(
                db=db, content_record_id=content_record.id, brand_id=brand_id
            )
            picks.append(StrategyResult(
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
            ))
        return picks
