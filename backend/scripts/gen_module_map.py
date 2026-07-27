"""Auto-generate the module dependency map for the Code docs.

Anti-drift tool: instead of hand-maintaining "module X depends on module Y" on
every module page, this reads the actual `import` graph from `backend/app/` and
regenerates the map. Re-run it whenever module boundaries change:

    cd backend && python scripts/gen_module_map.py

It writes `docs/architecture/Code/Module dependency map.md` (a mermaid graph +
an edge table) and prints the edges. It parses with `ast`, so it catches
**function-local imports too** (e.g. delivery imports audience inside a function
to keep the dependency one-directional) — a plain top-of-file grep would miss
those.

Only edges between the top-level `app.<module>` packages are recorded;
intra-module imports and stdlib/third-party imports are ignored.
"""
from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

# backend/app — the package whose sub-packages are our "modules".
APP_DIR = Path(__file__).resolve().parent.parent / "app"
REPO_ROOT = APP_DIR.parent.parent
OUT_FILE = REPO_ROOT / "docs" / "architecture" / "Code" / "Module dependency map.md"

# Not real code modules: empty placeholders (automation/privacy have no .py yet),
# Jinja assets (templates), and `database` — which is app/database.py, a shared
# SQLAlchemy Base/session file every module imports, not a module of its own.
# Excluding it keeps the map about real inter-module relationships, not plumbing.
NON_MODULES = {"templates", "__pycache__", "database", "automation", "privacy"}


def module_of(path: Path) -> str | None:
    """The top-level app module a file belongs to, e.g. app/delivery/x.py -> 'delivery'."""
    rel = path.relative_to(APP_DIR)
    if len(rel.parts) < 2:  # a file directly in app/ (e.g. database.py) — not a module
        return None
    return rel.parts[0]


def imported_module(name: str | None) -> str | None:
    """From a dotted import target like 'app.audience.service', return 'audience'."""
    if not name:
        return None
    parts = name.split(".")
    if len(parts) >= 2 and parts[0] == "app":
        return parts[1]
    return None


def collect_edges() -> dict[str, set[str]]:
    edges: dict[str, set[str]] = defaultdict(set)
    for py in sorted(APP_DIR.rglob("*.py")):
        if "__pycache__" in py.parts:
            continue
        src_module = module_of(py)
        if src_module is None or src_module in NON_MODULES:
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            targets: list[str | None] = []
            if isinstance(node, ast.ImportFrom):
                targets.append(node.module)
            elif isinstance(node, ast.Import):
                targets.extend(alias.name for alias in node.names)
            for target in targets:
                dst_module = imported_module(target)
                if dst_module and dst_module != src_module and dst_module not in NON_MODULES:
                    edges[src_module].add(dst_module)
    return edges


def all_modules() -> list[str]:
    """A module = a folder under app/ holding at least one .py file. Note some
    real modules (content, frontend, providers) have no __init__.py, so presence
    of source — not of __init__.py — is what counts."""
    result = []
    for d in sorted(APP_DIR.iterdir()):
        if not d.is_dir() or d.name in NON_MODULES:
            continue
        if any(p.name != "__pycache__" for p in d.glob("*.py")):
            result.append(d.name)
    return result


def render(edges: dict[str, set[str]], modules: list[str]) -> str:
    # depended-on-by = reverse of the edge set
    depended_on_by: dict[str, set[str]] = defaultdict(set)
    for src, dsts in edges.items():
        for dst in dsts:
            depended_on_by[dst].add(src)

    lines: list[str] = []
    lines.append("---")
    lines.append("type: code-map")
    lines.append("topic:")
    lines.append("  - architecture")
    lines.append("  - code-map")
    lines.append("---")
    lines.append("")
    lines.append("# Module dependency map")
    lines.append("")
    lines.append(
        "> **Auto-generated** by `backend/scripts/gen_module_map.py` from the "
        "`import` graph — do not edit by hand. Re-run after changing module "
        "boundaries. Part of [[MOC - System Overview]]."
    )
    lines.append("")
    lines.append(
        "An arrow **A --> B** means module A imports from module B (A depends on B). "
        "Function-local imports are included."
    )
    lines.append("")
    lines.append("```mermaid")
    lines.append("graph LR")
    for src in modules:
        for dst in sorted(edges.get(src, set())):
            lines.append(f"  {src} --> {dst}")
    # Modules with no edges at all still appear as nodes.
    connected = set(edges) | {d for dsts in edges.values() for d in dsts}
    for m in modules:
        if m not in connected:
            lines.append(f"  {m}")
    lines.append("```")
    lines.append("")
    lines.append("## Edge table")
    lines.append("")
    lines.append("| Module | Depends on → | Depended on by ← |")
    lines.append("|---|---|---|")
    for m in modules:
        deps = ", ".join(sorted(edges.get(m, set()))) or "—"
        rdeps = ", ".join(sorted(depended_on_by.get(m, set()))) or "—"
        lines.append(f"| **{m}** | {deps} | {rdeps} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    edges = collect_edges()
    modules = all_modules()
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(render(edges, modules), encoding="utf-8")
    print(f"wrote {OUT_FILE.relative_to(REPO_ROOT)}")
    print(f"{len(modules)} modules, {sum(len(v) for v in edges.values())} edges\n")
    for src in modules:
        for dst in sorted(edges.get(src, set())):
            print(f"  {src} -> {dst}")


if __name__ == "__main__":
    main()
