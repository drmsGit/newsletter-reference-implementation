#!/usr/bin/env python3
"""Structural check of the Backlog.md queue in docs/queue/. Read-only.

Reports what can be decided mechanically: files in the wrong folder, IDs
and ordinals that collide or sit outside their section, references to
tasks that do not exist, labels and types the config does not know, and
wikilinks that do not resolve. Judgement calls (is this task still true,
did an ADR answer it) are backlog-sequencer's, not this script's.

It never edits a task and never reorders anything: the order is a record
of human decisions. It prints findings and exits 1 if any are errors.

Usage: python3 .claude/scripts/queue_check.py [--repo PATH]
"""

import argparse
import re
import sys
from pathlib import Path

# Ordinal ranges are the old docs/backlog.md sections (see CLAUDE.md).
SECTIONS = {1: "Bugs", 2: "Features", 3: "Needs ADR"}
DONE_BAND = 5
AREA_LABELS = {"backend", "frontend", "docs"}
TASK_REF = re.compile(r"\btask-(\d+)\b", re.IGNORECASE)
WIKILINK = re.compile(r"\[\[([^\]|#]+)")


def parse_frontmatter(text):
    """Parse the YAML subset Backlog.md writes: scalars, `>-` folded
    scalars, and `- item` lists. Returns a dict of strings and lists."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    fields, key, folding = {}, None, False
    for line in text[4:end].split("\n"):
        if line.startswith("  - ") and key:
            fields[key].append(line[4:].strip().strip("'\""))
        elif line.startswith("  ") and folding and key:
            fields[key] = (fields[key] + " " + line.strip()).strip()
        else:
            m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
            if not m:
                continue
            key, value = m.group(1), m.group(2).strip()
            folding = value in (">-", ">", "|", "|-")
            if folding:
                fields[key] = ""
            elif value in ("", "[]"):
                fields[key] = []
            else:
                fields[key] = value.strip("'\"")
    return fields


def section(text, name):
    m = re.search(
        rf"<!-- SECTION:{name}:BEGIN -->\n(.*?)\n<!-- SECTION:{name}:END -->",
        text, re.DOTALL)
    return m.group(1) if m else ""


def config_list(config_text, key):
    m = re.search(rf"^{key}:\s*\[(.*)\]\s*$", config_text, re.MULTILINE)
    return [v.strip().strip("'\"") for v in m.group(1).split(",")] if m else []


def load(repo):
    queue = repo / "docs" / "queue"
    tasks = []
    for folder in ("tasks", "completed", "archive/tasks"):
        for path in sorted((queue / folder).glob("*.md")):
            text = path.read_text(encoding="utf-8")
            fm = parse_frontmatter(text)
            tasks.append({
                "path": path, "folder": folder, "fm": fm,
                "id": (fm or {}).get("id", "").lower(),
                "body": section(text, "DESCRIPTION"),
                "notes": section(text, "NOTES"),
            })
    return tasks


def check(repo):
    errors, warnings = [], []
    config = (repo / "backlog.config.yml").read_text(encoding="utf-8")
    statuses = {s.lower() for s in config_list(config, "statuses")}
    priorities = {p.lower() for p in config_list(config, "priorities")}
    types = {t.lower() for t in config_list(config, "types")}
    labels = set(config_list(config, "labels"))

    vault = {p.stem for p in (repo / "docs").rglob("*.md")
             if not any(part.startswith(".") for part in p.parts)}
    tasks = load(repo)
    by_id = {}
    for t in tasks:
        by_id.setdefault(t["id"], []).append(t)

    def name(t):
        return f"{t['id'] or t['path'].name} ({t['folder']})"

    ordinals = {}
    for t in tasks:
        fm = t["fm"]
        if fm is None:
            errors.append(f"{t['path'].name}: no readable frontmatter")
            continue
        status = fm.get("status", "")
        open_task = t["folder"] == "tasks"

        # Folder agrees with status.
        if open_task and status == "Done":
            errors.append(f"{name(t)}: status Done but still in tasks/ — "
                          f"close with `backlog task complete {t['id']}`")
        if t["folder"] == "completed" and status != "Done":
            errors.append(f"{name(t)}: in completed/ with status '{status}'")

        # Filename carries the same ID as the frontmatter.
        if not t["path"].name.lower().startswith(t["id"] + " - "):
            errors.append(f"{name(t)}: filename does not start with its id")

        # Values the config knows.
        if status.lower() not in statuses:
            errors.append(f"{name(t)}: status '{status}' not in config")
        prio = fm.get("priority")
        if prio and prio.lower() not in priorities:
            errors.append(f"{name(t)}: priority '{prio}' not in config")
        ttype = fm.get("type")
        if ttype and ttype.lower() not in types:
            errors.append(f"{name(t)}: type '{ttype}' not in config")
        for label in fm.get("labels", []):
            if label not in labels:
                errors.append(f"{name(t)}: label '{label}' not in config")

        # Dependencies point at tasks that exist.
        for dep in fm.get("dependencies", []):
            if dep.lower() not in by_id:
                errors.append(f"{name(t)}: depends on {dep}, which does not exist")

        # task-N mentioned in description or notes must exist.
        for ref in sorted({f"task-{n}" for n in TASK_REF.findall(t["body"] + t["notes"])}):
            if ref not in by_id:
                errors.append(f"{name(t)}: mentions {ref}, which does not exist")

        if not open_task:
            continue

        # From here on, open tasks only.
        try:
            ordinal = int(fm.get("ordinal", ""))
        except ValueError:
            errors.append(f"{name(t)}: no ordinal — its place in the order is unknown")
            ordinal = None
        if ordinal is not None:
            band = ordinal // 100000
            if band not in SECTIONS:
                errors.append(f"{name(t)}: ordinal {ordinal} is outside the "
                              f"Bugs / Features / Needs ADR ranges")
            ordinals.setdefault(ordinal, []).append(t["id"])
            needs_adr = "needs-adr" in fm.get("labels", [])
            if needs_adr and band != 3:
                errors.append(f"{name(t)}: labelled needs-adr but ordered in "
                              f"{SECTIONS.get(band, band)}")
            if band == 3 and not needs_adr:
                errors.append(f"{name(t)}: in the Needs ADR range without the needs-adr label")

        if not ttype:
            warnings.append(f"{name(t)}: no type")
        if not AREA_LABELS & set(fm.get("labels", [])):
            warnings.append(f"{name(t)}: no area label (backend / frontend / docs)")
        if not t["body"].strip():
            errors.append(f"{name(t)}: empty description")

        for target in sorted(set(WIKILINK.findall(t["body"]))):
            if target.strip() not in vault:
                errors.append(f"{name(t)}: wikilink [[{target}]] does not resolve")

    for task_id, found in by_id.items():
        if task_id and len(found) > 1:
            errors.append(f"{task_id}: exists {len(found)} times — "
                          + ", ".join(f"{x['folder']}/{x['path'].name[:40]}" for x in found))
    for ordinal, ids in sorted(ordinals.items()):
        if len(ids) > 1:
            errors.append(f"ordinal {ordinal} shared by {', '.join(ids)} — the order between them is undefined")

    parked = [t["id"] for t in tasks if t["folder"] == "tasks"
              and (t["fm"] or {}).get("priority", "").lower() == "parked"]
    return errors, warnings, parked


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", type=Path,
                        default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    errors, warnings, parked = check(args.repo)

    for label, items in (("ERROR", errors), ("WARN", warnings)):
        for item in items:
            print(f"{label}  {item}")
    if parked:
        print(f"INFO   Parked: {', '.join(sorted(parked, key=lambda s: int(s.split('-')[1])))}")
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
