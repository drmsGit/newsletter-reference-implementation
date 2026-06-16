from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.campaigns.db_models import DecisionSlotDB
from app.campaigns.models import DecisionResolution


class DecisionStrategy(ABC):

    @abstractmethod
    def execute(
        self,
        db: Session,
        slot: DecisionSlotDB,
        recipient_id: int | None = None,
    ) -> DecisionResolution:
        pass