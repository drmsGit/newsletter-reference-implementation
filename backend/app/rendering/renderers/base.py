"""What a channel renderer is, and what it hands back.

[[ADR-162]] point 2: the renderer receives **fully resolved** content —
decisions resolved, overrides applied, versions pinned — so **it formats, it
never decides**. Every decision stays in the decision layer where it remains
explainable, and a renderer that cannot decide anything cannot disagree with
what the audit log says happened.

Point 4: **one renderer per channel, not per provider.** The artifact belongs
to the channel; the provider merely transmits it. A push artifact is the same
whether FCM or OneSignal carries it, so swapping vendor never changes what was
rendered.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.campaigns.db_models import DecisionResolutionDB

#: Artifact roles. ADR-162 point 3 wants rendering to return a *set* of
#: role-tagged artifacts plus a package hash over the set — **that is not built
#: here.** This introduces the role only, because push needed one, and each
#: renderer returns exactly one artifact. Said plainly so nobody reads a
#: single-artifact return as the point-3 contract arriving.
ROLE_HTML = "html"
ROLE_PAYLOAD = "payload"


@dataclass
class RenderedArtifact:
    """One rendered thing, and enough about it to store or transmit it.

    `body` and `fields` are alternatives, not both: an email is text, a push is
    a structured payload the receiving OS renders itself. Keeping them separate
    rather than serialising the push into a string is what lets the snapshot
    store it as data — which is the direction the snapshot-storage question is
    leaning anyway.
    """
    role: str
    media_type: str
    body: str | None = None
    fields: dict | None = None
    #: Per-module resolutions actually used, for the render context.
    resolutions_by_module_id: dict[int, DecisionResolutionDB] = field(default_factory=dict)

    def size_bytes(self) -> int:
        if self.body is not None:
            return len(self.body.encode("utf-8"))
        import json

        return len(json.dumps(self.fields or {}, ensure_ascii=False).encode("utf-8"))


class ChannelRenderer(ABC):
    """Drop a file in this package and the channel has a renderer.

    Auto-registration follows the `decision/strategies/` idiom and the
    "drop a file" standard ADR-160 point 6 sets — the third pattern that needs
    registering in several places is the one that eventually gets registered in
    two.
    """

    #: The channel name, matching `storage/channels/<name>.json`.
    channel: str = ""

    @abstractmethod
    def render(
        self,
        db: Session,
        variant_id: int,
        recipient_id: int | None = None,
        mode: str = "preview",
    ) -> RenderedArtifact:
        ...
