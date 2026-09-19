"""The AI task library — a registry and a generated settings surface.

Raised by the user 2026-09-17: `app/ai/tasks/` held one task and no registry,
so the settings route imported that module by name and the template hardcoded
a card bound to singular context keys. Tasks only *looked* like a plugin family
because there was exactly one — adding a second needed the new `.py`, an import
plus three context keys in the router, **and** a duplicated card.

Four registries already had this shape (`decision/strategies`, `modules`,
`channels`, `rendering/renderers`), which is the argument for a fifth being the
same rather than novel.

The test worth reading is `test_a_second_task_appears_without_touching_python
_or_markup`. Asserting that the one existing task renders proves nothing about
generality — it passes just as well against the hardcoded card that was there
before. Dropping a file in and expecting a second card is the only version that
distinguishes them.
"""
import json
import uuid

import pytest

from app.ai.tasks import registry as task_registry
from app.ai.tasks.base import TaskMeta
from app.auth import service as auth
from app.auth.db_models import RoleAssignmentDB, RoleDB, SessionDB, UserDB
from app.auth.permissions import ADMIN
from app.database import SessionLocal
from app.settings.db_models import AppConfigDB
from app.settings.service import (
    AI_TASK_MODELS_KEY, get_task_model, governed_models, set_task_model,
)

PREFIX = "aitask"


@pytest.fixture
def db():
    session = SessionLocal()
    auth.bootstrap(session)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _restore_task_models():
    """Per-task models are a shared config row, so a test that sets one must
    put it back — otherwise the next test runs against a deployment where
    somebody pinned a task to Haiku."""
    session = SessionLocal()
    row = session.query(AppConfigDB).filter(
        AppConfigDB.key == AI_TASK_MODELS_KEY).first()
    original = dict(row.value) if row and isinstance(row.value, dict) else None
    session.close()
    yield
    session = SessionLocal()
    if original is None:
        session.query(AppConfigDB).filter(
            AppConfigDB.key == AI_TASK_MODELS_KEY).delete()
    else:
        from app.settings.service import set_config
        set_config(session, AI_TASK_MODELS_KEY, original)
    session.commit()
    session.close()


@pytest.fixture
def admin_client(db):
    from fastapi.testclient import TestClient

    from main import app

    user = UserDB(email=f"{PREFIX}-{uuid.uuid4().hex[:8]}@example.invalid", is_active=True)
    db.add(user); db.commit(); db.refresh(user)
    role = db.query(RoleDB).filter(RoleDB.key == ADMIN).first()
    db.add(RoleAssignmentDB(user_id=user.id, role_id=role.id,
                            brand_id=auth.ensure_default_brand(db).id))
    db.commit()
    token = auth.create_session(db, user)
    client = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
    client.cookies.set(auth.SESSION_COOKIE, token)
    yield client, token
    db.query(SessionDB).filter(SessionDB.user_id == user.id).delete()
    db.query(RoleAssignmentDB).filter(RoleAssignmentDB.user_id == user.id).delete()
    db.query(UserDB).filter(UserDB.id == user.id).delete()
    db.commit()


class TestTasksAreDiscovered:

    def test_the_existing_task_declares_itself(self):
        keys = [t.key for t in task_registry.list_tasks()]
        assert "subject_preheader" in keys
        meta = task_registry.get_task("subject_preheader")
        assert meta.label and meta.default_prompt and meta.max_output_tokens == 400

    def test_a_module_without_meta_is_not_a_task(self):
        """`base.py` and `registry.py` live in the package and are not tasks.
        Excluding them by filename would break the moment somebody adds a
        helper, so discovery looks for a META rather than for a name."""
        keys = [t.key for t in task_registry.list_tasks()]
        assert "base" not in keys and "registry" not in keys

    def test_a_second_task_appears_without_touching_python_or_markup(
        self, db, admin_client, monkeypatch
    ):
        """**The test that makes "registry" mean something.** Rendering the one
        existing task proves nothing — the hardcoded card did that too."""
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        client, _token = admin_client
        from pathlib import Path

        planted = Path(task_registry.__file__).parent / f"{PREFIX}_planted.py"
        planted.write_text(
            "from app.ai.tasks.base import TaskMeta\n"
            "META = TaskMeta(key='aitask_planted', label='Planted task',\n"
            "                description='Dropped in by a test.',\n"
            "                default_prompt='Do the thing with {content}.',\n"
            "                max_output_tokens=100)\n"
        )
        try:
            task_registry._registry_mtime = None
            assert "aitask_planted" in [t.key for t in task_registry.list_tasks()]

            page = client.get("/ui/settings").text
            assert "Planted task" in page, (
                "a task file dropped into app/ai/tasks/ did not produce a card "
                "— the settings page is still bound to one task by name"
            )
            assert "Subject &amp; preheader" in page, "the real task must still render"
            assert page.count('name="task_key"') >= 4, (
                "each task needs its own prompt form and model form"
            )
        finally:
            planted.unlink(missing_ok=True)
            task_registry._registry_mtime = None

    def test_a_broken_task_file_does_not_take_the_registry_down(self):
        """Same tolerance the other four registries apply: a typo in a task
        nobody uses must not stop the ones that are used."""
        from pathlib import Path

        broken = Path(task_registry.__file__).parent / f"{PREFIX}_broken.py"
        broken.write_text("this is not valid python(\n")
        try:
            task_registry._registry_mtime = None
            assert "subject_preheader" in [t.key for t in task_registry.list_tasks()]
        finally:
            broken.unlink(missing_ok=True)
            task_registry._registry_mtime = None


