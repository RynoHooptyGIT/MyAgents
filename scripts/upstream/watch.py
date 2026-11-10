#!/usr/bin/env python3
"""Watch upstream repos, port the commits that apply cleanly, report the rest.

This repo was extracted from BMAD-METHOD, so there is no shared history to merge.
Each upstream commit since the baseline is classified against the path map in
manifest.json:

  ported            applied cleanly, tests passed, committed
  already-present   the change is already in this repo (reverse patch applies)
  not-applicable    touches no path this repo carries
  structural        matches structural_pattern; a human decides (never auto-ported)
  clean             applies, but the subject is not a fix/perf; listed for a human
  conflict          mapped, but the patch does not apply
  test-failed       applied, but tests failed; rolled back

Results go to a ledger so settled commits are not looked at again. The baseline
file never moves on its own: advancing it past unported structural commits would
hide them from every later run.

Usage:
  watch.py scan                    classify only, change nothing
  watch.py apply [--max N]         port clean commits as one commit each
  both take --report PATH to write the markdown report
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TERMINAL = {"ported", "already-present", "not-applicable"}
LIST_CAP = 40


class Watcher:
    def __init__(self, root: Path, manifest: dict):
        self.root = root
        self.m = manifest
        self.ledger_path = root / manifest["ledger"]

    # -- git helpers ---------------------------------------------------------

    def git(self, *args, check=True, stdin=None):
        r = subprocess.run(
            ["git", "-C", str(self.root), *args],
            capture_output=True, text=True, input=stdin,
        )
        if check and r.returncode:
            raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
        return r

    def ensure_remote(self, up: dict):
        if self.git("remote", "get-url", up["remote"], check=False).returncode:
            self.git("remote", "add", up["remote"], up["url"])
        self.git("fetch", "--no-tags", "-q", up["remote"], up["branch"])

    # -- ledger --------------------------------------------------------------

    def load_ledger(self) -> dict:
        if self.ledger_path.exists():
            return json.loads(self.ledger_path.read_text())
        return {}

    def save_ledger(self, ledger: dict):
        self.ledger_path.write_text(json.dumps(ledger, indent=1, sort_keys=True) + "\n")

    # -- classification ------------------------------------------------------

    @staticmethod
    def map_path(path: str, path_map: list):
        for up, local in path_map:
            if path.startswith(up):
                return local + path[len(up):]
        return None

    @staticmethod
    def rewrite_patch(patch: str, mapping: dict) -> str:
        """Point a patch's file headers at local paths. Content lines stay as-is."""
        out = []
        for line in patch.splitlines(keepends=True):
            if line.startswith(("diff --git ", "--- ", "+++ ")):
                for up, local in mapping.items():
                    line = line.replace(f"a/{up}", f"a/{local}").replace(f"b/{up}", f"b/{local}")
            out.append(line)
        return "".join(out)

    def new_commits(self, up: dict):
        base = (self.root / up["baseline_file"]).read_text().strip()
        rng = f"{base}..{up['remote']}/{up['branch']}"
        out = self.git("log", "--no-merges", "--reverse", "--date=short",
                       "--format=%H%x09%ad%x09%s", rng).stdout
        return [tuple(line.split("\t", 2)) for line in out.splitlines() if line]

    def classify(self, up: dict, sha: str, subject: str):
        """Return (status, detail, patch). status 'clean' means ready to apply."""
        files = self.git("diff-tree", "--no-commit-id", "--name-only", "-r",
                         "--no-renames", sha).stdout.split()
        if re.search(up["structural_pattern"], subject + " " + " ".join(files), re.I):
            return "structural", "matches structural_pattern", None
        mapping = {f: self.map_path(f, up["path_map"]) for f in files}
        mapping = {f: loc for f, loc in mapping.items() if loc}
        if not mapping:
            return "not-applicable", "no mapped paths", None
        patch = self.git("show", "--format=", "--no-renames", sha, "--", *mapping).stdout
        patch = self.rewrite_patch(patch, mapping)
        if self._apply_check(patch):
            return "clean", "", patch
        if self._apply_check(patch, reverse=True):
            return "already-present", "reverse patch applies", None
        return "conflict", "patch does not apply", patch

    def _apply_check(self, patch: str, reverse=False) -> bool:
        args = ["apply", "--check", "--whitespace=nowarn"] + (["--reverse"] if reverse else [])
        return self.git(*args, check=False, stdin=patch).returncode == 0

    # -- run -----------------------------------------------------------------

    def run(self, apply: bool, max_apply: int):
        ledger = self.load_ledger()
        rows = []  # (upstream, sha, date, subject, status, detail)
        ported = 0
        for up in self.m["upstreams"]:
            self.ensure_remote(up)
            seen = ledger.setdefault(up["name"], {})
            for sha, date, subject in self.new_commits(up):
                if seen.get(sha, {}).get("status") in TERMINAL:
                    continue
                status, detail, patch = self.classify(up, sha, subject)
                if status == "clean" and not re.match(up["auto_port_pattern"], subject):
                    detail = "not a fix: review before porting"
                elif status == "clean" and apply and ported < max_apply:
                    status, detail = self._port(up, sha, subject, patch)
                    ported += status == "ported"
                rows.append((up["name"], sha, date, subject, status, detail))
                seen[sha] = {"status": status, "subject": subject[:120], "date": date}
        if apply:
            self.save_ledger(ledger)
        return rows

    def _port(self, up: dict, sha: str, subject: str, patch: str):
        self.git("apply", "--index", "--whitespace=nowarn", stdin=patch)
        msg = (f"fix(upstream): port {up['name']} {sha[:8]} {subject}\n\n"
               f"Ported from {up['url']} commit {sha}.\n")
        self.git("commit", "-q", "-F", "-", stdin=msg)
        test = subprocess.run(self.m["test_cmd"], cwd=self.root, capture_output=True, text=True)
        if test.returncode:
            self.git("reset", "-q", "--hard", "HEAD~1")
            tail = (test.stdout + test.stderr).strip().splitlines() or ["no test output"]
            return "test-failed", tail[-1][:200]
        return "ported", ""


