"""Deterministic verification, run from the trusted checkout: `python3 -m scripts.factory.sandbox_verify`.

Operates on the `work/` checkout of the factory branch (data) and writes `verify.json`. Two checks,
each in its own scratch git worktree so one cannot contaminate the other or `work/`:

1. Revert check: do the new or changed Python tests fail once the rest of the change is reverted?
2. Sealed run: apply the sealed acceptance tests (validated again here) and run them.

Both run code from the branch on this machine, which is also the machine that writes verify.json,
so a hostile change can forge the result (see docs/factory.md). Inputs arrive as environment
variables and are validated before use.

pytest exit codes used (https://docs.pytest.org/en/stable/reference/exit-codes.html):
0 all passed, 1 some failed, 2 interrupted (collection errors land here), 3 internal error,
4 usage error, 5 no tests collected. For the revert check without the change, 1 and 2 both mean
"fails without the change": an import error because the implementation is missing is a legitimate
failure. Because exit 2 also covers a test file that is simply broken, the same tests must first
pass WITH the change (exit 0 and at least one test passed), otherwise the status is
`fails_with_change`. 5 means `no_new_tests`; anything else, and a timeout, is `error`.
"""
from __future__ import annotations

import base64
import binascii
import contextlib
import gzip
import io
import json
import os
import posixpath
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Mapping, Optional, Tuple

from . import envscrub
from .classifier import glob_match
from .policy import PolicyError, Policy, load as load_policy
from .proc import ProcResult, run as default_run
from .sandbox_worker import BRANCH_RE, REQUEST_ID_RE
from .sealed import SealedInvalid, issue_dir, validate_sealed_patch

PYTEST_TIMEOUT_S = 900
GIT_TIMEOUT_S = 300
MAX_JUNIT_BYTES = 5_000_000
BASE_REF = "origin/main"
BUNDLE_SLACK = 4096          # the canary file the operator side appends
_SHA = re.compile(r"[0-9a-f]{40}")
_ISSUE = re.compile(r"[0-9]{1,9}")
_NOT_TESTS = ("conftest.py", "__init__.py")
_NO_COUNTS = {"total": 0, "failed": 0, "errors": 0, "skipped": 0}


class VerifyInputError(ValueError):
    pass


class _StepError(RuntimeError):
    pass


def _require(environ: Mapping[str, str], name: str) -> str:
    v = environ.get(name)
    if v is None:
        raise VerifyInputError(f"missing input {name}")
    return v


def decode_bundle(b64: str, max_bytes: int) -> Optional[bytes]:
    if not b64:
        return None
    try:
        raw = base64.b64decode(b64, validate=True)
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as g:
            data = g.read(max_bytes + 1)
    except (binascii.Error, ValueError, OSError, EOFError) as e:
        raise VerifyInputError(f"sealed bundle is not valid gzip+base64: {type(e).__name__}") from None
    if len(data) > max_bytes:
        raise VerifyInputError("sealed bundle too large")
    return data


def validate_inputs(environ: Mapping[str, str], policy: Policy) -> Dict[str, object]:
    branch = _require(environ, "FACTORY_BRANCH")
    if not BRANCH_RE.fullmatch(branch):
        raise VerifyInputError("branch must match factory/<number>-<slug>")
    request_id = _require(environ, "FACTORY_REQUEST_ID")
    if not REQUEST_ID_RE.fullmatch(request_id):
        raise VerifyInputError("request_id must match [a-f0-9]{8,64}")
    sha = _require(environ, "FACTORY_EXPECTED_SHA")
    if not _SHA.fullmatch(sha):
        raise VerifyInputError("expected_sha must be 40 lowercase hex characters")
    raw_issue = _require(environ, "FACTORY_ISSUE")
    if not _ISSUE.fullmatch(raw_issue):
        raise VerifyInputError("issue must be a non-negative integer")
    issue = int(raw_issue)
    if branch.split("/", 1)[1].split("-", 1)[0] != str(issue):
        raise VerifyInputError("branch does not belong to the issue")
    bundle = decode_bundle(environ.get("FACTORY_SEALED_B64", ""), policy.sealed.max_patch_bytes + BUNDLE_SLACK)
    return {"branch": branch, "request_id": request_id, "sha": sha, "issue": issue, "bundle": bundle}


