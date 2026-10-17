"""The suite's image files never touch the installation's own folder.

Found 2026-10-17: the suite wrote to and deleted from `storage/assets/`, and a
run removed the dev demo's images. `conftest.py` points `ASSETS_DIR` at a
temporary folder; this says so, so a change that loses it fails here first.
"""
import tempfile
from pathlib import Path

from app.assets.store import DEFAULT_DIR, get_store


def test_the_suite_stores_images_in_a_temporary_folder_of_its_own():
    root = get_store().root.resolve()
    assert root != DEFAULT_DIR.resolve()
    assert DEFAULT_DIR.resolve() not in root.parents
    assert Path(tempfile.gettempdir()).resolve() in root.parents
