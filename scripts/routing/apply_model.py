#!/usr/bin/env python3
"""Idempotently set the orchestrator model in <project>/.claude/settings.json.

Only the `model` key is touched; every other setting is preserved.
Usage: apply_model.py PROJECT_DIR [MODEL]   (MODEL defaults to "fable")
"""
import json
import sys
from pathlib import Path


def apply(project, model="fable"):
    path = Path(project) / ".claude" / "settings.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if data.get("model") == model:
        return False
    data["model"] = model
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: apply_model.py PROJECT_DIR [MODEL]")
    changed = apply(*sys.argv[1:3])
    print(f"orchestrator model {'set' if changed else 'already set'}")
