#!/usr/bin/env bash
# migrate-to-team.sh — Extract BMAD v6 → "My Dev Team" Standalone Structure
#
# Converts the multi-module _bmad/ framework into a flat team/ structure.
# Idempotent: safe to re-run (removes team/ first if present).
#
# Usage: bash scripts/migrate-to-team.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "═══════════════════════════════════════════════"
echo "  BMAD → My Dev Team Migration"
echo "═══════════════════════════════════════════════"
echo ""
echo "Root: $ROOT"
echo ""

# ─────────────────────────────────────────────
# Pre-flight checks
# ─────────────────────────────────────────────
if [ ! -d "_bmad" ]; then
  echo "ERROR: _bmad/ directory not found. Nothing to migrate."
  exit 1
fi

if [ -d "team" ]; then
  echo "WARNING: team/ already exists. Removing for clean migration..."
  rm -rf team
fi

if [ -d "claude-commands/team" ]; then
  echo "WARNING: claude-commands/team/ already exists. Removing..."
  rm -rf claude-commands/team
fi

# ─────────────────────────────────────────────
# Step 1a: Create directory skeleton
# ─────────────────────────────────────────────
echo "▸ Step 1a: Creating directory skeleton..."

mkdir -p team/agents
mkdir -p team/engine
mkdir -p team/resources
mkdir -p team/data
mkdir -p team/teams
mkdir -p team/workflows
mkdir -p claude-commands/team
mkdir -p output/planning-artifacts
mkdir -p output/implementation-artifacts
mkdir -p output/context

echo "  ✓ Skeleton created"

# ─────────────────────────────────────────────
# Step 1b: Copy files
# ─────────────────────────────────────────────
echo "▸ Step 1b: Copying files..."

# --- Agents: flatten all modules into team/agents/ ---
echo "  Copying agents..."
for mod_dir in _bmad/core/agents _bmad/bmb/agents _bmad/bmm/agents _bmad/cis/agents; do
  if [ -d "$mod_dir" ]; then
    for f in "$mod_dir"/*.md; do
      [ -f "$f" ] && cp "$f" team/agents/
    done
  fi
done
AGENT_COUNT=$(find team/agents -name "*.md" | wc -l | tr -d ' ')
echo "  ✓ $AGENT_COUNT agents copied"

# --- Engine: core tasks ---
echo "  Copying engine..."
if [ -d "_bmad/core/tasks" ]; then
  cp -R _bmad/core/tasks/* team/engine/
fi
echo "  ✓ Engine copied"

# --- Resources ---
echo "  Copying resources..."
if [ -d "_bmad/core/resources" ]; then
  cp -R _bmad/core/resources/* team/resources/
fi
echo "  ✓ Resources copied"

# --- Data: bmm/data + testarch knowledge ---
echo "  Copying data..."
if [ -d "_bmad/bmm/data" ]; then
  cp -R _bmad/bmm/data/* team/data/
fi
if [ -d "_bmad/bmm/testarch" ]; then
  cp -R _bmad/bmm/testarch team/data/testarch
fi
echo "  ✓ Data copied"

# --- Teams ---
echo "  Copying teams..."
for team_dir in _bmad/bmm/teams _bmad/cis/teams; do
  if [ -d "$team_dir" ]; then
    for f in "$team_dir"/*; do
      [ -f "$f" ] && cp "$f" team/teams/
    done
  fi
done
echo "  ✓ Teams copied"

# --- Workflows: BMM phase-based (with renaming) ---
echo "  Copying workflows..."

# BMM phase workflows — renamed (explicit copies for bash 3 compatibility)
copy_phase() {
  local old="$1" new="$2"
  if [ -d "_bmad/bmm/workflows/$old" ]; then
    cp -R "_bmad/bmm/workflows/$old" "team/workflows/$new"
  fi
}
copy_phase "1-analysis" "analysis"
copy_phase "2-plan-workflows" "planning"
copy_phase "3-solutioning" "solutioning"
copy_phase "4-implementation" "implementation"
copy_phase "bmad-quick-flow" "quick-flow"

# BMM specialist workflows — keep names
BMM_KEEP_DIRS=(
  agentic api-contract custodian data devops
  document-project excalidraw-diagrams generate-project-context
  ml nav-audit navigator nist-rmf security
  testarch workflow-status
)

for dir_name in "${BMM_KEEP_DIRS[@]}"; do
  if [ -d "_bmad/bmm/workflows/$dir_name" ]; then
    cp -R "_bmad/bmm/workflows/$dir_name" "team/workflows/$dir_name"
  fi
done

# BMB workflows → builders/
if [ -d "_bmad/bmb/workflows" ]; then
  mkdir -p team/workflows/builders
  for sub in _bmad/bmb/workflows/*/; do
    [ -d "$sub" ] && cp -R "$sub" team/workflows/builders/
  done
