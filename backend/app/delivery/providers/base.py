from abc import ABC, abstractmethod

from pydantic import BaseModel


class SendResult(BaseModel):
    success: bool
    # None on failure — a failed send has no provider message id, and the
    # DeliveryExecution column is nullable+unique (multiple nulls are fine),
    # so failures don't collide on an empty string.
    provider_message_id: str | None = None
    message: str | None = None


class DeliveryProvider(ABC):

    @abstractmethod
    def send(
        self,
        recipient_email: str,
        subject: str,
        html: str,
    ) -> SendResult:
        pass