class _Ctx:
    def __init__(self, policy: Policy, runner: Callable[..., ProcResult], env: Dict[str, str]):
        self.policy, self.runner, self.env = policy, runner, env

    def git(self, cwd, *args: str, timeout: int = GIT_TIMEOUT_S) -> ProcResult:
        return self.runner(["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", *args],
                           cwd=cwd, timeout=timeout, env=self.env)

    def git_ok(self, cwd, *args: str) -> str:
        r = self.git(cwd, *args)
        if r.returncode != 0:
            raise _StepError(f"git {args[0]} failed ({r.returncode}): {r.stderr.strip()[:200]}")
        return r.stdout

    def pytest(self, cwd, paths: List[str], junit: Path) -> int:
        argv = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", "--no-header",
                f"--junitxml={junit}", "--", *paths]
        return self.runner(argv, cwd=cwd, timeout=PYTEST_TIMEOUT_S, env=self.env).returncode


@contextlib.contextmanager
def scratch_worktree(ctx: _Ctx, work: Path) -> Iterator[Path]:
    """A throwaway detached worktree of work's HEAD, outside work. Removed afterwards."""
    tmp = Path(tempfile.mkdtemp(prefix="factory-verify-"))
    wt = tmp / "wt"
    try:
        ctx.git_ok(work, "worktree", "add", "--detach", str(wt), "HEAD")
        yield wt
    finally:
        ctx.git(work, "worktree", "remove", "--force", str(wt))
        ctx.git(work, "worktree", "prune")
        shutil.rmtree(tmp, ignore_errors=True)


def junit_counts(path: Path) -> Optional[Dict[str, int]]:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_JUNIT_BYTES:
            return None
        root = ET.parse(str(path)).getroot()
        total = failed = errors = skipped = 0
        for ts in root.iter("testsuite"):
            total += int(ts.get("tests", 0))
            failed += int(ts.get("failures", 0))
            errors += int(ts.get("errors", 0))
            skipped += int(ts.get("skipped", 0))
    except (ET.ParseError, ValueError, OSError):
        return None
    return {"total": total, "failed": failed, "errors": errors, "skipped": skipped}


def _name_status(raw: str) -> List[Tuple[str, str]]:
    toks = raw.split("\0")
    if toks and toks[-1] == "":
        toks.pop()
    if len(toks) % 2:
        raise _StepError("unparseable name-status output")
    return [(toks[i], toks[i + 1]) for i in range(0, len(toks), 2)]


def _is_test_file(policy: Policy, path: str) -> bool:
    return (path.endswith(".py") and posixpath.basename(path) not in _NOT_TESTS
            and any(glob_match(p, path) for p in policy.test_paths))


def _chunks(items: List[str], n: int = 100) -> Iterator[List[str]]:
    for i in range(0, len(items), n):
        yield items[i:i + n]


def revert_check(work: Path, ctx: _Ctx) -> Dict[str, object]:
    def result(status: str, tests: int = 0, code: Optional[int] = None) -> Dict[str, object]:
        return {"status": status, "tests": tests, "exit_code": code}

    base = ctx.git_ok(work, "merge-base", BASE_REF, "HEAD").strip()
    changes = _name_status(ctx.git_ok(work, "diff", "--name-status", "-z", "--no-renames", f"{BASE_REF}...HEAD"))
    tests = [p for st, p in changes if st in ("A", "M", "T") and _is_test_file(ctx.policy, p)]
    rest = [(st, p) for st, p in changes if p not in tests]
    if not tests:
        return result("no_new_tests")
    if not rest:
        return result("nothing_to_revert", len(tests))
    for st, _ in rest:
        if st not in ("A", "M", "D", "T"):
            raise _StepError(f"unexpected change status {st!r}")
    out = Path(tempfile.mkdtemp(prefix="factory-junit-"))
    try:
        with scratch_worktree(ctx, work) as wt:                      # 1. with the change
            code = ctx.pytest(wt, tests, out / "with.xml")
            counts = junit_counts(out / "with.xml")
        if code == 5:
            return result("no_new_tests", len(tests), code)
        if code not in (0, 1, 2):
            return result("error", len(tests), code)
        passed = counts["total"] - counts["skipped"] - counts["failed"] - counts["errors"] if counts else 0
        if code != 0 or passed < 1:
            return result("fails_with_change", len(tests), code)
        with scratch_worktree(ctx, work) as wt:                      # 2. everything but the tests reverted
            existed = [p for st, p in rest if st in ("M", "D", "T")]
            added = [p for st, p in rest if st == "A"]
            for chunk in _chunks(existed):
                ctx.git_ok(wt, "checkout", base, "--", *chunk)
            for chunk in _chunks(added):
                ctx.git_ok(wt, "rm", "-f", "-q", "--ignore-unmatch", "--", *chunk)
            code = ctx.pytest(wt, tests, out / "without.xml")
        if code in (1, 2):
            return result("fails_without_change", len(tests), code)
        if code == 0:
            return result("passes_without_change", len(tests), code)
        if code == 5:
            return result("no_new_tests", len(tests), code)
        return result("error", len(tests), code)
    finally:
        shutil.rmtree(out, ignore_errors=True)


