#!/usr/bin/env python3
"""Generate module-index.md — Feature map of frontend modules + backend services.

Config-driven: reads scan paths from context-config.yaml.
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def count_files(directory: Path, extensions: tuple[str, ...]) -> int:
    """Count files with given extensions in a directory tree."""
    if not directory.exists():
        return 0
    return sum(1 for f in directory.rglob("*") if f.is_file() and f.suffix in extensions)


def get_key_files(feature_dir: Path, extensions: tuple[str, ...] = (".ts", ".tsx")) -> list[str]:
    """Get the most important files in a feature directory."""
    key_files = []
    for subdir_name in ["components", "pages", "hooks", "services", "types", "utils"]:
        subdir = feature_dir / subdir_name
        if subdir.exists():
            files = sorted(
                f.name for f in subdir.iterdir()
                if f.is_file() and f.suffix in extensions
                and ".test." not in f.name and ".spec." not in f.name
            )
            if files:
                key_files.extend(f"{subdir_name}/{f}" for f in files[:3])
                if len(files) > 3:
                    key_files.append(f"{subdir_name}/... (+{len(files) - 3} more)")
    if (feature_dir / "index.ts").exists():
        key_files.insert(0, "index.ts")
    elif (feature_dir / "index.js").exists():
        key_files.insert(0, "index.js")
    return key_files


def scan_features(project_root: Path, scanner: dict) -> str:
    """Scan feature directories (e.g., src/features/)."""
    lines = []
    label = scanner.get("label", "Features")
    rel_path = scanner["path"]
    features_dir = project_root / rel_path
    extensions = tuple(scanner.get("extensions", [".ts", ".tsx"]))

    lines.append(f"## {label}")
    lines.append(f"_Location: `{rel_path}/`_\n")

    if not features_dir.exists():
        lines.append("_(Directory not found)_\n")
        return "\n".join(lines)

    features = sorted(d for d in features_dir.iterdir() if d.is_dir())
    lines.append(f"**{len(features)} feature modules**\n")

    for feature in features:
        name = feature.name
        file_count = count_files(feature, extensions)
        test_count = sum(
            1 for f in feature.rglob("*")
            if f.is_file() and (".test." in f.name or ".spec." in f.name)
        )
        subdirs = sorted(d.name for d in feature.iterdir() if d.is_dir() and not d.name.startswith("_"))
        key_files = get_key_files(feature, extensions)

        lines.append(f"### {name}/")
        lines.append(f"- **Structure:** {', '.join(subdirs) if subdirs else 'flat'}")
        lines.append(f"- **Files:** {file_count} ({test_count} tests)")
        if key_files:
            lines.append(f"- **Key files:** {', '.join(key_files[:6])}")

        # Check for service files to extract API endpoints
        services_dir = feature / "services"
        if services_dir.exists():
            for svc in services_dir.iterdir():
                if svc.is_file() and svc.suffix in extensions and ".test." not in svc.name:
                    endpoints = _extract_api_calls(svc)
                    if endpoints:
                        lines.append(f"- **API calls:** {', '.join(endpoints[:3])}")
                        break
        lines.append("")

    return "\n".join(lines)


def scan_shared(project_root: Path, scanner: dict) -> str:
    """Scan shared code directories (components, hooks, utils, etc.)."""
    lines = []
    label = scanner.get("label", "Shared Code")
    rel_path = scanner["path"]
    base_dir = project_root / rel_path
    subdirs = scanner.get("subdirs", ["components", "hooks", "utils", "lib", "types"])
    extensions = tuple(scanner.get("extensions", [".ts", ".tsx"]))

    lines.append(f"## {label}")
    lines.append(f"_Location: `{rel_path}/`_\n")

    for dirname in subdirs:
        shared_dir = base_dir / dirname
        if shared_dir.exists():
            file_count = count_files(shared_dir, extensions)
            if file_count > 0:
                files = sorted(
                    f.name for f in shared_dir.rglob("*")
                    if f.is_file() and f.suffix in extensions and ".test." not in f.name
                )[:5]
                lines.append(f"### {dirname}/")
                lines.append(f"- **Files:** {file_count}")
                lines.append(f"- **Key:** {', '.join(files)}")
                lines.append("")

    return "\n".join(lines)


def scan_routers(project_root: Path, scanner: dict) -> str:
    """Scan backend router files."""
    lines = []
    label = scanner.get("label", "Backend Routers")
    rel_path = scanner["path"]
    routers_dir = project_root / rel_path

    lines.append(f"## {label}")
    lines.append(f"_Location: `{rel_path}/`_\n")

    if not routers_dir.exists():
        lines.append("_(Directory not found)_\n")
        return "\n".join(lines)

    routers = sorted(
        f for f in routers_dir.iterdir()
        if f.is_file() and f.suffix == ".py" and f.name != "__init__.py"
    )
    lines.append(f"**{len(routers)} router files**\n")

    for router in routers:
        try:
            content = router.read_text(errors="replace")
            endpoint_count = len(re.findall(r"@router\.(get|post|put|patch|delete)\(", content))
            prefix_match = re.search(r'prefix\s*=\s*["\']([^"\']+)["\']', content)
            prefix = prefix_match.group(1) if prefix_match else f"/{router.stem}"
            if endpoint_count > 0:
                lines.append(f"- **{router.stem}.py** — `{prefix}` ({endpoint_count} endpoints)")
        except Exception:
            lines.append(f"- **{router.stem}.py** — (parse error)")

    lines.append("")
    return "\n".join(lines)


def scan_models(project_root: Path, scanner: dict) -> str:
    """Scan backend model files."""
    lines = []
    label = scanner.get("label", "Backend Models")
    rel_path = scanner["path"]
    models_dir = project_root / rel_path

    lines.append(f"## {label}")
    lines.append(f"_Location: `{rel_path}/`_\n")

    if not models_dir.exists():
        lines.append("_(Directory not found)_\n")
        return "\n".join(lines)

    models = sorted(
        f for f in models_dir.iterdir()
        if f.is_file() and f.suffix == ".py" and f.name != "__init__.py"
    )
    lines.append(f"**{len(models)} model files**\n")

    for model in models:
        try:
            content = model.read_text(errors="replace")
            classes = re.findall(r"class\s+(\w+)\(", content)
            model_classes = [c for c in classes if c not in ("Base", "BaseModel")]
            if model_classes:
                lines.append(f"- **{model.stem}.py** — {', '.join(model_classes)}")
        except Exception:
            lines.append(f"- **{model.stem}.py** — (parse error)")

    lines.append("")
    return "\n".join(lines)


def scan_services(project_root: Path, scanner: dict) -> str:
    """Scan backend service files."""
    lines = []
    label = scanner.get("label", "Backend Services")
    rel_path = scanner["path"]
    services_dir = project_root / rel_path

    lines.append(f"## {label}")
    lines.append(f"_Location: `{rel_path}/`_\n")

    if not services_dir.exists():
        lines.append("_(Directory not found)_\n")
        return "\n".join(lines)

    services = sorted(
        f for f in services_dir.rglob("*.py") if f.is_file() and f.name != "__init__.py"
    )
    lines.append(f"**{len(services)} service files**\n")

    for svc in services:
        rel = svc.relative_to(services_dir)
        try:
            content = svc.read_text(errors="replace")
            classes = re.findall(r"class\s+(\w+Service)\b", content)
            if classes:
                lines.append(f"- **{rel}** — {', '.join(classes)}")
            else:
                funcs = re.findall(r"^async\s+def\s+(\w+)", content, re.MULTILINE)
                if funcs:
                    lines.append(f"- **{rel}** — {', '.join(funcs[:3])}")
                else:
                    lines.append(f"- **{rel}**")
        except Exception:
            lines.append(f"- **{rel}** — (parse error)")

    lines.append("")
    return "\n".join(lines)


def scan_infrastructure(project_root: Path, scanner: dict) -> str:
    """Scan infrastructure directories."""
    lines = []
    label = scanner.get("label", "Infrastructure")
    rel_path = scanner["path"]
    base_dir = project_root / rel_path
    subdirs = scanner.get("subdirs", [])

    lines.append(f"## {label}")
    lines.append(f"_Location: `{rel_path}/`_\n")

    for dirname in subdirs:
        subdir = base_dir / dirname
        if subdir.exists():
            py_count = count_files(subdir, (".py",))
            if py_count > 0:
                lines.append(f"- **{dirname}/** — {py_count} Python files")

    lines.append("")
    return "\n".join(lines)


def _extract_api_calls(service_file: Path) -> list[str]:
    """Extract API paths from a frontend service file."""
    endpoints = []
    try:
        content = service_file.read_text(errors="replace")
        for match in re.finditer(r"\.(get|post|put|patch|delete)\(['\"]([^'\"]+)['\"]", content):
            method = match.group(1).upper()
            path = match.group(2)
            endpoints.append(f"{method} {path}")
    except Exception:
        pass
    return endpoints[:5]


# Scanner type dispatch
SCANNER_TYPES = {
    "features": scan_features,
    "shared": scan_shared,
    "routers": scan_routers,
    "models": scan_models,
    "services": scan_services,
    "infrastructure": scan_infrastructure,
}


def generate_with_config(project_root: Path, output_dir: Path, config: dict):
    """Generate module-index.md using config-driven scanners."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    scanners = config.get("scanners", [])

    sections = [
        f"# Module Index\n",
        f"_Auto-generated: {now} | Regenerate: `python scripts/context/generate_all.py`_\n",
        "---\n",
    ]

    for scanner in scanners:
        scanner_type = scanner.get("type", "features")
        handler = SCANNER_TYPES.get(scanner_type)
        if handler:
            sections.append(handler(project_root, scanner))
        else:
            logger.warning("Unknown scanner type: %s", scanner_type)

    content = "\n".join(sections)
    output_file = output_dir / "module-index.md"
    output_file.write_text(content)
    line_count = content.count("\n")
    logger.info("  module-index.md: %d lines -> %s", line_count, output_file)


def main():
    """Legacy entry point (uses hardcoded paths)."""
    project_root = Path(__file__).resolve().parents[2]
    output_dir = project_root / "_bmad-output" / "context"
    output_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "scanners": [
            {"type": "features", "label": "Frontend Features", "path": "src/features", "extensions": [".ts", ".tsx"]},
            {"type": "shared", "label": "Frontend Shared", "path": "src", "subdirs": ["components", "hooks", "utils", "lib", "types"]},
            {"type": "routers", "label": "Backend Routers", "path": "backend/app/routers"},
            {"type": "models", "label": "Backend Models", "path": "backend/app/models"},
            {"type": "services", "label": "Backend Services", "path": "backend/app/services"},
        ]
    }
    generate_with_config(project_root, output_dir, config)


if __name__ == "__main__":
    main()
