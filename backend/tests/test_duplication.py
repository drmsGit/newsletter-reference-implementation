"""Duplicating a campaign — brand step 3, 2026-09-16.

ADR-150 point 2 fixes a content record to one brand, so a campaign cannot be
shared into a second one. Duplication is the escape hatch that decision creates,
and **the boundary is the only thing that decides what it means**: inside a
brand the copy references the same content records, across a brand it cannot.

The two tests worth reading first are the pair that pin that asymmetry —
`test_a_same_brand_copy_creates_no_content_rows_at_all` and
`test_a_cross_brand_copy_repoints_every_module_at_a_new_record`. A same-brand
copy that silently duplicated content would look *identical* in the UI and
would be the data-hygiene failure this whole design exists to avoid, so "no
rows were created" has to be asserted as a count, not inferred from a screen.

Runs against the shared dev database like the rest of the suite. Cleanup is in
`finally` and covers the whole graph a duplication touches — including
`audit_events`, which has no foreign keys by design (ADR-153 point 5) and so
cascades from nothing.
"""
import uuid

import pytest

from app.audit.db_models import AuditEventDB
from app.auth import service as auth
from app.auth.db_models import BrandDB, RoleAssignmentDB, RoleDB, SessionDB, UserDB
from app.auth.permissions import CAMPAIGNS_MANAGE, MANAGER, VIEWER
from app.campaigns import duplication
from app.campaigns.db_models import (
    CampaignDB,
    DecisionResolutionDB,
    DecisionSlotDB,
    ModuleInstanceDB,
    VariantDB,
)
from app.content.db_models import (
    ContentCategoryAssignmentDB,
    ContentRecordDB,
    ContentVersionDB,
)
from app.content.service import assign_category_to_content, create_category, create_content
from app.database import SessionLocal
from app.overrides.db_models import ContentOverrideDB
# Imported for its side effect as much as its use: `snapshots.recipient_id` is a
# foreign key to `recipients`, and SQLAlchemy cannot configure the mapper until
# that table is registered. Without it the first query touching SnapshotDB fails
# with a mapper error that reads like a database problem and is not one.
from app.recipients.db_models import RecipientDB  # noqa: F401
from app.snapshots.db_models import SnapshotDB


#: Every campaign and content record these tests create carries this prefix, and
#: the module-level sweep below removes anything wearing it.
#:
#: **Cleanup here has to assume the test did the opposite of what it asserts.**
#: Deleting "everything in the target brand" is the obvious shape and it is
#: wrong: a mutation run that breaks the brand assignment puts the copy in a
#: brand the fixture is not watching, the delete finds nothing, and the row
#: survives the run. That is not hypothetical — it happened twice while this
#: file was being written, and the second time it left a snapshot that became
#: the newest in the database, which silently broke two consent tests that pick
#: the newest snapshot to send from.
PREFIX = "duptest"


def _name(label: str) -> str:
    return f"{PREFIX}-{label}-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def db():
    session = SessionLocal()
    auth.bootstrap(session)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module", autouse=True)
def _sweep():
    """Last line of defence: remove anything wearing the prefix, in any brand."""
    yield
    session = SessionLocal()
    try:
        _purge_campaigns(session, [
            row.id
            for row in session.query(CampaignDB)
            .filter(CampaignDB.name.like(f"{PREFIX}-%"))
            .all()
        ])
        stray = [
            row.id
            for row in session.query(ContentRecordDB)
            .filter(ContentRecordDB.title.like(f"{PREFIX}-%"))
            .all()
        ]
        if stray:
            session.query(ContentCategoryAssignmentDB).filter(
                ContentCategoryAssignmentDB.content_id.in_(stray)
            ).delete(synchronize_session=False)
            session.query(ContentVersionDB).filter(
                ContentVersionDB.content_record_id.in_(stray)
            ).delete(synchronize_session=False)
            session.query(ContentRecordDB).filter(
                ContentRecordDB.id.in_(stray)
            ).delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()


@pytest.fixture
def default_brand(db):
    return auth.ensure_default_brand(db)


@pytest.fixture
def temp_brand(db):
    created: list[int] = []

    def make(label: str = "target") -> BrandDB:
        brand = BrandDB(key=_name(label), name=f"Dup {label}")
        db.add(brand)
        db.commit()
        db.refresh(brand)
        created.append(brand.id)
        return brand

    yield make

    for brand_id in created:
        _purge_brand(db, brand_id)
        db.query(RoleAssignmentDB).filter(RoleAssignmentDB.brand_id == brand_id).delete()
        db.query(SessionDB).filter(SessionDB.brand_id == brand_id).update({"brand_id": None})
        db.query(BrandDB).filter(BrandDB.id == brand_id).delete()
    db.commit()