def sealed_run(work: Path, issue: int, bundle: Optional[bytes], ctx: _Ctx) -> Dict[str, object]:
    def result(status: str, counts: Optional[Dict[str, int]] = None) -> Dict[str, object]:
        return {"status": status, **(counts or _NO_COUNTS)}

    if bundle is None:
        return result("not_provided")
    try:
        validate_sealed_patch(bundle, issue, ctx.policy.sealed.max_patch_bytes + BUNDLE_SLACK,
                              runner=ctx.runner, allow_canary=True)
    except SealedInvalid as e:
        print(f"sandbox_verify: sealed bundle invalid: {e}", file=sys.stderr)
        return result("invalid")
    out = Path(tempfile.mkdtemp(prefix="factory-sealed-"))
    try:
        patch = out / "sealed.patch"
        patch.write_bytes(bundle)
        with scratch_worktree(ctx, work) as wt:
            applied = ctx.git(wt, "apply", "--whitespace=nowarn", str(patch))
            if applied.returncode != 0:
                print(f"sandbox_verify: sealed bundle does not apply: {applied.stderr.strip()[:200]}", file=sys.stderr)
                return result("invalid")
            code = ctx.pytest(wt, [issue_dir(issue) + "/"], out / "sealed.xml")
        counts = junit_counts(out / "sealed.xml")
        if code not in (0, 1, 2, 5):
            return result("crash")
        if counts is None:
            return result("no_tests") if code == 5 else result("crash")
        bad = counts["failed"] + counts["errors"]
        if counts["total"] - counts["skipped"] < 1:
            return result("no_tests", counts) if code in (0, 5) and not bad else result("crash")
        if (code == 0 and bad) or (code in (1, 2) and not bad) or code == 5:
            return result("crash")        # pytest and its XML disagree
        return result("ran", counts)
    finally:
        shutil.rmtree(out, ignore_errors=True)


def run(environ: Mapping[str, str], policy: Policy, runner: Callable[..., ProcResult] = default_run) -> int:
    v = validate_inputs(environ, policy)
    work = Path(environ.get("FACTORY_WORK_DIR", "work")).resolve()
    out = Path(environ.get("FACTORY_OUT_DIR", "out")).resolve()
    env = envscrub.scrub_env(environ, list(policy.env_allowlist))
    env.update(PYTHONDONTWRITEBYTECODE="1", GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null",
               GIT_TERMINAL_PROMPT="0")
    ctx = _Ctx(policy, runner, env)
    try:
        head = ctx.git_ok(work, "rev-parse", "HEAD").strip()
        branch = ctx.git_ok(work, "rev-parse", "--abbrev-ref", "HEAD").strip()
    except _StepError as e:
        print(f"sandbox_verify: {e}", file=sys.stderr)
        return 2
    if head != v["sha"] or branch != v["branch"]:
        print("sandbox_verify: work checkout is not the expected branch and commit", file=sys.stderr)
        return 2
    steps = {}
    for name, fn, fallback in (
            ("revert_check", lambda: revert_check(work, ctx), {"status": "error", "tests": 0, "exit_code": None}),
            ("sealed", lambda: sealed_run(work, int(v["issue"]), v["bundle"], ctx), {"status": "crash", **_NO_COUNTS})):
        try:
            steps[name] = fn()
        except (_StepError, OSError) as e:
            print(f"sandbox_verify: {name} failed: {e}", file=sys.stderr)
            steps[name] = fallback
    out.mkdir(parents=True, exist_ok=True)
    (out / "verify.json").write_text(json.dumps({"request_id": v["request_id"], "sha": head, **steps}),
                                     encoding="utf-8")
    return 0


def main(argv=None, root: Optional[Path] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(root) if root else Path(__file__).resolve().parents[2]   # the trusted checkout
    try:
        policy = load_policy(root)
        if args == ["--validate-only"]:
            validate_inputs(os.environ, policy)
            return 0
        if args:
            raise VerifyInputError("unexpected arguments")
        return run(os.environ, policy)
    except (VerifyInputError, PolicyError) as e:
        print(f"sandbox_verify: rejected: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
