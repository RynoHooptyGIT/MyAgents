#!/bin/bash
# =============================================================================
# BMAD v6 Setup Script
# =============================================================================
# Installs the BMAD methodology into a new project.
# Run from the bmad-method-v6 directory:
#   bash scripts/setup.sh /path/to/your/project
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BMAD_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "  ██████╗ ███╗   ███╗ █████╗ ██████╗     ██╗   ██╗ ██████╗ "
echo "  ██╔══██╗████╗ ████║██╔══██╗██╔══██╗    ██║   ██║██╔════╝ "
echo "  ██████╔╝██╔████╔██║███████║██║  ██║    ██║   ██║███████╗ "
echo "  ██╔══██╗██║╚██╔╝██║██╔══██║██║  ██║    ╚██╗ ██╔╝██╔═══╝ "
echo "  ██████╔╝██║ ╚═╝ ██║██║  ██║██████╔╝     ╚████╔╝ ╚██████╗"
echo "  ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚═════╝      ╚═══╝   ╚═════╝"
echo -e "${NC}"
echo -e "${BLUE}Build, Manage, Architect, Deploy — AI-Assisted Development${NC}"
echo ""

# ── Target directory ─────────────────────────────────────────────
TARGET_DIR="${1:-$(pwd)}"

if [ "$TARGET_DIR" = "$BMAD_ROOT" ]; then
    echo -e "${RED}ERROR: Cannot install BMAD into the template repository itself.${NC}"
    echo "Usage: bash scripts/setup.sh /path/to/your/project"
    exit 1
fi

if [ ! -d "$TARGET_DIR" ]; then
    echo -e "${YELLOW}Target directory does not exist: $TARGET_DIR${NC}"
    read -p "Create it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        mkdir -p "$TARGET_DIR"
    else
        exit 1
    fi
fi

echo -e "${GREEN}Installing BMAD v6 into: ${TARGET_DIR}${NC}"
echo ""

# ── Collect project info ─────────────────────────────────────────
read -p "Project name: " PROJECT_NAME
if [ -z "$PROJECT_NAME" ]; then
    echo -e "${RED}Project name is required.${NC}"
    exit 1
fi

read -p "Your display name (default: Developer): " USER_NAME
USER_NAME="${USER_NAME:-Developer}"

read -p "Base branch (default: main): " BASE_BRANCH
BASE_BRANCH="${BASE_BRANCH:-main}"

read -p "Production branch (default: main): " PROD_BRANCH
PROD_BRANCH="${PROD_BRANCH:-main}"

read -p "GitHub owner (leave empty to skip): " GITHUB_OWNER
read -p "GitHub repo name (leave empty to skip): " GITHUB_REPO

echo ""
echo -e "${BLUE}Select AI tools to configure:${NC}"
echo "  1) Claude Code only (recommended)"
echo "  2) Claude Code + GitHub Copilot"
echo "  3) Claude Code + Cursor"
echo "  4) All three (Claude Code + Copilot + Cursor)"
echo "  5) None (just install BMAD core)"
read -p "Choice [1]: " TOOL_CHOICE
TOOL_CHOICE="${TOOL_CHOICE:-1}"

INSTALL_DATE=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")

# ── Helper: template substitution ────────────────────────────────
substitute() {
    local file="$1"
    sed -i '' \
        -e "s|{{PROJECT_NAME}}|${PROJECT_NAME}|g" \
        -e "s|{{USER_NAME}}|${USER_NAME}|g" \
        -e "s|{{BASE_BRANCH}}|${BASE_BRANCH}|g" \
        -e "s|{{PRODUCTION_BRANCH}}|${PROD_BRANCH}|g" \
        -e "s|{{GITHUB_OWNER}}|${GITHUB_OWNER}|g" \
        -e "s|{{GITHUB_REPO}}|${GITHUB_REPO}|g" \
        -e "s|{{INSTALL_DATE}}|${INSTALL_DATE}|g" \
        "$file" 2>/dev/null || true
}

# ── Step 1: Copy BMAD core ───────────────────────────────────────
echo -e "\n${CYAN}[1/6] Copying BMAD core system...${NC}"
cp -R "$BMAD_ROOT/_bmad" "$TARGET_DIR/_bmad"

# Apply project name to agents and config
sed -i '' "s|{project_name}|${PROJECT_NAME}|g" "$TARGET_DIR/_bmad/bmm/config.yaml" 2>/dev/null || true

echo -e "  ${GREEN}✓${NC} _bmad/ directory installed (34 agents, 70+ workflows)"

# ── Step 2: Generate config files ────────────────────────────────
echo -e "${CYAN}[2/6] Generating configuration files...${NC}"

# BMM config
cp "$BMAD_ROOT/templates/config.bmm.yaml.template" "$TARGET_DIR/_bmad/bmm/config.yaml"
substitute "$TARGET_DIR/_bmad/bmm/config.yaml"

# Core config
cp "$BMAD_ROOT/templates/config.core.yaml.template" "$TARGET_DIR/_bmad/core/config.yaml"
substitute "$TARGET_DIR/_bmad/core/config.yaml"

# BMB config
cp "$BMAD_ROOT/templates/config.bmb.yaml.template" "$TARGET_DIR/_bmad/bmb/config.yaml"
substitute "$TARGET_DIR/_bmad/bmb/config.yaml"

# Manifest
cp "$BMAD_ROOT/templates/manifest.yaml.template" "$TARGET_DIR/_bmad/_config/manifest.yaml"
substitute "$TARGET_DIR/_bmad/_config/manifest.yaml"

# IDE config
cp "$BMAD_ROOT/templates/claude-code.yaml.template" "$TARGET_DIR/_bmad/_config/ides/claude-code.yaml"
substitute "$TARGET_DIR/_bmad/_config/ides/claude-code.yaml"

