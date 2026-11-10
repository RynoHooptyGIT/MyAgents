"""Git worktree seam: create the per-issue worktree and measure its diff."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List

from .proc import ProcResult, run as default_run


class WorkspaceError(RuntimeError):
    pass


@dataclass(frozen=True)
class DiffStats:
    paths: List[str]
    added: int
    deleted: int
    deleted_files: int


def slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")[:40].strip("-")
    return s or "issue"


class Workspace:
    def prepare(self, number: int, title_slug: str) -> Path:
        raise NotImplementedError

    def snapshot(self, path: Path) -> None:
        raise NotImplementedError

    def diff(self, path: Path) -> DiffStats:
        raise NotImplementedError


class FakeWorkspace(Workspace):
    def __init__(self, base: Path, stats: DiffStats):
        self._base, self._stats = Path(base), stats
        self.prepared = []

    def prepare(self, number, title_slug):
        p = self._base / f"wt-{number}"
        p.mkdir(parents=True, exist_ok=True)
        self.prepared.append((number, title_slug))
        return p

    def snapshot(self, path):
        pass

    def diff(self, path):
        return self._stats


class GitWorkspace(Workspace):
    def __init__(self, root, runner: Callable[..., ProcResult] = default_run,
                 base: str = "origin/main", binary_lines: int = 300):
        self._root = Path(root)
        self._run = runner
        self._base = base
        self._binary_lines = binary_lines

    def _git(self, args, cwd) -> str:
        r = self._run(["git"] + list(args), cwd=cwd, timeout=300)
        if r.returncode != 0:
            raise WorkspaceError(f"git {args[0]} failed ({r.returncode}): {r.stderr.strip()}")
        return r.stdout

    def prepare(self, number, title_slug):
        path = self._root / ".worktrees" / f"factory-{number}"
        self._git(["worktree", "add", str(path), "-b", f"factory/{int(number)}-{slug(title_slug)}", self._base],
                  self._root)
        return path

    def snapshot(self, path):
        if self._git(["status", "--porcelain"], path).strip():
            self._git(["add", "-A"], path)
            self._git(["commit", "-m", "factory: snapshot of worker output"], path)

    def diff(self, path):
        numstat = self._git(["diff", "--numstat", "--no-renames", "-z", f"{self._base}...HEAD"], path)
        gone = self._git(["diff", "--name-only", "--diff-filter=D", "--no-renames", "-z",
                          f"{self._base}...HEAD"], path)
        paths, added, deleted = [], 0, 0
        for rec in filter(None, numstat.split("\0")):
            a, d, p = rec.split("\t", 2)
            paths.append(p)
            if a == "-" or d == "-":
                added += self._binary_lines
            else:
                added += int(a)
                deleted += int(d)
        deleted_paths = [p for p in gone.split("\0") if p]
        return DiffStats(paths, added, deleted, len(deleted_paths))
