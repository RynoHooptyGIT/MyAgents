"""Sealed acceptance tests: strict validation, the operator-side store, and the verification bundle.

A `sealed_test_author` worker writes pytest files under `tests/sealed/issue-<N>/` before the build.
They are collected as a patch (never applied, never committed, never pushed) and kept in
`state_dir/sealed/`, outside the repository. The builder never sees them. After the build they are
sent to the verify job as a bundle: the stored patch plus a canary file whose name carries a token
that only the operator side knows.
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List

from .actions import GIT, GIT_TIMEOUT_S, PatchRejected, header_paths, numstat_paths
from .launcher import build_prompt
from .policy import SEALED_DIR
from .proc import ProcResult, run as default_run

_CANARY_NAME = re.compile(r"canary_[0-9a-f]{32}\.txt")
_COMPONENT = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*")
_CREATE = re.compile(r"^ create mode 100644 (.+)$")
_FORBIDDEN_LINES = (b"old mode ", b"new mode ", b"deleted file mode ", b"rename ", b"copy ", b"similarity index ",
                    b"dissimilarity index ", b"GIT binary patch", b"Binary files ")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_SHA1 = re.compile(r"[0-9a-f]{40}")
_TOKEN = re.compile(r"[0-9a-f]{32}")


class SealedError(RuntimeError):
    pass


class SealedInvalid(SealedError):
    """The sealed patch is not a set of new, plain test files under the issue's sealed directory."""


class SealedHashMismatch(SealedError):
    pass


def issue_dir(issue: int) -> str:
    return f"{SEALED_DIR}/issue-{int(issue)}"


def canary_path(issue: int, token: str) -> str:
    return f"{issue_dir(issue)}/canary_{token}.txt"


def new_file_patch(path: str, content: bytes) -> bytes:
    """A git patch that creates one regular file (mode 100644). Used for the canary and by tests."""
    blob = hashlib.sha1(b"blob %d\0" % len(content) + content).hexdigest()
    head = (f"diff --git a/{path} b/{path}\nnew file mode 100644\nindex 0000000..{blob[:7]}\n").encode()
    if not content:
        return head
    lines = content.split(b"\n")
    trailing_newline = lines[-1] == b""
    if trailing_newline:
        lines.pop()
    body = b"".join(b"+" + ln + b"\n" for ln in lines)
    if not trailing_newline:
        body += b"\\ No newline at end of file\n"
    return head + f"--- /dev/null\n+++ b/{path}\n@@ -0,0 +1,{len(lines)} @@\n".encode() + body


def _fail(why: str):
    raise SealedInvalid(why)


def validate_sealed_patch(patch: bytes, issue: int, max_bytes: int,
                          runner: Callable[..., ProcResult] = default_run, allow_canary: bool = False) -> List[str]:
    """Return the created paths, or raise SealedInvalid. Fails closed on anything unclear.

    Accepts only new regular files (mode 100644) directly or nested under `tests/sealed/issue-<N>/`,
    named `test_*.py` or `__init__.py` (plus, for a verification bundle, one `canary_<32 hex>.txt`),
    with at least one `test_*.py`. No modifications, deletions, renames, copies, mode changes, links
    or binary content."""
    if len(patch) > max_bytes:
        _fail(f"sealed patch is too large ({len(patch)} > {max_bytes} bytes)")
    if not patch.strip():
        _fail("sealed patch is empty")
    for line in patch.split(b"\n"):
        if line.startswith(_FORBIDDEN_LINES):
            _fail("sealed patch has a rename, copy, deletion, mode change or binary content")
        if line.startswith(b"new file mode ") and line.rstrip() != b"new file mode 100644":
            _fail("sealed patch creates a file that is not a regular 100644 file")
    prefix = issue_dir(issue) + "/"
    for tok in header_paths(patch):
        p = tok[2:] if tok[:2] in ("a/", "b/") else tok
        if not p.startswith(prefix):
            _fail(f"sealed patch header names a path outside {prefix}")
    with tempfile.TemporaryDirectory(prefix="sealed-check-") as td:
        pf = Path(td) / "sealed.patch"
        pf.write_bytes(patch)
        num = runner([*GIT, "apply", "--numstat", "-z", str(pf)], cwd=td, timeout=GIT_TIMEOUT_S)
        if num.returncode != 0:
            _fail(f"git cannot parse the sealed patch: {num.stderr.strip()[:200]}")
        try:
            paths = numstat_paths(num.stdout)
        except PatchRejected as e:
            raise SealedInvalid(str(e)) from None
        summ = runner([*GIT, "apply", "--summary", str(pf)], cwd=td, timeout=GIT_TIMEOUT_S)
        if summ.returncode != 0:
            _fail("git cannot summarise the sealed patch")
        chk = runner([*GIT, "apply", "--check", str(pf)], cwd=td, timeout=GIT_TIMEOUT_S)   # into an empty directory
        if chk.returncode != 0:
            _fail(f"the sealed patch does not apply to an empty tree: {chk.stderr.strip()[:200]}")
    created = []
    for line in summ.stdout.splitlines():
        m = _CREATE.match(line)
        if not m:
            _fail(f"sealed patch does something other than create new files: {line.strip()[:80]!r}")
        created.append(m.group(1).strip('"'))
    if not paths or sorted(paths) != sorted(created) or len(set(paths)) != len(paths):
        _fail("sealed patch must create each path exactly once and touch nothing else")
    tests, canaries = 0, 0
    for p in paths:
        if not p.startswith(prefix):
            _fail(f"sealed patch touches {p!r}, outside {prefix}")
        parts = p[len(prefix):].split("/")
        if len(parts) > 3 or not all(_COMPONENT.fullmatch(c) and c.lower() != ".git" for c in parts):
            _fail(f"sealed path {p!r} is not acceptable")
        name = parts[-1]
        if name == "__init__.py":
            continue
        if re.fullmatch(r"test_[A-Za-z0-9_]*\.py", name):
            tests += 1
        elif allow_canary and len(parts) == 1 and _CANARY_NAME.fullmatch(name):
            canaries += 1
        else:
            _fail(f"sealed file name {name!r} must be test_*.py or __init__.py")
    if canaries > 1:
        _fail("more than one canary file")
    if tests < 1:
        _fail("sealed patch has no test_*.py file")
    return paths


