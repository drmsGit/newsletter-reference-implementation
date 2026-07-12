import uuid

from app.delivery.providers.base import (
    DeliveryProvider,
    SendResult,
)


class MockProvider(DeliveryProvider):

    def send(
        self,
        recipient_email: str,
        subject: str,
        html: str,
    ) -> SendResult:

        return SendResult(
            success=True,
            provider_message_id=f"mock-{uuid.uuid4()}",
            message="accepted",
        )