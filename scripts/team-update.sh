#!/bin/bash
# =============================================================================
# My Dev Team — Update Script
# =============================================================================
# Pulls the latest agent definitions, workflows, engine protocols, and standards
# from the upstream template repo while preserving project-specific configuration.
#
# Usage (from the installed project root):
#   bash scripts/team-update.sh                         # uses stored upstream
#   bash scripts/team-update.sh /path/to/MyAgents       # local upstream
#   bash scripts/team-update.sh https://github.com/...  # git upstream
#   bash scripts/team-update.sh --dry-run               # preview only
#   bash scripts/team-update.sh --force                 # skip confirmation
#   bash scripts/team-update.sh --check                 # check only, no update
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
DIM='\033[2m'
NC='\033[0m'

DRY_RUN=false
FORCE=false
CHECK_ONLY=false
UPSTREAM=""

# ── Parse arguments ──────────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --dry-run)  DRY_RUN=true ;;
        --force)    FORCE=true ;;
        --check)    CHECK_ONLY=true ;;
        *)          UPSTREAM="$arg" ;;
    esac
done

# ── Check-only mode delegates to team-check.sh ──────────────────
if [ "$CHECK_ONLY" = true ]; then
    bash "$SCRIPT_DIR/team-check.sh"
    exit $?
fi

echo -e "${CYAN}"
echo "  ⚔️  My Dev Team — Update"
echo "  ─────────────────────────────"
echo -e "${NC}"

# ── Verify we're in an installed project ─────────────────────────
if [ ! -d "$PROJECT_ROOT/team/agents" ] || [ ! -f "$PROJECT_ROOT/team/config.yaml" ]; then
    echo -e "${RED}ERROR: This doesn't look like a project with My Dev Team installed.${NC}"
    echo "Expected to find team/agents/ and team/config.yaml"
    exit 1
fi

# ── Resolve upstream source ──────────────────────────────────────
UPSTREAM_FILE="$PROJECT_ROOT/.team-upstream"

if [ -z "$UPSTREAM" ]; then
    if [ -f "$UPSTREAM_FILE" ]; then
        UPSTREAM=$(head -1 "$UPSTREAM_FILE" | sed 's/[[:space:]]*$//')
        echo -e "  Upstream: ${YELLOW}${UPSTREAM}${NC} ${DIM}(from .team-upstream)${NC}"
    else
        echo -e "${RED}ERROR: No upstream specified and no .team-upstream file found.${NC}"
        echo ""
        echo "Usage:"
        echo "  bash scripts/team-update.sh /path/to/MyAgents"
        echo "  bash scripts/team-update.sh https://github.com/user/MyAgents.git"
        echo ""
        echo "To save for future updates:"
        echo "  echo '/path/to/MyAgents' > .team-upstream"
        exit 1
    fi
else
    echo -e "  Upstream: ${YELLOW}${UPSTREAM}${NC}"
fi

# ── Get upstream into a local directory ──────────────────────────
CLEANUP_TEMP=false

if [ -d "$UPSTREAM" ]; then
    # Local directory
    UPSTREAM_DIR="$UPSTREAM"
    echo -e "  Source: ${GREEN}local directory${NC}"
elif [[ "$UPSTREAM" == http* ]] || [[ "$UPSTREAM" == git@* ]]; then
    # Git URL — clone to temp
    UPSTREAM_DIR=$(mktemp -d)
    CLEANUP_TEMP=true
    echo -e "  Source: ${GREEN}git repository${NC}"
    echo -e "  ${DIM}Cloning...${NC}"
    git clone --depth 1 --quiet "$UPSTREAM" "$UPSTREAM_DIR" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo -e "${RED}ERROR: Failed to clone upstream repository.${NC}"
        rm -rf "$UPSTREAM_DIR"
        exit 1
    fi
else
    echo -e "${RED}ERROR: Upstream '$UPSTREAM' is neither a directory nor a git URL.${NC}"
    exit 1
fi

# ── Verify upstream is valid ─────────────────────────────────────
if [ ! -f "$UPSTREAM_DIR/VERSION" ] || [ ! -d "$UPSTREAM_DIR/team/agents" ]; then
    echo -e "${RED}ERROR: Upstream doesn't look like a MyAgents template repo.${NC}"
    echo "Expected VERSION file and team/agents/ directory."
    [ "$CLEANUP_TEMP" = true ] && rm -rf "$UPSTREAM_DIR"
    exit 1
fi

# ── Version comparison ───────────────────────────────────────────
UPSTREAM_VERSION=$(head -1 "$UPSTREAM_DIR/VERSION" | sed 's/[[:space:]]*$//')
if [ -f "$PROJECT_ROOT/VERSION" ]; then
    CURRENT_VERSION=$(head -1 "$PROJECT_ROOT/VERSION" | sed 's/[[:space:]]*$//')
