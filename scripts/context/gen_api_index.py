#!/usr/bin/env python3
"""Generate api-index.md — Central API reference from router files.

Config-driven: reads framework type and router path from context-config.yaml.
Supports: FastAPI, Express (basic).
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_fastapi_router(filepath: Path) -> dict:
    """Parse a FastAPI router file to extract endpoints."""
    content = filepath.read_text(errors="replace")
    result = {"prefix": "", "tags": [], "endpoints": []}

    prefix_match = re.search(r'prefix\s*=\s*["\']([^"\']+)["\']', content)
    result["prefix"] = prefix_match.group(1) if prefix_match else f"/{filepath.stem}"

    tags_match = re.search(r'tags\s*=\s*\["([^"]+)"', content)
    result["tags"] = [tags_match.group(1)] if tags_match else [filepath.stem.replace("_", " ").title()]

    endpoint_pattern = re.compile(
        r'@router\.(get|post|put|patch|delete)\(\s*["\']([^"\']*)["\']',
        re.MULTILINE,
    )

    for match in endpoint_pattern.finditer(content):
        method = match.group(1).upper()
        path = match.group(2)
        rest = content[match.end():]

        response_model = ""
        rm_match = re.search(r'response_model\s*=\s*(\w+)', rest[:500])
        if rm_match:
            response_model = rm_match.group(1)

        func_match = re.search(r'async\s+def\s+(\w+)\s*\(([^)]*)\)', rest[:1000])
        func_name = func_match.group(1) if func_match else ""
        func_params = func_match.group(2) if func_match else ""

        auth = "None"
        if "require_any_role" in func_params or "require_role" in func_params:
            auth = "Role-based"
        elif "current_user" in func_params or "get_current_user" in func_params:
            auth = "Bearer"

        desc = ""
        doc_match = re.search(r'"""(.+?)"""', rest[:500], re.DOTALL)
        if doc_match:
            desc = doc_match.group(1).strip().split("\n")[0][:80]

        result["endpoints"].append({
            "method": method, "path": path, "auth": auth,
            "func": func_name, "response_model": response_model, "description": desc,
        })

    return result


def parse_express_router(filepath: Path) -> dict:
    """Parse an Express.js router file to extract endpoints."""
    content = filepath.read_text(errors="replace")
    result = {"prefix": f"/{filepath.stem}", "tags": [filepath.stem], "endpoints": []}

    endpoint_pattern = re.compile(
        r'router\.(get|post|put|patch|delete)\(\s*["\']([^"\']*)["\']',
        re.MULTILINE,
    )

    for match in endpoint_pattern.finditer(content):
        method = match.group(1).upper()
        path = match.group(2)

        auth = "None"
        rest = content[match.end():match.end() + 200]
        if "auth" in rest.lower() or "middleware" in rest.lower():
            auth = "Middleware"

        result["endpoints"].append({
            "method": method, "path": path, "auth": auth,
            "func": "", "response_model": "", "description": "",
        })

    return result


def generate_with_config(project_root: Path, output_dir: Path, config: dict):
    """Generate api-index.md using config settings."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    framework = config.get("framework", "fastapi")
    routers_rel = config.get("routers_dir", "backend/app/routers")
    routers_dir = project_root / routers_rel

    lines = []
    lines.append("# API Index")
    lines.append(f"\n_Auto-generated: {now} | Regenerate: `python scripts/context/generate_all.py`_")
    lines.append(f"_Source: `{routers_rel}/`_\n")
    lines.append("---\n")

    if not routers_dir.exists():
        lines.append("_(Routers directory not found)_\n")
        content = "\n".join(lines)
        (output_dir / "api-index.md").write_text(content)
        logger.info("  api-index.md: directory not found")
        return

    # Determine file extension and parser
    if framework == "fastapi":
        ext = ".py"
        parser = parse_fastapi_router
    elif framework == "express":
        ext = ".js"
        parser = parse_express_router
    else:
        lines.append(f"_(Unsupported framework: {framework})_\n")
        content = "\n".join(lines)
        (output_dir / "api-index.md").write_text(content)
        return

    # Also support .ts files for Express
    router_files = sorted(
        f for f in routers_dir.iterdir()
        if f.is_file() and f.suffix in (ext, ".ts") and f.name not in ("__init__.py", "index.ts", "index.js")
    )

    total_endpoints = 0
    router_data = []

    for rf in router_files:
        try:
            data = parser(rf)
            if data["endpoints"]:
                router_data.append((rf.stem, data))
                total_endpoints += len(data["endpoints"])
        except Exception as e:
            lines.append(f"- **{rf.stem}** — parse error: {e}")

    lines.append(f"**{len(router_data)} routers, {total_endpoints} endpoints total**\n")

    # Summary table
    lines.append("## Router Summary\n")
    lines.append("| Router | Prefix | Endpoints | Tag |")
    lines.append("|--------|--------|-----------|-----|")
    for name, data in router_data:
        tag = data["tags"][0] if data["tags"] else ""
        lines.append(f"| {name} | `{data['prefix']}` | {len(data['endpoints'])} | {tag} |")
    lines.append("")

    # Detailed listing
    lines.append("## Endpoints by Router\n")
    for name, data in router_data:
        prefix = data["prefix"]
        lines.append(f"### {data['tags'][0] if data['tags'] else name} (`{prefix}`)\n")
        lines.append("| Method | Path | Auth | Description |")
        lines.append("|--------|------|------|-------------|")
        for ep in data["endpoints"]:
            full_path = f"{prefix}{ep['path']}" if ep["path"] != "/" else prefix
            desc = ep["description"][:60] if ep["description"] else ep["func"]
            lines.append(f"| {ep['method']} | `{full_path}` | {ep['auth']} | {desc} |")
        lines.append("")

    content = "\n".join(lines)
    output_file = output_dir / "api-index.md"
    output_file.write_text(content)
    line_count = content.count("\n")
    logger.info("  api-index.md: %d lines -> %s", line_count, output_file)


def main():
    """Legacy entry point."""
    project_root = Path(__file__).resolve().parents[2]
    output_dir = project_root / "_bmad-output" / "context"
    output_dir.mkdir(parents=True, exist_ok=True)
    generate_with_config(project_root, output_dir, {"framework": "fastapi", "routers_dir": "backend/app/routers"})


if __name__ == "__main__":
    main()
