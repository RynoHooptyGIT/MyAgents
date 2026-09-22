#!/usr/bin/env python3
"""Read the `instincts:` block of .agents/config.yaml.

Thin wrapper around scripts/lib/config.py's generic section loader.
Missing file, missing block, or unparsable values fall back to DEFAULTS.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import config as libconfig  # noqa: E402

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


def load(root):
    return libconfig.load(root, "instincts", DEFAULTS)


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
