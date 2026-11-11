"""Run factory workers and gates on ephemeral GitHub Actions runners.

Local side only. `ActionsClient` wraps `gh` (argv lists through the injectable `proc.run` seam).
`ActionsLauncher` and `ActionsGateRunner` push the factory branch, dispatch a workflow that always
runs from `main`, wait, and download the result. Everything that comes back from a runner (result
file, patch, gate output) was produced on a machine where worker code ran, so it is validated as
untrusted data before use. Nothing here ever forces a push.
"""
from __future__ import annotations

import base64
import gzip
import json
import math
import re
import secrets
import shutil
import tempfile
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .gates import GateResult, GateRunner, parse_verdict
from .launcher import SANDBOX_REJECTED_PREFIX, ClaudeLauncher, Launcher, WorkerResult
from .policy import Policy
from .proc import ProcResult, run as default_run
from .sandbox_worker import BRANCH_RE, REQUEST_ID_RE

DISPATCH_REF = "main"                 # the workflow file and the scripts that drive it always come from main
MAX_PROMPT_B64 = 48_000               # workflow_dispatch inputs are capped at 65,535 characters in total
MAX_PATCH_BYTES = 5_000_000
MAX_RESULT_BYTES = 262_144
MAX_GATES_BYTES = 2_000_000
MAX_TEXT_CHARS = 20_000
GIT_TIMEOUT_S = 300
GH_TIMEOUT_S = 120
GIT = ["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false"]   # operator-side git: no hooks
BASE_REF = "origin/main"
QUEUE_TIMEOUT_S = 1800                # how long a run may take to appear and start (queueing is GitHub's)
_SHA = re.compile(r"[0-9a-f]{40}")
_RESULT_FIELDS = ("returncode", "result", "input_tokens", "output_tokens", "total_cost_usd",
                  "model", "start_sha", "request_id")


class ActionsError(RuntimeError):
    pass


class ActionsTimeout(ActionsError):
    pass


class PatchRejected(ActionsError):
    pass


class PathDenied(PatchRejected):
    """A path that executes once pushed or once a person opens the worktree. Never applied or pushed."""


# Hard deny-list. A code constant on purpose: it must not depend on the policy file, which a
# worker might also be able to edit. In sandbox mode the factory cannot propose changes to these
# paths at all (a deliberate narrowing of the spec). Matched case-insensitively on normalised
# path components; anything unclear fails closed.
DENIED_DIRS_ANYWHERE = frozenset({".github", ".claude", ".vscode", ".idea", ".devcontainer", ".husky"})
DENIED_FILES_ANYWHERE = frozenset({"claude.md", "claude.local.md", "agents.md", ".mcp.json", ".envrc",
                                   ".gitattributes", ".gitmodules", ".lfsconfig"})
DENIED_ROOT_DIRS = frozenset({".agents", "hooks"})


def denied_path(path: str) -> Optional[str]:
    parts = [c.casefold().rstrip(". ") for c in path.replace("\\", "/").split("/") if c not in ("", ".")]
    parts = [c for c in parts if c]
    for c in parts:
        if c in DENIED_DIRS_ANYWHERE or c in DENIED_FILES_ANYWHERE:
            return f"denied path {path!r}"
    if parts and parts[0] in DENIED_ROOT_DIRS:
        return f"denied path {path!r}"
    return None


def _int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


