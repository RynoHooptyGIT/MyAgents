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
