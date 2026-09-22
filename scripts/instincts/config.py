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
        raw_lower = raw.lower()
        if raw_lower in ("true", "yes", "on", "1"):
            return True
        if raw_lower in ("false", "no", "off", "0"):
            return False
        return default
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
