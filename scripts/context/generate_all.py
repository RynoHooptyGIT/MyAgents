#!/usr/bin/env python3
"""Generate all context files for AI agents.

Reads context-config.yaml for project-specific scan paths and generator settings.

Usage:
    python scripts/context/generate_all.py          # Generate all context files
    python scripts/context/generate_all.py --sprint  # Only regenerate sprint digest
    python scripts/context/generate_all.py --check   # Check if files are stale (exit 1 if so)

Output directory: _bmad-output/context/
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Add scripts/context to path for imports
sys.path.insert(0, str(Path(__file__).parent))

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = Path(__file__).parent / "context-config.yaml"


def load_config() -> dict:
    """Load context-config.yaml without PyYAML (simple parser for flat YAML)."""
    if not CONFIG_FILE.exists():
        logger.warning("context-config.yaml not found at %s", CONFIG_FILE)
        logger.warning("Copy context-config.example.yaml and customize for your project.")
        return {}

    # Use PyYAML if available, otherwise fall back to basic parsing
    try:
        import yaml
        with open(CONFIG_FILE) as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        logger.warning("PyYAML not installed. Using basic YAML parser (limited).")
        return _basic_yaml_parse(CONFIG_FILE)


def _basic_yaml_parse(filepath: Path) -> dict:
    """Minimal YAML parser for the config file structure."""
    # This handles the basic nested structure we need
    import json
    content = filepath.read_text()
    # Strip comments
    lines = []
    for line in content.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#") or not stripped:
            continue
        lines.append(line)

    # For basic configs, try to extract just the enabled generators
    result = {"generators": {}, "output_dir": "_bmad-output/context"}

    current_gen = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("output_dir:"):
            result["output_dir"] = stripped.split(":", 1)[1].strip().strip('"')
        elif stripped.endswith(":") and not stripped.startswith("-"):
            key = stripped.rstrip(":")
            if current_gen is None and key in ("sprint-digest", "module-index", "api-index", "schema-digest", "patterns"):
                current_gen = key
                result["generators"][key] = {"enabled": True}
            elif key == "generators":
                pass
            else:
                current_gen = None
        elif current_gen and "enabled:" in stripped:
            val = stripped.split(":", 1)[1].strip()
            result["generators"][current_gen]["enabled"] = val.lower() == "true"

    return result


def get_context_dir(config: dict) -> Path:
    """Get the output directory from config."""
    output_dir = config.get("output_dir", "_bmad-output/context")
    return PROJECT_ROOT / output_dir


def check_staleness(config: dict, max_age_days: int = 7) -> bool:
    """Check if context files exist and are within max age."""
    context_dir = get_context_dir(config)
    all_fresh = True
    now = datetime.now(timezone.utc)

    generator_names = ["module-index", "sprint-digest", "api-index", "schema-digest", "patterns"]

    for name in generator_names:
        filepath = context_dir / f"{name}.md"
        if not filepath.exists():
            logger.info("  MISSING: %s.md", name)
            all_fresh = False
        else:
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime, tz=timezone.utc)
            age_days = (now - mtime).days
            if age_days > max_age_days:
                logger.info("  STALE (%dd): %s.md", age_days, name)
                all_fresh = False
            else:
                logger.info("  OK (%dd): %s.md", age_days, name)

    return all_fresh


def main():
    parser = argparse.ArgumentParser(description="Generate AI agent context files")
    parser.add_argument("--sprint", action="store_true", help="Only regenerate sprint digest")
    parser.add_argument("--check", action="store_true", help="Check if files are stale")
    parser.add_argument("--max-age", type=int, default=7, help="Max age in days for --check (default: 7)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("BMAD Context Generator")

    config = load_config()
    if not config:
        logger.error("No configuration loaded. Cannot proceed.")
        sys.exit(1)

    context_dir = get_context_dir(config)
    logger.info("Output: %s/\n", context_dir)

    if args.check:
        logger.info("Checking context freshness...")
        fresh = check_staleness(config, args.max_age)
        sys.exit(0 if fresh else 1)

    context_dir.mkdir(parents=True, exist_ok=True)
    generators_config = config.get("generators", {})

    if args.sprint:
        logger.info("Regenerating sprint digest only...")
        start = time.time()
        from gen_sprint_digest import generate_with_config
        sprint_config = generators_config.get("sprint-digest", {})
        generate_with_config(PROJECT_ROOT, context_dir, sprint_config)
        elapsed = time.time() - start
        logger.info("\nDone in %.1fs", elapsed)
        return

    logger.info("Generating all context files...\n")
    start = time.time()
    errors = []

    # Import and run each generator with config
    generator_modules = [
        ("module-index", "gen_module_index"),
        ("sprint-digest", "gen_sprint_digest"),
        ("api-index", "gen_api_index"),
        ("schema-digest", "gen_schema_digest"),
        ("patterns", "gen_patterns"),
    ]

    for name, module_name in generator_modules:
        gen_config = generators_config.get(name, {})
        if not gen_config.get("enabled", True):
            logger.info("  SKIP: %s (disabled)", name)
            continue

        try:
            module = __import__(module_name)
            if hasattr(module, "generate_with_config"):
                module.generate_with_config(PROJECT_ROOT, context_dir, gen_config)
            else:
                # Fallback to legacy main() for backward compatibility
                module.main()
        except Exception as e:
            logger.error("  ERROR generating %s: %s", name, e)
            errors.append((name, str(e)))

    elapsed = time.time() - start
    total = len([n for n, _ in generator_modules if generators_config.get(n, {}).get("enabled", True)])
    success = total - len(errors)
    logger.info("\nGenerated %d/%d files in %.1fs", success, total, elapsed)

    if errors:
        logger.error("\nErrors:")
        for name, err in errors:
            logger.error("  - %s: %s", name, err)
        sys.exit(1)


if __name__ == "__main__":
    main()