class ActionsClient:
    def __init__(self, state_dir, runner: Callable[..., ProcResult] = default_run, repo: Optional[str] = None,
                 cwd=None, poll_seconds: float = 10, timeout_s: float = 4500,
                 queue_timeout_s: float = QUEUE_TIMEOUT_S, sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic):
        self._state = Path(state_dir)
        self._run = runner
        self._repo = repo
        self._cwd = cwd
        self._poll = poll_seconds
        self._timeout = timeout_s              # a started run may take this long (job cap is 60 min)
        self._queue_timeout = queue_timeout_s   # time for the run to appear and start
        self._sleep = sleep
        self._clock = clock

    def _gh(self, args: List[str]) -> ProcResult:
        argv = ["gh", *args] + (["-R", self._repo] if self._repo else [])
        return self._run(argv, cwd=self._cwd, timeout=GH_TIMEOUT_S)

    def dispatch(self, workflow: str, fields: Dict[str, str]) -> None:
        args = ["workflow", "run", workflow, "--ref", DISPATCH_REF]
        for k, v in fields.items():
            args += ["-f", f"{k}={v}"]
        r = self._gh(args)
        if r.returncode != 0:
            raise ActionsError(f"dispatch of {workflow} failed ({r.returncode}): {r.stderr.strip()[:500]}")

    def find_run(self, workflow: str, title: str, deadline: float) -> int:
        """`gh workflow run` prints no run id, so find the run by the run-name set from request_id."""
        while True:
            r = self._gh(["run", "list", "--workflow", workflow, "--limit", "50",
                          "--json", "databaseId,displayTitle,status,conclusion"])
            if r.returncode != 0:
                raise ActionsError(f"gh run list failed ({r.returncode}): {r.stderr.strip()[:500]}")
            try:
                rows = json.loads(r.stdout)
            except ValueError:
                raise ActionsError("gh run list returned invalid JSON") from None
            for row in rows if isinstance(rows, list) else []:
                if isinstance(row, dict) and row.get("displayTitle") == title and _int(row.get("databaseId")):
                    return row["databaseId"]
            if self._clock() >= deadline:
                raise ActionsTimeout(f"no run named {title!r} appeared")
            self._sleep(self._poll)

    def wait(self, run_id: int, queue_deadline: float, run_timeout_s: float) -> str:
        """Queue time and run time are limited separately, so a job that is legitimately running is
        never cancelled for time it spent waiting for a runner."""
        run_deadline: Optional[float] = None
        while True:
            r = self._gh(["run", "view", str(run_id), "--json", "status,conclusion"])
            if r.returncode != 0:
                raise ActionsError(f"gh run view failed ({r.returncode}): {r.stderr.strip()[:500]}")
            try:
                data = json.loads(r.stdout)
            except ValueError:
                raise ActionsError("gh run view returned invalid JSON") from None
            status = data.get("status") if isinstance(data, dict) else None
            if status == "completed":
                return str(data.get("conclusion") or "")
            if status == "in_progress" and run_deadline is None:
                run_deadline = self._clock() + run_timeout_s
            if run_deadline is None:
                if self._clock() >= queue_deadline:
                    self._gh(["run", "cancel", str(run_id)])
                    raise ActionsTimeout(f"run {run_id} did not start in time")
            elif self._clock() >= run_deadline:
                self._gh(["run", "cancel", str(run_id)])   # best effort; the workflow has its own cap too
                raise ActionsTimeout(f"run {run_id} did not finish in time")
            self._sleep(self._poll)

    def new_download_dir(self) -> Path:
        base = self._state / "actions"
        base.mkdir(parents=True, exist_ok=True, mode=0o700)
        return Path(tempfile.mkdtemp(prefix="dl-", dir=base))

    def download(self, run_id: int, artifact: str) -> Optional[Path]:
        d = self.new_download_dir()
        r = self._gh(["run", "download", str(run_id), "-n", artifact, "-D", str(d)])
        if r.returncode != 0:
            try:
                d.rmdir()
            except OSError:
                pass
            return None
        return d

    def run_workflow(self, workflow: str, title_prefix: str, fields: Dict[str, str],
                     artifact: str) -> Tuple[str, Optional[Path]]:
        queue_deadline = self._clock() + self._queue_timeout
        self.dispatch(workflow, fields)
        # If the run never appears there is no run id, so there is nothing to cancel: a dispatched
        # run that shows up late can still execute (known limit, see docs/factory.md).
        run_id = self.find_run(workflow, f"{title_prefix} {fields['request_id']}", queue_deadline)
        conclusion = self.wait(run_id, queue_deadline, self._timeout)
        return conclusion, self.download(run_id, artifact)

    @staticmethod
    def cleanup(d: Optional[Path]) -> None:
        if d is not None:
            shutil.rmtree(d, ignore_errors=True)


def read_artifact_file(d: Path, name: str, cap: int) -> bytes:
    p = d / name
    if p.is_symlink() or not p.is_file():
        raise ActionsError(f"artifact has no regular file {name}")
    if p.stat().st_size > cap:
        raise ActionsError(f"artifact file {name} is over {cap} bytes")
    return p.read_bytes()