else
    CURRENT_VERSION="unknown"
fi

echo ""
echo -e "  Current version: ${YELLOW}${CURRENT_VERSION}${NC}"
echo -e "  Upstream version: ${GREEN}${UPSTREAM_VERSION}${NC}"

if [ "$CURRENT_VERSION" = "$UPSTREAM_VERSION" ]; then
    echo -e "\n  ${GREEN}Already up to date.${NC}"
    [ "$CLEANUP_TEMP" = true ] && rm -rf "$UPSTREAM_DIR"
    exit 0
fi

# ── Diff summary ─────────────────────────────────────────────────
echo ""
echo -e "${CYAN}  Changes detected:${NC}"

count_files() {
    local dir="$1"
    local upstream_dir="$2"
    local added=0
    local modified=0

    if [ -d "$upstream_dir" ]; then
        for f in "$upstream_dir"/*; do
            [ -f "$f" ] || continue
            local basename=$(basename "$f")
            local target="$dir/$basename"
            if [ ! -f "$target" ]; then
                added=$((added + 1))
            elif ! diff -q "$f" "$target" > /dev/null 2>&1; then
                modified=$((modified + 1))
            fi
        done
    fi
    echo "${added} new, ${modified} modified"
}

echo -e "    Agents:    $(count_files "$PROJECT_ROOT/team/agents" "$UPSTREAM_DIR/team/agents")"
echo -e "    Engine:    $(count_files "$PROJECT_ROOT/team/engine" "$UPSTREAM_DIR/team/engine")"
echo -e "    Standards: $(count_files "$PROJECT_ROOT/team/data" "$UPSTREAM_DIR/team/data")"
echo -e "    Commands:  $(count_files "$PROJECT_ROOT/.claude/commands/team" "$UPSTREAM_DIR/claude-commands/team" 2>/dev/null || count_files "$PROJECT_ROOT/claude-commands/team" "$UPSTREAM_DIR/claude-commands/team")"

# Count workflows recursively
WF_ADDED=0
WF_MODIFIED=0
if [ -d "$UPSTREAM_DIR/team/workflows" ]; then
    while IFS= read -r f; do
        rel="${f#$UPSTREAM_DIR/}"
        target="$PROJECT_ROOT/$rel"
        if [ ! -f "$target" ]; then
            WF_ADDED=$((WF_ADDED + 1))
        elif ! diff -q "$f" "$target" > /dev/null 2>&1; then
            WF_MODIFIED=$((WF_MODIFIED + 1))
        fi
    done < <(find "$UPSTREAM_DIR/team/workflows" -type f)
fi
echo -e "    Workflows: ${WF_ADDED} new, ${WF_MODIFIED} modified"

echo ""
echo -e "${BLUE}  Will preserve:${NC}"
echo -e "    ✓ team/config.yaml (your project configuration)"
echo -e "    ✓ team/_memory/ (agent memories and communications)"
echo -e "    ✓ team/manifest.yaml (your team customizations)"
echo -e "    ✓ *.customize.yaml (your agent customizations)"
echo -e "    ✓ output/ (all project artifacts)"
echo -e "    ✓ CLAUDE.md (your project rules)"
echo -e "    ✓ .claude/settings.local.json (your permissions)"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}  DRY RUN — no changes made.${NC}"
    [ "$CLEANUP_TEMP" = true ] && rm -rf "$UPSTREAM_DIR"
    exit 0
fi

# ── Confirm ──────────────────────────────────────────────────────
if [ "$FORCE" = false ]; then
    read -p "  Proceed with update? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "  ${YELLOW}Update cancelled.${NC}"
        [ "$CLEANUP_TEMP" = true ] && rm -rf "$UPSTREAM_DIR"
        exit 0
    fi
fi

echo ""
echo -e "${CYAN}  Updating...${NC}"

# ── Step 1: Backup project-specific files ────────────────────────
BACKUP_DIR=$(mktemp -d)
echo -e "  ${DIM}[1/7] Backing up project-specific files...${NC}"

cp "$PROJECT_ROOT/team/config.yaml" "$BACKUP_DIR/config.yaml"

if [ -d "$PROJECT_ROOT/team/_memory" ]; then
    cp -R "$PROJECT_ROOT/team/_memory" "$BACKUP_DIR/_memory"
fi

# Backup customize files
find "$PROJECT_ROOT/team/agents" -name "*.customize.yaml" -exec cp {} "$BACKUP_DIR/" \; 2>/dev/null || true

# Backup user-added agents (not in upstream)
if [ -f "$PROJECT_ROOT/team/agent-manifest.csv" ] && [ -f "$UPSTREAM_DIR/team/agent-manifest.csv" ]; then
    # Extract agent names from both manifests (first column, skip header)
    tail -n +2 "$PROJECT_ROOT/team/agent-manifest.csv" | cut -d',' -f1 | tr -d '"' | sort > "$BACKUP_DIR/local-agents.txt"
    tail -n +2 "$UPSTREAM_DIR/team/agent-manifest.csv" | cut -d',' -f1 | tr -d '"' | sort > "$BACKUP_DIR/upstream-agents.txt"

    # Find agents only in local (user-added)
    comm -23 "$BACKUP_DIR/local-agents.txt" "$BACKUP_DIR/upstream-agents.txt" > "$BACKUP_DIR/user-agents.txt"

    # Backup user-added agent files and their manifest rows
    while IFS= read -r agent_name; do
        [ -z "$agent_name" ] && continue
        if [ -f "$PROJECT_ROOT/team/agents/${agent_name}.md" ]; then
            cp "$PROJECT_ROOT/team/agents/${agent_name}.md" "$BACKUP_DIR/user-agent-${agent_name}.md"
        fi
        grep "\"${agent_name}\"" "$PROJECT_ROOT/team/agent-manifest.csv" >> "$BACKUP_DIR/user-manifest-rows.csv" 2>/dev/null || true
    done < "$BACKUP_DIR/user-agents.txt"
fi

# ── Step 2: Update core team files ───────────────────────────────
echo -e "  ${DIM}[2/7] Updating agents...${NC}"
cp "$UPSTREAM_DIR/team/agents/"*.md "$PROJECT_ROOT/team/agents/"

echo -e "  ${DIM}[3/7] Updating workflows...${NC}"
# Sync workflows — copy new and updated, don't delete removed ones
if [ -d "$UPSTREAM_DIR/team/workflows" ]; then
    rsync -a --ignore-existing "$UPSTREAM_DIR/team/workflows/" "$PROJECT_ROOT/team/workflows/" 2>/dev/null || \
    cp -R "$UPSTREAM_DIR/team/workflows/"* "$PROJECT_ROOT/team/workflows/"
fi

echo -e "  ${DIM}[4/7] Updating engine protocols...${NC}"
cp "$UPSTREAM_DIR/team/engine/"* "$PROJECT_ROOT/team/engine/" 2>/dev/null || true

echo -e "  ${DIM}[5/7] Updating data and standards...${NC}"
# Recursively copy data directory
rsync -a "$UPSTREAM_DIR/team/data/" "$PROJECT_ROOT/team/data/" 2>/dev/null || \
cp -R "$UPSTREAM_DIR/team/data/"* "$PROJECT_ROOT/team/data/"

# Update agent manifest
cp "$UPSTREAM_DIR/team/agent-manifest.csv" "$PROJECT_ROOT/team/agent-manifest.csv"

# ── Step 3: Restore project-specific files ───────────────────────
echo -e "  ${DIM}[6/7] Restoring project-specific files...${NC}"

cp "$BACKUP_DIR/config.yaml" "$PROJECT_ROOT/team/config.yaml"

if [ -d "$BACKUP_DIR/_memory" ]; then
    # Ensure _memory exists then restore contents
    mkdir -p "$PROJECT_ROOT/team/_memory"
    cp -R "$BACKUP_DIR/_memory/"* "$PROJECT_ROOT/team/_memory/" 2>/dev/null || true
fi

# Restore customize files
for f in "$BACKUP_DIR"/*.customize.yaml; do
    [ -f "$f" ] || continue
    cp "$f" "$PROJECT_ROOT/team/agents/"
done

# Restore user-added agents
if [ -f "$BACKUP_DIR/user-agents.txt" ]; then
    while IFS= read -r agent_name; do
        [ -z "$agent_name" ] && continue
        if [ -f "$BACKUP_DIR/user-agent-${agent_name}.md" ]; then
            cp "$BACKUP_DIR/user-agent-${agent_name}.md" "$PROJECT_ROOT/team/agents/${agent_name}.md"
        fi
    done < "$BACKUP_DIR/user-agents.txt"

    # Append user-added manifest rows
    if [ -f "$BACKUP_DIR/user-manifest-rows.csv" ]; then
        cat "$BACKUP_DIR/user-manifest-rows.csv" >> "$PROJECT_ROOT/team/agent-manifest.csv"
    fi
fi

# ── Step 4: Update slash commands ────────────────────────────────
COMMANDS_TARGET=""
if [ -d "$PROJECT_ROOT/.claude/commands/team" ]; then
    COMMANDS_TARGET="$PROJECT_ROOT/.claude/commands/team"
elif [ -d "$PROJECT_ROOT/claude-commands/team" ]; then
    COMMANDS_TARGET="$PROJECT_ROOT/claude-commands/team"
fi

if [ -n "$COMMANDS_TARGET" ] && [ -d "$UPSTREAM_DIR/claude-commands/team" ]; then
    cp "$UPSTREAM_DIR/claude-commands/team/"* "$COMMANDS_TARGET/"
fi

# ── Step 5: Update scripts ──────────────────────────────────────
if [ -d "$UPSTREAM_DIR/scripts/context" ]; then
    cp "$UPSTREAM_DIR/scripts/context/"*.py "$PROJECT_ROOT/scripts/context/" 2>/dev/null || true
fi

# Copy update and check scripts
if [ -f "$UPSTREAM_DIR/scripts/team-update.sh" ]; then
    cp "$UPSTREAM_DIR/scripts/team-update.sh" "$PROJECT_ROOT/scripts/team-update.sh"
    chmod +x "$PROJECT_ROOT/scripts/team-update.sh"
fi
if [ -f "$UPSTREAM_DIR/scripts/team-check.sh" ]; then
    cp "$UPSTREAM_DIR/scripts/team-check.sh" "$PROJECT_ROOT/scripts/team-check.sh"
    chmod +x "$PROJECT_ROOT/scripts/team-check.sh"
fi

# Copy update check hook
if [ -f "$UPSTREAM_DIR/.claude/hooks/check-for-updates.sh" ]; then
    mkdir -p "$PROJECT_ROOT/.claude/hooks"
    cp "$UPSTREAM_DIR/.claude/hooks/check-for-updates.sh" "$PROJECT_ROOT/.claude/hooks/check-for-updates.sh"
    chmod +x "$PROJECT_ROOT/.claude/hooks/check-for-updates.sh"
fi

# ── Step 6: Update version and manifest ──────────────────────────
echo -e "  ${DIM}[7/7] Updating version...${NC}"

# Update VERSION file
cp "$UPSTREAM_DIR/VERSION" "$PROJECT_ROOT/VERSION"

# Update manifest version and date only (preserve teams section)
UPDATE_DATE=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")
if command -v python3 &> /dev/null; then
    python3 -c "
import re
with open('$PROJECT_ROOT/team/manifest.yaml', 'r') as f:
    content = f.read()
content = re.sub(r'version: .*', 'version: $UPSTREAM_VERSION', content)
content = re.sub(r'lastUpdated: .*', 'lastUpdated: $UPDATE_DATE', content)
with open('$PROJECT_ROOT/team/manifest.yaml', 'w') as f:
    f.write(content)
"
else
    sed -i '' "s|version: .*|version: $UPSTREAM_VERSION|" "$PROJECT_ROOT/team/manifest.yaml" 2>/dev/null || true
    sed -i '' "s|lastUpdated: .*|lastUpdated: $UPDATE_DATE|" "$PROJECT_ROOT/team/manifest.yaml" 2>/dev/null || true
fi

# Store upstream for future updates
echo "$UPSTREAM" > "$PROJECT_ROOT/.team-upstream"

# Clear update-available marker
rm -f "$PROJECT_ROOT/.team-update-available"

# ── Step 7: Sync plugins ──────────────────────────────────────────
PLUGIN_SYNC="$PROJECT_ROOT/scripts/plugin-sync.sh"
if [ -f "$PLUGIN_SYNC" ] && [ -f "$PROJECT_ROOT/plugins/registry.json" ]; then
    echo -e "  ${DIM}[8/8] Syncing plugins...${NC}"
    bash "$PLUGIN_SYNC" 2>/dev/null || true
fi

# ── Cleanup ──────────────────────────────────────────────────────
rm -rf "$BACKUP_DIR"
[ "$CLEANUP_TEMP" = true ] && rm -rf "$UPSTREAM_DIR"

# ── Summary ──────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}  ═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ⚔️  Update complete: ${CURRENT_VERSION} → ${UPSTREAM_VERSION}${NC}"
echo -e "${GREEN}  ═══════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BLUE}Updated:${NC}"
echo -e "    • Agents, workflows, engine, data, standards"
echo -e "    • Slash commands, context scripts, plugins"
echo ""
echo -e "  ${BLUE}Preserved:${NC}"
echo -e "    • config.yaml, CLAUDE.md, settings"
echo -e "    • Agent memories, communications"
echo -e "    • Customize files, user-added agents"
echo -e "    • All output artifacts"
echo ""
AGENT_COUNT=$(tail -n +2 "$PROJECT_ROOT/team/agent-manifest.csv" | wc -l | tr -d ' ')
PLUGIN_COUNT=$(jq '.plugins | length' "$PROJECT_ROOT/plugins/registry.json" 2>/dev/null || echo "0")
echo -e "  Agents: ${YELLOW}${AGENT_COUNT}${NC}  |  Plugins: ${YELLOW}${PLUGIN_COUNT}${NC}"
echo ""
echo -e "  ${DIM}Run /team:maestro to activate with the latest changes.${NC}"
echo ""
