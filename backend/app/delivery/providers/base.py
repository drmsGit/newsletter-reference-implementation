from abc import ABC, abstractmethod

from pydantic import BaseModel


class SendResult(BaseModel):
    success: bool
    provider_message_id: str


class DeliveryProvider(ABC):

    @abstractmethod
    def send(
        self,
        recipient_id: str,
        subject: str,
        html: str,
    ) -> SendResult:
        pass