def parse_result(raw: bytes, request_id: str, start_sha: str) -> dict:
    """Strict validation of the runner's result.json. The runner is untrusted."""
    try:
        d = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise ActionsError("result.json is not valid JSON") from None
    if not isinstance(d, dict):
        raise ActionsError("result.json is not an object")
    for k in _RESULT_FIELDS:
        if k not in d:
            raise ActionsError(f"result.json missing {k!r}")
    if not _int(d["returncode"]):
        raise ActionsError("result.json returncode is not an integer")
    if not isinstance(d["result"], str) or not isinstance(d["model"], str):
        raise ActionsError("result.json result/model must be strings")
    for k in ("input_tokens", "output_tokens"):
        if not _int(d[k]) or d[k] < 0:
            raise ActionsError(f"result.json {k} must be a non-negative integer")
    c = d["total_cost_usd"]
    if c is not None and (isinstance(c, bool) or not isinstance(c, (int, float))
                          or not math.isfinite(c) or c < 0):
        raise ActionsError("result.json total_cost_usd must be null or a non-negative number")
    if d["request_id"] != request_id:
        raise ActionsError("result.json request_id does not match")
    if d["start_sha"] != start_sha:
        raise ActionsError("result.json start_sha does not match the pushed commit")
    return d


def _bad_path(path: str) -> Optional[str]:
    if not path or path.startswith("/") or "\\" in path or "\0" in path:
        return "absolute or malformed path"
    for part in path.split("/"):
        if part in ("", ".", ".."):
            return "path traversal"
        if part.lower().rstrip(". ") in (".git", "git~1"):
            return "path inside .git"
    return None


_SUMMARY_CREATE = re.compile(r"^ (?:create|delete) mode (\d+) ")
_SUMMARY_CHANGE = re.compile(r"^ mode change (\d+) => (\d+) ")
_INDEX_LINK = re.compile(rb"^index [0-9a-f]+\.\.[0-9a-f]+ (?:120000|160000)\s*$")
_NEW_MODE = re.compile(rb"^(?:new file mode|new mode) (?:120000|160000)\s*$")
_SPECIAL = ("120000", "160000")   # symlink, gitlink. classifier.py does not force these to T2, so reject.


_HEADER = (b"diff --git ", b"rename from ", b"rename to ", b"copy from ", b"copy to ", b"--- ", b"+++ ")


def header_paths(patch: bytes) -> List[str]:
    """Every path-looking token in the patch's header lines, read without trusting git's parse."""
    out: List[str] = []
    for line in patch.split(b"\n"):
        for h in _HEADER:
            if line.startswith(h):
                rest = line[len(h):].decode("utf-8", errors="replace")
                for tok in re.split(r'[\s"]+', rest):
                    if tok and tok != "/dev/null":
                        out.append(tok)
                        if tok[:2] in ("a/", "b/"):
                            out.append(tok[2:])
                break
    return out


def numstat_paths(numstat_z: str) -> List[str]:
    toks = numstat_z.split("\0")
    paths: List[str] = []
    i = 0
    while i < len(toks):
        t = toks[i]
        i += 1
        if not t:
            continue
        m = re.match(r"^(\S+)\t(\S+)\t(.*)$", t, re.S)
        if not m:
            raise PatchRejected("unparseable numstat record")
        if m.group(3):
            paths.append(m.group(3))
        else:                              # rename: old and new follow as separate records
            if i + 1 >= len(toks):
                raise PatchRejected("truncated rename record")
            paths.extend([toks[i], toks[i + 1]])
            i += 2
    return paths


def validate_patch(patch: bytes, patch_file: Path, cwd: Path,
                   runner: Callable[..., ProcResult] = default_run) -> bool:
    """Raise PatchRejected for anything unsafe. Returns False for an empty patch."""
    if len(patch) > MAX_PATCH_BYTES:
        raise PatchRejected("patch is too large")
    if not patch.strip():
        return False
    for line in patch.split(b"\n"):
        if _INDEX_LINK.match(line) or _NEW_MODE.match(line):
            raise PatchRejected("patch creates or changes a symlink or gitlink")
    for p in header_paths(patch):
        why = denied_path(p)
        if why:
            raise PathDenied(why)
    num = runner([*GIT, "apply", "--numstat", "-z", str(patch_file)], cwd=cwd, timeout=GIT_TIMEOUT_S)
    if num.returncode != 0:
        raise PatchRejected(f"git cannot parse the patch: {num.stderr.strip()[:300]}")
    paths = numstat_paths(num.stdout)
    if not paths:
        raise PatchRejected("patch touches no paths")
    for p in paths:
        why = denied_path(p)
        if why:
            raise PathDenied(why)
        why = _bad_path(p)
        if why:
            raise PatchRejected(f"{why}: {p!r}")
    summ = runner([*GIT, "apply", "--summary", str(patch_file)], cwd=cwd, timeout=GIT_TIMEOUT_S)
    if summ.returncode != 0:
        raise PatchRejected("git cannot summarise the patch")
    for line in summ.stdout.splitlines():
        a = _SUMMARY_CREATE.match(line)
        b = _SUMMARY_CHANGE.match(line)
        if (a and a.group(1) in _SPECIAL and line.startswith(" create")) or (b and b.group(2) in _SPECIAL):
            raise PatchRejected("patch creates or changes a symlink or gitlink")
    return True


