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


def project_identity(path):
    """Stable identity for a checkout: the git common dir, so worktrees share one identity.
    Falls back to the resolved path when git is unavailable or the path is not a repository."""
    path = Path(path).resolve()
    for args in (["--path-format=absolute", "--git-common-dir"], ["--git-common-dir"]):
        try:
            out = subprocess.run(["git", "-C", str(path), "rev-parse", *args],
                                 capture_output=True, text=True, check=True)
        except (OSError, subprocess.CalledProcessError):
            continue
        common = out.stdout.strip()
        if common:
            return str((path / common).resolve())
    return str(path)


def project_name_for(root):
    """Project name for ingest: the main checkout's directory name, even when root is a worktree."""
    ident = Path(project_identity(root))
    return ident.parent.name if ident.name == ".git" else Path(root).resolve().name


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
    raw = re.sub(r"\s+#.*$", "", raw)
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
    except (OSError, UnicodeDecodeError):
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


def days_since(day_str, today):
    try:
        d = date.fromisoformat(str(day_str))
    except (TypeError, ValueError):
        return 0
    return max(0, (today - d).days)


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


def _is_object_list(data):
    return isinstance(data, list) and bool(data) and all(isinstance(x, dict) for x in data)


def extract_json_array(text):
    """First JSON array of objects in the miner's output; prose like "[2] patterns" is skipped."""
    try:
        data = json.loads(text.strip())
        if isinstance(data, list):
            return data
    except ValueError:
        pass
    dec = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch != "[":
            continue
        try:
            data, _ = dec.raw_decode(text, i)
        except ValueError:
            continue
        if _is_object_list(data):
            return data
    return []


def ingest(root, objs, today, project_name=None):
    if project_name is None:
        project_name = project_name_for(root)
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
        age = days_since(d.get("last_seen"), today)
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
        try:
            for line in reg.read_text(encoding="utf-8").splitlines():
                p = line.split("\t")[0].strip()
                if p and Path(p).is_dir():
                    paths.add(p)
        except OSError:
            pass
    return sorted(paths)


def promote(root, today):
    groups = []
    for p in _registered_projects(root):
        for d in load_tier(project_dir(p), "project")[0]:
            if d["status"] != "active" or d.get("domain") not in GLOBAL_DOMAINS:
                continue
            if not d.get("trigger"):
                continue
            d["_project"] = project_identity(p)
            # Canopy grouping: each candidate is compared to the group's first member only (non-transitive by design; instinct sets are small).
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
        mean = sum(float(d.get("confidence", 0.3)) for d in g) / len(g)
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
    if a.cmd == "accept" and not a.ids and a.min_confidence is None:
        ap.error("accept needs instinct ids or --min-confidence")

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
        print(" ".join(prune(root, today, a.ttl_days if a.ttl_days is not None else cfg["pending_ttl_days"])))
        return 0
    if a.cmd == "inject":
        sys.stdout.write(inject(root, today, cfg))
        return 0
    if a.cmd == "ingest":
        objs = extract_json_array(stdin.read())
        r = ingest(root, objs, today, a.project_name)
        print(json.dumps(r))
        return 0
    if a.cmd == "rejected-ids":
        print("\n".join(status(root, today, cfg)["rejected_ids"]))
        return 0
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


if __name__ == "__main__":
    sys.exit(main())
