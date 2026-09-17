"""The mock every interface ships — ADR-161 point 2.

"Quick to test" has a concrete consequence: a mock per interface, which is
what keeps the test suite runnable without credentials. It is also the default
provider, so nothing leaves the machine unless somebody chose otherwise.

It claims **every** channel deliberately. A mock that only pretended to do
email would make push untestable for exactly the reason push is worth testing:
nobody has an APNs certificate on a laptop, and the user building this has no
app at all. What a mock owes is an honest record of what it was handed, which
is what the log line below is.
"""

import json
import logging
import uuid

from app.delivery.providers.base import DeliveryProvider, SendResult
from app.rendering.renderers.base import RenderedArtifact

logger = logging.getLogger(__name__)


class MockProvider(DeliveryProvider):

    #: Empty = every channel. See the module docstring.
    channels = frozenset()

    def send(self, address: str, artifact: RenderedArtifact) -> SendResult:
        # Logged rather than discarded: with no app and no device, this line is
        # the only evidence a push "went out", and "show me it actually works"
        # is the whole reason the mock path exists.
        if artifact.body is None:
            payload = json.dumps(artifact.fields or {}, ensure_ascii=False)
        else:
            payload = f"{len(artifact.body)} bytes of {artifact.media_type}"
        logger.info(
            "mock send: to=%s role=%s envelope=%s payload=%s",
            address, artifact.role, artifact.envelope or {}, payload,
        )
        return SendResult(
            success=True,
            provider_message_id=f"mock-{uuid.uuid4()}",
            message="accepted",
        )
