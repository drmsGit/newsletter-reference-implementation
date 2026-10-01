"""A broken channel and an undeclared one are different facts — task-20.

A malformed channel manifest is skipped at load, deliberately: a typo in a
channel nobody uses must not stop the ones in use. What was wrong is that,
skipped and forgotten, a channel that broke this morning read exactly like one
never declared — at the moment variants might already depend on it. Now the
registry remembers why it failed, refusals say "broken" rather than "unknown",
and startup refuses the one case where skipping costs more than it saves.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.channels import registry

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture
def channels(tmp_path, monkeypatch):
    directory = tmp_path / "channels"
    directory.mkdir()
    (directory / "email.json").write_text(json.dumps({"label": "Email"}))
    (directory / "push.json").write_text('{"label": "Push",')   # truncated: does not parse
    monkeypatch.setattr(registry, "CHANNELS_DIR", directory)
    monkeypatch.setattr(registry, "_registry_mtime", None)
    yield directory
    monkeypatch.setattr(registry, "_registry_mtime", None)


def test_a_broken_manifest_is_remembered_and_an_absent_one_is_not(channels):
    assert not registry.is_registered("push")
    assert registry.load_error("push"), "the parse failure was forgotten"
    assert registry.load_error("sms") is None, "an undeclared channel was reported as broken"
    assert registry.load_error("email") is None


def test_startup_refuses_only_when_a_broken_channel_is_in_use(channels):
    registry.assert_used_channels_load({"email"})          # healthy: fine
    registry.assert_used_channels_load({"email", "sms"})   # undeclared is not this check

    with pytest.raises(registry.UnreadableChannelInUse, match="push.json"):
        registry.assert_used_channels_load({"email", "push"})


def test_the_refusal_says_broken_rather_than_unknown(channels):
    from app.campaigns.service import ChannelUnavailable, _refuse_unavailable_channel
    from app.database import SessionLocal

    with SessionLocal() as db:
        with pytest.raises(ChannelUnavailable, match="could not be read"):
            _refuse_unavailable_channel(db, "push")
        with pytest.raises(ChannelUnavailable, match="not an available channel"):
            _refuse_unavailable_channel(db, "sms")


def test_the_app_refuses_to_start_on_a_broken_manifest_in_use(tmp_path):
    """The call site, in a fresh process: the seeded variants use email, so a
    broken email.json must stop `main` from importing."""
    directory = tmp_path / "channels"
    directory.mkdir()
    (directory / "email.json").write_text("{not json")
    probe = subprocess.run(
        [sys.executable, "-c",
         "import app.channels.registry as r, pathlib; "
         f"r.CHANNELS_DIR = pathlib.Path({str(directory)!r}); import main"],
        cwd=str(BACKEND), capture_output=True, text=True, timeout=60, env={**os.environ},
    )

    assert probe.returncode != 0, "main started with a broken manifest for a channel in use"
    assert "UnreadableChannelInUse" in probe.stderr
    assert "email.json" in probe.stderr
