"""Is every installed package one we chose? (task-236; ADR-189)

Compares what is installed with what is locked, and fails on any difference:

  - the backend venv against `backend/requirements.txt` + `requirements-dev.txt`
    (ADR-189's pip-tools locks), read through the venv's own pip;
  - `frontend/node_modules` against `frontend/package-lock.json`, read through
    npm's record of what it installed, `node_modules/.package-lock.json`;
  - `frontend/package.json` against the lock's root entry, so neither changes
    without the other.

A difference is a package installed but not locked, locked at another
version, or locked and missing. An npm package the lock marks optional may be
missing: those are builds for other platforms (`@rolldown/binding-android-*`
on a Mac). A name within two edits of a locked one is called out, because
that is the shape a typo or a squatted name takes — `httpx2` beside `httpx`,
which sat in the venv for three months before this existed.

What it does not do: ask whether a package is known to be bad (task-105's
vulnerability scan), or how old a name is on its registry (that needs a
network lookup at check time).

    backend/venv/bin/python backend/scripts/check_installed.py
    backend/venv/bin/python backend/scripts/check_installed.py --backend backend --frontend frontend

Exits 0 when everything matches, 1 otherwise. Reads nothing but the locks and
the installs — never `.env`.
"""
import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class OptionalVersion(str):
    """A locked version that may be absent: an npm build for another platform."""


@dataclass(frozen=True)
class Problem:
    ecosystem: str
    kind: str  # "not locked", "other version", "missing", "not in package.json", "not in the lock", "other range"
    name: str
    installed: str | None = None
    locked: str | None = None
    looks_like: str | None = None

    def describe(self) -> str:
        if self.kind == "not locked":
            text = f"{self.ecosystem}: {self.name} {self.installed} is installed but not locked"
            if self.looks_like:
                text += f" — it looks like {self.looks_like}: a typo, or a name squatting on it?"
            return text
        if self.kind == "other version":
            return f"{self.ecosystem}: {self.name} is {self.installed} here but locked at {self.locked}"
        if self.kind == "not in package.json":
            return f"{self.ecosystem}: the lock asks for {self.name} {self.locked}, package.json does not"
        if self.kind == "not in the lock":
            return f"{self.ecosystem}: package.json asks for {self.name} {self.installed}, the lock does not"
        if self.kind == "other range":
            return f"{self.ecosystem}: package.json asks for {self.name} {self.installed}, the lock for {self.locked}"
        return f"{self.ecosystem}: {self.name} {self.locked} is locked but not installed"


def normalise(name: str) -> str:
    """PEP 503: case and runs of '-', '_' and '.' do not distinguish names."""
    return re.sub(r"[-_.]+", "-", name).lower()


def read_python_lock(path: Path) -> dict[str, str]:
    """`name==version` lines of a pip-compile lock, names normalised."""
    pins = {}
    for line in path.read_text().splitlines():
        match = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s\\;]+)", line)
        if match:
            pins[normalise(match.group(1))] = match.group(2)
    return pins


def installed_python(python: str) -> dict[str, str]:
    """What the given interpreter's environment holds, pip and setuptools included."""
    listing = subprocess.run([python, "-m", "pip", "list", "--format=json", "--disable-pip-version-check"],
                             capture_output=True, text=True, check=True)
    return {normalise(p["name"]): p["version"] for p in json.loads(listing.stdout)}


def _npm_packages(path: Path) -> dict[str, str]:
    packages = json.loads(path.read_text()).get("packages", {})
    out = {}
    for key, entry in packages.items():
        if not key or entry.get("link"):
            continue  # the root project, or a workspace link
        name = key.removeprefix("node_modules/")
        version = entry.get("version", "")
        out[name] = OptionalVersion(version) if entry.get("optional") else version
    return out


def read_npm(frontend: Path) -> tuple[dict[str, str], dict[str, str]]:
    """(locked, installed) for the frontend, named by path below node_modules
    so a nested copy (`a/node_modules/b`) is told apart from the top-level one."""
    return (_npm_packages(frontend / "package-lock.json"),
            _npm_packages(frontend / "node_modules" / ".package-lock.json"))


def package_json_against_lock(frontend: Path) -> list[Problem]:
    """package.json against the lock's root entry, which records what
    package.json asked for when the lock was written: a dependency in one and
    not the other, or at another range, means one changed without the other."""
    def wanted(entry: dict) -> dict[str, str]:
        return {**entry.get("dependencies", {}), **entry.get("devDependencies", {})}

    asked = wanted(json.loads((frontend / "package.json").read_text()))
    recorded = wanted(json.loads((frontend / "package-lock.json").read_text()).get("packages", {}).get("", {}))
    problems = []
    for name in sorted(set(asked) | set(recorded)):
        if name not in asked:
            problems.append(Problem("npm", "not in package.json", name, locked=recorded[name]))
        elif name not in recorded:
            problems.append(Problem("npm", "not in the lock", name, installed=asked[name]))
        elif asked[name] != recorded[name]:
            problems.append(Problem("npm", "other range", name, installed=asked[name], locked=recorded[name]))
    return problems


def _distance(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def _looks_like(name: str, locked: dict[str, str]) -> str | None:
    base = name.rsplit("/", 1)[-1]
    candidates = sorted(
        (_distance(base, other.rsplit("/", 1)[-1]), other) for other in locked
        if other != name and len(base) >= 4)
    return candidates[0][1] if candidates and candidates[0][0] <= 2 else None


def compare(ecosystem: str, locked: dict[str, str], installed: dict[str, str]) -> list[Problem]:
    problems = []
    for name in sorted(installed):
        if name not in locked:
            problems.append(Problem(ecosystem, "not locked", name, installed=installed[name],
                                    looks_like=_looks_like(name, locked)))
        elif installed[name] != locked[name]:
            problems.append(Problem(ecosystem, "other version", name, installed=installed[name],
                                    locked=str(locked[name])))
    for name in sorted(set(locked) - set(installed)):
        if not isinstance(locked[name], OptionalVersion):
            problems.append(Problem(ecosystem, "missing", name, locked=str(locked[name])))
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail when an installed package is not the locked one.")
    parser.add_argument("--backend", type=Path, default=ROOT / "backend")
    parser.add_argument("--frontend", type=Path, default=ROOT / "frontend")
    parser.add_argument("--python", default=None,
                        help="the interpreter whose packages to check (default: <backend>/venv, else this one)")
    args = parser.parse_args(argv)

    problems: list[Problem] = []
    locks = [args.backend / "requirements.txt", args.backend / "requirements-dev.txt"]
    locked = {}
    for lock in locks:
        locked.update(read_python_lock(lock))
    venv_python = args.backend / "venv" / "bin" / "python"
    python = args.python or (str(venv_python) if venv_python.exists() else sys.executable)
    problems += compare("python", locked, installed_python(python))

    if (args.frontend / "package.json").exists():
        problems += package_json_against_lock(args.frontend)
    if (args.frontend / "node_modules").exists():
        problems += compare("npm", *read_npm(args.frontend))
    else:
        print(f"npm: {args.frontend / 'node_modules'} is not installed; not checked")

    for problem in problems:
        print(problem.describe())
    if problems:
        print(f"\n{len(problems)} difference(s) between what is installed and what is locked.")
        print("Re-install from the locks (ADR-189), or change the lock in a commit of its own.")
        return 1
    print("Every installed package is the locked one.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
