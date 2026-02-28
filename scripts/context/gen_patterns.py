#!/usr/bin/env python3
"""Generate patterns.md — Canonical code patterns extracted from the codebase.

Config-driven: reads pattern extraction definitions from context-config.yaml.
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_code_block(filepath: Path, search_text: str, max_lines: int = 20) -> str:
    """Extract a code block around a search text match."""
    try:
        content = filepath.read_text(errors="replace")
    except Exception:
        return f"// Could not read {filepath.name}"

    idx = content.find(search_text)
    if idx == -1:
        return f"// Pattern '{search_text}' not found in {filepath.name}"

    # Find the start of the containing construct (function, class, const)
    # Look backward for a def, class, const, function, or export line
    before = content[:idx]
    lines_before = before.split("\n")

    # Find the start line — go back to find a declaration
    start_line = max(0, len(lines_before) - 3)
    for i in range(len(lines_before) - 1, max(0, len(lines_before) - 10), -1):
        line = lines_before[i].strip()
        if any(line.startswith(kw) for kw in ("def ", "async def ", "class ", "const ", "export ", "function ", "@")):
            start_line = i
            break

    all_lines = content.split("\n")
    end_line = min(len(all_lines), start_line + max_lines)
    result_lines = all_lines[start_line:end_line]

    return "\n".join(result_lines).rstrip()


def find_matching_file(project_root: Path, search_dir: str, file_glob: str, search_text: str) -> Path | None:
    """Find the first file matching the glob that contains the search text."""
    base_dir = project_root / search_dir
    if not base_dir.exists():
        return None

    # If file_glob is a specific filename, search for it
    if not any(c in file_glob for c in "*?"):
        for f in base_dir.rglob(file_glob):
            if f.is_file():
                try:
                    content = f.read_text(errors="replace")
                    if search_text in content:
                        return f
                except Exception:
                    continue
        return None

    # Otherwise use glob pattern
    for f in base_dir.rglob(file_glob):
        if f.is_file() and ".test." not in f.name and ".spec." not in f.name:
            try:
                content = f.read_text(errors="replace")
                if search_text in content:
                    return f
            except Exception:
                continue

    return None


def generate_with_config(project_root: Path, output_dir: Path, config: dict):
    """Generate patterns.md using config settings."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    extractions = config.get("extractions", [])

    lines = []
    lines.append("# Code Patterns Reference")
    lines.append(f"\n_Auto-generated: {now} | Regenerate: `python scripts/context/generate_all.py`_")
    lines.append("_Canonical patterns extracted from the codebase. Follow these when implementing new code._\n")
    lines.append("---\n")

    if not extractions:
        lines.append("_(No pattern extractions configured in context-config.yaml)_\n")
        content = "\n".join(lines)
        (output_dir / "patterns.md").write_text(content)
        return

    for extraction in extractions:
        name = extraction.get("name", "Unknown Pattern")
        description = extraction.get("description", "")
        search_dir = extraction.get("search_dir", "")
        file_glob = extraction.get("file_glob", "*")
        search_text = extraction.get("search_text", "")
        language = extraction.get("language", "")

        lines.append(f"## Pattern: {name}\n")
        if description:
            lines.append(f"_{description}_\n")

        # Find a file matching the criteria
        matched_file = find_matching_file(project_root, search_dir, file_glob, search_text)

        lines.append(f"```{language}")
        if matched_file:
            code = extract_code_block(matched_file, search_text)
            lines.append(code)
        else:
            lines.append(f"// No matching file found for {file_glob} containing '{search_text}' in {search_dir}/")
        lines.append("```\n")

    content = "\n".join(lines)
    output_file = output_dir / "patterns.md"
    output_file.write_text(content)
    line_count = content.count("\n")
    logger.info("  patterns.md: %d lines -> %s", line_count, output_file)


def main():
    """Legacy entry point."""
    project_root = Path(__file__).resolve().parents[2]
    output_dir = project_root / "_bmad-output" / "context"
    output_dir.mkdir(parents=True, exist_ok=True)
    generate_with_config(project_root, output_dir, {"extractions": []})


if __name__ == "__main__":
    main()