class TestPerTaskModelSelection:
    """ADR-144 §2 recorded per-task model choice as the documented direction.
    The argument is arithmetic: tasks sit at very different points on the
    cost/capability curve and one global setting forces them all onto the most
    expensive model."""

    def test_unset_means_the_deployment_default_not_a_frozen_choice(self, db):
        """None is a real answer. Returning a concrete model would freeze
        today's default into every task the first time anyone opened Settings."""
        assert get_task_model(db, "subject_preheader") is None

    def test_a_model_outside_the_governed_list_is_refused(self, db):
        """ADR-140: a choice WITHIN what the deployment has enabled, never free
        text. A model the platform cannot price is one whose spend cap cannot
        be checked before the call, which is ADR-144 §5's whole basis."""
        from app.settings.service import task_models

        set_task_model(db, "subject_preheader", "gpt-9-ultra")
        assert "gpt-9-ultra" not in governed_models()

        # **Both layers, separately.** `set_task_model` refuses to store it and
        # `get_task_model` filters on read, so asserting only through the
        # reader passes even with the write guard removed — the two mask each
        # other exactly as the duplication permission checks did. The stored
        # row is checked directly for that reason.
        assert "subject_preheader" not in task_models(db), (
            "an ungoverned model was written to the config row; the reader "
            "hides it today, and a future reader that does not would pin the "
            "task to something the spend cap cannot price"
        )
        assert get_task_model(db, "subject_preheader") is None

    def test_a_model_withdrawn_after_being_chosen_falls_back(self, db, monkeypatch):
        """**What the read-side filter is actually for**, and the only way to
        reach it: the write guard means nothing ungoverned is ever stored, so
        the filter only ever fires for a model that WAS governed when it was
        chosen and is not any more — a price withdrawn, a model retired.

        Falling back to the deployment default is the safe direction. Returning
        the stale name would pin the task to a model the platform can no longer
        price, and ADR-144 §5's pre-call spend gate needs a price to exist.
        """
        from app.settings.service import task_models

        set_task_model(db, "subject_preheader", "claude-opus-5")
        assert get_task_model(db, "subject_preheader") == "claude-opus-5"

        monkeypatch.setattr(
            "app.ai.pricing.MODEL_PRICING",
            {"claude-sonnet-5": (3.00, 15.00), "mock-1": (0.0, 0.0)},
        )
        assert "claude-opus-5" not in governed_models()
        assert get_task_model(db, "subject_preheader") is None, (
            "a task stayed pinned to a model that is no longer priced, so its "
            "next run could not be cost-checked before the call"
        )
        # The stored value is untouched — withdrawing a price is not the same
        # as the manager changing their mind, and restoring it should restore
        # the choice rather than require re-picking it.
        assert task_models(db).get("subject_preheader") == "claude-opus-5"

    def test_the_governed_list_is_the_priced_models(self, db):
        from app.ai.pricing import MODEL_PRICING

        assert set(governed_models()) == {
            m for m in MODEL_PRICING if not m.startswith("mock")}, (
            "the selectable models drifted from the ones the platform can "
            "price, so a task could be pinned to something the spend cap "
            "cannot gate"
        )

    def test_the_choice_reaches_the_provider(self, db, monkeypatch):
        """The setting is worthless if `run_task` does not pass it on."""
        from app.ai import service as ai_service

        # `run_task` returns early when the task has no published prompt, so
        # without this the provider is never reached and the test passes for
        # the wrong reason — or, on a database that has one lying around, for
        # the right reason by luck. A test owns its preconditions.
        from app.ai.service import get_published_prompt, publish_prompt

        if get_published_prompt(db, "subject_preheader") is None:
            publish_prompt(db, "subject_preheader", "Write something about {content}.")

        set_task_model(db, "subject_preheader", "claude-haiku-4-5")
        captured = {}

        def fake_provider(provider_name=None, model=None):
            captured["provider"] = provider_name
            captured["model"] = model
            raise RuntimeError("stop here — the model is what this test is about")

        monkeypatch.setattr(ai_service, "get_ai_provider", fake_provider)
        with pytest.raises(RuntimeError):
            ai_service.run_task(
                db, task_key="subject_preheader", rendered_prompt="x",
                max_output_tokens=10, provider_name="claude")

        assert captured["model"] == "claude-haiku-4-5", (
            f"run_task handed the provider {captured['model']!r} — the task's "
            "configured model never reached the adapter"
        )

    def test_the_adapter_honours_a_pinned_model(self):
        from app.ai.adapters.factory import get_ai_provider

        assert get_ai_provider("claude", model="claude-haiku-4-5").model == "claude-haiku-4-5"
        assert get_ai_provider("claude").model == "claude-opus-5", (
            "an unpinned adapter stopped using its own default"
        )

    def test_setting_and_clearing_through_the_page(self, db, admin_client, monkeypatch):
        monkeypatch.setenv("SYSTEM_MAIL_PROVIDER", "mock")
        client, token = admin_client

        response = client.post("/ui/settings/ai-task-model", data={
            "task_key": "subject_preheader", "model": "claude-sonnet-5",
            "csrf_token": auth.csrf_token_for(token)})
        assert response.status_code == 303
        assert get_task_model(db, "subject_preheader") == "claude-sonnet-5"

        client.post("/ui/settings/ai-task-model", data={
            "task_key": "subject_preheader", "model": "",
            "csrf_token": auth.csrf_token_for(token)})
        assert get_task_model(db, "subject_preheader") is None, (
            "clearing the selection must return the task to the deployment "
            "default rather than leaving the last choice pinned"
        )