echo -e "  ${GREEN}✓${NC} config.yaml (bmm, core, bmb), manifest.yaml generated"

# ── Step 3: Set up AI tool integrations ──────────────────────────
echo -e "${CYAN}[3/6] Setting up AI tool integrations...${NC}"

# Claude Code (options 1-4)
if [ "$TOOL_CHOICE" != "5" ]; then
    mkdir -p "$TARGET_DIR/.claude/commands/bmad"
    mkdir -p "$TARGET_DIR/.claude/hooks"

    # CLAUDE.md
    cp "$BMAD_ROOT/templates/CLAUDE.md.template" "$TARGET_DIR/CLAUDE.md"
    substitute "$TARGET_DIR/CLAUDE.md"

    # Settings
    cp "$BMAD_ROOT/templates/settings.local.json.template" "$TARGET_DIR/.claude/settings.local.json"

    # Slash commands
    cp -R "$BMAD_ROOT/claude-commands/"* "$TARGET_DIR/.claude/commands/bmad/"

    # Hook
    cp "$BMAD_ROOT/hooks/post-commit-context.sh" "$TARGET_DIR/.claude/hooks/post-commit-context.sh"
    chmod +x "$TARGET_DIR/.claude/hooks/post-commit-context.sh"

    echo -e "  ${GREEN}✓${NC} Claude Code: CLAUDE.md, 81 slash commands, hooks"
fi

# GitHub Copilot (options 2, 4)
if [ "$TOOL_CHOICE" = "2" ] || [ "$TOOL_CHOICE" = "4" ]; then
    mkdir -p "$TARGET_DIR/.github"
    cp "$BMAD_ROOT/templates/copilot-instructions.md.template" "$TARGET_DIR/.github/copilot-instructions.md"
    substitute "$TARGET_DIR/.github/copilot-instructions.md"
    echo -e "  ${GREEN}✓${NC} GitHub Copilot: .github/copilot-instructions.md"
fi

# Cursor (options 3, 4)
if [ "$TOOL_CHOICE" = "3" ] || [ "$TOOL_CHOICE" = "4" ]; then
    mkdir -p "$TARGET_DIR/.cursor/rules"
    cp "$BMAD_ROOT/templates/cursor-rules/"*.mdc "$TARGET_DIR/.cursor/rules/"
    echo -e "  ${GREEN}✓${NC} Cursor: .cursor/rules/ (3 rule files)"
fi

# ── Step 4: Set up context generators ────────────────────────────
echo -e "${CYAN}[4/6] Setting up context generators...${NC}"
mkdir -p "$TARGET_DIR/scripts/context"
cp "$BMAD_ROOT/scripts/context/"*.py "$TARGET_DIR/scripts/context/"
cp "$BMAD_ROOT/scripts/context/context-config.yaml" "$TARGET_DIR/scripts/context/context-config.yaml"
cp "$BMAD_ROOT/scripts/context/context-config.example.yaml" "$TARGET_DIR/scripts/context/context-config.example.yaml"
echo -e "  ${GREEN}✓${NC} Context generators installed (edit scripts/context/context-config.yaml)"

# ── Step 5: Create output directory structure ────────────────────
echo -e "${CYAN}[5/6] Creating output directory structure...${NC}"
mkdir -p "$TARGET_DIR/_bmad-output/planning-artifacts"
mkdir -p "$TARGET_DIR/_bmad-output/implementation-artifacts/stories"
mkdir -p "$TARGET_DIR/_bmad-output/context"
mkdir -p "$TARGET_DIR/_bmad-output/analysis"
mkdir -p "$TARGET_DIR/_bmad-output/excalidraw-diagrams"
mkdir -p "$TARGET_DIR/_bmad-output/testing"
mkdir -p "$TARGET_DIR/_bmad-output/devops"

# Add .gitkeep files
for dir in planning-artifacts implementation-artifacts/stories context analysis excalidraw-diagrams testing devops; do
    touch "$TARGET_DIR/_bmad-output/$dir/.gitkeep"
done

echo -e "  ${GREEN}✓${NC} _bmad-output/ scaffolding created"

# ── Step 6: Final summary ────────────────────────────────────────
echo -e "${CYAN}[6/6] Installation complete!${NC}"
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  BMAD v6 installed successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  Project: ${YELLOW}${PROJECT_NAME}${NC}"
echo -e "  Location: ${YELLOW}${TARGET_DIR}${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""
echo "  1. Edit context generators config:"
echo "     ${YELLOW}scripts/context/context-config.yaml${NC}"
echo "     (Set your project's source paths, framework, ORM)"
echo ""
echo "  2. Add your technical rules to:"
if [ "$TOOL_CHOICE" != "5" ]; then
    echo "     ${YELLOW}CLAUDE.md${NC} → 'Critical Technical Rules' section"
fi
echo ""
echo "  3. Start a session — the Oracle activates automatically:"
if [ "$TOOL_CHOICE" != "5" ]; then
    echo "     ${YELLOW}/bmad:bmm:agents:oracle${NC}"
fi
echo ""
echo "  4. Initialize sprint tracking:"
echo "     Oracle → ${YELLOW}SP${NC} (Sprint Planning)"
echo ""
echo "  5. Create your first story:"
echo "     Oracle → ${YELLOW}CS${NC} (Create Story)"
echo ""
echo -e "${BLUE}Documentation:${NC}"
echo "  - Quick start:    docs/QUICKSTART.md"
echo "  - Architecture:   docs/ARCHITECTURE.md"
echo "  - Agent catalog:  docs/AGENT-CATALOG.md"
echo "  - Workflow catalog: docs/WORKFLOW-CATALOG.md"
echo ""