def build_sealed_prompt(issue_number: int, title: str, body: str) -> str:
    n = int(issue_number)
    rules = (
        f"Your task: read the spec at specs/{n}.md (committed on this branch) and the issue above, then write "
        f"acceptance tests for the behaviour they describe, as NEW pytest files under tests/sealed/issue-{n}/ "
        f"and nowhere else (files named test_*.py; an __init__.py is allowed). Test behaviour through public "
        f"interfaces only. Write no implementation code and do not modify, delete or add any other file. "
        f"The tests will be run later against the finished change, which you cannot see. Do not commit."
    )
    return build_prompt("sealed_test_author", n, title, body) + "\n\n" + rules


@dataclass(frozen=True)
class SealedSet:
    issue: int
    attempt: int
    patch: bytes
    spec_sha: str
    canary: str
    sha256: str


def bundle(sealed: SealedSet) -> bytes:
    """What the verify job receives: the author's patch plus the canary file."""
    patch = sealed.patch if sealed.patch.endswith(b"\n") else sealed.patch + b"\n"
    return patch + new_file_patch(canary_path(sealed.issue, sealed.canary), sealed.canary.encode() + b"\n")


class SealedStore:
    def __init__(self, state_dir, token: Callable[[], str] = lambda: secrets.token_hex(16),
                 now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self._base = Path(state_dir) / "sealed"
        self._token, self._now = token, now

    def _dir(self, issue: int, attempt: int) -> Path:
        return self._base / f"issue-{int(issue)}-a{int(attempt)}"

    def save(self, issue: int, attempt: int, patch: bytes, spec_sha: str) -> SealedSet:
        d = self._dir(issue, attempt)
        canary = self._token()
        if not _TOKEN.fullmatch(canary):
            raise SealedError("canary token is malformed")
        digest = hashlib.sha256(patch).hexdigest()
        try:
            self._base.mkdir(parents=True, exist_ok=True, mode=0o700)
            d.mkdir(mode=0o700)
            (d / "sealed.patch").write_bytes(patch)
            (d / "manifest.json").write_text(json.dumps({
                "issue": int(issue), "attempt": int(attempt), "patch_sha256": digest, "spec_sha": spec_sha,
                "canary": canary, "created_at": self._now().isoformat()}), encoding="utf-8")
        except OSError as e:
            raise SealedError(f"cannot write the sealed store: {e}") from None
        return SealedSet(int(issue), int(attempt), patch, spec_sha, canary, digest)

    def load(self, issue: int, attempt: int) -> SealedSet:
        """Recompute the hash before every use and refuse on mismatch."""
        d = self._dir(issue, attempt)
        try:
            patch = (d / "sealed.patch").read_bytes()
            m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise SealedError(f"sealed store unreadable: {type(e).__name__}") from None
        if (not isinstance(m, dict) or m.get("issue") != int(issue) or m.get("attempt") != int(attempt)
                or not isinstance(m.get("patch_sha256"), str) or not _SHA256.fullmatch(m["patch_sha256"])
                or not isinstance(m.get("spec_sha"), str) or not _SHA1.fullmatch(m["spec_sha"])
                or not isinstance(m.get("canary"), str) or not _TOKEN.fullmatch(m["canary"])):
            raise SealedError("sealed manifest is malformed")
        digest = hashlib.sha256(patch).hexdigest()
        if digest != m["patch_sha256"]:
            raise SealedHashMismatch("sealed patch does not match its recorded hash")
        return SealedSet(int(issue), int(attempt), patch, m["spec_sha"], m["canary"], digest)
