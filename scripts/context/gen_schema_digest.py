#!/usr/bin/env python3
"""Generate schema-digest.md — Database schema summary from ORM models.

Config-driven: reads ORM type and models path from context-config.yaml.
Supports: SQLAlchemy.
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_sqlalchemy_model(filepath: Path, config: dict) -> list[dict]:
    """Parse a SQLAlchemy model file to extract table definitions."""
    content = filepath.read_text(errors="replace")
    models = []
    model_bases = config.get("model_bases", ["BaseModel", "Base", "db.Model"])
    skip_classes = config.get("skip_classes", ["Base", "Mixin"])

    class_pattern = re.compile(r'class\s+(\w+)\s*\(([^)]+)\)\s*:', re.MULTILINE)

    for match in class_pattern.finditer(content):
        class_name = match.group(1)
        bases = match.group(2).strip()

        if any(skip in class_name for skip in skip_classes):
            continue
        if not any(b in bases for b in model_bases):
            continue

        start = match.end()
        next_class = re.search(r'\nclass\s+\w+', content[start:])
        body = content[start:start + next_class.start()] if next_class else content[start:]

        model = {
            "class_name": class_name, "bases": bases, "file": filepath.stem,
            "tablename": "", "columns": [], "relationships": [],
            "has_tenant_id": False, "has_rls": False, "indexes": [],
        }

        tn_match = re.search(r'__tablename__\s*=\s*["\'](\w+)["\']', body)
        if tn_match:
            model["tablename"] = tn_match.group(1)
        else:
            name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", class_name)
            model["tablename"] = re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()

        col_pattern = re.compile(r'(\w+)\s*=\s*(?:Column|mapped_column)\s*\(([^)]+)\)', re.MULTILINE)
        for col_match in col_pattern.finditer(body):
            col_name = col_match.group(1)
            col_def = col_match.group(2).strip()
            type_match = re.match(r'(\w+)(?:\(.*?\))?\s*,?', col_def)
            col_type = type_match.group(1) if type_match else "Unknown"

            if col_name == "tenant_id":
                model["has_tenant_id"] = True

            model["columns"].append({
                "name": col_name, "type": col_type,
                "pk": "primary_key=True" in col_def,
                "fk": "ForeignKey" in col_def,
                "nullable": "nullable=True" in col_def or "nullable" not in col_def,
                "indexed": "index=True" in col_def,
            })

        rel_pattern = re.compile(r'(\w+)\s*=\s*relationship\s*\(\s*["\'](\w+)["\']', re.MULTILINE)
        for rel_match in rel_pattern.finditer(body):
            model["relationships"].append({"name": rel_match.group(1), "target": rel_match.group(2)})

        if "rls" in body.lower() or "row_level_security" in body.lower():
            model["has_rls"] = True
        if "BaseModel" in bases:
            model["has_tenant_id"] = True
            model["has_rls"] = True

        models.append(model)

    return models


def generate_with_config(project_root: Path, output_dir: Path, config: dict):
    """Generate schema-digest.md using config settings."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    orm = config.get("orm", "sqlalchemy")
    models_rel = config.get("models_dir", "backend/app/models")
    models_dir = project_root / models_rel

    lines = []
    lines.append("# Schema Digest")
    lines.append(f"\n_Auto-generated: {now} | Regenerate: `python scripts/context/generate_all.py`_")
    lines.append(f"_Source: `{models_rel}/`_\n")
    lines.append("---\n")

    if not models_dir.exists():
        lines.append("_(Models directory not found)_\n")
        content = "\n".join(lines)
        (output_dir / "schema-digest.md").write_text(content)
        logger.info("  schema-digest.md: directory not found")
        return

    if orm != "sqlalchemy":
        lines.append(f"_(ORM '{orm}' parser not yet implemented. Only 'sqlalchemy' is supported.)_\n")
        content = "\n".join(lines)
        (output_dir / "schema-digest.md").write_text(content)
        return

    model_files = sorted(
        f for f in models_dir.iterdir()
        if f.is_file() and f.suffix == ".py" and f.name != "__init__.py"
    )

    all_models = []
    for mf in model_files:
        try:
            all_models.extend(parse_sqlalchemy_model(mf, config))
        except Exception as e:
            lines.append(f"- **{mf.stem}** — parse error: {e}")

    rls_count = sum(1 for m in all_models if m["has_rls"])
    lines.append(f"**{len(all_models)} tables** ({rls_count} with RLS/tenant isolation)\n")

    # Summary table
    lines.append("## Tables\n")
    lines.append("| Table | Model | File | Columns | RLS | Key Relationships |")
    lines.append("|-------|-------|------|---------|-----|-------------------|")

    for model in sorted(all_models, key=lambda m: m["tablename"]):
        rels = ", ".join(r["target"] for r in model["relationships"][:3])
        if len(model["relationships"]) > 3:
            rels += f" +{len(model['relationships']) - 3}"
        rls = "Yes" if model["has_rls"] else "No"
        lines.append(
            f"| {model['tablename']} | {model['class_name']} | {model['file']}.py | "
            f"{len(model['columns'])} | {rls} | {rels} |"
        )
    lines.append("")

    # Key model details
    key_models = sorted(all_models, key=lambda m: len(m["columns"]), reverse=True)[:15]
    lines.append("## Key Model Details\n")

    for model in key_models:
        if not model["columns"]:
            continue
        lines.append(f"### {model['class_name']} (`{model['tablename']}`)\n")
        lines.append(f"_File: `models/{model['file']}.py` | RLS: {'Yes' if model['has_rls'] else 'No'}_\n")

        pk_cols = [c["name"] for c in model["columns"] if c["pk"]]
        fk_cols = [c["name"] for c in model["columns"] if c["fk"]]
        other_cols = [c["name"] for c in model["columns"] if not c["pk"] and not c["fk"]]

        if pk_cols:
            lines.append(f"- **PK:** {', '.join(pk_cols)}")
        if fk_cols:
            lines.append(f"- **FK:** {', '.join(fk_cols)}")
        if other_cols:
            lines.append(f"- **Columns:** {', '.join(other_cols)}")
        if model["relationships"]:
            rels = [f"{r['name']} -> {r['target']}" for r in model["relationships"]]
            lines.append(f"- **Relationships:** {', '.join(rels)}")
        lines.append("")

    content = "\n".join(lines)
    output_file = output_dir / "schema-digest.md"
    output_file.write_text(content)
    line_count = content.count("\n")
    logger.info("  schema-digest.md: %d lines -> %s", line_count, output_file)


def main():
    """Legacy entry point."""
    project_root = Path(__file__).resolve().parents[2]
    output_dir = project_root / "_bmad-output" / "context"
    output_dir.mkdir(parents=True, exist_ok=True)
    generate_with_config(project_root, output_dir, {"orm": "sqlalchemy", "models_dir": "backend/app/models"})


if __name__ == "__main__":
    main()