fi

# CIS workflows — keep names
if [ -d "_bmad/cis/workflows" ]; then
  for sub in _bmad/cis/workflows/*/; do
    [ -d "$sub" ] && cp -R "$sub" "team/workflows/$(basename "$sub")"
  done
fi

# Core workflows — keep names
if [ -d "_bmad/core/workflows" ]; then
  for sub in _bmad/core/workflows/*/; do
    [ -d "$sub" ] && cp -R "$sub" "team/workflows/$(basename "$sub")"
  done
fi

WORKFLOW_COUNT=$(find team/workflows \( -name "workflow.yaml" -o -name "workflow.md" \) | wc -l | tr -d ' ')
echo "  ✓ $WORKFLOW_COUNT workflows copied"

# --- Config files ---
echo "  Copying config files..."
# agent-manifest.csv
if [ -f "_bmad/_config/agent-manifest.csv" ]; then
  cp _bmad/_config/agent-manifest.csv team/agent-manifest.csv
fi
# manifest.yaml
if [ -f "_bmad/_config/manifest.yaml" ]; then
  cp _bmad/_config/manifest.yaml team/manifest.yaml
fi
# agent-teams-guide
if [ -f "_bmad/_config/agent-teams-guide.md" ]; then
  cp _bmad/_config/agent-teams-guide.md team/agent-teams-guide.md
fi
echo "  ✓ Config files copied"

# ─────────────────────────────────────────────
# Step 1c: Bulk sed replacements in team/
# ─────────────────────────────────────────────
echo "▸ Step 1c: Applying path replacements in team/..."

# Create sed script — ORDER MATTERS: most-specific patterns first
SED_SCRIPT=$(mktemp)
cat > "$SED_SCRIPT" << 'SEDEOF'
# Config paths (all modules → unified)
s|_bmad/bmm/config\.yaml|team/config.yaml|g
s|_bmad/cis/config\.yaml|team/config.yaml|g
s|_bmad/bmb/config\.yaml|team/config.yaml|g
s|_bmad/core/config\.yaml|team/config.yaml|g

# Engine (core tasks)
s|_bmad/core/tasks/|team/engine/|g

# BMM phase workflows (specific before generic)
s|_bmad/bmm/workflows/1-analysis|team/workflows/analysis|g
s|_bmad/bmm/workflows/2-plan-workflows|team/workflows/planning|g
s|_bmad/bmm/workflows/3-solutioning|team/workflows/solutioning|g
s|_bmad/bmm/workflows/4-implementation|team/workflows/implementation|g
s|_bmad/bmm/workflows/bmad-quick-flow|team/workflows/quick-flow|g

# Generic workflow paths
s|_bmad/bmm/workflows/|team/workflows/|g
s|_bmad/cis/workflows/|team/workflows/|g
s|_bmad/bmb/workflows/|team/workflows/builders/|g
s|_bmad/core/workflows/|team/workflows/|g

# Resources
s|_bmad/core/resources/|team/resources/|g

# Agents (all modules → flat)
s|_bmad/bmm/agents/|team/agents/|g
s|_bmad/cis/agents/|team/agents/|g
s|_bmad/bmb/agents/|team/agents/|g
s|_bmad/core/agents/|team/agents/|g

# Data and teams
s|_bmad/bmm/data/|team/data/|g
s|_bmad/bmm/testarch/|team/data/testarch/|g
s|_bmad/bmm/teams/|team/teams/|g
s|_bmad/cis/teams/|team/teams/|g

# Config directory
s|_bmad/_config/|team/|g

# Output folder
s|_bmad-output|output|g

# Slash command prefixes (all modules → /team:)
s|/bmad:bmm:agents:|/team:|g
s|/bmad:cis:agents:|/team:|g
s|/bmad:bmb:agents:|/team:|g
s|/bmad:core:agents:|/team:|g
s|/bmad:bmm:workflows:|/team:|g
s|/bmad:cis:workflows:|/team:|g
s|/bmad:bmb:workflows:|/team:|g
s|/bmad:core:workflows:|/team:|g
s|/bmad:core:tasks:|/team:|g

# Template-style {_bmad} references (curly brace wrapped)
s|{_bmad}/core/tasks/|team/engine/|g
s|{_bmad}/core/|team/|g
s|{_bmad}/|team/|g

# Catch remaining generic _bmad/ references
s|_bmad/bmm/|team/|g
s|_bmad/cis/|team/|g
s|_bmad/bmb/|team/|g
s|_bmad/core/|team/|g
s|_bmad/|team/|g
SEDEOF

