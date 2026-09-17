"""The email renderer — the existing composition path, behind the channel
contract.

Nothing about how email renders changed here. ADR-162 point 4 keeps MJML
compilation in the frontend layer per ADR-131: the email renderer assembles
already-compiled module HTML and inlines CSS; it does not gain a compiler.
"""

from sqlalchemy.orm import Session

from app.rendering.renderers.base import ROLE_HTML, ChannelRenderer, RenderedArtifact


class EmailRenderer(ChannelRenderer):
    channel = "email"

    def render(
        self,
        db: Session,
        variant_id: int,
        recipient_id: int | None = None,
        mode: str = "preview",
    ) -> RenderedArtifact:
        # Imported here rather than at module scope: the service imports this
        # package's registry, so a top-level import would close the loop.
        from app.rendering.service import render_variant_html

        html, resolutions = render_variant_html(
            db=db,
            variant_id=variant_id,
            recipient_id=recipient_id,
            mode=mode,
            collect_resolutions=True,
        )
        return RenderedArtifact(
            role=ROLE_HTML,
            media_type="text/html",
            body=html,
            resolutions_by_module_id=resolutions,
        )
