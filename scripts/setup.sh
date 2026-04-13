#!/bin/bash
# =============================================================================
# My Dev Team — Setup Script
# =============================================================================
# Installs the agent team methodology into a new project.
# Run from the MyAgents directory:
#   bash scripts/setup.sh /path/to/your/project
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEAM_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "  ╔═══════════════════════════════════════════╗"
echo "  ║         My Dev Team — Setup               ║"
echo "  ║    AI-Assisted Development Methodology    ║"
echo "  ╚═══════════════════════════════════════════╝"
echo -e "${NC}"

# ── Target directory ─────────────────────────────────────────────
TARGET_DIR="${1:-$(pwd)}"

if [ "$TARGET_DIR" = "$TEAM_ROOT" ]; then
    echo -e "${RED}ERROR: Cannot install into the template repository itself.${NC}"
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

echo -e "${GREEN}Installing My Dev Team into: ${TARGET_DIR}${NC}"
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
echo "  5) None (just install core)"
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

# ── Step 1: Copy team system ────────────────────────────────────
echo -e "\n${CYAN}[1/6] Copying team system...${NC}"
cp -R "$TEAM_ROOT/team" "$TARGET_DIR/team"

echo -e "  ${GREEN}✓${NC} team/ directory installed (27 agents, 70+ workflows)"

# ── Step 2: Generate config ─────────────────────────────────────
echo -e "${CYAN}[2/6] Generating configuration...${NC}"

# Unified config
cp "$TEAM_ROOT/templates/config.yaml.template" "$TARGET_DIR/team/config.yaml"
substitute "$TARGET_DIR/team/config.yaml"

# Manifest
cp "$TEAM_ROOT/templates/manifest.yaml.template" "$TARGET_DIR/team/manifest.yaml"
substitute "$TARGET_DIR/team/manifest.yaml"

echo -e "  ${GREEN}✓${NC} config.yaml, manifest.yaml generated"

# ── Step 3: Set up AI tool integrations ──────────────────────────
echo -e "${CYAN}[3/6] Setting up AI tool integrations...${NC}"

# Claude Code (options 1-4)
if [ "$TOOL_CHOICE" != "5" ]; then
    mkdir -p "$TARGET_DIR/.claude/commands/team"
    mkdir -p "$TARGET_DIR/.claude/hooks"

    # CLAUDE.md
    cp "$TEAM_ROOT/templates/CLAUDE.md.template" "$TARGET_DIR/CLAUDE.md"
    substitute "$TARGET_DIR/CLAUDE.md"

    # Settings
    cp "$TEAM_ROOT/templates/settings.local.json.template" "$TARGET_DIR/.claude/settings.local.json"

    # Slash commands (flat namespace)
    cp "$TEAM_ROOT/claude-commands/team/"* "$TARGET_DIR/.claude/commands/team/"

    # Hook
    cp "$TEAM_ROOT/hooks/post-commit-context.sh" "$TARGET_DIR/.claude/hooks/post-commit-context.sh"
    chmod +x "$TARGET_DIR/.claude/hooks/post-commit-context.sh"

    echo -e "  ${GREEN}✓${NC} Claude Code: CLAUDE.md, 76 slash commands, hooks"
fi

# GitHub Copilot (options 2, 4)
if [ "$TOOL_CHOICE" = "2" ] || [ "$TOOL_CHOICE" = "4" ]; then
    mkdir -p "$TARGET_DIR/.github"
    cp "$TEAM_ROOT/templates/copilot-instructions.md.template" "$TARGET_DIR/.github/copilot-instructions.md"
    substitute "$TARGET_DIR/.github/copilot-instructions.md"
    echo -e "  ${GREEN}✓${NC} GitHub Copilot: .github/copilot-instructions.md"
fi

# Cursor (options 3, 4)
if [ "$TOOL_CHOICE" = "3" ] || [ "$TOOL_CHOICE" = "4" ]; then
    mkdir -p "$TARGET_DIR/.cursor/rules"
    cp "$TEAM_ROOT/templates/cursor-rules/"*.mdc "$TARGET_DIR/.cursor/rules/"
    echo -e "  ${GREEN}✓${NC} Cursor: .cursor/rules/ (3 rule files)"
fi

# ── Step 4: Set up context generators ────────────────────────────
echo -e "${CYAN}[4/6] Setting up context generators...${NC}"
mkdir -p "$TARGET_DIR/scripts/context"
cp "$TEAM_ROOT/scripts/context/"*.py "$TARGET_DIR/scripts/context/"
cp "$TEAM_ROOT/scripts/context/context-config.yaml" "$TARGET_DIR/scripts/context/context-config.yaml"
cp "$TEAM_ROOT/scripts/context/context-config.example.yaml" "$TARGET_DIR/scripts/context/context-config.example.yaml"
echo -e "  ${GREEN}✓${NC} Context generators installed (edit scripts/context/context-config.yaml)"

# Update script and upstream tracking
cp "$TEAM_ROOT/scripts/team-update.sh" "$TARGET_DIR/scripts/team-update.sh"
chmod +x "$TARGET_DIR/scripts/team-update.sh"

# VERSION file
cp "$TEAM_ROOT/VERSION" "$TARGET_DIR/VERSION"

# Store upstream path for future updates
echo "$TEAM_ROOT" > "$TARGET_DIR/.team-upstream"

echo -e "  ${GREEN}✓${NC} Update script installed (run: bash scripts/team-update.sh)"

# ── Step 5: Create output directory structure ────────────────────
echo -e "${CYAN}[5/6] Creating output directory structure...${NC}"
mkdir -p "$TARGET_DIR/output/planning-artifacts"
mkdir -p "$TARGET_DIR/output/implementation-artifacts/stories"
mkdir -p "$TARGET_DIR/output/context"
mkdir -p "$TARGET_DIR/output/analysis"
mkdir -p "$TARGET_DIR/output/excalidraw-diagrams"
mkdir -p "$TARGET_DIR/output/testing"
mkdir -p "$TARGET_DIR/output/devops"

# Add .gitkeep files
for dir in planning-artifacts implementation-artifacts/stories context analysis excalidraw-diagrams testing devops; do
    touch "$TARGET_DIR/output/$dir/.gitkeep"
done

echo -e "  ${GREEN}✓${NC} output/ scaffolding created"

# ── Step 6: Final summary ────────────────────────────────────────
echo -e "${CYAN}[6/6] Installation complete!${NC}"
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  My Dev Team installed successfully!${NC}"
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
echo "  3. Start Tanto (your project commander):"
if [ "$TOOL_CHOICE" != "5" ]; then
    echo "     ${YELLOW}/team:tanto${NC}  — then say 'let's ride' for full scan & plan"
fi
echo ""
echo "  4. Or onboard a new venture:"
if [ "$TOOL_CHOICE" != "5" ]; then
    echo "     ${YELLOW}/team:tanto${NC}  — then say 'new venture' for CEO deep-dive"
fi
echo ""
echo "  5. Pull future updates:"
echo "     ${YELLOW}bash scripts/team-update.sh${NC}"
echo ""
echo -e "${BLUE}Documentation:${NC}"
echo "  - Quick start:      docs/QUICKSTART.md"
echo "  - Architecture:     docs/ARCHITECTURE.md"
echo "  - Agent catalog:    docs/AGENT-CATALOG.md"
echo "  - Workflow catalog:  docs/WORKFLOW-CATALOG.md"
echo ""
