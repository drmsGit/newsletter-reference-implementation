"""CI keeps its own two promises (task-332, ADR-190).

The workflow's header says third-party code is pinned so a moved tag cannot
change what runs, and that the weekly run exists so a new vulnerability is
noticed when nobody pushes. The secret scanner was still pulled by tag, and a
push to main cancelled a running weekly scan — both found in the 2026-10-09
interview review (CI Q1, Q4). Read as text: the file is small and stable, and a
YAML parser would be one more dependency for two assertions.
"""
import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"


def _text() -> str:
    return WORKFLOW.read_text()


def test_every_action_is_pinned_to_a_commit():
    uses = re.findall(r"uses:\s*(\S+)", _text())
    assert uses, "no actions found — has the file moved?"
    unpinned = [u for u in uses if not re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", u)]
    assert unpinned == [], unpinned


def test_every_container_image_is_pinned_to_a_digest():
    images = re.findall(r"docker run [^\n]*?(\S+/\S+(?::\S+|@sha256:[0-9a-f]{64}))", _text())
    assert images, "no container images found"
    unpinned = [i for i in images if not re.search(r"@sha256:[0-9a-f]{64}$", i)]
    assert unpinned == [], unpinned


def test_a_push_never_cancels_the_scheduled_scan():
    """Runs that cancel each other must share a group; the weekly run must not
    share one with pushes, which all land on main."""
    group = re.search(r"concurrency:\s*\n\s*group:\s*(.+)", _text()).group(1)
    assert "github.event_name" in group, group
