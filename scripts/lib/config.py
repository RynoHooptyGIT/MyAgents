#!/usr/bin/env python3
"""Read one top-level section of .agents/config.yaml.

A section is a `<section>:` line followed by indented `key: value  # comment`
lines, so no YAML library is needed. Missing file, missing section, or
unparsable values fall back to the caller-supplied defaults. Different
sections in the same file are isolated from one another.
"""
import argparse
import json
import sys
from pathlib import Path


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


def load(root, section, defaults):
    cfg = dict(defaults)
    path = Path(root) / ".agents" / "config.yaml"
    if not path.is_file():
        return cfg
    in_block = False
    prefix = f"{section}:"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
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
        if key in defaults:
            cfg[key] = _coerce(raw, defaults[key])
    return cfg


def main(argv=None):
    ap = argparse.ArgumentParser(description="Print one config section's values, one per line.")
    ap.add_argument("--root", required=True)
    ap.add_argument("--section", required=True)
    ap.add_argument("--default-json", default="{}", help="JSON object of default key/values")
    ap.add_argument("keys", nargs="+")
    a = ap.parse_args(argv)
    try:
        defaults = json.loads(a.default_json)
    except ValueError:
        defaults = {}
    cfg = load(a.root, a.section, defaults)
    for k in a.keys:
        print(cfg.get(k, ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
