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