def report(rows, applied: bool) -> str:
    by = {}
    for r in rows:
        by.setdefault(r[4], []).append(r)
    verb = {"clean": "apply cleanly (not yet ported)", "ported": "ported in this run"}
    lines = ["# Upstream sync report", ""]
    lines.append("| Status | Commits |\n|---|---|")
    for status in ("ported", "clean", "conflict", "test-failed", "structural",
                   "already-present", "not-applicable"):
        if status in by:
            lines.append(f"| {verb.get(status, status)} | {len(by[status])} |")
    for status, title in (("ported", "Ported (review in this PR)"),
                          ("clean", "Apply cleanly, not yet ported"),
                          ("test-failed", "Applied but broke tests (rolled back)"),
                          ("conflict", "Conflicts: need a hand port"),
                          ("structural", "Structural: need a decision")):
        items = by.get(status)
        if not items:
            continue
        lines += ["", f"## {title}", ""]
        for name, sha, date, subject, _, detail in items[:LIST_CAP]:
            extra = f" — {detail}" if detail else ""
            lines.append(f"- `{sha[:8]}` {date} {subject}{extra}")
        if len(items) > LIST_CAP:
            lines.append(f"- … and {len(items) - LIST_CAP} more")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("mode", choices=["scan", "apply"])
    p.add_argument("--max", type=int, help="most commits to port this run")
    p.add_argument("--report", type=Path, help="write the markdown report here")
    args = p.parse_args(argv)

    manifest = json.loads((ROOT / "scripts/upstream/manifest.json").read_text())
    w = Watcher(ROOT, manifest)
    rows = w.run(args.mode == "apply", args.max or manifest["max_apply"])
    text = report(rows, args.mode == "apply")
    if args.report:
        args.report.write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
