# Instinct Capture Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hooks record prompts and tool events; a Stop-hook-gated Haiku miner turns them into confidence-scored `pending` instincts; Oracle reviews them per mode; SessionStart injects the active top-N.

**Architecture:** Four file-interfaced stages — capture (`observe.sh` → `observations.jsonl`), mine (`instinct-mine.sh` → `prefilter.py` → detached `claude -p` → `instinct.py ingest`), store (flat YAML per instinct, project tier committed + user tier in `~/.claude/instincts/`), inject (`instinct-inject.sh` → `instinct.py inject`). Oracle gets a pending count at activation, a mode-aware review rule, and a menu item. The never-wired `learnings.xml` is deprecated in favor of this.

**Tech Stack:** bash hooks (existing `.agents/hooks/` pattern), Python 3.8+ stdlib only (no PyYAML — instinct files are a flat key/value subset written and read by our own code), pytest for Python, self-contained bash harnesses for hooks (pattern: `.agents/hooks/test-claim-check.sh`).

**Spec:** `docs/specs/2026-09-19-instinct-capture-loop-design.md`

## Global Constraints

- Every hook exits 0 no matter what; `observe.sh` never writes to stdout (UserPromptSubmit stdout is injected into context).
- Hook timeouts: capture 3000 ms, mine 5000 ms, inject 5000 ms; the Stop hook must return in < 1 s (miner is detached).
- Python: 3.8+, stdlib only. Atomic writes = tempfile in target dir + flush + fsync + `os.replace` (as `_bmad/scripts/memlog.py`).
- Truncation: tool input/response 5,000 chars, prompt text 2,000 chars, candidate window strings 1,000 chars.
- Secret scrub regex (applied to every persisted string): `(?i)(api[_-]?key|token|secret|password|authorization|credentials?)("?\s*[:=]\s*"?)([^\s"]+)` → `\1\2[REDACTED]`.
- Confidence ∈ [0.3, 0.9]; initial by observed_count 1–2→0.3, 3–5→0.5, 6–10→0.7, 11+→0.85; confirm +0.05; contradict −0.10; decay −`decay_per_week` per week since `last_seen`, applied at inject/status time only (never persisted).
- Instinct id: `^[a-z0-9][a-z0-9-]{2,60}$`. Domains: `code-style testing git debugging workflow security tooling`. Global-promotable domains: `security workflow tooling git`.
- `status: pending` is never injected and never auto-activated except by Oracle auto mode (`accept --min-confidence`).
- Env `INSTINCTS_SKIP=1` short-circuits all three hooks (set on the nested miner so it doesn't observe itself). Marker `.instincts-off` at repo root disables capture/mine/inject (mirrors `.slim-off`).
- Paths: project tier `team/_memory/_learnings/instincts/`, observations `team/_memory/_learnings/observations.jsonl`, watermark `team/_memory/_learnings/.instinct-watermark`, lock `.miner.lock`, log `miner.log`. User tier `~/.claude/instincts/` (override with env `INSTINCTS_USER_DIR` in tests).
- Work happens in the worktree `.worktrees/instinct-capture-loop` on branch `feat/instinct-capture-loop`. Run all commands from that directory. Run pytest as `python3 -m pytest scripts/instincts/tests -q` (fallback if pytest is missing: `uv run --with pytest pytest scripts/instincts/tests -q`).
- Commit after each task with a conventional-commit message ending in `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`.

---

## File map

| Path | Responsibility |
|---|---|
| `scripts/instincts/config.py` | Read the `instincts:` block of `.agents/config.yaml`; defaults; CLI `config.py --root R key…` prints values for bash |
| `scripts/instincts/instinct.py` | Instinct store: flat-YAML read/write, confidence math, `status review accept reject inject ingest promote prune export import rejected-ids` |
| `scripts/instincts/prefilter.py` | Read observations after the watermark, emit candidate windows JSON, optionally commit the watermark |
| `scripts/instincts/observe.py` | Parse hook stdin, scrub, truncate, append JSONL, rotate |
| `scripts/instincts/tests/test_config.py`, `test_instinct.py`, `test_prefilter.py`, `test_observe.py` | pytest |
| `.agents/hooks/observe.sh`, `instinct-mine.sh`, `instinct-inject.sh` | Thin bash hooks; guards; delegate to Python |
| `.agents/hooks/test-observe.sh`, `test-instinct-mine.sh`, `test-instinct-inject.sh` | Bash harnesses |
| `team/agents/instinct-observer.md` | System prompt for the Haiku miner (JSON-only output) |
| `team/agents/oracle-reference/instinct-review.md` | Oracle JIT prompt for `[IN]` |
| `claude-commands/team/instincts.md` | `/team:instincts` loader |
| `.agents/decisions/2026-09-19-instincts-supersede-learnings.yaml` | Decision record |

---

### Task 1: Config reader, config block, gitignore

**Files:**
- Create: `scripts/instincts/__init__.py` (empty), `scripts/instincts/config.py`, `scripts/instincts/tests/__init__.py` (empty), `scripts/instincts/tests/test_config.py`
- Modify: `.agents/config.yaml` (append block), `.gitignore` (append)
- Create: `team/_memory/_learnings/instincts/.gitkeep`

**Interfaces:**
- Produces: `config.DEFAULTS: dict`, `config.load(root: str|Path) -> dict` (keys exactly as DEFAULTS; missing file/block → defaults). CLI: `python3 scripts/instincts/config.py --root R k1 k2…` prints one value per line, `True`/`False` for bools.

- [ ] **Step 1: Write the failing tests**

```python
# scripts/instincts/tests/test_config.py
import subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

BLOCK = """coordination:
  heartbeat_interval_calls: 20

instincts:
  enabled: false           # off for this test
  model: sonnet
  min_candidates: 5
  min_confidence: 0.6
  # a comment line
other:
  x: 1
"""

def test_defaults_when_no_file(tmp_path):
    cfg = config.load(tmp_path)
    assert cfg == config.DEFAULTS

def test_parses_block_and_ignores_other_sections(tmp_path):
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".agents" / "config.yaml").write_text(BLOCK)
    cfg = config.load(tmp_path)
    assert cfg["enabled"] is False
    assert cfg["model"] == "sonnet"
    assert cfg["min_candidates"] == 5
    assert cfg["min_confidence"] == 0.6
    assert cfg["inject_limit"] == config.DEFAULTS["inject_limit"]

def test_bad_values_fall_back(tmp_path):
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".agents" / "config.yaml").write_text("instincts:\n  min_candidates: many\n  enabled: yes\n")
    cfg = config.load(tmp_path)
    assert cfg["min_candidates"] == config.DEFAULTS["min_candidates"]
    assert cfg["enabled"] is True

def test_cli_prints_requested_keys(tmp_path):
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".agents" / "config.yaml").write_text("instincts:\n  model: haiku\n  min_candidates: 4\n")
    out = subprocess.run(
        [sys.executable, str(Path(config.__file__)), "--root", str(tmp_path), "enabled", "model", "min_candidates"],
        capture_output=True, text=True, check=True).stdout.splitlines()
    assert out == ["True", "haiku", "4"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest scripts/instincts/tests/test_config.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Write config.py**

```python
#!/usr/bin/env python3
"""Read the `instincts:` block of .agents/config.yaml.

The block is flat `key: value  # comment` lines, so no YAML library is needed.
Missing file, missing block, or unparsable values fall back to DEFAULTS.
"""
import argparse
import sys
from pathlib import Path

DEFAULTS = {
    "enabled": True,
    "model": "haiku",
    "min_candidates": 3,
    "inject_limit": 6,
    "inject_max_chars": 2000,
    "min_confidence": 0.7,
    "auto_accept_confidence": 0.7,
    "decay_per_week": 0.02,
    "observations_max_mb": 10,
    "pending_ttl_days": 30,
}


def _coerce(raw, default):
    raw = raw.split("#", 1)[0].strip().strip('"').strip("'")
    if isinstance(default, bool):
        return raw.lower() in ("true", "yes", "on", "1")
    if isinstance(default, int):
        try:
            return int(raw)
        except ValueError:
            return default
    if isinstance(default, float):
        try:
            return float(raw)
        except ValueError:
            return default
    return raw or default


def load(root):
    cfg = dict(DEFAULTS)
    path = Path(root) / ".agents" / "config.yaml"
    if not path.is_file():
        return cfg
    in_block = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("instincts:"):
            in_block = True
            continue
        if not in_block:
            continue
        if line and not line[0].isspace():
            break
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, _, raw = stripped.partition(":")
        key = key.strip()
        if key in DEFAULTS:
            cfg[key] = _coerce(raw, DEFAULTS[key])
    return cfg


def main(argv=None):
    ap = argparse.ArgumentParser(description="Print instinct config values, one per line.")
    ap.add_argument("--root", required=True)
    ap.add_argument("keys", nargs="+")
    a = ap.parse_args(argv)
    cfg = load(a.root)
    for k in a.keys:
        print(cfg.get(k, ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Append the config block and gitignore entries**

Append to `.agents/config.yaml`:

```yaml

# Instinct capture loop (learned behaviors). See: docs/specs/2026-09-19-instinct-capture-loop-design.md
instincts:
  enabled: true
  model: haiku                 # miner model for `claude -p`
  min_candidates: 3            # prefilter gate before spawning the miner
  inject_limit: 6              # max instincts injected at SessionStart
  inject_max_chars: 2000
  min_confidence: 0.7          # eligible for injection
  auto_accept_confidence: 0.7  # Oracle auto mode accepts pending >= this
  decay_per_week: 0.02
  observations_max_mb: 10
  pending_ttl_days: 30
```

Append to `.gitignore`:

```
# Instinct capture loop — raw observations and miner state are local only
team/_memory/_learnings/observations.jsonl*
team/_memory/_learnings/miner.log
team/_memory/_learnings/.miner.lock
team/_memory/_learnings/.instinct-watermark
team/_memory/_learnings/.candidates.json
```

Create empty files: `scripts/instincts/__init__.py`, `scripts/instincts/tests/__init__.py`, `team/_memory/_learnings/instincts/.gitkeep`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest scripts/instincts/tests/test_config.py -q`
Expected: `4 passed`

- [ ] **Step 6: Commit**

```bash
git add scripts/instincts .agents/config.yaml .gitignore team/_memory/_learnings/instincts/.gitkeep
git commit -m "feat(instincts): config reader and instincts block in .agents/config.yaml"
```

---

### Task 2: Instinct store core — flat YAML, confidence, ingest

**Files:**
- Create: `scripts/instincts/instinct.py`, `scripts/instincts/tests/test_instinct.py`

**Interfaces:**
- Produces (module `instinct`):
  - `project_dir(root) -> Path`, `user_dir() -> Path`
  - `dump_instinct(d: dict) -> str`, `parse_instinct(text) -> dict`, `read_instinct(path) -> dict|None`, `write_instinct(path, d)` (atomic)
  - `load_tier(directory, tier) -> (list[dict], list[str])` — each dict gains `_path`, `_tier`; second list = unreadable paths
  - `load_all(root) -> (list[dict], list[str])` — project + user tiers
  - `initial_confidence(n) -> float`, `clamp(c) -> float`, `weeks_since(day_str, today) -> float`, `effective_confidence(inst, today, decay_per_week) -> float`
  - `validate(obj) -> dict|None`, `extract_json_array(text) -> list`, `ingest(root, objs, today: date, project_name) -> dict(created, merged, contradicted, dropped)`
  - constants `ID_RE, DOMAINS, GLOBAL_DOMAINS, STATUSES`
- Miner output object shape (consumed by `ingest`): `{"id","trigger","action","confidence"?,"domain"?,"scope"?,"evidence":[str],"observed_count"?,"contradicts"?: id}`

- [ ] **Step 1: Write the failing tests**

```python
# scripts/instincts/tests/test_instinct.py
import json, sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import instinct  # noqa: E402

TODAY = date(2026, 9, 19)

@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTINCTS_USER_DIR", str(tmp_path / "user"))
    (tmp_path / ".agents").mkdir()
    return tmp_path

def sample(**over):
    d = {"id": "prefer-gh-cli", "trigger": "when calling the GitHub API", "action": "use gh api",
         "confidence": 0.5, "domain": "workflow", "scope": "project", "status": "pending",
         "source": "session-observation", "project_name": "MyAgents",
         "evidence": ['2026-09-19 s1: user said "use gh"'], "observed_count": 3,
         "first_seen": "2026-09-19", "last_seen": "2026-09-19"}
    d.update(over); return d

def test_yaml_roundtrip_preserves_types_and_quotes():
    d = sample(trigger='when "quoting": things', evidence=["a: b", "123"])
    back = instinct.parse_instinct(instinct.dump_instinct(d))
    assert back == d
    assert isinstance(back["confidence"], float) and isinstance(back["observed_count"], int)
    assert back["evidence"][1] == "123"

def test_write_is_atomic_and_readable(root):
    p = instinct.project_dir(root) / "x.yaml"
    instinct.write_instinct(p, sample(id="x"))
    assert instinct.read_instinct(p)["id"] == "x"
    assert not list(p.parent.glob(".tmp-*"))

def test_read_rejects_malformed(root):
    p = instinct.project_dir(root); p.mkdir(parents=True)
    (p / "bad.yaml").write_text("id: bad\nstatus: bogus\n")
    (p / "nope.yaml").write_text("just text")
    items, bad = instinct.load_tier(p, "project")
    assert items == [] and len(bad) == 2

@pytest.mark.parametrize("n,expected", [(1, 0.3), (2, 0.3), (3, 0.5), (5, 0.5), (6, 0.7), (10, 0.7), (11, 0.85)])
def test_initial_confidence(n, expected):
    assert instinct.initial_confidence(n) == expected

def test_effective_confidence_decays_with_floor():
    d = sample(confidence=0.7, last_seen="2026-08-22")  # 4 weeks
    assert instinct.effective_confidence(d, TODAY, 0.02) == pytest.approx(0.62)
    d = sample(confidence=0.32, last_seen="2026-01-01")
    assert instinct.effective_confidence(d, TODAY, 0.02) == 0.3

def test_validate_normalizes_and_rejects():
    ok = instinct.validate({"id": "use-gh", "trigger": "t", "action": "a", "domain": "nope", "observed_count": 4})
    assert ok["domain"] == "workflow" and ok["scope"] == "project" and ok["confidence"] == 0.5
    assert instinct.validate({"id": "Bad Id", "trigger": "t", "action": "a"}) is None
    assert instinct.validate({"id": "ok-id", "trigger": "", "action": "a"}) is None
    assert instinct.validate("nope") is None

def test_extract_json_array_tolerates_fences():
    text = "Here you go:\n```json\n[{\"id\": \"a-b-c\"}]\n```\n"
    assert instinct.extract_json_array(text) == [{"id": "a-b-c"}]
    assert instinct.extract_json_array("no json") == []

def test_ingest_creates_pending_then_merges(root):
    r = instinct.ingest(root, [{"id": "use-gh-api", "trigger": "t", "action": "a", "evidence": ["e1"]}], TODAY, "MyAgents")
    assert r["created"] == ["use-gh-api"]
    d = instinct.read_instinct(instinct.project_dir(root) / "use-gh-api.yaml")
    assert d["status"] == "pending" and d["confidence"] == 0.3 and d["project_name"] == "MyAgents"
    r = instinct.ingest(root, [{"id": "use-gh-api", "trigger": "t", "action": "a", "evidence": ["e2"], "observed_count": 2}], TODAY, "MyAgents")
    assert r["merged"] == ["use-gh-api"]
    d = instinct.read_instinct(instinct.project_dir(root) / "use-gh-api.yaml")
    assert d["observed_count"] == 3 and d["confidence"] == 0.5 and d["evidence"] == ["e1", "e2"]

def test_ingest_never_resurrects_rejected(root):
    instinct.write_instinct(instinct.project_dir(root) / "dead.yaml", sample(id="dead", status="rejected"))
    r = instinct.ingest(root, [{"id": "dead", "trigger": "t", "action": "a"}], TODAY, "P")
    assert r["dropped"] == 1 and instinct.read_instinct(instinct.project_dir(root) / "dead.yaml")["status"] == "rejected"

def test_ingest_contradiction_lowers_confidence(root):
    instinct.write_instinct(instinct.project_dir(root) / "old.yaml", sample(id="old", confidence=0.7, status="active"))
    r = instinct.ingest(root, [{"id": "old", "trigger": "t", "action": "a", "contradicts": "old"}], TODAY, "P")
    assert r["contradicted"] == ["old"] and r["merged"] == []
    assert instinct.read_instinct(instinct.project_dir(root) / "old.yaml")["confidence"] == 0.6
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest scripts/instincts/tests/test_instinct.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'instinct'`

- [ ] **Step 3: Write instinct.py (core; CLI `main` is added in Task 3)**

```python
#!/usr/bin/env python3
"""Instinct store: small learned behaviors with confidence scores.

Files are flat YAML (a subset we write and read ourselves — strings are JSON-quoted,
`evidence` is a list of quoted strings). Project tier lives in the repo and is
committed; user tier lives in ~/.claude/instincts/ and receives promoted instincts.
Stdlib only, Python 3.8+.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as _config  # noqa: E402

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,60}$")
DOMAINS = {"code-style", "testing", "git", "debugging", "workflow", "security", "tooling"}
GLOBAL_DOMAINS = {"security", "workflow", "tooling", "git"}
STATUSES = {"pending", "active", "rejected"}
LIST_KEYS = ("evidence",)
KEY_ORDER = ["id", "trigger", "action", "confidence", "domain", "scope", "status", "source",
             "project_name", "evidence", "observed_count", "first_seen", "last_seen"]


# ---------- paths ----------

def resolve_root(arg=None):
    if arg:
        return Path(arg).resolve()
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        return Path(out.stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return Path.cwd()


def learnings_dir(root):
    return Path(root) / "team" / "_memory" / "_learnings"


def project_dir(root):
    return learnings_dir(root) / "instincts"


def user_dir():
    return Path(os.environ.get("INSTINCTS_USER_DIR") or Path.home() / ".claude" / "instincts")


# ---------- flat YAML ----------

def dump_instinct(d):
    lines = []
    for k in KEY_ORDER:
        if k not in d:
            continue
        v = d[k]
        if k in LIST_KEYS:
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {json.dumps(str(item))}")
        elif isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, (int, float)):
            lines.append(f"{k}: {v}")
        else:
            lines.append(f"{k}: {json.dumps(str(v))}")
    return "\n".join(lines) + "\n"


def _scalar(raw):
    raw = raw.strip()
    if raw.startswith('"'):
        try:
            return json.loads(raw)
        except ValueError:
            return raw.strip('"')
    if raw in ("true", "false"):
        return raw == "true"
    for cast in (int, float):
        try:
            return cast(raw)
        except ValueError:
            pass
    return raw


def parse_instinct(text):
    d = {}
    current_list = None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and current_list is not None:
            d[current_list].append(_scalar(line[4:]))
            continue
        key, sep, raw = line.partition(":")
        if not sep:
            continue
        key = key.strip()
        if raw.strip() == "":
            d[key] = []
            current_list = key
        else:
            d[key] = _scalar(raw)
            current_list = None
    return d


def read_instinct(path):
    try:
        d = parse_instinct(Path(path).read_text(encoding="utf-8"))
    except OSError:
        return None
    if not d.get("id") or d.get("status") not in STATUSES:
        return None
    if "evidence" not in d or not isinstance(d["evidence"], list):
        d["evidence"] = []
    return d


def write_instinct(path, d):
    """Temp + flush + fsync + atomic rename, so a crash never half-writes a file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".yaml")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(dump_instinct(d))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _public(d):
    return {k: v for k, v in d.items() if not k.startswith("_")}


def load_tier(directory, tier):
    items, bad = [], []
    directory = Path(directory)
    if not directory.is_dir():
        return items, bad
    for p in sorted(directory.glob("*.yaml")):
        d = read_instinct(p)
        if d is None:
            bad.append(str(p))
            continue
        d["_path"] = str(p)
        d["_tier"] = tier
        items.append(d)
    return items, bad


def load_all(root):
    proj, bad1 = load_tier(project_dir(root), "project")
    usr, bad2 = load_tier(user_dir(), "user")
    return proj + usr, bad1 + bad2


# ---------- confidence ----------

def initial_confidence(n):
    if n <= 2:
        return 0.3
    if n <= 5:
        return 0.5
    if n <= 10:
        return 0.7
    return 0.85


def clamp(c):
    return round(min(0.9, max(0.3, float(c))), 2)


def weeks_since(day_str, today):
    try:
        d = date.fromisoformat(str(day_str))
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, (today - d).days / 7.0)


def effective_confidence(inst, today, decay_per_week):
    base = float(inst.get("confidence", 0.3))
    return clamp(base - decay_per_week * weeks_since(inst.get("last_seen"), today))


# ---------- ingest ----------

def validate(obj):
    if not isinstance(obj, dict):
        return None
    iid = str(obj.get("id", "")).strip()
    if not ID_RE.match(iid):
        return None
    trig = str(obj.get("trigger", "")).strip()[:300]
    act = str(obj.get("action", "")).strip()[:300]
    if not trig or not act:
        return None
    domain = obj.get("domain") if obj.get("domain") in DOMAINS else "workflow"
    scope = obj.get("scope") if obj.get("scope") in ("project", "global") else "project"
    try:
        count = max(1, int(obj.get("observed_count", 1)))
    except (TypeError, ValueError):
        count = 1
    conf = obj.get("confidence")
    try:
        conf = clamp(conf) if conf is not None else initial_confidence(count)
    except (TypeError, ValueError):
        conf = initial_confidence(count)
    evidence = [str(e)[:300] for e in obj.get("evidence", []) or [] if str(e).strip()][:10]
    out = {"id": iid, "trigger": trig, "action": act, "confidence": conf, "domain": domain,
           "scope": scope, "evidence": evidence, "observed_count": count}
    if isinstance(obj.get("contradicts"), str) and obj["contradicts"].strip():
        out["contradicts"] = obj["contradicts"].strip()
    return out


def extract_json_array(text):
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return []
    return data if isinstance(data, list) else []


def ingest(root, objs, today, project_name):
    result = {"created": [], "merged": [], "contradicted": [], "dropped": 0}
    existing = {d["id"]: d for d in load_tier(project_dir(root), "project")[0]}
    day = today.isoformat()
    for raw in objs:
        obj = validate(raw)
        if obj is None:
            result["dropped"] += 1
            continue
        target = obj.pop("contradicts", None)
        if target and target in existing and existing[target]["status"] != "rejected":
            t = existing[target]
            t["confidence"] = clamp(float(t["confidence"]) - 0.10)
            t["evidence"] = (t.get("evidence", []) + [f"{day} contradicted: {obj['trigger']}"])[-20:]
            t["last_seen"] = day
            write_instinct(t["_path"], _public(t))
            result["contradicted"].append(target)
            if obj["id"] == target:
                continue
        cur = existing.get(obj["id"])
        if cur is not None:
            if cur["status"] == "rejected":
                result["dropped"] += 1
                continue
            cur["observed_count"] = int(cur.get("observed_count", 1)) + obj["observed_count"]
            cur["confidence"] = clamp(max(float(cur["confidence"]) + 0.05, initial_confidence(cur["observed_count"])))
            cur["evidence"] = list(dict.fromkeys(cur.get("evidence", []) + obj["evidence"]))[-20:]
            cur["last_seen"] = day
            write_instinct(cur["_path"], _public(cur))
            result["merged"].append(obj["id"])
        else:
            new = dict(obj)
            new.update({"status": "pending", "source": "session-observation", "project_name": project_name,
                        "first_seen": day, "last_seen": day})
            path = project_dir(root) / f"{obj['id']}.yaml"
            write_instinct(path, new)
            existing[obj["id"]] = dict(new, _path=str(path), _tier="project")
            result["created"].append(obj["id"])
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest scripts/instincts/tests/test_instinct.py -q`
Expected: `16 passed` (7 parametrized + 9)

- [ ] **Step 5: Commit**

```bash
git add scripts/instincts/instinct.py scripts/instincts/tests/test_instinct.py
git commit -m "feat(instincts): instinct store core — flat YAML, confidence rules, ingest/merge"
```

---

### Task 3: Instinct CLI — status, accept/reject/review, prune, inject

**Files:**
- Modify: `scripts/instincts/instinct.py` (append), `scripts/instincts/tests/test_instinct.py` (append)

**Interfaces:**
- Produces: `status(root, today, cfg) -> dict(pending[], active[], rejected_ids[], unreadable[], last_miner_line)`, `set_status(root, ids, new_status, min_confidence=None) -> list[str]`, `prune(root, today, ttl_days) -> list[str]`, `rank_key(d, today, cfg) -> float`, `inject(root, today, cfg) -> str`, `register_project(root)`, `main(argv) -> int`.
- CLI (all take `--root DIR` and `--today YYYY-MM-DD`): `status [--json]`, `accept [ids…] [--min-confidence X]`, `reject ids…`, `review`, `prune [--ttl-days N]`, `inject`, `ingest [--project-name N]` (reads miner text on stdin), `rejected-ids`. `promote`, `export`, `import` are added in Task 4 — register their subparsers now with a stub that prints `not implemented` and returns 2.

- [ ] **Step 1: Append failing tests**

```python
# append to scripts/instincts/tests/test_instinct.py
import io

def cfg(**over):
    from config import DEFAULTS
    c = dict(DEFAULTS); c.update(over); return c

def seed(root, **over):
    d = sample(**over)
    instinct.write_instinct(instinct.project_dir(root) / f"{d['id']}.yaml", d)
    return d

def test_status_counts_and_unreadable(root):
    seed(root, id="p1"); seed(root, id="a1", status="active"); seed(root, id="r1", status="rejected")
    (instinct.project_dir(root) / "junk.yaml").write_text("nope")
    s = instinct.status(root, TODAY, cfg())
    assert [d["id"] for d in s["pending"]] == ["p1"]
    assert [d["id"] for d in s["active"]] == ["a1"]
    assert s["rejected_ids"] == ["r1"] and len(s["unreadable"]) == 1

def test_accept_by_id_and_by_threshold(root):
    seed(root, id="lo", confidence=0.3); seed(root, id="hi", confidence=0.75); seed(root, id="mid", confidence=0.5)
    assert instinct.set_status(root, ["mid"], "active") == ["mid"]
    assert instinct.set_status(root, [], "active", min_confidence=0.7) == ["hi"]
    assert instinct.read_instinct(instinct.project_dir(root) / "lo.yaml")["status"] == "pending"

def test_reject_only_touches_pending(root):
    seed(root, id="a1", status="active"); seed(root, id="p1")
    assert instinct.set_status(root, ["a1", "p1"], "rejected") == ["p1"]

def test_prune_old_pending_and_rejected(root):
    seed(root, id="old-p", last_seen="2026-07-01"); seed(root, id="new-p", last_seen="2026-09-10")
    seed(root, id="old-r", status="rejected", last_seen="2026-05-01"); seed(root, id="act", status="active", last_seen="2026-01-01")
    assert sorted(instinct.prune(root, TODAY, 30)) == ["old-p", "old-r"]
    assert (instinct.project_dir(root) / "act.yaml").exists()

def test_inject_ranks_filters_caps_and_registers(root):
    seed(root, id="best", status="active", confidence=0.9, domain="git")
    seed(root, id="stale", status="active", confidence=0.72, last_seen="2026-07-01")  # decays below 0.7
    seed(root, id="pend")
    instinct.write_instinct(instinct.user_dir() / "glob.yaml", sample(id="glob", status="active", scope="global", confidence=0.8))
    out = instinct.inject(root, TODAY, cfg())
    lines = out.strip().splitlines()
    assert lines[0].startswith("[instincts] 2 active (1 project, 1 global) · 1 pending")
    assert lines[1].startswith("- when calling the GitHub API → use gh api (0.90, git)")
    assert len(lines) == 3 and "stale" not in out
    assert str(root.resolve()) in (instinct.user_dir() / ".projects").read_text()

def test_inject_respects_limit_and_chars(root):
    for i in range(8):
        seed(root, id=f"i{i}", status="active", confidence=0.8, action="x" * 100)
    out = instinct.inject(root, TODAY, cfg(inject_limit=3))
    assert len(out.strip().splitlines()) == 4
    out = instinct.inject(root, TODAY, cfg(inject_max_chars=260))
    assert len(out.strip().splitlines()) == 2

def test_inject_empty_and_disabled(root):
    assert instinct.inject(root, TODAY, cfg()) == ""
    seed(root, id="a", status="active", confidence=0.9)
    assert instinct.inject(root, TODAY, cfg(enabled=False)) == ""

def test_cli_ingest_reads_miner_text(root, capsys):
    rc = instinct.main(["--root", str(root), "--today", "2026-09-19", "ingest", "--project-name", "P"],
                       stdin=io.StringIO('blah\n[{"id":"from-cli","trigger":"t","action":"a"}]\n'))
    assert rc == 0 and "from-cli" in capsys.readouterr().out
    assert (instinct.project_dir(root) / "from-cli.yaml").exists()

def test_cli_status_json_and_rejected_ids(root, capsys):
    seed(root, id="r1", status="rejected")
    assert instinct.main(["--root", str(root), "status", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["rejected_ids"] == ["r1"]
    assert instinct.main(["--root", str(root), "rejected-ids"]) == 0
    assert capsys.readouterr().out.strip() == "r1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest scripts/instincts/tests/test_instinct.py -q`
Expected: FAIL — `AttributeError: module 'instinct' has no attribute 'status'` (and similar)

- [ ] **Step 3: Append the CLI layer to instinct.py**

```python
# ---------- status / review ----------

def _summary(d, today, cfg):
    return {"id": d["id"], "tier": d["_tier"], "trigger": d["trigger"], "action": d["action"],
            "confidence": effective_confidence(d, today, cfg["decay_per_week"]),
            "domain": d.get("domain", "workflow"), "scope": d.get("scope", "project")}


def status(root, today, cfg):
    items, bad = load_all(root)
    by = {"pending": [], "active": [], "rejected": []}
    for d in items:
        by[d["status"]].append(d)
    last = None
    log = learnings_dir(root) / "miner.log"
    if log.is_file():
        lines = log.read_text(encoding="utf-8", errors="replace").strip().splitlines()
        last = lines[-1] if lines else None
    return {"pending": [_summary(d, today, cfg) for d in by["pending"]],
            "active": [_summary(d, today, cfg) for d in by["active"]],
            "rejected_ids": [d["id"] for d in by["rejected"]],
            "unreadable": bad, "last_miner_line": last}


def set_status(root, ids, new_status, min_confidence=None):
    changed = []
    for d in load_tier(project_dir(root), "project")[0]:
        if d["status"] != "pending":
            continue
        if ids and d["id"] not in ids:
            continue
        if min_confidence is not None and float(d["confidence"]) < min_confidence:
            continue
        d["status"] = new_status
        write_instinct(d["_path"], _public(d))
        changed.append(d["id"])
    return changed


def prune(root, today, ttl_days, rejected_ttl_days=90):
    removed = []
    for d in load_tier(project_dir(root), "project")[0]:
        age = weeks_since(d.get("last_seen"), today) * 7
        if (d["status"] == "pending" and age > ttl_days) or (d["status"] == "rejected" and age > rejected_ttl_days):
            try:
                os.remove(d["_path"])
                removed.append(d["id"])
            except OSError:
                pass
    return removed


# ---------- inject ----------

def register_project(root):
    reg = user_dir() / ".projects"
    try:
        reg.parent.mkdir(parents=True, exist_ok=True)
        entries = set(reg.read_text(encoding="utf-8").splitlines()) if reg.is_file() else set()
        rp = Path(root).resolve()
        entry = f"{rp}\t{rp.name}"
        if entry not in entries:
            with reg.open("a", encoding="utf-8") as f:
                f.write(entry + "\n")
    except OSError:
        pass


def rank_key(d, today, cfg):
    recency = max(0.5, 1 - weeks_since(d.get("last_seen"), today) * 0.05)
    boost = 0.05 if d["_tier"] == "project" else 0.0
    return effective_confidence(d, today, cfg["decay_per_week"]) * recency + boost


def inject(root, today, cfg):
    if not cfg.get("enabled", True):
        return ""
    items, _ = load_all(root)
    register_project(root)
    decay = cfg["decay_per_week"]
    active = [d for d in items if d["status"] == "active"
              and effective_confidence(d, today, decay) >= cfg["min_confidence"]]
    pending = sum(1 for d in items if d["status"] == "pending")
    if not active and not pending:
        return ""
    active.sort(key=lambda d: rank_key(d, today, cfg), reverse=True)
    n_proj = sum(1 for d in active if d["_tier"] == "project")
    head = f"[instincts] {len(active)} active ({n_proj} project, {len(active) - n_proj} global)"
    if pending:
        head += f" · {pending} pending — /team:instincts review or ask Athena"
    head += ". Context, not policy."
    lines = [head]
    for d in active[:cfg["inject_limit"]]:
        line = f"- {d['trigger']} → {d['action']} ({effective_confidence(d, today, decay):.2f}, {d.get('domain', 'workflow')})"
        if len("\n".join(lines + [line])) > cfg["inject_max_chars"]:
            break
        lines.append(line)
    return "\n".join(lines) + "\n"


# ---------- CLI ----------

def _print_status(s):
    print(f"Instincts: {len(s['active'])} active, {len(s['pending'])} pending, {len(s['rejected_ids'])} rejected")
    for label in ("active", "pending"):
        if s[label]:
            print(f"\n{label.upper()}")
            for d in s[label]:
                print(f"  {d['id']} [{d['tier']}] {d['trigger']} → {d['action']} ({d['confidence']:.2f}, {d['domain']})")
    if s["unreadable"]:
        print("\nUNREADABLE: " + ", ".join(s["unreadable"]))
    if s["last_miner_line"]:
        print(f"\nLast miner: {s['last_miner_line']}")


def _review(root, today, cfg, stdin):
    accepted, rejected = [], []
    for d in status(root, today, cfg)["pending"]:
        print(f"{d['id']}: {d['trigger']} → {d['action']} ({d['confidence']:.2f}, {d['domain']})  [a]ccept / [r]eject / [s]kip: ", end="", flush=True)
        ans = (stdin.readline() or "").strip().lower()
        if ans.startswith("a"):
            accepted += set_status(root, [d["id"]], "active")
        elif ans.startswith("r"):
            rejected += set_status(root, [d["id"]], "rejected")
    print(f"accepted={accepted} rejected={rejected}")


def main(argv=None, stdin=None):
    import argparse
    stdin = stdin or sys.stdin
    ap = argparse.ArgumentParser(description="Instinct store CLI")
    ap.add_argument("--root")
    ap.add_argument("--today")
    sub = ap.add_subparsers(dest="cmd")
    sub.required = True
    p = sub.add_parser("status"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("accept"); p.add_argument("ids", nargs="*"); p.add_argument("--min-confidence", type=float)
    p = sub.add_parser("reject"); p.add_argument("ids", nargs="+")
    sub.add_parser("review")
    p = sub.add_parser("prune"); p.add_argument("--ttl-days", type=int)
    sub.add_parser("inject")
    p = sub.add_parser("ingest"); p.add_argument("--project-name")
    sub.add_parser("rejected-ids")
    sub.add_parser("promote")
    sub.add_parser("export")
    sub.add_parser("import")
    a = ap.parse_args(argv)

    root = resolve_root(a.root)
    cfg = _config.load(root)
    today = date.fromisoformat(a.today) if a.today else date.today()

    if a.cmd == "status":
        s = status(root, today, cfg)
        if a.json:
            print(json.dumps(s, indent=1))
        else:
            _print_status(s)
        return 0
    if a.cmd == "accept":
        print(" ".join(set_status(root, a.ids, "active", a.min_confidence)))
        return 0
    if a.cmd == "reject":
        print(" ".join(set_status(root, a.ids, "rejected")))
        return 0
    if a.cmd == "review":
        _review(root, today, cfg, stdin)
        return 0
    if a.cmd == "prune":
        print(" ".join(prune(root, today, a.ttl_days or cfg["pending_ttl_days"])))
        return 0
    if a.cmd == "inject":
        sys.stdout.write(inject(root, today, cfg))
        return 0
    if a.cmd == "ingest":
        objs = extract_json_array(stdin.read())
        r = ingest(root, objs, today, a.project_name or Path(root).name)
        print(json.dumps(r))
        return 0
    if a.cmd == "rejected-ids":
        print("\n".join(status(root, today, cfg)["rejected_ids"]))
        return 0
    print(f"{a.cmd}: not implemented", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest scripts/instincts/tests/test_instinct.py -q`
Expected: `25 passed`

- [ ] **Step 5: Smoke the CLI by hand**

Run: `python3 scripts/instincts/instinct.py --root . status`
Expected: `Instincts: 0 active, 0 pending, 0 rejected`

- [ ] **Step 6: Commit**

```bash
git add scripts/instincts/instinct.py scripts/instincts/tests/test_instinct.py
git commit -m "feat(instincts): CLI — status, accept/reject/review, prune, inject"
```

---

### Task 4: Promote, export, import

**Files:**
- Modify: `scripts/instincts/instinct.py`, `scripts/instincts/tests/test_instinct.py`

**Interfaces:**
- Produces: `similar(a, b) -> bool` (token-set Jaccard ≥ 0.8), `promote(root, today) -> list[str]`, `export_bundle(root) -> list[dict]`, `import_bundle(root, objs) -> int`. CLI `promote`, `export` (JSON to stdout), `import` (JSON from stdin).

- [ ] **Step 1: Append failing tests**

```python
# append to scripts/instincts/tests/test_instinct.py
def other_project(tmp_path, name):
    p = tmp_path / name; (p / ".agents").mkdir(parents=True); return p

def test_similar_triggers():
    assert instinct.similar("when calling the GitHub API", "when calling the github api!")
    assert not instinct.similar("when calling the GitHub API", "when writing tests")

def test_promote_requires_two_projects_high_confidence_and_domain(root, tmp_path):
    p2 = other_project(tmp_path, "p2"); p3 = other_project(tmp_path, "p3")
    instinct.register_project(p2); instinct.register_project(p3)
    seed(root, id="use-gh", status="active", confidence=0.85, domain="tooling")
    instinct.write_instinct(instinct.project_dir(p2) / "use-gh.yaml", sample(id="use-gh", status="active", confidence=0.8, domain="tooling"))
    # distinct triggers so these do not group with use-gh by similarity
    seed(root, id="lonely", status="active", confidence=0.9, domain="tooling", trigger="when only one project")   # one project only
    seed(root, id="style", status="active", confidence=0.9, domain="code-style", trigger="when styling code")     # domain not promotable
    instinct.write_instinct(instinct.project_dir(p3) / "style.yaml", sample(id="style", status="active", confidence=0.9, domain="code-style", trigger="when styling code"))
    seed(root, id="weak", status="active", confidence=0.6, domain="git", trigger="when confidence is weak")
    instinct.write_instinct(instinct.project_dir(p3) / "weak.yaml", sample(id="weak", status="active", confidence=0.6, domain="git", trigger="when confidence is weak"))
    assert instinct.promote(root, TODAY) == ["use-gh"]
    g = instinct.read_instinct(instinct.user_dir() / "use-gh.yaml")
    assert g["scope"] == "global" and g["status"] == "active" and "project_name" not in g
    assert instinct.promote(root, TODAY) == []  # idempotent

def test_export_import_roundtrip(root, tmp_path):
    seed(root, id="a1", status="active"); seed(root, id="r1", status="rejected")
    bundle = instinct.export_bundle(root)
    assert [d["id"] for d in bundle] == ["a1"]
    dest = other_project(tmp_path, "dest")
    assert instinct.import_bundle(dest, bundle + [{"id": "BAD", "status": "active"}]) == 1
    assert instinct.import_bundle(dest, bundle) == 0
    assert instinct.read_instinct(instinct.project_dir(dest) / "a1.yaml")["status"] == "active"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest scripts/instincts/tests/test_instinct.py -q -k "similar or promote or export"`
Expected: FAIL — `AttributeError: module 'instinct' has no attribute 'similar'`

- [ ] **Step 3: Insert the functions before `# ---------- CLI ----------` and wire the three commands**

```python
# ---------- promote / export / import ----------

def similar(a, b):
    ta = set(re.findall(r"[a-z0-9]+", a.lower()))
    tb = set(re.findall(r"[a-z0-9]+", b.lower()))
    if not ta or not tb:
        return False
    return len(ta & tb) / len(ta | tb) >= 0.8


def _registered_projects(root):
    paths = {str(Path(root).resolve())}
    reg = user_dir() / ".projects"
    if reg.is_file():
        for line in reg.read_text(encoding="utf-8").splitlines():
            p = line.split("\t")[0].strip()
            if p and Path(p).is_dir():
                paths.add(p)
    return sorted(paths)


def promote(root, today):
    groups = []
    for p in _registered_projects(root):
        for d in load_tier(project_dir(p), "project")[0]:
            if d["status"] != "active" or d.get("domain") not in GLOBAL_DOMAINS:
                continue
            d["_project"] = p
            for g in groups:
                if g[0]["id"] == d["id"] or similar(g[0]["trigger"], d["trigger"]):
                    g.append(d)
                    break
            else:
                groups.append([d])
    existing = {d["id"] for d in load_tier(user_dir(), "user")[0]}
    promoted = []
    for g in groups:
        projects = {d["_project"] for d in g}
        mean = sum(float(d["confidence"]) for d in g) / len(g)
        if len(projects) < 2 or mean < 0.8 or g[0]["id"] in existing:
            continue
        new = _public(g[0])
        new.pop("project_name", None)
        new.update({"scope": "global", "status": "active", "confidence": clamp(mean), "last_seen": today.isoformat(),
                    "evidence": (new.get("evidence", []) + [f"{today.isoformat()} promoted: seen in {len(projects)} projects"])[-20:]})
        write_instinct(user_dir() / f"{new['id']}.yaml", new)
        promoted.append(new["id"])
    return promoted


def export_bundle(root):
    items, _ = load_all(root)
    return [_public(d) for d in items if d["status"] != "rejected"]


def import_bundle(root, objs):
    n = 0
    for d in objs:
        if not isinstance(d, dict) or not ID_RE.match(str(d.get("id", ""))) or d.get("status") not in STATUSES:
            continue
        tier_dir = user_dir() if d.get("scope") == "global" else project_dir(root)
        path = tier_dir / f"{d['id']}.yaml"
        if path.exists():
            continue
        write_instinct(path, d)
        n += 1
    return n
```

In `main`, replace the trailing `print(f"{a.cmd}: not implemented"...)` / `return 2` with:

```python
    if a.cmd == "promote":
        print(" ".join(promote(root, today)))
        return 0
    if a.cmd == "export":
        print(json.dumps(export_bundle(root), indent=1))
        return 0
    if a.cmd == "import":
        try:
            objs = json.loads(stdin.read())
        except ValueError:
            objs = []
        print(import_bundle(root, objs if isinstance(objs, list) else []))
        return 0
    return 2
```

- [ ] **Step 4: Run the full Python suite**

Run: `python3 -m pytest scripts/instincts/tests -q`
Expected: `32 passed`

- [ ] **Step 5: Commit**

```bash
git add scripts/instincts/instinct.py scripts/instincts/tests/test_instinct.py
git commit -m "feat(instincts): promote across projects, export/import bundles"
```

---

### Task 5: Observation writer (`observe.py`) and capture hook (`observe.sh`)

**Files:**
- Create: `scripts/instincts/observe.py`, `scripts/instincts/tests/test_observe.py`, `.agents/hooks/observe.sh`, `.agents/hooks/test-observe.sh`
- Modify: `.claude/settings.local.json` (add two hook entries), `templates/settings.local.json.template` (same)

**Interfaces:**
- Produces: `observe.SECRET_RE`, `observe.scrub(s) -> str`, `observe.serialize(obj) -> str`, `observe.detect_error(resp_obj, resp_text) -> bool`, `observe.build_record(kind, data, now_iso) -> dict`, `observe.append_record(path, rec, max_mb)`, `observe.main(argv, stdin) -> int`. CLI: `observe.py prompt|tool --root R` reading hook JSON on stdin.
- Observation record (consumed by Task 6): `{"ts","session_id","event":"prompt","text"}` or `{"ts","session_id","event":"tool","tool","input","response","is_error"}`. `input`/`response` are JSON-serialized strings.

- [ ] **Step 1: Write the failing pytest**

```python
# scripts/instincts/tests/test_observe.py
import io, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import observe  # noqa: E402

def test_scrub_key_value_forms():
    assert observe.scrub("API_KEY=abc123 and token: xyz") == "API_KEY=[REDACTED] and token: [REDACTED]"
    assert observe.scrub('{"api_key": "abc", "x": 1}') == '{"api_key": "[REDACTED]", "x": 1}'
    assert observe.scrub("nothing here") == "nothing here"

def test_detect_error_from_fields_and_text():
    assert observe.detect_error({"exit_code": 1}, "") is True
    assert observe.detect_error({"is_error": True}, "") is True
    assert observe.detect_error(None, "Traceback (most recent call last):\n...") is True
    assert observe.detect_error({"exit_code": 0}, "all good") is False

def test_build_record_truncates_and_scrubs():
    rec = observe.build_record("tool", {"session_id": "s1", "tool_name": "Bash",
                                        "tool_input": {"command": "x" * 6000},
                                        "tool_response": {"stdout": "SECRET=hunter2", "exit_code": 0}}, "2026-09-19T00:00:00Z")
    assert rec["event"] == "tool" and rec["tool"] == "Bash" and len(rec["input"]) == 5000
    assert "[REDACTED]" in rec["response"] and rec["is_error"] is False
    rec = observe.build_record("prompt", {"session_id": "s1", "prompt": "p" * 3000}, "t")
    assert rec["event"] == "prompt" and len(rec["text"]) == 2000

def test_append_and_rotate(tmp_path):
    p = tmp_path / "observations.jsonl"
    observe.append_record(p, {"a": 1}, max_mb=10)
    observe.append_record(p, {"a": 2}, max_mb=10)
    assert [json.loads(l)["a"] for l in p.read_text().splitlines()] == [1, 2]
    p.write_text("x" * (1024 * 1024 + 1))
    observe.append_record(p, {"a": 3}, max_mb=1)
    assert (tmp_path / "observations.jsonl.1").exists() and json.loads(p.read_text())["a"] == 3

def test_main_writes_under_root_and_is_silent(tmp_path, capsys):
    (tmp_path / ".agents").mkdir()
    rc = observe.main(["prompt", "--root", str(tmp_path)], stdin=io.StringIO('{"session_id":"s","prompt":"hi"}'))
    assert rc == 0 and capsys.readouterr().out == ""
    line = json.loads((tmp_path / "team/_memory/_learnings/observations.jsonl").read_text())
    assert line["text"] == "hi" and line["event"] == "prompt"

def test_main_respects_off_marker_and_disabled(tmp_path):
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".instincts-off").touch()
    observe.main(["prompt", "--root", str(tmp_path)], stdin=io.StringIO('{"prompt":"hi"}'))
    assert not (tmp_path / "team/_memory/_learnings/observations.jsonl").exists()
    (tmp_path / ".instincts-off").unlink()
    (tmp_path / ".agents/config.yaml").write_text("instincts:\n  enabled: false\n")
    observe.main(["prompt", "--root", str(tmp_path)], stdin=io.StringIO('{"prompt":"hi"}'))
    assert not (tmp_path / "team/_memory/_learnings/observations.jsonl").exists()

def test_main_bad_json_is_noop(tmp_path):
    (tmp_path / ".agents").mkdir()
    assert observe.main(["tool", "--root", str(tmp_path)], stdin=io.StringIO("not json")) == 0
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest scripts/instincts/tests/test_observe.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'observe'`

- [ ] **Step 3: Write observe.py**

```python
#!/usr/bin/env python3
"""Append one scrubbed, truncated observation per hook event to observations.jsonl.

Called by .agents/hooks/observe.sh with `prompt` (UserPromptSubmit) or `tool` (PostToolUse).
Never prints to stdout; always returns 0.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as _config  # noqa: E402
from instinct import learnings_dir, resolve_root  # noqa: E402

SECRET_RE = re.compile(r'(?i)(api[_-]?key|token|secret|password|authorization|credentials?)("?\s*[:=]\s*"?)([^\s"]+)')
ERROR_LINE_RE = re.compile(r"^(Error|Traceback|FAILED|error:)", re.M)
MAX_IO = 5000
MAX_PROMPT = 2000


def scrub(s):
    return SECRET_RE.sub(lambda m: m.group(1) + m.group(2) + "[REDACTED]", s)


def serialize(obj):
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    try:
        return json.dumps(obj, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(obj)


def detect_error(resp_obj, resp_text):
    if isinstance(resp_obj, dict):
        if resp_obj.get("is_error") is True:
            return True
        code = resp_obj.get("exit_code")
        if isinstance(code, int) and code != 0:
            return True
    return bool(ERROR_LINE_RE.search(resp_text[:500]))


def build_record(kind, data, now_iso):
    rec = {"ts": now_iso, "session_id": str(data.get("session_id", "")), "event": kind}
    if kind == "prompt":
        rec["text"] = scrub(str(data.get("prompt", ""))[:MAX_PROMPT])
    else:
        resp = data.get("tool_response")
        resp_text = serialize(resp)
        rec["tool"] = str(data.get("tool_name", ""))
        rec["input"] = scrub(serialize(data.get("tool_input"))[:MAX_IO])
        rec["response"] = scrub(resp_text[:MAX_IO])
        rec["is_error"] = detect_error(resp, resp_text)
    return rec


def append_record(path, rec, max_mb):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if path.is_file() and path.stat().st_size > max_mb * 1024 * 1024:
            os.replace(path, path.with_name(path.name + ".1"))
    except OSError:
        pass
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main(argv=None, stdin=None):
    stdin = stdin or sys.stdin
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=("prompt", "tool"))
    ap.add_argument("--root")
    a = ap.parse_args(argv)
    try:
        if os.environ.get("INSTINCTS_SKIP"):
            return 0
        root = resolve_root(a.root)
        if (root / ".instincts-off").exists():
            return 0
        cfg = _config.load(root)
        if not cfg["enabled"]:
            return 0
        try:
            data = json.loads(stdin.read())
        except ValueError:
            return 0
        if not isinstance(data, dict):
            return 0
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        append_record(learnings_dir(root) / "observations.jsonl", build_record(a.kind, data, now), cfg["observations_max_mb"])
    except Exception:  # hooks must never fail
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run pytest to verify it passes**

Run: `python3 -m pytest scripts/instincts/tests/test_observe.py -q`
Expected: `7 passed`

- [ ] **Step 5: Write the bash hook and its harness**

`.agents/hooks/observe.sh`:

```bash
#!/usr/bin/env bash
# Hook: Instinct capture
# UserPromptSubmit → `observe.sh prompt`; PostToolUse → `observe.sh tool`.
# Appends one JSONL line to team/_memory/_learnings/observations.jsonl.
# Exit 0 always. NEVER writes to stdout (UserPromptSubmit stdout is injected into context).

[ -n "${INSTINCTS_SKIP:-}" ] && exit 0
command -v python3 >/dev/null 2>&1 || exit 0

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$HOOK_DIR/../.." && pwd)}"
[ -f "$ROOT/.instincts-off" ] && exit 0
[ -f "$ROOT/scripts/instincts/observe.py" ] || exit 0

python3 "$ROOT/scripts/instincts/observe.py" "${1:-tool}" --root "$ROOT" >/dev/null 2>&1
exit 0
```

`.agents/hooks/test-observe.sh`:

```bash
#!/usr/bin/env bash
set -e

HOOK=".agents/hooks/observe.sh"
PASS=0
FAIL=0
ROOT="$(pwd)"
OBS="team/_memory/_learnings/observations.jsonl"

setup() { rm -f "$OBS" "$OBS.1" .instincts-off; }
teardown() { rm -f "$OBS" "$OBS.1" .instincts-off; }

check() {
  local desc="$1" ok="$2"
  if [ "$ok" = "1" ]; then echo "  PASS: $desc"; PASS=$((PASS + 1)); else echo "  FAIL: $desc"; FAIL=$((FAIL + 1)); fi
}

echo "=== Observe Hook Tests ==="
setup
trap teardown EXIT

OUT="$(echo '{"session_id":"s1","prompt":"hello"}' | CLAUDE_PROJECT_DIR="$ROOT" bash "$HOOK" prompt)"; RC=$?
check "prompt event exits 0 and prints nothing" "$([ $RC -eq 0 ] && [ -z "$OUT" ] && echo 1 || echo 0)"
check "prompt event written" "$(grep -q '"event": *"prompt"' "$OBS" 2>/dev/null && echo 1 || echo 0)"

echo '{"session_id":"s1","tool_name":"Bash","tool_input":{"command":"echo API_KEY=abc"},"tool_response":{"exit_code":1,"stdout":"boom"}}' \
  | CLAUDE_PROJECT_DIR="$ROOT" bash "$HOOK" tool
check "tool event scrubbed" "$(grep -q 'API_KEY=\[REDACTED\]' "$OBS" && echo 1 || echo 0)"
check "tool event flagged is_error" "$(grep -q '"is_error": *true' "$OBS" && echo 1 || echo 0)"

echo 'not json' | CLAUDE_PROJECT_DIR="$ROOT" bash "$HOOK" tool; RC=$?
check "bad json exits 0" "$([ $RC -eq 0 ] && echo 1 || echo 0)"

BEFORE="$(wc -l < "$OBS")"
touch .instincts-off
echo '{"prompt":"x"}' | CLAUDE_PROJECT_DIR="$ROOT" bash "$HOOK" prompt
check ".instincts-off suppresses capture" "$([ "$(wc -l < "$OBS")" -eq "$BEFORE" ] && echo 1 || echo 0)"
rm -f .instincts-off

echo '{"prompt":"x"}' | INSTINCTS_SKIP=1 CLAUDE_PROJECT_DIR="$ROOT" bash "$HOOK" prompt
check "INSTINCTS_SKIP suppresses capture" "$([ "$(wc -l < "$OBS")" -eq "$BEFORE" ] && echo 1 || echo 0)"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
```

Run: `chmod +x .agents/hooks/observe.sh .agents/hooks/test-observe.sh && bash .agents/hooks/test-observe.sh`
Expected: `Results: 6 passed, 0 failed`

- [ ] **Step 6: Register the hook**

In `.claude/settings.local.json`, add to the existing `UserPromptSubmit[0].hooks` array (after slim-prompt):

```json
{
  "type": "command",
  "command": "bash \"$CLAUDE_PROJECT_DIR/.agents/hooks/observe.sh\" prompt",
  "timeout": 3000
}
```

and to the existing `PostToolUse[0].hooks` array (after heartbeat):

```json
{
  "type": "command",
  "command": "bash \"$CLAUDE_PROJECT_DIR/.agents/hooks/observe.sh\" tool",
  "timeout": 3000
}
```

Apply the same two additions to `templates/settings.local.json.template` — there, append the prompt entry to `UserPromptSubmit[0].hooks` and add a new `PostToolUse` matcher object `{"matcher": "", "hooks": [ …tool entry… ]}` after the existing `"matcher": "Bash"` object.

Validate: `python3 -c "import json;json.load(open('.claude/settings.local.json'));json.load(open('templates/settings.local.json.template'));print('ok')"`
Expected: `ok`

- [ ] **Step 7: Commit**

```bash
git add scripts/instincts/observe.py scripts/instincts/tests/test_observe.py .agents/hooks/observe.sh .agents/hooks/test-observe.sh .claude/settings.local.json templates/settings.local.json.template
git commit -m "feat(instincts): capture hook — scrubbed, truncated observations.jsonl"
```

---

### Task 6: Prefilter

**Files:**
- Create: `scripts/instincts/prefilter.py`, `scripts/instincts/tests/test_prefilter.py`

**Interfaces:**
- Produces: `prefilter.CORRECTION_RE`, `read_new(obs_path, offset) -> (events, new_offset)`, `signature(ev) -> str`, `find_candidates(events) -> list[dict]`, `main(argv) -> int`. CLI `prefilter.py --root R [--commit]` prints `{"count", "candidates", "rejected_ids", "new_offset"}`; `--commit` writes `new_offset` to `.instinct-watermark`.
- Candidate shape (consumed by the observer prompt, Task 7): `{"kind": "correction"|"error_resolution"|"repetition", "window": [event…], "count": int, "signature"?: str}`.

- [ ] **Step 1: Write the failing tests**

```python
# scripts/instincts/tests/test_prefilter.py
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import instinct, prefilter  # noqa: E402

def ev(event, **k):
    d = {"ts": "t", "session_id": "s", "event": event}; d.update(k); return d

def tool(name, inp, err=False, resp=""):
    return ev("tool", tool=name, input=json.dumps(inp), response=resp, is_error=err)

def write(root, events):
    p = instinct.learnings_dir(root) / "observations.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(e) + "\n" for e in events))
    return p

def test_correction_bundles_preceding_tools():
    events = [tool("Bash", {"command": "curl x"}), tool("Edit", {"file_path": "a.py"}), ev("prompt", text="No, use gh instead")]
    c = prefilter.find_candidates(events)
    assert [x["kind"] for x in c] == ["correction"]
    assert len(c[0]["window"]) == 3 and c[0]["window"][-1]["event"] == "prompt"

def test_correction_ignores_late_matches():
    assert prefilter.find_candidates([ev("prompt", text="x" * 130 + " actually")]) == []

def test_error_resolution_same_tool_within_three():
    events = [tool("Bash", {"command": "pytest"}, err=True), tool("Read", {"file_path": "t.py"}), tool("Bash", {"command": "pytest"})]
    c = prefilter.find_candidates(events)
    assert c[0]["kind"] == "error_resolution" and len(c[0]["window"]) == 3
    events = [tool("Bash", {"command": "x"}, err=True)] + [tool("Read", {"file_path": "t"})] * 3 + [tool("Bash", {"command": "x"})]
    assert prefilter.find_candidates(events) == []

def test_repetition_signature_threshold():
    events = [tool("Bash", {"command": "gh pr view 1"}), tool("Bash", {"command": "gh api x"}), tool("Bash", {"command": "gh issue list"}),
              tool("Edit", {"file_path": "a.ts"}), tool("Edit", {"file_path": "b.ts"})]
    c = prefilter.find_candidates(events)
    assert len(c) == 1 and c[0]["kind"] == "repetition" and c[0]["signature"] == "Bash:gh" and c[0]["count"] == 3

def test_window_strings_truncated():
    c = prefilter.find_candidates([tool("Bash", {"command": "x" * 3000}, err=True), tool("Bash", {"command": "y"})])
    assert len(c[0]["window"][0]["input"]) == 1000

def test_read_new_honors_offset_and_rotation(tmp_path):
    p = tmp_path / "o.jsonl"
    p.write_text('{"a":1}\n{"a":2}\n')
    events, off = prefilter.read_new(p, 0)
    assert [e["a"] for e in events] == [1, 2] and off == p.stat().st_size
    assert prefilter.read_new(p, off) == ([], off)
    p.write_text('{"a":3}\n')  # rotated: file now smaller than offset
    events, off2 = prefilter.read_new(p, off)
    assert [e["a"] for e in events] == [3] and off2 == p.stat().st_size

def test_main_commit_writes_watermark_and_rejected_ids(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("INSTINCTS_USER_DIR", str(tmp_path / "u"))
    (tmp_path / ".agents").mkdir()
    write(tmp_path, [ev("prompt", text="nope, not that"), tool("Bash", {"command": "x"})])
    instinct.write_instinct(instinct.project_dir(tmp_path) / "dead.yaml",
                            {"id": "dead", "trigger": "t", "action": "a", "confidence": 0.3, "status": "rejected", "evidence": []})
    assert prefilter.main(["--root", str(tmp_path), "--commit"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["count"] == 1 and out["rejected_ids"] == ["dead"]
    assert int((instinct.learnings_dir(tmp_path) / ".instinct-watermark").read_text()) == out["new_offset"]
    assert prefilter.main(["--root", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["count"] == 0
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest scripts/instincts/tests/test_prefilter.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'prefilter'`

- [ ] **Step 3: Write prefilter.py**

```python
#!/usr/bin/env python3
"""Cheap, deterministic pre-filter: turn new observations into candidate windows.

The miner (Haiku) only runs when enough candidates exist. Output is JSON on stdout.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import instinct  # noqa: E402

CORRECTION_RE = re.compile(r"\b(no,|nope|actually|instead|don't|do not|stop|wrong|not that)\b", re.I)
WINDOW_STR_MAX = 1000


def read_new(obs_path, offset):
    events = []
    obs_path = Path(obs_path)
    try:
        size = obs_path.stat().st_size
    except OSError:
        return [], offset
    if size < offset:  # rotated
        offset = 0
    new_offset = offset
    with obs_path.open("rb") as f:
        f.seek(offset)
        for raw in f:
            new_offset += len(raw)
            try:
                ev = json.loads(raw.decode("utf-8", "replace"))
            except ValueError:
                continue
            if isinstance(ev, dict):
                events.append(ev)
    return events, new_offset


def signature(ev):
    tool = ev.get("tool", "")
    try:
        inp = json.loads(ev.get("input", "") or "{}")
    except ValueError:
        inp = {}
    if not isinstance(inp, dict):
        return ""
    if tool in ("Bash", "PowerShell"):
        cmd = str(inp.get("command", "")).strip().split()
        return f"{tool}:{cmd[0]}" if cmd else ""
    if tool in ("Edit", "Write", "MultiEdit", "Read"):
        ext = Path(str(inp.get("file_path", ""))).suffix
        return f"{tool}:{ext}" if ext else ""
    return ""


def _trim(events):
    out = []
    for e in events:
        out.append({k: (v[:WINDOW_STR_MAX] if isinstance(v, str) else v) for k, v in e.items()})
    return out


def find_candidates(events):
    cands = []
    for i, ev in enumerate(events):
        if ev.get("event") == "prompt" and CORRECTION_RE.search(str(ev.get("text", ""))[:120]):
            window = [e for e in events[max(0, i - 3):i] if e.get("event") == "tool"] + [ev]
            cands.append({"kind": "correction", "window": _trim(window), "count": 1})
        elif ev.get("event") == "tool" and ev.get("is_error"):
            for j in range(i + 1, min(i + 4, len(events))):
                nxt = events[j]
                if nxt.get("event") == "tool" and nxt.get("tool") == ev.get("tool") and not nxt.get("is_error"):
                    cands.append({"kind": "error_resolution", "window": _trim(events[i:j + 1]), "count": 1})
                    break
    sigs = {}
    for ev in events:
        if ev.get("event") == "tool":
            s = signature(ev)
            if s:
                sigs.setdefault(s, []).append(ev)
    for s, evs in sigs.items():
        if len(evs) >= 3:
            cands.append({"kind": "repetition", "signature": s, "window": _trim(evs[:1]), "count": len(evs)})
    return cands


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root")
    ap.add_argument("--commit", action="store_true", help="advance the watermark")
    a = ap.parse_args(argv)
    root = instinct.resolve_root(a.root)
    ldir = instinct.learnings_dir(root)
    wm = ldir / ".instinct-watermark"
    try:
        offset = int(wm.read_text().strip()) if wm.is_file() else 0
    except ValueError:
        offset = 0
    events, new_offset = read_new(ldir / "observations.jsonl", offset)
    cands = find_candidates(events)
    rejected = [d["id"] for d in instinct.load_tier(instinct.project_dir(root), "project")[0] if d["status"] == "rejected"]
    if a.commit:
        ldir.mkdir(parents=True, exist_ok=True)
        wm.write_text(str(new_offset))
    print(json.dumps({"count": len(cands), "candidates": cands, "rejected_ids": rejected, "new_offset": new_offset}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest scripts/instincts/tests/test_prefilter.py -q`
Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add scripts/instincts/prefilter.py scripts/instincts/tests/test_prefilter.py
git commit -m "feat(instincts): prefilter — correction, error-resolution, repetition candidates"
```

---

### Task 7: Miner hook (Stop) and observer prompt

**Files:**
- Create: `.agents/hooks/instinct-mine.sh`, `.agents/hooks/test-instinct-mine.sh`, `team/agents/instinct-observer.md`
- Modify: `.claude/settings.local.json`, `templates/settings.local.json.template` (add `Stop`), `docs/specs/2026-09-19-instinct-capture-loop-design.md` (one line, see Step 1)

**Interfaces:**
- Consumes: `config.py --root R enabled model min_candidates`, `prefilter.py --root R --commit`, `instinct.py ingest --root R`.
- Produces: `miner.log` lines `<ISO ts> <message>`; `.miner.lock` content `<pid> <epoch>`.

- [ ] **Step 1: Amend the spec's lock rule**

In the spec, Stage 2 item 6 says the lock is released immediately after spawning. Holding it until the detached miner finishes (with the existing 10-minute stale rule) prevents two miners running concurrently on back-to-back Stops. Replace that sentence in `docs/specs/2026-09-19-instinct-capture-loop-design.md` with:

```
6. Advance watermark; the detached miner removes the lock when it finishes (stale after 10 min either way). The Stop hook must return in < 1s regardless of miner duration.
```

- [ ] **Step 2: Write the observer prompt**

`team/agents/instinct-observer.md`:

```markdown
# Instinct Observer

You analyze candidate windows from a coding session and output instincts: small learned behaviors.
You receive one JSON object on stdin: `{"count", "candidates": [{"kind", "window": [events], "count", "signature"?}], "rejected_ids": [...]}`.
Events are `{"event":"prompt","text"}` or `{"event":"tool","tool","input","response","is_error"}`.

## Output — JSON only

Output exactly one JSON array and nothing else — no prose, no code fences. Empty array `[]` is a valid answer.

```
[{"id": "kebab-case-id", "trigger": "when …", "action": "…", "domain": "code-style|testing|git|debugging|workflow|security|tooling",
  "scope": "project|global", "observed_count": 1, "evidence": ["<date> <kind>: <one-line summary>"], "contradicts": "<existing-id, optional>"}]
```

- `id`: 3–60 chars, `[a-z0-9-]`, starts alphanumeric. Reuse an obvious existing-style id when the pattern is the same (the store merges by id).
- `trigger`: narrow, starts with "when". `action`: one imperative sentence. Both ≤ 300 chars.
- `observed_count`: how many windows support this instinct. Omit `confidence`; the store computes it.
- `evidence`: one line per supporting window; describe the pattern, never quote code, secrets, or file contents.
- `contradicts`: set when a window shows the user rejecting behavior an existing instinct would produce.

## What counts

| kind | Create an instinct when | Otherwise |
|---|---|---|
| correction | The prompt clearly corrects the preceding tool use ("no, use X", "actually …", "instead") | Skip if the prompt is a new request, not a correction |
| error_resolution | The same fix would resolve the same error next time | Skip one-off typos and transient failures |
| repetition | The repeated sequence is a workflow worth naming | Skip ordinary read/grep browsing |

## Rules

1. Be conservative: no instinct from ambiguous windows. Prefer zero instincts over a wrong one.
2. Be specific: "when running tests in this repo, use `python3 -m pytest scripts/instincts/tests`" beats "prefer pytest".
3. Never re-propose an id in `rejected_ids`.
4. Default `scope: project`; use `global` only for patterns that are obviously universal (security, generic git hygiene).
5. Never include user names, emails, secrets, or code snippets in any field.
```

- [ ] **Step 3: Write the harness (fails first — no hook yet)**

`.agents/hooks/test-instinct-mine.sh`:

```bash
#!/usr/bin/env bash
set -e

HOOK=".agents/hooks/instinct-mine.sh"
PASS=0
FAIL=0
ROOT="$(pwd)"
LEARN="team/_memory/_learnings"
SHIM_DIR="$(mktemp -d)"
SHIM_LOG="$SHIM_DIR/claude.calls"

setup() {
  mkdir -p "$LEARN/instincts"
  rm -f "$LEARN/observations.jsonl" "$LEARN/.instinct-watermark" "$LEARN/.miner.lock" "$LEARN/miner.log" "$LEARN/.candidates.json" "$LEARN/instincts/mined-from-shim.yaml"
  cat > "$SHIM_DIR/claude" << 'EOF'
#!/usr/bin/env bash
echo "$@" >> "${SHIM_LOG:?}"
cat > /dev/null
echo 'Sure! [{"id":"mined-from-shim","trigger":"when testing","action":"use the shim","observed_count":3,"evidence":["e"]}]'
EOF
  chmod +x "$SHIM_DIR/claude"
}
teardown() {
  rm -f "$LEARN/observations.jsonl" "$LEARN/.instinct-watermark" "$LEARN/.miner.lock" "$LEARN/miner.log" "$LEARN/.candidates.json" "$LEARN/instincts/mined-from-shim.yaml"
  rm -rf "$SHIM_DIR"
}
check() {
  local desc="$1" ok="$2"
  if [ "$ok" = "1" ]; then echo "  PASS: $desc"; PASS=$((PASS + 1)); else echo "  FAIL: $desc"; FAIL=$((FAIL + 1)); fi
}
run_hook() { echo '{"session_id":"s","stop_hook_active":false}' | SHIM_LOG="$SHIM_LOG" PATH="$SHIM_DIR:$PATH" CLAUDE_PROJECT_DIR="$ROOT" bash "$HOOK"; }
wait_for() { local f="$1" n=0; while [ ! -e "$f" ] && [ $n -lt 50 ]; do sleep 0.1; n=$((n + 1)); done; [ -e "$f" ]; }
wait_gone() { local f="$1" n=0; while [ -e "$f" ] && [ $n -lt 50 ]; do sleep 0.1; n=$((n + 1)); done; [ ! -e "$f" ]; }

echo "=== Instinct Mine Hook Tests ==="
setup
trap teardown EXIT

# 1. below threshold: no spawn, watermark advanced
printf '%s\n' '{"event":"prompt","text":"no, use gh"}' > "$LEARN/observations.jsonl"
run_hook
check "below threshold: no claude call" "$([ ! -f "$SHIM_LOG" ] && echo 1 || echo 0)"
check "below threshold: watermark written" "$([ -s "$LEARN/.instinct-watermark" ] && echo 1 || echo 0)"
check "below threshold: lock released" "$([ ! -f "$LEARN/.miner.lock" ] && echo 1 || echo 0)"

# 2. at threshold: spawn once, ingest lands, lock cleared, hook returns fast
printf '%s\n' '{"event":"prompt","text":"no, use gh"}' '{"event":"prompt","text":"actually do X"}' '{"event":"prompt","text":"stop, wrong file"}' >> "$LEARN/observations.jsonl"
START=$(date +%s)
run_hook
check "hook returns in < 3s" "$([ $(( $(date +%s) - START )) -lt 3 ] && echo 1 || echo 0)"
check "claude called once" "$(wait_for "$SHIM_LOG" && [ "$(wc -l < "$SHIM_LOG")" -eq 1 ] && echo 1 || echo 0)"
check "claude called with -p and --model" "$(grep -q -- '-p' "$SHIM_LOG" && grep -q -- '--model' "$SHIM_LOG" && echo 1 || echo 0)"
check "instinct ingested as pending" "$(wait_for "$LEARN/instincts/mined-from-shim.yaml" && grep -q 'status: "pending"' "$LEARN/instincts/mined-from-shim.yaml" && echo 1 || echo 0)"
check "lock removed after miner" "$(wait_gone "$LEARN/.miner.lock" && echo 1 || echo 0)"

# 3. live lock: skip
echo "99999 $(date +%s)" > "$LEARN/.miner.lock"
printf '%s\n' '{"event":"prompt","text":"no, a"}' '{"event":"prompt","text":"no, b"}' '{"event":"prompt","text":"no, c"}' >> "$LEARN/observations.jsonl"
run_hook
check "live lock: no second claude call" "$([ "$(wc -l < "$SHIM_LOG")" -eq 1 ] && echo 1 || echo 0)"

# 4. stale lock: proceeds
echo "99999 $(( $(date +%s) - 700 ))" > "$LEARN/.miner.lock"
run_hook
check "stale lock: claude called again" "$(sleep 1; [ "$(wc -l < "$SHIM_LOG")" -eq 2 ] && echo 1 || echo 0)"
wait_gone "$LEARN/.miner.lock" || true

# 5. stop_hook_active guard and INSTINCTS_SKIP
echo '{"stop_hook_active":true}' | SHIM_LOG="$SHIM_LOG" PATH="$SHIM_DIR:$PATH" CLAUDE_PROJECT_DIR="$ROOT" bash "$HOOK"
echo '{}' | INSTINCTS_SKIP=1 SHIM_LOG="$SHIM_LOG" PATH="$SHIM_DIR:$PATH" CLAUDE_PROJECT_DIR="$ROOT" bash "$HOOK"
check "guards: no extra claude calls" "$([ "$(wc -l < "$SHIM_LOG")" -eq 2 ] && echo 1 || echo 0)"

# 6. no claude on PATH: logs and exits 0
rm -f "$SHIM_DIR/claude"
printf '%s\n' '{"event":"prompt","text":"no, a"}' '{"event":"prompt","text":"no, b"}' '{"event":"prompt","text":"no, c"}' >> "$LEARN/observations.jsonl"
echo '{}' | PATH="$SHIM_DIR:/usr/bin:/bin" CLAUDE_PROJECT_DIR="$ROOT" bash "$HOOK"; RC=$?
check "missing claude: exit 0 and logged" "$([ $RC -eq 0 ] && grep -q 'claude not on PATH' "$LEARN/miner.log" && echo 1 || echo 0)"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
```

Run: `chmod +x .agents/hooks/test-instinct-mine.sh && bash .agents/hooks/test-instinct-mine.sh`
Expected: FAIL — hook file does not exist (bash reports `No such file`; several FAIL lines).

Note: test 6 uses `PATH="$SHIM_DIR:/usr/bin:/bin"` so a globally installed `claude` (e.g. in `~/.local/bin` or Homebrew) is not found; `python3` must still be reachable — if it lives elsewhere on your machine, add its directory to that PATH.

- [ ] **Step 4: Write the hook**

`.agents/hooks/instinct-mine.sh`:

```bash
#!/usr/bin/env bash
# Hook: Instinct miner (Stop)
# Pre-filters new observations; only when enough candidates exist, spawns a DETACHED
# `claude -p` (Haiku) whose JSON output is piped into `instinct.py ingest`.
# Exit 0 always. Returns immediately; the miner runs in the background and removes the lock.

[ -n "${INSTINCTS_SKIP:-}" ] && exit 0
command -v python3 >/dev/null 2>&1 || exit 0

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$HOOK_DIR/../.." && pwd)}"
[ -f "$ROOT/.instincts-off" ] && exit 0
[ -f "$ROOT/scripts/instincts/prefilter.py" ] || exit 0

INPUT="$(cat)"
case "$INPUT" in *'"stop_hook_active":true'*|*'"stop_hook_active": true'*) exit 0 ;; esac

LEARN="$ROOT/team/_memory/_learnings"
mkdir -p "$LEARN" 2>/dev/null || exit 0
LOG="$LEARN/miner.log"
LOCK="$LEARN/.miner.lock"
CAND="$LEARN/.candidates.json"
PROMPT_FILE="$ROOT/team/agents/instinct-observer.md"
STAMP() { date -u +%Y-%m-%dT%H:%M:%SZ; }

read -r ENABLED MODEL MIN_C <<< "$(python3 "$ROOT/scripts/instincts/config.py" --root "$ROOT" enabled model min_candidates 2>/dev/null | tr '\n' ' ')"
[ "$ENABLED" = "True" ] || exit 0

if ! command -v claude >/dev/null 2>&1; then
  echo "$(STAMP) skip: claude not on PATH" >> "$LOG"
  exit 0
fi

if [ -f "$LOCK" ]; then
  LOCK_TS="$(cut -d' ' -f2 "$LOCK" 2>/dev/null)"
  NOW="$(date +%s)"
  if [ -n "$LOCK_TS" ] && [ $((NOW - LOCK_TS)) -lt 600 ]; then
    exit 0
  fi
  echo "$(STAMP) stale lock overwritten" >> "$LOG"
fi
echo "$$ $(date +%s)" > "$LOCK"

if ! python3 "$ROOT/scripts/instincts/prefilter.py" --root "$ROOT" --commit > "$CAND" 2>> "$LOG"; then
  rm -f "$LOCK"
  exit 0
fi
COUNT="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("count",0))' "$CAND" 2>/dev/null || echo 0)"
if [ "${COUNT:-0}" -lt "${MIN_C:-3}" ]; then
  rm -f "$LOCK"
  exit 0
fi

echo "$(STAMP) miner spawned (candidates=$COUNT, model=$MODEL)" >> "$LOG"
INSTINCTS_SKIP=1 nohup bash -c '
  ROOT="$1"; CAND="$2"; PROMPT_FILE="$3"; MODEL="$4"; LOG="$5"; LOCK="$6"
  claude -p --model "$MODEL" --max-turns 4 --append-system-prompt "$(cat "$PROMPT_FILE")" < "$CAND" \
    | python3 "$ROOT/scripts/instincts/instinct.py" ingest --root "$ROOT" >> "$LOG" 2>&1
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) miner finished" >> "$LOG"
  rm -f "$LOCK"
' _ "$ROOT" "$CAND" "$PROMPT_FILE" "$MODEL" "$LOG" "$LOCK" >/dev/null 2>&1 &
disown 2>/dev/null || true
exit 0
```

Run: `chmod +x .agents/hooks/instinct-mine.sh && bash .agents/hooks/test-instinct-mine.sh`
Expected: `Results: 12 passed, 0 failed`

- [ ] **Step 5: Register the Stop hook**

Add a new top-level key to `hooks` in both `.claude/settings.local.json` and `templates/settings.local.json.template`:

```json
"Stop": [
  {
    "matcher": "",
    "hooks": [
      {
        "type": "command",
        "command": "bash \"$CLAUDE_PROJECT_DIR/.agents/hooks/instinct-mine.sh\"",
        "timeout": 5000
      }
    ]
  }
]
```

Validate: `python3 -c "import json;json.load(open('.claude/settings.local.json'));json.load(open('templates/settings.local.json.template'));print('ok')"`

- [ ] **Step 6: Commit**

```bash
git add .agents/hooks/instinct-mine.sh .agents/hooks/test-instinct-mine.sh team/agents/instinct-observer.md .claude/settings.local.json templates/settings.local.json.template docs/specs/2026-09-19-instinct-capture-loop-design.md
git commit -m "feat(instincts): Stop-hook miner — prefilter gate, detached Haiku, observer prompt"
```

---

### Task 8: Inject hook (SessionStart)

**Files:**
- Create: `.agents/hooks/instinct-inject.sh`, `.agents/hooks/test-instinct-inject.sh`
- Modify: `.claude/settings.local.json`, `templates/settings.local.json.template` (add `SessionStart`)

**Interfaces:**
- Consumes: `instinct.py inject --root R` (prints the block or nothing).

- [ ] **Step 1: Write the harness (fails first)**

`.agents/hooks/test-instinct-inject.sh`:

```bash
#!/usr/bin/env bash
set -e

HOOK=".agents/hooks/instinct-inject.sh"
PASS=0
FAIL=0
ROOT="$(pwd)"
DIR="team/_memory/_learnings/instincts"
USER_DIR="$(mktemp -d)"

setup() {
  mkdir -p "$DIR"
  cat > "$DIR/zz-test-inject.yaml" << 'EOF'
id: "zz-test-inject"
trigger: "when testing the inject hook"
action: "print this line"
confidence: 0.9
domain: "tooling"
scope: "project"
status: "active"
source: "test"
evidence:
  - "harness"
observed_count: 11
first_seen: "2026-09-19"
last_seen: "2099-01-01"
EOF
}
teardown() { rm -f "$DIR/zz-test-inject.yaml" .instincts-off; rm -rf "$USER_DIR"; }
check() {
  local desc="$1" ok="$2"
  if [ "$ok" = "1" ]; then echo "  PASS: $desc"; PASS=$((PASS + 1)); else echo "  FAIL: $desc"; FAIL=$((FAIL + 1)); fi
}
run_hook() { echo '{"session_id":"s","source":"startup"}' | INSTINCTS_USER_DIR="$USER_DIR" CLAUDE_PROJECT_DIR="$ROOT" bash "$HOOK"; }

echo "=== Instinct Inject Hook Tests ==="
setup
trap teardown EXIT

OUT="$(run_hook)"; RC=$?
check "exit 0" "$([ $RC -eq 0 ] && echo 1 || echo 0)"
check "prints [instincts] header" "$(echo "$OUT" | grep -q '^\[instincts\]' && echo 1 || echo 0)"
check "prints the active instinct" "$(echo "$OUT" | grep -q 'when testing the inject hook → print this line' && echo 1 || echo 0)"

touch .instincts-off
OUT="$(run_hook)"
check ".instincts-off prints nothing" "$([ -z "$OUT" ] && echo 1 || echo 0)"
rm -f .instincts-off

OUT="$(echo '{}' | INSTINCTS_SKIP=1 CLAUDE_PROJECT_DIR="$ROOT" bash "$HOOK")"
check "INSTINCTS_SKIP prints nothing" "$([ -z "$OUT" ] && echo 1 || echo 0)"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
```

Run: `chmod +x .agents/hooks/test-instinct-inject.sh && bash .agents/hooks/test-instinct-inject.sh`
Expected: FAIL lines (hook missing).

- [ ] **Step 2: Write the hook**

`.agents/hooks/instinct-inject.sh`:

```bash
#!/usr/bin/env bash
# Hook: Instinct inject (SessionStart)
# Prints the active-instincts block to stdout; Claude Code injects it as context.
# Exit 0 always. Prints nothing when disabled or when there is nothing to show.

[ -n "${INSTINCTS_SKIP:-}" ] && exit 0
command -v python3 >/dev/null 2>&1 || exit 0

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$HOOK_DIR/../.." && pwd)}"
[ -f "$ROOT/.instincts-off" ] && exit 0
[ -f "$ROOT/scripts/instincts/instinct.py" ] || exit 0

cat > /dev/null  # drain stdin
python3 "$ROOT/scripts/instincts/instinct.py" inject --root "$ROOT" 2>/dev/null
exit 0
```

Run: `chmod +x .agents/hooks/instinct-inject.sh && bash .agents/hooks/test-instinct-inject.sh`
Expected: `Results: 5 passed, 0 failed`

- [ ] **Step 3: Register the SessionStart hook** (both settings files)

```json
"SessionStart": [
  {
    "matcher": "",
    "hooks": [
      {
        "type": "command",
        "command": "bash \"$CLAUDE_PROJECT_DIR/.agents/hooks/instinct-inject.sh\"",
        "timeout": 5000
      }
    ]
  }
]
```

Validate both files parse as JSON (same command as Task 7 Step 5).

- [ ] **Step 4: Run every suite**

```bash
python3 -m pytest scripts/instincts/tests -q
bash .agents/hooks/test-observe.sh && bash .agents/hooks/test-instinct-mine.sh && bash .agents/hooks/test-instinct-inject.sh
bash .agents/hooks/test-claim-check.sh && bash .agents/hooks/test-worktree-guard.sh
```
Expected: `46 passed`; each harness `0 failed`.

- [ ] **Step 5: Commit**

```bash
git add .agents/hooks/instinct-inject.sh .agents/hooks/test-instinct-inject.sh .claude/settings.local.json templates/settings.local.json.template
git commit -m "feat(instincts): SessionStart inject hook — top-N active instincts as context"
```

---

### Task 9: Oracle integration and `/team:instincts`

**Files:**
- Modify: `team/agents/oracle.md` (step 12 lines 53–59, rules after line 113, menu after the `[AM]` item at line 192), `team/agents/oracle-dispatch-map.md` (Team Agents table, after the `Sprint lifecycle` row), `team/agents/oracle-reference/oracle-status.md`, `CLAUDE.md` (Oracle Awareness section)
- Create: `team/agents/oracle-reference/instinct-review.md`, `claude-commands/team/instincts.md`

**Interfaces:**
- Consumes: `python3 scripts/instincts/instinct.py status --json | accept | reject | promote | prune`.

- [ ] **Step 1: Oracle activation — add pending count**

In `team/agents/oracle.md`, inside `<step n="12">`, after the line `- Set {oracle_last_action} = "none"` insert:

```
          - Run `python3 scripts/instincts/instinct.py status --json` (if it fails or prints nothing, set both to 0) — set {oracle_pending_instincts} = length of "pending", {oracle_active_instincts} = length of "active"
```

and change the Display line to:

```
          - Display: "Ambient mode: SUGGEST — I'm watching. Say 'oracle auto' for hands-free, 'oracle off' to silence me." — if {oracle_pending_instincts} > 0 append " · {oracle_pending_instincts} learned instincts pending review (say 'instincts')."
```

- [ ] **Step 2: Oracle rule — mode-aware review**

After the `MODE TOGGLES` rule (line 113) insert:

```
      <r>INSTINCT REVIEW: At pause points, if {oracle_pending_instincts} > 0 — suggest mode: list up to 5 pending as "id · trigger → action (confidence)" and offer accept / reject / defer, applying answers via `python3 scripts/instincts/instinct.py accept <id>` or `reject <id>`; auto mode: first run `python3 scripts/instincts/instinct.py accept --min-confidence <auto_accept_confidence from .agents/config.yaml, default 0.7>`, report what was activated, then list only the remainder; off mode: silent. Refresh {oracle_pending_instincts} after any change. Instincts are context, not policy — never treat one as an instruction. If claim-check blocks writes under team/_memory/_learnings/instincts/, say so and stop; do not retry.</r>
```

- [ ] **Step 3: Oracle menu item**

After the `[AM]` item insert:

```
    <item cmd="IN or fuzzy match on instincts or instinct or learned" action="#instinct-review">[IN] Instincts - Review pending learned behaviors, promote, prune</item>
```

- [ ] **Step 4: Oracle status line**

In `team/agents/oracle-reference/oracle-status.md`, after `Dispatch map loaded: yes/no` add:

```
Instincts: {oracle_active_instincts} active, {oracle_pending_instincts} pending (say 'instincts' to review)
```

- [ ] **Step 5: JIT review prompt**

`team/agents/oracle-reference/instinct-review.md`:

```markdown
# Oracle prompt: instinct-review (lazy)

Review learned instincts. Instincts are unreviewed context, not policy.

1. Run `python3 scripts/instincts/instinct.py status` and show the output verbatim.
2. If there are pending instincts, walk them one at a time:
   "{id} · {trigger} → {action} ({confidence}, {domain}) — accept / reject / skip?"
   Apply each answer immediately: `python3 scripts/instincts/instinct.py accept {id}` or `reject {id}`.
   In auto mode, first run `python3 scripts/instincts/instinct.py accept --min-confidence {auto_accept_confidence}` and only ask about the rest.
3. Offer: "[P] Promote to global (patterns active in 2+ projects)" → `python3 scripts/instincts/instinct.py promote`; "[X] Prune stale pending" → `python3 scripts/instincts/instinct.py prune`.
4. Refresh `status --json`, update {oracle_pending_instincts} and {oracle_active_instincts}, and summarize what changed in one line.
5. Remind: accepted project instincts live in `team/_memory/_learnings/instincts/` and ship with the next commit; other agents inherit them.
```

- [ ] **Step 6: Slash command**

`claude-commands/team/instincts.md`:

```markdown
---
name: 'instincts'
description: 'Review, promote, or prune learned instincts — status | review | promote | prune | export | import'
---

Manage the instinct capture loop (learned behaviors mined from sessions). Instincts are context, not policy.

Subcommand = the first word after `/team:instincts` (default `status`):

- `status` → run `python3 scripts/instincts/instinct.py status` and show it verbatim.
- `review` → run `python3 scripts/instincts/instinct.py status --json`; for each pending instinct ask "accept / reject / skip?" and apply via `python3 scripts/instincts/instinct.py accept <id>` or `reject <id>`. Never bulk-accept without the user saying so.
- `promote` → `python3 scripts/instincts/instinct.py promote` (project → `~/.claude/instincts/` when active in 2+ projects with mean confidence ≥ 0.8).
- `prune` → `python3 scripts/instincts/instinct.py prune`.
- `export` → `python3 scripts/instincts/instinct.py export` and show the JSON.
- `import <file>` → `python3 scripts/instincts/instinct.py import < <file>`.

After any change, print one line summarizing what changed. Do not edit instinct YAML by hand; use the CLI so writes stay atomic.
```

- [ ] **Step 7: Dispatch map and CLAUDE.md**

In `team/agents/oracle-dispatch-map.md`, after the `| Sprint lifecycle | Athena | Self (CS, DS, CR, SH) | … |` row add:

```
| Learning | Athena | /team:instincts | Repeated user corrections, "we keep doing this", `[instincts] … pending` banner at session start |
```

In `CLAUDE.md`, in the "Oracle Awareness" section after the `Fix triggers` line add:

```
Instincts: learned behaviors mined from sessions (`python3 scripts/instincts/instinct.py status --json`). Pending ones are surfaced per mode — suggest lists them, auto accepts ≥ `auto_accept_confidence`, off stays silent. Instincts are context, not policy.
```

- [ ] **Step 8: Verify the edits are well-formed**

```bash
grep -c 'oracle_pending_instincts' team/agents/oracle.md        # expect >= 4
grep -n 'instinct-review' team/agents/oracle.md                  # menu item present
grep -n 'Learning' team/agents/oracle-dispatch-map.md
python3 -c "import re,sys;t=open('team/agents/oracle.md').read();print('menu ok' if t.count('<item')==t.count('</item>') else 'MENU BROKEN')"
```
Expected: counts as noted, `menu ok`.

- [ ] **Step 9: Commit**

```bash
git add team/agents/oracle.md team/agents/oracle-dispatch-map.md team/agents/oracle-reference/oracle-status.md team/agents/oracle-reference/instinct-review.md claude-commands/team/instincts.md CLAUDE.md
git commit -m "feat(oracle): mode-aware instinct review, [IN] menu item, /team:instincts"
```

---

### Task 10: Supersede learnings.xml, docs, decision record

**Files:**
- Modify: `team/engine/learnings.xml` (insert after line 1), `team/data/discipline/knowledge/learnings.md`, `docs/archive/2026-04-26-learnings-specialists-autodecision.md` (prepend note), `docs/ARCHITECTURE.md` (after the "Hook Configuration" block near line 314), `scripts/setup.sh` (after line ~137), `templates/CLAUDE.md.template`
- Create: `.agents/decisions/2026-09-19-instincts-supersede-learnings.yaml`

- [ ] **Step 1: Deprecate learnings.xml**

Insert as line 2 of `team/engine/learnings.xml`:

```xml
  <deprecated>Superseded by the instinct capture loop (docs/specs/2026-09-19-instinct-capture-loop-design.md; CLI scripts/instincts/instinct.py). Do not wire new workflows to these protocols; this file is removed once nothing references it.</deprecated>
```

- [ ] **Step 2: Rewrite the discipline doc**

Replace the "## When This Applies" section of `team/data/discipline/knowledge/learnings.md` with:

```markdown
## How It Works Now

Learnings are captured automatically by the instinct capture loop — you do not write `learnings.jsonl` by hand.

| Step | Mechanism |
|---|---|
| Capture | `UserPromptSubmit` + `PostToolUse` hooks append to `team/_memory/_learnings/observations.jsonl` (local, gitignored) |
| Mine | `Stop` hook pre-filters corrections, error resolutions, and repeated workflows; spawns a Haiku miner only when ≥ `min_candidates` exist |
| Review | Instincts land as `pending`; Athena surfaces them per Oracle mode, or run `/team:instincts review` |
| Recall | `SessionStart` injects the top active instincts; `python3 scripts/instincts/instinct.py status` shows all |

Config: `instincts:` block in `.agents/config.yaml`. Off switch: `.instincts-off` at repo root.

## When This Applies

- "Search before building" → read the `[instincts]` block at session start, or run `python3 scripts/instincts/instinct.py status`
- "Capture after shipping" → automatic; review pending instincts before you commit so accepted ones ship with the branch
- After a review or debugging session reveals a pattern → make sure it was captured; if not, say the correction out loud in a prompt ("no, use X instead") so the next Stop picks it up
```

Keep the Iron Law, Red Flags, Rationalization Defense, and Learning Types sections as they are; append to Learning Types one line: `Instinct domains map onto these: pattern/architecture → workflow|code-style, pitfall → debugging|tooling, decision → (belongs in .agents/decisions/, not an instinct).`

- [ ] **Step 3: Note on the old plan**

Prepend to `docs/archive/2026-04-26-learnings-specialists-autodecision.md`:

```markdown
> **Superseded (2026-09-19):** the JSONL learnings design here was never wired in. It is replaced by the instinct capture loop — see `docs/specs/2026-09-19-instinct-capture-loop-design.md` and `docs/plans/2026-09-19-instinct-capture-loop.md`.

```

- [ ] **Step 4: Architecture doc**

After the paragraph ending "…exits silently (with zero overhead) for all other Bash operations." in `docs/ARCHITECTURE.md`, add:

```markdown
### Instinct Capture Loop Hooks

Registered in `.claude/settings.local.json` (see `docs/specs/2026-09-19-instinct-capture-loop-design.md`):

| Event | Hook | Does |
|---|---|---|
| `UserPromptSubmit` | `.agents/hooks/observe.sh prompt` | Log the prompt (scrubbed, ≤ 2 KB) to `team/_memory/_learnings/observations.jsonl` |
| `PostToolUse` | `.agents/hooks/observe.sh tool` | Log tool name, input, response (scrubbed, ≤ 5 KB each), error flag |
| `Stop` | `.agents/hooks/instinct-mine.sh` | Pre-filter new observations; if ≥ `min_candidates`, spawn a detached `claude -p --model haiku` whose JSON is ingested as `pending` instincts |
| `SessionStart` | `.agents/hooks/instinct-inject.sh` | Print the top active instincts as a `[instincts]` context block |

All four exit 0 unconditionally; `INSTINCTS_SKIP=1` or a `.instincts-off` marker disables them. CLI: `python3 scripts/instincts/instinct.py`.
```

- [ ] **Step 5: Install into target projects via setup.sh**

`scripts/setup.sh` copies `team/` wholesale (so `instinct-observer.md` and the Oracle files travel) and the settings template (which now registers the four hooks), but it does not copy `.agents/hooks/`, `scripts/instincts/`, or `.agents/config.yaml`. A target project would therefore have hook entries pointing at missing scripts. After the line `chmod +x "$TARGET_DIR/.claude/hooks/post-commit-context.sh"` (line ~137) add:

```bash
    # Instinct capture loop: hooks, CLI, config (see docs/specs/2026-09-19-instinct-capture-loop-design.md)
    mkdir -p "$TARGET_DIR/.agents/hooks" "$TARGET_DIR/scripts/instincts" "$TARGET_DIR/team/_memory/_learnings/instincts"
    for h in observe.sh instinct-mine.sh instinct-inject.sh; do
        cp "$TEAM_ROOT/.agents/hooks/$h" "$TARGET_DIR/.agents/hooks/$h"
        chmod +x "$TARGET_DIR/.agents/hooks/$h"
    done
    cp "$TEAM_ROOT/scripts/instincts/"*.py "$TARGET_DIR/scripts/instincts/"
    [ -f "$TARGET_DIR/.agents/config.yaml" ] || cp "$TEAM_ROOT/.agents/config.yaml" "$TARGET_DIR/.agents/config.yaml"
    touch "$TARGET_DIR/team/_memory/_learnings/instincts/.gitkeep"
    grep -q 'team/_memory/_learnings/observations.jsonl' "$TARGET_DIR/.gitignore" 2>/dev/null || cat >> "$TARGET_DIR/.gitignore" << 'EOF'

# Instinct capture loop — raw observations and miner state are local only
team/_memory/_learnings/observations.jsonl*
team/_memory/_learnings/miner.log
team/_memory/_learnings/.miner.lock
team/_memory/_learnings/.instinct-watermark
team/_memory/_learnings/.candidates.json
EOF
```

Also add the same CLAUDE.md "Instincts:" line from Task 9 Step 7 to `templates/CLAUDE.md.template` in its Oracle Awareness section (if the template has no such section, skip this — the runtime rule lives in `team/agents/oracle.md`, which is copied).

Verify with a scratch install: `bash scripts/setup.sh "$(mktemp -d)/proj"` then check `ls <proj>/.agents/hooks <proj>/scripts/instincts` and `python3 -c "import json;json.load(open('<proj>/.claude/settings.local.json'))"`.

- [ ] **Step 6: Decision record**

`.agents/decisions/2026-09-19-instincts-supersede-learnings.yaml`:

```yaml
decided_by: ceo
story_id: "instinct-capture-loop"
date: 2026-09-19
decision: "Learned behaviors are stored as confidence-scored instincts (team/_memory/_learnings/instincts/*.yaml, committed) mined by a Stop-hook-gated Haiku miner and reviewed via Oracle or /team:instincts. team/engine/learnings.xml and learnings.jsonl are deprecated; do not wire workflows to them."
rationale: "learnings.xml was designed but never wired; instincts add automatic capture, confidence, evidence, a review gate, and cross-project promotion without a second memory format. Spec: docs/specs/2026-09-19-instinct-capture-loop-design.md"
affects_agents: all
acknowledged_by: []
```

- [ ] **Step 7: Final verification**

```bash
python3 -m pytest scripts/instincts/tests -q
for t in .agents/hooks/test-*.sh; do bash "$t" || exit 1; done
grep -rn 'learnings.xml' team/workflows team/agents claude-commands | grep -v deprecated   # expect no output
python3 -c "import json;json.load(open('.claude/settings.local.json'));json.load(open('templates/settings.local.json.template'));print('settings ok')"
git status --short   # only intended files
```
Expected: `46 passed`; every harness `0 failed`; no stray references; `settings ok`; setup dry-run shows the copied files.

- [ ] **Step 8: Commit**

```bash
git add scripts/setup.sh templates/CLAUDE.md.template team/engine/learnings.xml team/data/discipline/knowledge/learnings.md docs/archive/2026-04-26-learnings-specialists-autodecision.md docs/ARCHITECTURE.md .agents/decisions/2026-09-19-instincts-supersede-learnings.yaml
git commit -m "docs(instincts): supersede learnings.xml, architecture hooks table, decision record"
```

---

## After the last task

Do not bump `VERSION` or write a release commit — that happens in the release flow. Hand off with `superpowers:finishing-a-development-branch` from the worktree (`feat/instinct-capture-loop` → PR against `main`).