# Apply sed to all text files in team/
find team -type f \( -name "*.md" -o -name "*.yaml" -o -name "*.yml" \
  -o -name "*.xml" -o -name "*.csv" -o -name "*.json" -o -name "*.txt" \
  -o -name "*.mdc" -o -name "*.sh" -o -name "*.html" \) | while read -r file; do
  if [ "$(uname)" = "Darwin" ]; then
    sed -i '' -f "$SED_SCRIPT" "$file"
  else
    sed -i -f "$SED_SCRIPT" "$file"
  fi
done

rm -f "$SED_SCRIPT"

# Verify no stale _bmad references remain in team/
STALE=$(grep -rl "_bmad" team/ 2>/dev/null | wc -l | tr -d ' ')
if [ "$STALE" -gt 0 ]; then
  echo "  ⚠ WARNING: $STALE files in team/ still reference '_bmad':"
  grep -rl "_bmad" team/ 2>/dev/null | head -10
else
  echo "  ✓ All _bmad references replaced in team/"
fi

# ─────────────────────────────────────────────
# Step 1d: Generate claude-commands/team/
# ─────────────────────────────────────────────
echo "▸ Step 1d: Generating claude-commands/team/..."

# Create a second sed script for claude-commands content
CC_SED_SCRIPT=$(mktemp)
cat > "$CC_SED_SCRIPT" << 'SEDEOF'
s|_bmad/bmm/config\.yaml|team/config.yaml|g
s|_bmad/cis/config\.yaml|team/config.yaml|g
s|_bmad/bmb/config\.yaml|team/config.yaml|g
s|_bmad/core/config\.yaml|team/config.yaml|g
s|_bmad/core/tasks/|team/engine/|g
s|_bmad/bmm/workflows/1-analysis|team/workflows/analysis|g
s|_bmad/bmm/workflows/2-plan-workflows|team/workflows/planning|g
s|_bmad/bmm/workflows/3-solutioning|team/workflows/solutioning|g
s|_bmad/bmm/workflows/4-implementation|team/workflows/implementation|g
s|_bmad/bmm/workflows/bmad-quick-flow|team/workflows/quick-flow|g
s|_bmad/bmm/workflows/|team/workflows/|g
s|_bmad/cis/workflows/|team/workflows/|g
s|_bmad/bmb/workflows/|team/workflows/builders/|g
s|_bmad/core/workflows/|team/workflows/|g
s|_bmad/core/resources/|team/resources/|g
s|_bmad/bmm/agents/|team/agents/|g
s|_bmad/cis/agents/|team/agents/|g
s|_bmad/bmb/agents/|team/agents/|g
s|_bmad/core/agents/|team/agents/|g
s|_bmad/bmm/data/|team/data/|g
s|_bmad/bmm/testarch/|team/data/testarch/|g
s|_bmad/bmm/teams/|team/teams/|g
s|_bmad/cis/teams/|team/teams/|g
s|_bmad/_config/|team/|g
s|_bmad-output|output|g
s|_bmad/bmm/|team/|g
s|_bmad/cis/|team/|g
s|_bmad/bmb/|team/|g
s|_bmad/core/|team/|g
s|_bmad/|team/|g
SEDEOF

# Copy all command files from all modules into flat claude-commands/team/
for mod_dir in claude-commands/core claude-commands/bmb claude-commands/bmm claude-commands/cis; do
  if [ -d "$mod_dir" ]; then
    find "$mod_dir" -name "*.md" -type f | while read -r src; do
      filename=$(basename "$src")
      dest="claude-commands/team/$filename"
      if [ -f "$dest" ]; then
        echo "  ⚠ NAME COLLISION: $filename (from $src)"
      fi
      cp "$src" "$dest"
    done
  fi
done

# Apply sed to all claude-commands/team/ files
find claude-commands/team -name "*.md" -type f | while read -r file; do
  if [ "$(uname)" = "Darwin" ]; then
    sed -i '' -f "$CC_SED_SCRIPT" "$file"
  else
    sed -i -f "$CC_SED_SCRIPT" "$file"
  fi
done

rm -f "$CC_SED_SCRIPT"

CC_COUNT=$(find claude-commands/team -name "*.md" | wc -l | tr -d ' ')
echo "  ✓ $CC_COUNT claude commands generated"

# ─────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════"
echo "  Migration Complete!"
echo "═══════════════════════════════════════════════"
echo ""
echo "  Agents:          $AGENT_COUNT"
echo "  Workflows:       $WORKFLOW_COUNT"
echo "  Claude Commands: $CC_COUNT"
echo ""
echo "  Next steps:"
echo "  1. Create team/config.yaml (unified config)"
echo "  2. Update root-level docs, templates, IDE guides"
echo "  3. Remove _bmad/ and old claude-commands/{bmm,cis,bmb,core}/"
echo "  4. Update docs/agent-visual.html"
echo "  5. Run verification checklist"
echo ""
