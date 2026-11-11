"""Entrypoint that runs inside the ephemeral Actions runner: `python3 -m scripts.factory.sandbox_worker`.

Runs from the `trusted/` checkout of main, operates on the `work/` checkout of the worker's
branch. Every input arrives as an environment variable (never interpolated into a shell
line) and is validated here before use. Outputs: `changes.patch` and `result.json` in the
out directory. Everything written there is data the operator's machine treats as untrusted.
"""
from __future__ import annotations

import base64
import binascii
import gzip
import io
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Callable, Dict, Mapping, Optional

from . import envscrub
from .launcher import ClaudeLauncher, LauncherError, result_from_proc
from .policy import PolicyError, load as load_policy, Policy
from .proc import ProcResult, run as default_run

BRANCH_RE = re.compile(r"factory/[0-9]+-[a-z0-9-]+")
REQUEST_ID_RE = re.compile(r"[a-f0-9]{8,64}")
_BUDGET_RE = re.compile(r"[0-9]+(?:\.[0-9]+)?")
_MODEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
MAX_PROMPT_BYTES = 1_000_000
CLAUDE_TIMEOUT_S = 3000          # below the workflow's 60 minute cap so result.json still gets written
GIT_TIMEOUT_S = 300
MAX_RESULT_TEXT = 20_000


class SandboxInputError(ValueError):
    pass


def _require(environ: Mapping[str, str], name: str) -> str:
    v = environ.get(name)
    if v is None:
        raise SandboxInputError(f"missing input {name}")
    return v


def decode_prompt(b64: str) -> str:
    try:
        raw = base64.b64decode(b64, validate=True)
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as g:
            data = g.read(MAX_PROMPT_BYTES + 1)
        text = data.decode("utf-8")
    except (binascii.Error, ValueError, OSError, EOFError) as e:
        raise SandboxInputError(f"prompt is not valid gzip+base64 utf-8: {type(e).__name__}") from None
    if len(data) > MAX_PROMPT_BYTES:
        raise SandboxInputError("prompt too large")
    if not text.strip():
        raise SandboxInputError("prompt is empty")
    return text


def validate_inputs(environ: Mapping[str, str], policy: Policy) -> Dict[str, object]:
    branch = _require(environ, "FACTORY_BRANCH")
    if not BRANCH_RE.fullmatch(branch):
        raise SandboxInputError("branch must match factory/<number>-<slug>")
    role = _require(environ, "FACTORY_ROLE")
    if role not in policy.routing:
        raise SandboxInputError("role is not a routing key in the policy")
    request_id = _require(environ, "FACTORY_REQUEST_ID")
    if not REQUEST_ID_RE.fullmatch(request_id):
        raise SandboxInputError("request_id must match [a-f0-9]{8,64}")
    raw_budget = _require(environ, "FACTORY_MAX_BUDGET_USD")
    if not _BUDGET_RE.fullmatch(raw_budget):
        raise SandboxInputError("max_budget_usd must be a non-negative decimal number")
    budget = float(raw_budget)
    if not math.isfinite(budget):
        raise SandboxInputError("max_budget_usd must be finite")
    model = environ.get("FACTORY_MODEL", "")
    if model and not _MODEL_RE.fullmatch(model):
        raise SandboxInputError("model has unexpected characters")
    try:
        model = ClaudeLauncher(policy).model_for(role, model or None)
    except LauncherError as e:
        raise SandboxInputError(str(e)) from None
    prompt = decode_prompt(_require(environ, "FACTORY_PROMPT_B64"))
    return {"branch": branch, "role": role, "request_id": request_id, "budget": budget,
            "model": model, "prompt": prompt}


def _config_files(work: Path):
    """Worker-controlled files claude could load as configuration: .mcp.json, CLAUDE.local.md, .claude/**."""
    found = []
    for rel in (".mcp.json", "CLAUDE.local.md"):
        p = work / rel
        if p.is_symlink() or p.exists():
            found.append(rel)
    cdir = work / ".claude"
    if cdir.is_symlink():
        raise SandboxInputError("work/.claude is a symlink; refusing to run")
    if cdir.is_dir():
        for dirpath, dirnames, filenames in os.walk(cdir, followlinks=False):
            for name in dirnames + filenames:
                full = Path(dirpath) / name
                if full.is_symlink():
                    raise SandboxInputError(f"{full.relative_to(work)} is a symlink; refusing to run")
            found.extend(str((Path(dirpath) / n).relative_to(work)) for n in filenames)
    return found