class _Git:
    def __init__(self, runner: Callable[..., ProcResult], cwd: Path):
        self._run, self.cwd = runner, Path(cwd)

    def __call__(self, *args: str, timeout: int = GIT_TIMEOUT_S) -> ProcResult:
        return self._run([*GIT, *args], cwd=self.cwd, timeout=timeout)

    def out(self, *args: str) -> str:
        r = self(*args)
        if r.returncode != 0:
            raise ActionsError(f"git {args[0]} failed ({r.returncode}): {r.stderr.strip()[:300]}")
        return r.stdout.strip()

    def branch(self) -> str:
        b = self.out("rev-parse", "--abbrev-ref", "HEAD")
        if not BRANCH_RE.fullmatch(b):
            raise ActionsError(f"branch {b!r} is not a factory/<number>-<slug> branch")
        if self.out("status", "--porcelain"):
            raise ActionsError("worktree is not clean")
        return b

    def assert_pushable(self) -> None:
        """One check before every push: nothing on this branch since main may touch a denied path.
        Fails closed (no base ref, git error)."""
        if self("rev-parse", "--verify", "-q", f"{BASE_REF}^{{commit}}").returncode != 0:
            raise ActionsError(f"base ref {BASE_REF} not found; refusing to push")
        r = self("diff", "--name-only", "--no-renames", "-z", f"{BASE_REF}...HEAD")
        if r.returncode != 0:
            raise ActionsError(f"cannot list branch changes against {BASE_REF}: {r.stderr.strip()[:300]}")
        for p in filter(None, r.stdout.split("\0")):
            why = denied_path(p)
            if why:
                raise PathDenied(why)
            why = _bad_path(p)
            if why:
                raise PathDenied(f"{why}: {p!r}")

    def push(self, branch: str) -> None:
        self.assert_pushable()
        # Never forced: a rejected push is an error, not a retry.
        r = self("push", "origin", f"refs/heads/{branch}:refs/heads/{branch}")
        if r.returncode != 0:
            raise ActionsError(f"push of {branch} was rejected or failed: {r.stderr.strip()[:300]}")