def _purge_brand(db, brand_id: int) -> None:
    """Everything a duplication can put into a brand, in FK order."""
    campaign_ids = [
        row.id for row in db.query(CampaignDB).filter(CampaignDB.brand_id == brand_id).all()
    ]
    _purge_campaigns(db, campaign_ids)
    content_ids = [
        row.id
        for row in db.query(ContentRecordDB).filter(ContentRecordDB.brand_id == brand_id).all()
    ]
    if content_ids:
        db.query(ContentCategoryAssignmentDB).filter(
            ContentCategoryAssignmentDB.content_id.in_(content_ids)
        ).delete(synchronize_session=False)
        db.query(ContentRecordDB).filter(ContentRecordDB.id.in_(content_ids)).delete(
            synchronize_session=False
        )
    db.query(AuditEventDB).filter(AuditEventDB.brand_id == brand_id).delete(
        synchronize_session=False
    )
    db.commit()


def _purge_named(db, name: str) -> None:
    """By name, in whatever brand it ended up in. See PREFIX."""
    _purge_campaigns(db, [
        row.id for row in db.query(CampaignDB).filter(CampaignDB.name == name).all()
    ])


def _purge_campaigns(db, campaign_ids: list[int]) -> None:
    if not campaign_ids:
        return
    variant_ids = [
        row.id
        for row in db.query(VariantDB).filter(VariantDB.campaign_id.in_(campaign_ids)).all()
    ]
    if variant_ids:
        module_ids = [
            row.id
            for row in db.query(ModuleInstanceDB)
            .filter(ModuleInstanceDB.variant_id.in_(variant_ids))
            .all()
        ]
        if module_ids:
            db.query(ContentOverrideDB).filter(
                ContentOverrideDB.module_instance_id.in_(module_ids)
            ).delete(synchronize_session=False)
        # A test that asserts "no snapshot was written" cleans up as though one
        # was: if the assertion ever fails, the row it found is real and would
        # otherwise block the delete and leak into the shared dev database.
        db.query(SnapshotDB).filter(SnapshotDB.variant_id.in_(variant_ids)).delete(
            synchronize_session=False
        )
        slot_ids = [
            row.id
            for row in db.query(DecisionSlotDB)
            .filter(DecisionSlotDB.variant_id.in_(variant_ids))
            .all()
        ]
        if slot_ids:
            db.query(DecisionResolutionDB).filter(
                DecisionResolutionDB.decision_slot_id.in_(slot_ids)
            ).delete(synchronize_session=False)
        db.query(ModuleInstanceDB).filter(
            ModuleInstanceDB.variant_id.in_(variant_ids)
        ).delete(synchronize_session=False)
        db.query(DecisionSlotDB).filter(DecisionSlotDB.variant_id.in_(variant_ids)).delete(
            synchronize_session=False
        )
        db.query(VariantDB).filter(VariantDB.id.in_(variant_ids)).delete(
            synchronize_session=False
        )
    db.query(CampaignDB).filter(CampaignDB.id.in_(campaign_ids)).delete(
        synchronize_session=False
    )
    db.query(AuditEventDB).filter(
        AuditEventDB.subject_type == "campaign",
        AuditEventDB.subject_id.in_(campaign_ids),
    ).delete(synchronize_session=False)
    db.commit()


