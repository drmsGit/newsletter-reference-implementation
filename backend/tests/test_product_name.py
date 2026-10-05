"""The product's name has one source of truth: `product.json` (task-29).

Decided with the user 2026-10-05: the name is **provisional** — Tarrow, not yet
legally cleared — so a later rename must be quick. Everything that runs reads
`product.json`; what cannot read a value (prose, file names, YAML) carries the
name literally and `scripts/rename_product.py` rewrites it. Dated records keep
the wording they were written with; living documents and code may not carry a
retired name. Business decision: `docs/business/decisions/naming-brand-tarrow.md`.
"""
import json
import re
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts import rename_product

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = json.loads((ROOT / "product.json").read_text())


class TestTheSource:
    def test_it_holds_a_display_name_a_slug_and_the_names_retired(self):
        assert PRODUCT["name"] and re.fullmatch(r"[a-z][a-z0-9-]*", PRODUCT["slug"])
        assert PRODUCT["name"] not in PRODUCT["retired_names"]
        assert PRODUCT["retired_names"], "the names it replaced are kept, so no living file brings one back"


class TestWhatRunsReadsIt:
    def test_the_api_title_and_description(self):
        from main import app

        assert app.title == f"{PRODUCT['name']} API"
        assert f"**{PRODUCT['name']}**" in app.description

    def test_the_jinja_nav(self):
        from main import app

        page = TestClient(app).get("/ui/login")
        assert page.status_code == 200
        nav = page.text.split('class="navbar-brand"')[1].split("</span>")[0]
        assert nav.strip().strip(">").strip() == PRODUCT["name"]

    def test_the_session_cookie_is_named_after_the_slug(self):
        """Not a bare "session": browsers share cookies per host, not per port,
        so on localhost a bare name would meet every other dev app's cookie."""
        from app.auth.service import SESSION_COOKIE

        assert SESSION_COOKIE == f"{PRODUCT['slug']}_session"

    def test_the_react_page_title_comes_from_it(self):
        index = (ROOT / "frontend" / "index.html").read_text()
        assert "<title>%PRODUCT_NAME%</title>" in index


class TestNoRetiredNameIsLeft:
    def test_living_files_carry_no_retired_name(self):
        hits = rename_product.retired_name_hits(ROOT, PRODUCT["retired_names"])
        assert hits == [], "a retired name in a living file — run scripts/rename_product.py:\n" + "\n".join(hits)

    def test_no_wikilink_anywhere_points_at_a_retired_name(self):
        """Dated records keep their wording, but a link is plumbing: one to a
        renamed note is simply broken. ADR titles are permanent, so ADR links
        are not this test's business."""
        broken = []
        for path in rename_product.tracked(ROOT):
            if path.suffix != ".md":
                continue
            for link in re.findall(r"\[\[([^\]|#]+)", (ROOT / path).read_text(errors="ignore")):
                if link.startswith("ADR-"):
                    continue
                if any(old in link for old in PRODUCT["retired_names"]):
                    broken.append(f"{path}: [[{link}]]")
        assert broken == [], "\n".join(broken)


class TestTheRenameScript:
    """A later rename is one command; prove it on a scratch repository."""

    @pytest.fixture
    def repo(self, tmp_path):
        files = {
            "product.json": json.dumps({"name": "Tarrow", "slug": "tarrow", "retired_names": ["Old Name"]}),
            "README.md": "# Tarrow\n\nTarrow is used here. Tarrowish is not the name. [[MOC - Tarrow]]\n",
            "docs/architecture/MOC/MOC - Tarrow.md": "# MOC - Tarrow\n- [[ADR-001 — Tarrow Boundaries]]\n",
            "docs/architecture/ADR/ADR-001 — Tarrow Boundaries.md": "Tarrow, as written then. [[MOC - Tarrow]]\n",
            "backend/x.py": 'PACKAGE = "tarrow"\nCOOKIE = "tarrow_session"\n',
        }
        for name, text in files.items():
            (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / name).write_text(text)
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        return tmp_path

    def test_it_renames_living_text_files_and_links_and_retires_the_old_name(self, repo):
        rename_product.rename(repo, name="Corrigan", slug="corrigan")

        assert (repo / "README.md").read_text() == (
            "# Corrigan\n\nCorrigan is used here. Tarrowish is not the name. [[MOC - Corrigan]]\n")
        moc = repo / "docs/architecture/MOC/MOC - Corrigan.md"
        assert not (repo / "docs/architecture/MOC/MOC - Tarrow.md").exists() and moc.exists()
        # An ADR title is permanent, so its link is left alone.
        assert moc.read_text() == "# MOC - Corrigan\n- [[ADR-001 — Tarrow Boundaries]]\n"
        # A dated record keeps its wording; only its link to the renamed note follows.
        assert (repo / "docs/architecture/ADR/ADR-001 — Tarrow Boundaries.md").read_text() == (
            "Tarrow, as written then. [[MOC - Corrigan]]\n")
        # The slug as a whole word only: an identifier built at runtime is not touched.
        assert (repo / "backend/x.py").read_text() == 'PACKAGE = "corrigan"\nCOOKIE = "tarrow_session"\n'
        product = json.loads((repo / "product.json").read_text())
        assert (product["name"], product["slug"]) == ("Corrigan", "corrigan")
        assert product["retired_names"] == ["Old Name", "Tarrow"]

    def test_the_check_finds_a_retired_name_in_a_living_file_only(self, repo):
        (repo / "README.md").write_text("Old Name lives on. [[ADR-002 — Old Name Was Here]]\n")
        (repo / "docs/architecture/ADR/ADR-001 — Tarrow Boundaries.md").write_text("Old Name, then.\n")
        hits = rename_product.retired_name_hits(repo, ["Old Name"])
        assert hits == ["README.md:1: Old Name lives on. [[ADR-002 — Old Name Was Here]]"]

    def test_a_dry_run_changes_nothing(self, repo):
        before = {p: p.read_text() for p in repo.rglob("*") if p.is_file() and ".git" not in p.parts}
        changes = rename_product.rename(repo, name="Corrigan", slug="corrigan", dry_run=True)
        assert changes, "it says what it would change"
        after = {p: p.read_text() for p in repo.rglob("*") if p.is_file() and ".git" not in p.parts}
        assert after == before