def check_worker_config(work: Path, trusted: Path) -> None:
    """Refuse to run if the worker's branch carries Claude Code config that main does not."""
    for rel in _config_files(work):
        mine, theirs = work / rel, trusted / rel
        if mine.is_symlink() or not mine.is_file():
            raise SandboxInputError(f"{rel} is not a regular file; refusing to run")
        if theirs.is_symlink() or not theirs.is_file() or theirs.read_bytes() != mine.read_bytes():
            raise SandboxInputError(f"{rel} in the worker branch differs from the copy in trusted/ "
                                    "(or main has none); refusing to run")


def _git_env(policy: Policy) -> Dict[str, str]:
    """No API key, no tokens: git (and anything a planted config makes it run) never sees them."""
    env = envscrub.scrub_env(os.environ, list(policy.env_allowlist))
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null", GIT_TERMINAL_PROMPT="0")
    return env


def run(environ: Mapping[str, str], policy: Policy,
        runner: Callable[..., ProcResult] = default_run, trusted_root: Optional[Path] = None) -> int:
    v = validate_inputs(environ, policy)
    api_key = environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SandboxInputError("ANTHROPIC_API_KEY is not set")
    work = Path(environ.get("FACTORY_WORK_DIR", "work")).resolve()
    out = Path(environ.get("FACTORY_OUT_DIR", "out")).resolve()
    check_worker_config(work, Path(trusted_root) if trusted_root else Path(__file__).resolve().parents[2])
    out.mkdir(parents=True, exist_ok=True)
    genv = _git_env(policy)

    def git(*args: str, timeout: int = GIT_TIMEOUT_S) -> ProcResult:
        return runner(["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", *args],
                      cwd=work, timeout=timeout, env=genv)

    head = git("rev-parse", "--abbrev-ref", "HEAD")
    if head.returncode != 0 or head.stdout.strip() != v["branch"]:
        raise SandboxInputError("work checkout is not on the requested branch")
    sha = git("rev-parse", "HEAD")
    start_sha = sha.stdout.strip()
    if sha.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", start_sha):
        raise SandboxInputError("cannot resolve the start commit")

    argv = ClaudeLauncher(policy).build_argv(str(v["model"]), float(v["budget"]))
    # Ignore project and local settings (hooks, env overrides, apiKeyHelper) and project MCP config
    # from the worker-controlled branch. Both flags are in the Claude Code CLI reference.
    argv += ["--setting-sources", "user", "--strict-mcp-config"]
    cenv = envscrub.scrub_env(os.environ, list(policy.env_allowlist))
    cenv["ANTHROPIC_API_KEY"] = api_key
    cenv["CLAUDE_CODE_SUBPROCESS_ENV_SCRUB"] = "1"
    r = runner(argv, cwd=work, input_text=str(v["prompt"]), timeout=CLAUDE_TIMEOUT_S, env=cenv)
    res = result_from_proc(r, str(v["model"]))

    # Snapshot whatever the worker left uncommitted, then diff against the start commit.
    if git("status", "--porcelain").stdout.strip():
        git("add", "-A")
        git("-c", "user.name=factory-sandbox", "-c", "user.email=factory-sandbox@invalid",
            "commit", "--no-verify", "-q", "-m", "factory: sandbox snapshot")
    patch = out / "changes.patch"
    d = git("diff", "--binary", "--no-ext-diff", "--no-textconv", f"--output={patch}", f"{start_sha}..HEAD")
    if d.returncode != 0:
        patch.write_bytes(b"")
        res = type(res)(res.returncode or 1, (res.text + "\nfactory: could not produce the patch").strip(),
                        res.input_tokens, res.output_tokens, res.cost_usd, res.cost_known, res.model)

    result = {"returncode": res.returncode, "result": res.text[:MAX_RESULT_TEXT], "input_tokens": res.input_tokens,
              "output_tokens": res.output_tokens,
              "total_cost_usd": res.cost_usd if res.cost_known else None,
              "model": res.model, "start_sha": start_sha, "request_id": v["request_id"]}
    (out / "result.json").write_text(json.dumps(result), encoding="utf-8")
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
            raise SandboxInputError("unexpected arguments")
        return run(os.environ, policy, runner=default_run, trusted_root=root)
    except (SandboxInputError, PolicyError) as e:
        print(f"sandbox_worker: rejected: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