@pytest.fixture
def source(db, default_brand):
    """A campaign with everything a copy has to handle.

    One variant, a content-bound module, a static module carrying a URL, a
    decision-slot module with a configured filter, and **a gap in the module
    positions** — `delete_module` leaves holes, so a real campaign has them.
    """
    made = {"campaigns": [], "content": [], "categories": []}

    category = create_category(db, name=_name("cat"))
    made["categories"].append(category.id)

    record = create_content(
        db,
        title=_name("content"),
        content={"headline_medium": "Winter", "button_url": "https://brand-a.example/winter"},
        brand_id=default_brand.id,
        description="A record the copy has to decide about",
    )
    made["content"].append(record.id)
    assign_category_to_content(
        db, content_id=record.id, category_id=category.id, score=7,
        brand_id=default_brand.id,
    )

    campaign = CampaignDB(
        name=_name("source"), status="sent", brand_id=default_brand.id
    )
    db.add(campaign)
    db.flush()
    made["campaigns"].append(campaign.id)

    variant = VariantDB(
        campaign_id=campaign.id, channel="email", name="Variant A", status="sent",
    )
    db.add(variant)
    db.flush()
    # Envelope copy lives in the header module since ADR-162 point 1, so the
    # fixture writes it the way the application does rather than setting
    # columns the code no longer reads.
    from app.campaigns.service import set_envelope_fields

    set_envelope_fields(
        db, variant.id, {"subject": "Hello", "preheader": "Peek"},
        brand_id=default_brand.id,
    )

    slot = DecisionSlotDB(
        variant_id=variant.id,
        name="Top pick",
        decision_type="content_recommendation",
        decision_strategy="top_score",
        candidate_filter={"category_ids": [category.id]},
        strategy_config={},
        max_results=2,
    )
    db.add(slot)
    db.flush()

    db.add(ModuleInstanceDB(
        variant_id=variant.id, module_type="single_stack", position=1,
        content_record_id=record.id,
    ))
    db.add(ModuleInstanceDB(
        variant_id=variant.id, module_type="cta", position=4,   # the gap
        module_data={"button_label": "Book", "button_url": "https://brand-a.example/book"},
    ))
    db.add(ModuleInstanceDB(
        variant_id=variant.id, module_type="single_stack", position=7,  # and another
        decision_slot_id=slot.id,
    ))
    db.commit()

    yield {
        "campaign": campaign,
        "variant": variant,
        "slot": slot,
        "record": record,
        "category": category,
    }

    _purge_campaigns(db, made["campaigns"])
    for content_id in made["content"]:
        db.query(ContentCategoryAssignmentDB).filter(
            ContentCategoryAssignmentDB.content_id == content_id
        ).delete()
        db.query(ContentRecordDB).filter(ContentRecordDB.id == content_id).delete()
    db.query(ContentCategoryAssignmentDB).filter(
        ContentCategoryAssignmentDB.category_id.in_(made["categories"])
    ).delete(synchronize_session=False)
    from app.content.db_models import CategoryDB
    db.query(CategoryDB).filter(CategoryDB.id.in_(made["categories"])).delete(
        synchronize_session=False
    )
    db.commit()


def _modules(db, campaign_id: int) -> list[ModuleInstanceDB]:
    variant_ids = [
        row.id for row in db.query(VariantDB).filter(VariantDB.campaign_id == campaign_id).all()
    ]
    return (
        db.query(ModuleInstanceDB)
        .filter(ModuleInstanceDB.variant_id.in_(variant_ids))
        .order_by(ModuleInstanceDB.position.asc())
        .all()
    )


