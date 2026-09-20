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
            if not raw.endswith(b"\n"):  # partial line, leave for next run
                break
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
