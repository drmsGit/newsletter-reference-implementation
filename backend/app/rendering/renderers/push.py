"""The push renderer — fills fields, and has no layout job.

[[ADR-160]] point 2: "APNs, FCM and Web Push all take structured fields
(`title`, `body`, `image`, link) inside a roughly 4 KB budget, and the
receiving OS does all rendering — a push renderer fills fields and has no
layout job." So this returns data, not a document, and there is no template
file behind it (`has_template: false` on the module manifest).

**Everything it needs was already decided before it ran.** The single module
may point at a content record *or* a decision slot, and
`resolve_module_variables` handles both identically — which is how ADR-160
point 2's "personalised push comes free" is actually free. It also means the
override layer applies to push without push knowing overrides exist.

What this deliberately does not do: check lengths. ADR-161 point 7 is explicit
that lengths are "enforced by the editor as an input constraint, not as a
validation gate", because title and body are *accepted* by APNs and FCM and
then truncated by the device — so a gate here would refuse things that work,
while the thing that actually fails (the 4 KB total) is a transport concern.
The preferred handling is a preview showing potential truncation.
"""

from sqlalchemy.orm import Session

from app.campaigns.db_models import ModuleInstanceDB
from app.modules.registry import get_manifest
from app.rendering.renderers.base import ROLE_PAYLOAD, ChannelRenderer, RenderedArtifact


class PushRenderer(ChannelRenderer):
    channel = "push"

    def render(
        self,
        db: Session,
        variant_id: int,
        recipient_id: int | None = None,
        mode: str = "preview",
    ) -> RenderedArtifact:
        from app.rendering.service import resolve_module_variables

        modules = (
            db.query(ModuleInstanceDB)
            .filter(ModuleInstanceDB.variant_id == variant_id)
            .order_by(ModuleInstanceDB.position)
            .all()
        )

        fields: dict = {}
        resolutions: dict = {}

        # Cardinality is enforced at authoring time (ADR-160 point 2 via the
        # channel manifest's max_modules), so there is at most one. Iterating
        # anyway rather than asserting: a variant that predates a lowered limit
        # is a real state, and a renderer is the wrong place to discover it.
        for module in modules:
            manifest = get_manifest(self.channel, module.module_type)
            if manifest is None:
                continue

            if manifest.cms:
                variables, _content, resolution = resolve_module_variables(
                    db=db, module=module, manifest=manifest,
                    recipient_id=recipient_id, mode=mode,
                )
                if resolution is not None:
                    resolutions[module.id] = resolution
                # ADR-086: nothing resolved is a hidden slot, not a placeholder.
                # For a push that means an empty payload, which the send path
                # must refuse rather than deliver as a blank notification.
                if variables is None:
                    continue
            else:
                variables = {
                    var.name: (module.module_data or {}).get(var.name, "")
                    for var in manifest.variables
                }

            fields.update(variables)
            break

        return RenderedArtifact(
            role=ROLE_PAYLOAD,
            media_type="application/json",
            fields=fields,
            resolutions_by_module_id=resolutions,
        )
