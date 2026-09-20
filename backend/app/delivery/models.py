from datetime import datetime

from pydantic import BaseModel


class DeliveryExecution(BaseModel):
    id: int
    send_instance_id: int
    recipient_id: int
    status: str
    provider: str | None = None
    provider_message_id: str | None = None
    created_at: datetime
    updated_at: datetime


class DeliveryExecutionCreate(BaseModel):
    send_instance_id: int
    recipient_id: int
    status: str = "created"
    provider: str | None = None
    provider_message_id: str | None = None


class SendInstance(BaseModel):
    id: int
    snapshot_id: int
    name: str
    status: str
    provider: str | None = None
    scheduled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SendInstanceCreate(BaseModel):
    snapshot_id: int
    name: str
    status: str = "draft"
    provider: str | None = None
    scheduled_at: datetime | None = None

class TestSendRequest(BaseModel):
    """One real email to one typed address.

    `variant_id` is optional: without it a plain test body goes, which is the
    question "does mail leave the building at all" asked on its own. With it,
    the variant is rendered through the email path — and if that fails the send
    still happens with `render_note` explaining what the recipient got instead.
    """

    to: str
    subject: str = "Test from the newsletter reference build"
    provider: str = "resend"
    variant_id: int | None = None
    recipient_id: int | None = None


class TestSendResponse(BaseModel):
    """What one test send did, as the API answers it.

    **Named `...Response`, not `...Result`, deliberately.**
    `delivery.service.TestSendResult` is the dataclass this mirrors, and
    the router imports from both modules — a shared name would shadow one
    silently. `app/rendering/router.py` carries a comment about the 500
    that shape already caused once.
    """

    success: bool
    to: str
    provider: str
    provider_message_id: str | None = None
    message: str | None = None
    #: Set when the chosen variant could not be rendered and a plain body went
    #: instead. **Not an error** — the send still happened.
    render_note: str | None = None


class ProcessDueResult(BaseModel):
    """What firing the due scheduled sends did."""

    triggered: int
    send_instance_ids: list[int] = []
