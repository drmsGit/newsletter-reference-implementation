from app.decision.strategies.base import DecisionStrategy
from app.decision.strategies.top_score import TopScoreStrategy


STRATEGIES: dict[str, DecisionStrategy] = {
    "top_score": TopScoreStrategy(),
}


def get_strategy(strategy_name: str) -> DecisionStrategy:
    strategy = STRATEGIES.get(strategy_name)

    if strategy is None:
        raise ValueError(
            f"Unsupported decision strategy: {strategy_name}"
        )

    return strategy