class TestTheBoundaryDecidesWhetherContentIsCopied:
    """The one rule everything else follows from."""

    def test_a_same_brand_copy_creates_no_content_rows_at_all(self, db, source, default_brand):
        before = db.query(ContentRecordDB).count()

        report = duplication.duplicate_campaign(
            db,
            campaign_id=source["campaign"].id,
            target_brand_id=default_brand.id,
            name=_name('Copy in place'),
            content_mode=duplication.KEEP,
        )
        try:
            after = db.query(ContentRecordDB).count()
            assert after == before, (
                f"a same-brand duplication created {after - before} content record(s). "
                "It must create none — inside one brand the copy references the same "
                "records (ADR-013), and silently forking the catalogue is the hygiene "
                "failure this design exists to avoid. It would look identical in the UI."
            )
            assert report.content_records_copied == {}

            bound = [m for m in _modules(db, report.campaign_id) if m.content_record_id]
            assert [m.content_record_id for m in bound] == [source["record"].id], (
                "the copy's module must point at the SAME record, not a new one"
            )
        finally:
            _purge_campaigns(db, [report.campaign_id])

    def test_a_cross_brand_copy_repoints_every_module_at_a_new_record(
        self, db, source, temp_brand
    ):
        target = temp_brand()

        report = duplication.duplicate_campaign(
            db,
            campaign_id=source["campaign"].id,
            target_brand_id=target.id,
            name=_name('Copy across'),
            content_mode=duplication.COPY,
        )
        try:
            campaign = db.get(CampaignDB, report.campaign_id)
            assert campaign.brand_id == target.id, (
                f"the copy landed in brand {campaign.brand_id}, not {target.id} — "
                "the target brand is the single field the whole wizard exists to set"
            )
            assert report.content_records_copied, "nothing was copied across the boundary"

            bound = [m for m in _modules(db, report.campaign_id) if m.content_record_id]
            assert bound, "the copy lost its content-bound module"
            for module in bound:
                assert module.content_record_id != source["record"].id, (
                    "a module still points at the source brand's record — the copy "
                    "would render another brand's content"
                )
                copy = db.get(ContentRecordDB, module.content_record_id)
                assert copy.brand_id == target.id, (
                    f"the copied record landed in brand {copy.brand_id}, not {target.id}"
                )
                assert copy.title == source["record"].title
                assert copy.content == source["record"].content
        finally:
            _purge_campaigns(db, [report.campaign_id])
            _purge_brand(db, target.id)

    def test_a_copied_record_keeps_its_categories(self, db, source, temp_brand):
        target = temp_brand()
        report = duplication.duplicate_campaign(
            db,
            campaign_id=source["campaign"].id,
            target_brand_id=target.id,
            name=_name('Copy across'),
            content_mode=duplication.COPY,
        )
        try:
            new_id = report.content_records_copied[source["record"].id]
            assignments = (
                db.query(ContentCategoryAssignmentDB)
                .filter(ContentCategoryAssignmentDB.content_id == new_id)
                .all()
            )
            assert [(a.category_id, a.score) for a in assignments] == [
                (source["category"].id, 7)
            ], (
                "the copy lost its category assignment — categories are global "
                "(ADR-150 point 2), so the copy points at the same rows and the "
                "decision engine can still find it"
            )
        finally:
            _purge_campaigns(db, [report.campaign_id])
            _purge_brand(db, target.id)

    def test_two_modules_citing_one_record_produce_one_copy(self, db, source, temp_brand):
        """Otherwise the target's catalogue gains a duplicate per reference."""
        variant = source["variant"]
        db.add(ModuleInstanceDB(
            variant_id=variant.id, module_type="single_stack", position=9,
            content_record_id=source["record"].id,
        ))
        db.commit()

        target = temp_brand()
        report = duplication.duplicate_campaign(
            db,
            campaign_id=source["campaign"].id,
            target_brand_id=target.id,
            name=_name('Copy across'),
            content_mode=duplication.COPY,
        )
        try:
            copies = (
                db.query(ContentRecordDB)
                .filter(ContentRecordDB.brand_id == target.id)
                .count()
            )
            assert copies == 1, f"one source record produced {copies} copies"
            bound = {m.content_record_id for m in _modules(db, report.campaign_id) if m.content_record_id}
            assert len(bound) == 1, "the two modules landed on different copies"
        finally:
            _purge_campaigns(db, [report.campaign_id])
            _purge_brand(db, target.id)

    def test_referencing_across_brands_is_refused(self, db, source, temp_brand):
        target = temp_brand()
        with pytest.raises(duplication.DuplicationRefused, match="one brand"):
            duplication.duplicate_campaign(
                db,
                campaign_id=source["campaign"].id,
                target_brand_id=target.id,
                name=_name('Impossible'),
                content_mode=duplication.KEEP,
            )

    def test_copying_inside_one_brand_is_refused(self, db, source, default_brand):
        """Not a preference — it is the case ADR-013 says must stay a reference."""
        with pytest.raises(duplication.DuplicationRefused, match="same records"):
            duplication.duplicate_campaign(
                db,
                campaign_id=source["campaign"].id,
                target_brand_id=default_brand.id,
                name=_name('Pointless fork'),
                content_mode=duplication.COPY,
            )

    def test_the_offered_modes_follow_the_boundary(self, db):
        assert duplication.content_modes_for(1, 1) == [duplication.KEEP, duplication.LAYOUT]
        assert duplication.content_modes_for(1, 2) == [duplication.COPY, duplication.LAYOUT]