class ActionsLauncher(Launcher):
    def __init__(self, policy: Policy, client: ActionsClient, runner: Callable[..., ProcResult] = default_run,
                 new_request_id: Callable[[], str] = lambda: secrets.token_hex(8)):
        self._policy, self._client, self._run, self._rid = policy, client, runner, new_request_id
        self._claude = ClaudeLauncher(policy)

    @staticmethod
    def _failed(text: str, model: str, rc: int = 1) -> WorkerResult:
        return WorkerResult(rc, text[:MAX_TEXT_CHARS], 0, 0, 0.0, False, model)

    def run(self, role, prompt, cwd, model=None, max_budget_usd=None):
        m = self._claude.model_for(role, model)   # raises LauncherError for an unknown role
        try:
            return self._run_sandboxed(role, prompt, Path(cwd), m, max_budget_usd)
        except ActionsTimeout as e:
            return self._failed(f"sandbox worker timed out: {e}", m, 124)
        except PathDenied as e:
            return self._failed(f"{SANDBOX_REJECTED_PREFIX} {e}", m)
        except (ActionsError, OSError) as e:
            return self._failed(f"sandbox worker failed: {e}", m)

    def _run_sandboxed(self, role, prompt, cwd, m, max_budget_usd) -> WorkerResult:
        git = _Git(self._run, cwd)
        branch = git.branch()
        b64 = base64.b64encode(gzip.compress(prompt.encode("utf-8"), mtime=0)).decode("ascii")
        if len(b64) > MAX_PROMPT_B64:
            return self._failed(f"prompt too large for a workflow_dispatch input ({len(b64)} encoded "
                                f"characters, cap {MAX_PROMPT_B64}); nothing was dispatched", m)
        git.push(branch)
        start_sha = git.out("rev-parse", "HEAD")
        request_id = self._rid()
        if not REQUEST_ID_RE.fullmatch(request_id):
            raise ActionsError("generated request id is malformed")
        budget = self._policy.per_issue_usd if max_budget_usd is None else max_budget_usd
        fields = {"branch": branch, "role": role, "model": m, "max_budget_usd": f"{max(budget, 0.0):.2f}",
                  "request_id": request_id, "prompt_b64": b64}
        conclusion, d = self._client.run_workflow(self._policy.sandbox.worker_workflow, "factory-worker",
                                                  fields, f"factory-result-{request_id}")
        if d is None:
            raise ActionsError(f"run concluded {conclusion or 'unknown'} with no result artifact")
        try:
            res = parse_result(read_artifact_file(d, "result.json", MAX_RESULT_BYTES), request_id, start_sha)
            patch = read_artifact_file(d, "changes.patch", MAX_PATCH_BYTES + 1)
            self._apply(git, patch, d / "changes.patch", role, start_sha, branch)
        finally:
            self._client.cleanup(d)
        rc = res["returncode"]
        if conclusion != "success" and rc == 0:
            rc = 1
        cost = res["total_cost_usd"]
        return WorkerResult(rc, res["result"][:MAX_TEXT_CHARS], res["input_tokens"], res["output_tokens"],
                            float(cost) if cost is not None else 0.0, cost is not None, m)

    def _apply(self, git: _Git, patch: bytes, patch_file: Path, role: str, start_sha: str, branch: str) -> None:
        if not validate_patch(patch, patch_file, git.cwd, self._run):
            return
        if git.out("rev-parse", "HEAD") != start_sha or git.out("status", "--porcelain"):
            raise ActionsError("worktree changed while the worker ran")
        r = git("apply", "--index", "--binary", str(patch_file))
        if r.returncode != 0:
            raise ActionsError(f"patch does not apply: {r.stderr.strip()[:300]}")
        if git("diff", "--cached", "--quiet").returncode == 0:
            return
        c = git("commit", "--no-verify", "-q", "-m", f"factory: worker output ({role})")
        if c.returncode != 0:
            raise ActionsError(f"commit failed: {c.stderr.strip()[:300]}")
        git.push(branch)   # so the gates workflow sees the worker's output


class ActionsGateRunner(GateRunner):
    def __init__(self, client: ActionsClient, runner: Callable[..., ProcResult] = default_run,
                 new_request_id: Callable[[], str] = lambda: secrets.token_hex(8),
                 gates_workflow: str = "factory-gates.yml"):
        self._client, self._run, self._rid, self._workflow = client, runner, new_request_id, gates_workflow

    def run(self, worktree):
        try:
            return self._run_gates(Path(worktree))
        except (ActionsError, OSError) as e:   # includes timeouts: a gate that cannot run is MISCONFIGURED
            return GateResult("MISCONFIGURED", f"actions gates: {e}")

    def _run_gates(self, worktree: Path) -> GateResult:
        git = _Git(self._run, worktree)
        branch = git.branch()
        local = git.out("rev-parse", "HEAD")
        r = git("ls-remote", "origin", f"refs/heads/{branch}")
        if r.returncode != 0:
            raise ActionsError(f"ls-remote failed: {r.stderr.strip()[:300]}")
        remote = r.stdout.split()[0] if r.stdout.strip() else ""
        if remote and not _SHA.fullmatch(remote):
            raise ActionsError("ls-remote returned a malformed sha")
        if remote != local:
            if remote and git("merge-base", "--is-ancestor", remote, local).returncode != 0:
                raise ActionsError("remote branch has diverged from the local branch; refusing to force")
            git.push(branch)
        request_id = self._rid()
        conclusion, d = self._client.run_workflow(self._workflow, "factory-gates",
                                                  {"branch": branch, "request_id": request_id},
                                                  f"factory-gates-{request_id}")
        if d is None:
            raise ActionsError(f"run concluded {conclusion or 'unknown'} with no gates artifact")
        try:
            if conclusion != "success":
                raise ActionsError(f"gates run concluded {conclusion or 'unknown'}")
            text = read_artifact_file(d, "gates-output.txt", MAX_GATES_BYTES).decode("utf-8", errors="replace")
            ran = read_artifact_file(d, "gates-sha.txt", 128).decode("ascii", errors="replace").strip()
        finally:
            self._client.cleanup(d)
        if ran != local:
            raise ActionsError("gates ran on a different commit than the local head")
        return GateResult(parse_verdict(text), text)
