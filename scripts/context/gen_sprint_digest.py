#!/usr/bin/env python3
"""Generate sprint-digest.md — Pre-computed sprint status summary.

Config-driven: reads phase mapping from context-config.yaml.
Parses sprint-status.yaml without PyYAML dependency.
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_sprint_status(sprint_file: Path) -> dict:
    """Parse sprint-status.yaml without PyYAML dependency."""
    if not sprint_file.exists():
        return {}

    content = sprint_file.read_text()
    entries = {}
    in_dev_status = False

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped == "development_status:":
            in_dev_status = True
            continue
        if in_dev_status and ":" in stripped and not stripped.startswith("#"):
            key, value = stripped.split(":", 1)
            entries[key.strip()] = value.strip()

    return entries


def categorize_entries(entries: dict) -> dict:
    """Categorize entries into epics and stories."""
    epics = {}

    for key, status in entries.items():
        if key.startswith("epic-") and "-retrospective" not in key:
            epic_num = key.replace("epic-", "")
            epics[epic_num] = {"status": status, "stories": {}}
        elif re.match(r"^\d+-\d+", key):
            parts = key.split("-", 2)
            epic_num = parts[0]
            if epic_num not in epics:
                epics[epic_num] = {"status": "unknown", "stories": {}}
            epics[epic_num]["stories"][key] = status

    return epics


def determine_phase(epic_num: int, phases: list[dict]) -> tuple[int, str]:
    """Map epic number to phase using config."""
    for i, phase in enumerate(phases):
        range_vals = phase.get("range", [0, 0])
        if range_vals[0] <= epic_num <= range_vals[1]:
            return i + 1, phase.get("name", f"Phase {i + 1}")
    return 0, "Unknown"


def generate_with_config(project_root: Path, output_dir: Path, config: dict):
    """Generate sprint-digest.md using config settings."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sprint_file = project_root / "_bmad-output" / "implementation-artifacts" / "sprint-status.yaml"
    phases = config.get("phases", [
        {"range": [1, 4], "name": "Foundation"},
        {"range": [5, 99], "name": "Features"},
    ])

    entries = parse_sprint_status(sprint_file)

    if not entries:
        content = f"# Sprint Digest\n\n_Auto-generated: {now}_\n\n_(sprint-status.yaml not found or empty)_\n"
        (output_dir / "sprint-digest.md").write_text(content)
        logger.info("  sprint-digest.md: no data")
        return

    epics = categorize_entries(entries)

    # Stats
    total_epics = len(epics)
    done_epics = sum(1 for e in epics.values() if e["status"] == "done")
    in_progress_epics = sum(1 for e in epics.values() if e["status"] == "in-progress")
    total_stories = sum(len(e["stories"]) for e in epics.values())
    done_stories = sum(sum(1 for s in e["stories"].values() if s == "done") for e in epics.values())

    in_progress_stories = []
    review_stories = []
    ready_stories = []

    for epic_data in epics.values():
        for story_key, status in epic_data["stories"].items():
            if status == "in-progress":
                in_progress_stories.append(story_key)
            elif status == "review":
                review_stories.append(story_key)
            elif status == "ready-for-dev":
                ready_stories.append(story_key)

    # Current phase
    current_phase = 0
    current_phase_desc = ""
    for epic_num_str in sorted(epics.keys(), key=lambda x: int(x) if x.isdigit() else 0):
        if epics[epic_num_str]["status"] == "in-progress":
            try:
                current_phase, current_phase_desc = determine_phase(int(epic_num_str), phases)
            except ValueError:
                pass

    # Build output
    lines = []
    lines.append("# Sprint Digest")
    lines.append(f"\n_Auto-generated: {now} | Regenerate: `python scripts/context/generate_all.py`_\n")
    lines.append("---\n")
    lines.append("## Overview\n")

    if current_phase:
        lines.append(f"- **Active Phase:** {current_phase} ({current_phase_desc})")
    lines.append(
        f"- **Epics:** {done_epics}/{total_epics} done"
        + (f", {in_progress_epics} in-progress" if in_progress_epics else "")
    )
    pct = done_stories * 100 // max(total_stories, 1)
    lines.append(f"- **Stories:** {done_stories}/{total_stories} done ({pct}%)")

    if in_progress_stories:
        lines.append(f"- **In-Progress:** {', '.join(in_progress_stories)}")
    if review_stories:
        lines.append(f"- **Awaiting Review:** {', '.join(review_stories)}")
    if ready_stories:
        lines.append(f"- **Ready for Dev:** {', '.join(ready_stories)}")
    lines.append("")

    # Phase summary
    lines.append("## Phase Summary\n")
    lines.append("| Phase | Description | Epics | Stories Done | Status |")
    lines.append("|-------|-------------|-------|-------------|--------|")

    phase_data = {}
    for epic_num_str, epic_data in epics.items():
        try:
            epic_num = int(epic_num_str)
        except ValueError:
            continue
        phase_num, desc = determine_phase(epic_num, phases)
        if phase_num not in phase_data:
            phase_data[phase_num] = {"desc": desc, "epics": 0, "stories_done": 0, "stories_total": 0, "statuses": set()}
        phase_data[phase_num]["epics"] += 1
        phase_data[phase_num]["stories_done"] += sum(1 for s in epic_data["stories"].values() if s == "done")
        phase_data[phase_num]["stories_total"] += len(epic_data["stories"])
        phase_data[phase_num]["statuses"].add(epic_data["status"])

    for phase_num in sorted(phase_data.keys()):
        pd = phase_data[phase_num]
        if "in-progress" in pd["statuses"]:
            status = "In Progress"
        elif all(s == "done" for s in pd["statuses"]):
            status = "Complete"
        elif "backlog" in pd["statuses"] and len(pd["statuses"]) == 1:
            status = "Backlog"
        else:
            status = "Partial"
        lines.append(f"| {phase_num} | {pd['desc']} | {pd['epics']} | {pd['stories_done']}/{pd['stories_total']} | {status} |")
    lines.append("")

    # Active epics
    active_epics = {k: v for k, v in epics.items() if v["status"] == "in-progress"}
    if active_epics:
        lines.append("## Active Epics\n")
        for epic_num_str in sorted(active_epics.keys(), key=lambda x: int(x) if x.isdigit() else 0):
            epic_data = active_epics[epic_num_str]
            story_count = len(epic_data["stories"])
            done_count = sum(1 for s in epic_data["stories"].values() if s == "done")
            lines.append(f"### Epic {epic_num_str} ({done_count}/{story_count} stories done)\n")
            for story_key, status in sorted(epic_data["stories"].items()):
                icon = {"done": "v", "in-progress": "->", "review": "?", "ready-for-dev": "o", "backlog": " "}.get(status, " ")
                lines.append(f"- [{icon}] {story_key}: {status}")
            lines.append("")

    content = "\n".join(lines)
    output_file = output_dir / "sprint-digest.md"
    output_file.write_text(content)
    line_count = content.count("\n")
    logger.info("  sprint-digest.md: %d lines -> %s", line_count, output_file)


def main():
    """Legacy entry point."""
    project_root = Path(__file__).resolve().parents[2]
    output_dir = project_root / "_bmad-output" / "context"
    output_dir.mkdir(parents=True, exist_ok=True)
    generate_with_config(project_root, output_dir, {})


if __name__ == "__main__":
    main()