class TestWhatTheCopyArrivesAs:

    def test_layout_only_leaves_modules_unbound_but_keeps_the_slots(
        self, db, source, default_brand
    ):
        report = duplication.duplicate_campaign(
            db,
            campaign_id=source["campaign"].id,
            target_brand_id=default_brand.id,
            name=_name('Skeleton'),
            content_mode=duplication.LAYOUT,
        )
        try:
            modules = _modules(db, report.campaign_id)
            assert all(m.content_record_id is None for m in modules), (
                "layout-only still bound content"
            )
            assert any(m.decision_slot_id is not None for m in modules), (
                "a decision slot is layout, not content — it must survive "
                "layout-only, because what that option drops is the binding to a "
                "specific record"
            )
        finally:
            _purge_campaigns(db, [report.campaign_id])

    def test_decision_slots_arrive_unconfigured_and_modules_repoint_to_them(
        self, db, source, default_brand
    ):
        report = duplication.duplicate_campaign(
            db,
            campaign_id=source["campaign"].id,
            target_brand_id=default_brand.id,
            name=_name('Copy in place'),
            content_mode=duplication.KEEP,
        )
        try:
            variant_ids = [
                row.id
                for row in db.query(VariantDB)
                .filter(VariantDB.campaign_id == report.campaign_id)
                .all()
            ]
            slots = (
                db.query(DecisionSlotDB)
                .filter(DecisionSlotDB.variant_id.in_(variant_ids))
                .all()
            )
            assert len(slots) == 1
            slot = slots[0]
            assert slot.name == "Top pick" and slot.max_results == 2
            assert not slot.candidate_filter, (
                "the slot inherited a candidate filter. A configured slot that "
                "resolves nothing looks finished; an empty one is visibly "
                "incomplete, and the manager should choose against the catalogue "
                "that now exists"
            )

            repointed = [m for m in _modules(db, report.campaign_id) if m.decision_slot_id]
            assert len(repointed) == 1
            assert repointed[0].decision_slot_id == slot.id, (
                "a module still points at the SOURCE campaign's decision slot — "
                "editing the copy's slot would change the original's output"
            )
            assert repointed[0].decision_slot_id != source["slot"].id
        finally:
            _purge_campaigns(db, [report.campaign_id])

    def test_positions_are_renumbered_contiguously(self, db, source, default_brand):
        """The source has holes at 2, 3, 5, 6 — `delete_module` leaves them."""
        report = duplication.duplicate_campaign(
            db,
            campaign_id=source["campaign"].id,
            target_brand_id=default_brand.id,
            name=_name('Copy in place'),
            content_mode=duplication.KEEP,
        )
        try:
            positions = [m.position for m in _modules(db, report.campaign_id)]
            # 0 is the header module, which keeps its slot; the content modules
            # renumber from 1 and close the source's gaps.
            assert positions == [0, 1, 2, 3], f"positions came across as {positions}"
            types = [m.module_type for m in _modules(db, report.campaign_id)]
            assert types == ["header", "single_stack", "cta", "single_stack"], (
                "renumbering reordered the layout"
            )
        finally:
            _purge_campaigns(db, [report.campaign_id])

    def test_nothing_that_happened_comes_across(self, db, source, default_brand):
        """Resolutions, snapshots, versions and overrides record events. A copy
        has no history, and reproducing them would claim sends that never were."""
        report = duplication.duplicate_campaign(
            db,
            campaign_id=source["campaign"].id,
            target_brand_id=default_brand.id,
            name=_name('Copy in place'),
            content_mode=duplication.KEEP,
        )
        try:
            variant_ids = [
                row.id
                for row in db.query(VariantDB)
                .filter(VariantDB.campaign_id == report.campaign_id)
                .all()
            ]
            assert db.query(SnapshotDB).filter(
                SnapshotDB.variant_id.in_(variant_ids)
            ).count() == 0
            module_ids = [m.id for m in _modules(db, report.campaign_id)]
            assert db.query(ContentOverrideDB).filter(
                ContentOverrideDB.module_instance_id.in_(module_ids)
            ).count() == 0, (
                "an override came across — an override is a correction layered on "
                "a system pick that has not happened in the copy"
            )
            assert db.query(DecisionResolutionDB).filter(
                DecisionResolutionDB.decision_slot_id.in_(
                    [s.id for s in db.query(DecisionSlotDB).filter(
                        DecisionSlotDB.variant_id.in_(variant_ids)).all()]
                )
            ).count() == 0
            # And the copy does not claim to have been sent, though its source did.
            campaign = db.get(CampaignDB, report.campaign_id)
            assert campaign.status == "draft", (
                f"the copy claims status {campaign.status!r} — the source was sent, "
                "the copy has not been"
            )
            variants = db.query(VariantDB).filter(VariantDB.id.in_(variant_ids)).all()
            assert all(v.status == "draft" for v in variants)
            # Carried as a module now, not as columns — which is also why
            # duplication needed no special case for it: the header module
            # copies like any other.
            from app.rendering.service import envelope_fields_for_variant

            envelope = envelope_fields_for_variant(db, variant_ids[0], "email")
            assert envelope.get("subject") == "Hello", (
                "the copy lost its subject line — envelope copy is a module "
                "since ADR-162 point 1, so it travels with the modules"
            )
            assert envelope.get("preheader") == "Peek"
        finally:
            _purge_campaigns(db, [report.campaign_id])

    def test_a_cross_brand_copy_cannot_be_sent_until_its_content_is_published(
        self, db, source, temp_brand
    ):
        """The behaviour most likely to surprise, so it is the one pinned.

        A copied record has no frozen version (ADR-128), and `mode="send"`
        refuses unpublished content — so the copy previews perfectly and refuses
        to snapshot. The wizard says so; this proves the wizard is telling the
        truth.
        """
        from app.rendering.service import UnpublishedContentError
        from app.snapshots.service import create_snapshot_for_variant

        target = temp_brand()
        report = duplication.duplicate_campaign(
            db,
            campaign_id=source["campaign"].id,
            target_brand_id=target.id,
            name=_name('Copy across'),
            content_mode=duplication.COPY,
        )
        try:
            variant = (
                db.query(VariantDB)
                .filter(VariantDB.campaign_id == report.campaign_id)
                .first()
            )
            with pytest.raises(UnpublishedContentError):
                create_snapshot_for_variant(db, variant_id=variant.id)

            new_id = report.content_records_copied[source["record"].id]
            assert db.query(ContentVersionDB).filter(
                ContentVersionDB.content_record_id == new_id
            ).count() == 0, (
                "a version came across — ADR-128 makes a version the audit answer "
                "to what a recipient received, so copying one fabricates a "
                "publication that never happened"
            )
        finally:
            _purge_campaigns(db, [report.campaign_id])
            _purge_brand(db, target.id)

    def test_the_report_names_the_urls_that_came_across_verbatim(
        self, db, source, temp_brand
    ):
        target = temp_brand()
        report = duplication.duplicate_campaign(
            db,
            campaign_id=source["campaign"].id,
            target_brand_id=target.id,
            name=_name('Copy across'),
            content_mode=duplication.COPY,
        )
        try:
            joined = " | ".join(report.url_carriers)
            assert "button_url" in joined, (
                "the copy carried brand A's URLs into brand B and said nothing — "
                "those are exactly the per-brand values ADR-150 point 2 cited when "
                "it refused to share content across brands"
            )
        finally:
            _purge_campaigns(db, [report.campaign_id])
            _purge_brand(db, target.id)


