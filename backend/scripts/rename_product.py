"""Rename the product: `product.json` is the one place the name is decided (task-29).

The name is a neutral working title (2026-10-12) until a brand is chosen — see
`docs/business/decisions/naming-brand-tarrow.md` — so renaming must be quick.
Everything that runs reads `product.json` (`app/product.py`, `vite.config.ts`);
this script rewrites what cannot read a value: prose, file names and YAML.

    venv/bin/python scripts/rename_product.py --name Corrigan --slug corrigan --dry-run
    venv/bin/python scripts/rename_product.py --name Corrigan --slug corrigan

What it does, in the repository's tracked files:
- **living files**: every whole-word use of the current name becomes the new
  one, and of the current slug the new slug; a file or folder named after the
  current name is renamed;
- **every Markdown file, dated ones too**: a wikilink to a renamed note
  follows it — a link is plumbing, and a broken one helps nobody;
- `product.json`: the new name and slug, the old name added to
  `retired_names`, which `tests/test_product_name.py` keeps out of living files.

What it leaves alone, deliberately (decided with the user, 2026-10-05):
- **dated records** (`DATED` below) keep the wording they were written with;
- **ADR titles and links to them** — ADR numbers and titles are permanent;
- "newsletter" as a plain word (task-48 is about those).

What it cannot do is printed at the end (`CANNOT`).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: Records of what was true on a date. They keep their wording; only their
#: links to renamed notes follow (user, 2026-10-05).
DATED = (
    "docs/architecture/ADR/",
    "docs/architecture/interview-prep/",
    "docs/business/decisions/",
    "docs/queue/",
    "docs/backlog.md",
    "docs/playbook-strategy.md",
    "docs/react-session-brief.md",
    "docs/business-interview-baseline.md",
    # Added 2026-10-08 (task-97): an interview log, a dated summary and a
    # dated sweep report — records of a date like the others.
    "docs/business-interview.md",
    "docs/weekly-summary.md",
    "docs/architecture/code-slimmer-report.md",
    "docs/history/",  # HANDOFF.md moved here 2026-10-09 (task-306)
    ".claude/agent-memory/",
    "product.json",
)

#: Text files the script reads; anything else is left as it is.
TEXT = {".md", ".py", ".ts", ".tsx", ".html", ".json", ".yml", ".yaml", ".css", ".txt", ".toml", ".sql", ".sh"}

#: A link to an ADR, which keeps its permanent title.
ADR_LINK = re.compile(r"\[\[ADR-\d+[^\]]*\]\]")

#: Steps outside the tracked files, printed after every rename.
CANNOT = """\
Not done by this script, deliberately:
- The GitHub repository and the local folder keep their names until the name is
  legally cleared; then the product moves to its own GitHub account (user, 2026-10-05).
  Moving the local folder: close every session, move it, rebuild backend/venv
  (its scripts hold the absolute path), copy Claude's project memory folder to
  the new path's key, reopen the Obsidian vault.
- Signed-in browsers are signed out once: the session cookie is named after the slug.
- Restart the preview servers, so the backend and Vite read product.json again."""


def tracked(root: Path) -> list[Path]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True).stdout
    return [Path(p) for p in out.decode().split("\0") if p]


def is_dated(path: Path) -> bool:
    text = path.as_posix()
    return any(text == d or text.startswith(d) for d in DATED)


def _word(term: str) -> re.Pattern:
    return re.compile(rf"(?<![\w-]){re.escape(term)}(?![\w-])")


def _outside_adr_links(text: str, change) -> str:
    """Apply `change` to `text` except inside ADR wikilinks."""
    parts, last = [], 0
    for match in ADR_LINK.finditer(text):
        parts += [change(text[last:match.start()]), match.group(0)]
        last = match.end()
    return "".join(parts + [change(text[last:])])


def retired_name_hits(root: Path, retired: list[str]) -> list[str]:
    """`path:line: text` for every retired name in a living file (ADR links aside)."""
    hits = []
    patterns = [_word(name) for name in retired]
    for path in tracked(root):
        if is_dated(path) or path.suffix not in TEXT or not (root / path).is_file():
            continue
        for number, line in enumerate((root / path).read_text(errors="ignore").splitlines(), 1):
            plain = ADR_LINK.sub("", line)
            if any(p.search(plain) for p in patterns):
                hits.append(f"{path}:{number}: {line.strip()[:120]}")
    return hits


def rename(root: Path, *, name: str, slug: str, dry_run: bool = False) -> list[str]:
    """Rename the product from what `product.json` says to `name`/`slug`.
    Returns what changed (or would change)."""
    product_file = root / "product.json"
    product = json.loads(product_file.read_text())
    old_name, old_slug = product["name"], product["slug"]
    changes: list[str] = []

    def rewrite(text: str) -> str:
        text = _word(old_name).sub(name, text)
        return _word(old_slug).sub(slug, text)

    # 1. Living files' content.
    for path in tracked(root):
        full = root / path
        if is_dated(path) or path.suffix not in TEXT or not full.is_file():
            continue
        before = full.read_text()
        after = _outside_adr_links(before, rewrite)
        if after != before:
            changes.append(f"edit {path}")
            if not dry_run:
                full.write_text(after)

    # 2. Living files named after the product, and the notes they were.
    renamed_notes: dict[str, str] = {}
    for path in tracked(root):
        if is_dated(path) or not _word(old_name).search(path.name):
            continue
        target = path.with_name(_word(old_name).sub(name, path.name))
        changes.append(f"move {path} -> {target}")
        if path.suffix == ".md":
            renamed_notes[path.stem] = target.stem
        if not dry_run:
            subprocess.run(["git", "mv", str(path), str(target)], cwd=root, check=True)

    # 3. Links to a renamed note, in every Markdown file — dated ones too.
    if renamed_notes:
        link = re.compile(r"\[\[(" + "|".join(re.escape(s) for s in renamed_notes) + r")(?=[\]|#])")
        for path in tracked(root):
            full = root / path
            if path.suffix != ".md" or not full.is_file():
                continue
            before = full.read_text()
            after = link.sub(lambda m: "[[" + renamed_notes[m.group(1)], before)
            if after != before:
                changes.append(f"relink {path}")
                if not dry_run:
                    full.write_text(after)

    # 4. The source of truth, last.
    changes.append(f"product.json: {old_name}/{old_slug} -> {name}/{slug}")
    if not dry_run:
        retired = product.get("retired_names", [])
        product.update(name=name, slug=slug,
                       retired_names=retired + ([old_name] if old_name not in retired else []))
        product_file.write_text(json.dumps(product, indent=2) + "\n")
    return changes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--name", required=True, help="the new display name, e.g. Omnichannel Orchestration Reference")
    parser.add_argument("--slug", required=True, help="the new lowercase slug, e.g. omnichannel-orchestration-reference")
    parser.add_argument("--dry-run", action="store_true", help="list what would change; change nothing")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9-]*", args.slug):
        parser.error("the slug is lowercase letters, digits and hyphens, starting with a letter")
    for line in rename(ROOT, name=args.name, slug=args.slug, dry_run=args.dry_run):
        print(line)
    print()
    print(CANNOT)


if __name__ == "__main__":
    main()
