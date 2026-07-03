from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.campaigns.db_models import DecisionSlotDB


@dataclass
class StrategyResult:
    content_record_id: int
    content_version_id: int | None
    score: float
    reason: str


@dataclass
class StrategyMeta:
    name: str
    label: str
    description: str
    requires_recipient: bool = False


class DecisionStrategy(ABC):

    @property
    @abstractmethod
    def meta(self) -> StrategyMeta:
        pass

    @abstractmethod
    def execute(
        self,
        db: Session,
        slot: DecisionSlotDB,
        recipient_id: int | None = None,
    ) -> StrategyResult | None:
        """
        Return a StrategyResult when content is found, or None when no
        suitable content exists. Never raise for a missing-content case —
        the caller handles graceful degradation (ADR-086).
        """
        pass