class TestTheContentRecordButton:

    def test_inside_one_brand_the_copy_is_distinguishable(self, db, source, default_brand):
        copy = duplication.duplicate_content_record(
            db, content_id=source["record"].id, target_brand_id=default_brand.id
        )
        try:
            assert copy.title == f"{source['record'].title} (copy)", (
                "two records with the same title in one catalogue cannot be told apart"
            )
            assert copy.brand_id == default_brand.id
        finally:
            db.query(ContentCategoryAssignmentDB).filter(
                ContentCategoryAssignmentDB.content_id == copy.id
            ).delete()
            db.query(ContentRecordDB).filter(ContentRecordDB.id == copy.id).delete()
            db.commit()

    def test_across_brands_the_title_is_left_alone(self, db, source, temp_brand):
        target = temp_brand()
        copy = duplication.duplicate_content_record(
            db, content_id=source["record"].id, target_brand_id=target.id
        )
        try:
            assert copy.title == source["record"].title, (
                "the title is unambiguous in the other brand — it is the only one there"
            )
            assert copy.brand_id == target.id
        finally:
            _purge_brand(db, target.id)


class TestTheTargetBrandIsChecked:
    """`campaigns.manage` is checked against the WORKING brand, so without an
    explicit check the target is unguarded — a Manager on A could create a
    campaign in B by choosing it from a dropdown."""

    def _user_on(self, db, grants: dict) -> UserDB:
        user = UserDB(email=f"dup-{uuid.uuid4().hex[:10]}@example.invalid", is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        for brand, role_key in grants.items():
            role = db.query(RoleDB).filter(RoleDB.key == role_key).first()
            db.add(RoleAssignmentDB(user_id=user.id, role_id=role.id, brand_id=brand.id))
        db.commit()
        return user

    def _cleanup_user(self, db, user):
        db.query(SessionDB).filter(SessionDB.user_id == user.id).delete()
        db.query(RoleAssignmentDB).filter(RoleAssignmentDB.user_id == user.id).delete()
        db.query(AuditEventDB).filter(AuditEventDB.actor_id == user.id).delete(
            synchronize_session=False
        )
        db.query(UserDB).filter(UserDB.id == user.id).delete()
        db.commit()

    def _client(self, db, user, brand):
        from fastapi.testclient import TestClient

        from main import app

        token = auth.create_session(db, user)
        auth.set_session_brand(db, token, brand.id)
        client = TestClient(app, follow_redirects=False)
        client.cookies.set(auth.SESSION_COOKIE, token)
        return client, token

    def test_a_brand_the_user_cannot_write_to_is_refused(
        self, db, source, default_brand, temp_brand, monkeypatch
    ):
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        target = temp_brand()
        user = self._user_on(db, {default_brand: MANAGER, target: VIEWER})
        client, token = self._client(db, user, default_brand)
        name = _name("sneaky")
        try:
            response = client.post(
                f"/ui/campaigns/{source['campaign'].id}/duplicate",
                data={
                    "name": name,
                    "target_brand_id": str(target.id),
                    # LAYOUT, not COPY, and that is the point. Copying content
                    # is refused by a SECOND check (content.manage on the
                    # target), so a COPY request here would be refused either
                    # way and the two guards would mask each other — breaking
                    # either one would fail nothing. Asking for the layout
                    # leaves exactly one guard standing.
                    "content_mode": duplication.LAYOUT,
                    "csrf_token": auth.csrf_token_for(token),
                },
            )
            assert response.status_code == 303
            assert "error=" in response.headers["location"], (
                "the duplication was accepted into a brand where this user is a "
                "Viewer — the policy table only checked the brand they came from"
            )
            assert db.query(CampaignDB).filter(CampaignDB.brand_id == target.id).count() == 0, (
                "a campaign was created in a brand the user cannot write to"
            )
        finally:
            _purge_named(db, name)
            _purge_brand(db, target.id)
            self._cleanup_user(db, user)

    def test_copying_content_needs_the_target_brand_s_content_permission(
        self, db, source, default_brand, temp_brand, monkeypatch
    ):
        """The second guard, isolated from the first.

        A role that can manage campaigns but not content is not one of the three
        presets, so it has to be built — and that is the point: without it, this
        user would be refused by the `campaigns.manage` check and this check
        could be deleted without a single test noticing.
        """
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        target = temp_brand()
        role = auth.create_role(db, key=_name("campaigns-only"), name="Campaigns only")
        auth.set_role_permissions(db, role.id, [CAMPAIGNS_MANAGE])
        user = self._user_on(db, {default_brand: MANAGER})
        db.add(RoleAssignmentDB(user_id=user.id, role_id=role.id, brand_id=target.id))
        db.commit()

        client, token = self._client(db, user, default_brand)
        name = _name("content-grab")
        try:
            response = client.post(
                f"/ui/campaigns/{source['campaign'].id}/duplicate",
                data={
                    "name": name,
                    "target_brand_id": str(target.id),
                    "content_mode": duplication.COPY,
                    "csrf_token": auth.csrf_token_for(token),
                },
            )
            assert response.status_code == 303
            assert "error=" in response.headers["location"], (
                "content was copied into a brand where this user cannot edit "
                "content — they can manage campaigns there, which is why the "
                "campaign check let this through"
            )
            assert db.query(ContentRecordDB).filter(
                ContentRecordDB.brand_id == target.id
            ).count() == 0
        finally:
            _purge_named(db, name)
            _purge_brand(db, target.id)
            self._cleanup_user(db, user)
            from app.auth.db_models import RolePermissionDB
            db.query(RolePermissionDB).filter(RolePermissionDB.role_id == role.id).delete()
            db.query(RoleDB).filter(RoleDB.id == role.id).delete()
            db.commit()

    def test_the_same_request_succeeds_where_the_user_is_a_manager(
        self, db, source, default_brand, temp_brand, monkeypatch
    ):
        """Without this, the test above could pass by refusing everything."""
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        target = temp_brand()
        user = self._user_on(db, {default_brand: MANAGER, target: MANAGER})
        client, token = self._client(db, user, default_brand)
        name = _name("legitimate")
        try:
            response = client.post(
                f"/ui/campaigns/{source['campaign'].id}/duplicate",
                data={
                    "name": name,
                    "target_brand_id": str(target.id),
                    "content_mode": duplication.COPY,
                    "csrf_token": auth.csrf_token_for(token),
                },
            )
            assert response.status_code == 303
            assert "error=" not in response.headers["location"], (
                f"a Manager was refused on their own brand: {response.headers['location']}"
            )
            copies = db.query(CampaignDB).filter(CampaignDB.brand_id == target.id).all()
            assert len(copies) == 1 and copies[0].name == name, (
                "the copy is not in the target brand — the brand the form named "
                "is the only thing that decides where it lands"
            )

            entry = (
                db.query(AuditEventDB)
                .filter(
                    AuditEventDB.action == "campaign.duplicated",
                    AuditEventDB.subject_id == copies[0].id,
                )
                .first()
            )
            assert entry is not None, (
                "nothing was logged — the audit log is how provenance is answered, "
                "deliberately instead of a copied_from_id column that could go stale"
            )
            assert entry.actor_id == user.id
            assert entry.brand_id == target.id
            assert entry.detail["source_campaign_id"] == source["campaign"].id
            assert entry.detail["source_brand_id"] == default_brand.id
        finally:
            _purge_named(db, name)
            _purge_brand(db, target.id)
            self._cleanup_user(db, user)


class TestChoosingWhichVariantsComeAcross:
    """Asked for by the user 2026-09-17 after a cross-brand duplication brought
    both an email and a push variant across.

    It became worth having when variants gained channels (ADR-160 point 4):
    before that, "duplicate this campaign" meant one kind of thing; after it,
    "give brand A just the push" is a real operation with no expression short
    of deleting the rest afterwards.
    """

    def _two_variant_campaign(self, db, source):
        """The fixture campaign plus a push variant, so a selection is possible."""
        from app.campaigns.service import create_variant_for_campaign

        push = create_variant_for_campaign(
            db, campaign_id=source["campaign"].id,
            name=_name("push"), channel="push",
            brand_id=source["campaign"].brand_id)
        return source["variant"], push

    def test_only_the_chosen_variants_are_copied(self, db, source, default_brand):
        email_variant, push_variant = self._two_variant_campaign(db, source)

        report = duplication.duplicate_campaign(
            db,
            campaign_id=source["campaign"].id,
            target_brand_id=default_brand.id,
            name=_name("copy"),
            content_mode=duplication.KEEP,
            variant_ids=[push_variant.id],
        )
        try:
            copied = db.query(VariantDB).filter(
                VariantDB.campaign_id == report.campaign_id).all()
            assert [v.channel for v in copied] == ["push"], (
                f"asked for the push variant and got {[v.channel for v in copied]}"
            )
            assert report.variants == 1
        finally:
            _purge_campaigns(db, [report.campaign_id])

    def test_passing_nothing_still_copies_everything(self, db, source, default_brand):
        """The default has to stay "the whole campaign" — a wizard nobody
        touches must behave as it did before there was anything to choose."""
        self._two_variant_campaign(db, source)
        report = duplication.duplicate_campaign(
            db,
            campaign_id=source["campaign"].id,
            target_brand_id=default_brand.id,
            name=_name("copy"),
            content_mode=duplication.KEEP,
        )
        try:
            assert report.variants == 2
        finally:
            _purge_campaigns(db, [report.campaign_id])

    def test_an_empty_selection_is_refused_not_read_as_all(self, db, source, default_brand):
        """A campaign must always have a variant, so a request naming none is a
        mistake rather than a shorthand — and treating it as "all" would be the
        opposite of what was asked."""
        self._two_variant_campaign(db, source)
        with pytest.raises(duplication.DuplicationRefused, match="at least one"):
            duplication.duplicate_campaign(
                db,
                campaign_id=source["campaign"].id,
                target_brand_id=default_brand.id,
                name=_name("copy"),
                content_mode=duplication.KEEP,
                variant_ids=[],
            )

    def test_the_content_count_reflects_only_the_chosen_variants(self, db, source):
        """**The one that would have lied rather than failed.** Step 2 warns how
        many content records a cross-brand copy will create. Summarising the
        whole campaign while copying one of its variants advertises records the
        copy never makes."""
        _email, push_variant = self._two_variant_campaign(db, source)

        whole = duplication.summarise_source(db, source["campaign"].id)
        just_push = duplication.summarise_source(
            db, source["campaign"].id, [push_variant.id])

        assert whole["content_titles"], "the fixture's email variant references content"
        assert just_push["content_titles"] == [], (
            "the push variant references no content, so a copy of it creates "
            "no records — the count must say so"
        )
        assert [v["id"] for v in just_push["variants"]] == [push_variant.id]

    def test_a_variant_from_another_campaign_is_refused(self, db, source, default_brand):
        """Ids arrive from a form, so they are a claim rather than a fact."""
        other = duplication.duplicate_campaign(
            db,
            campaign_id=source["campaign"].id,
            target_brand_id=default_brand.id,
            name=_name("elsewhere"),
            content_mode=duplication.KEEP,
        )
        stranger = db.query(VariantDB).filter(
            VariantDB.campaign_id == other.campaign_id).first()
        try:
            with pytest.raises(duplication.DuplicationRefused, match="belong to this campaign"):
                duplication.duplicate_campaign(
                    db,
                    campaign_id=source["campaign"].id,
                    target_brand_id=default_brand.id,
                    name=_name("copy"),
                    content_mode=duplication.KEEP,
                    variant_ids=[stranger.id],
                )
        finally:
            _purge_campaigns(db, [other.campaign_id])
