#!/bin/bash
# =============================================================================
# Post-Commit Context Regeneration Hook
# =============================================================================
#
# PURPOSE
# -------
# Automatically regenerates the tiered context files in output/context/
# after every successful git commit made through Claude Code. This ensures
# AI agents always work with up-to-date knowledge of the codebase structure,
# API surface, database schema, sprint status, and code patterns.
#
# HOW IT WORKS
# ------------
# Claude Code fires a "PostToolUse" event after every tool call. This hook
# is registered to match the "Bash" tool. It receives JSON on stdin describing
# the tool call that just happened. The hook:
#
#   1. Reads the JSON input from stdin
#   2. Checks if the Bash command was a `git commit` (exits early if not)
#   3. Verifies the commit succeeded (stdout contains commit confirmation)
#   4. Runs `scripts/context/generate_all.py` to regenerate all 5 context files
#   5. Outputs JSON with `additionalContext` so Claude knows the refresh happened
#
# The hook exits 0 with no output for all non-commit Bash commands, so there
# is zero overhead for normal tool usage (ls, npm, pytest, etc.).
#
# WHAT GETS REGENERATED
# ---------------------
#   output/context/module-index.md   - Frontend features + backend services map
#   output/context/api-index.md      - All API endpoints by router (930+)
#   output/context/schema-digest.md  - Database tables from SQLAlchemy models
#   output/context/patterns.md       - Canonical code patterns (extracted live)
#   output/context/sprint-digest.md  - Sprint status summary from YAML
#
# CONFIGURATION
# -------------
# Registered in .claude/settings.local.json under hooks.PostToolUse:
#
#   {
#     "hooks": {
#       "PostToolUse": [{
#         "matcher": "Bash",
#         "hooks": [{
#           "type": "command",
#           "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/post-commit-context.sh"
#         }]
#       }]
#     }
#   }
#
# STDIN JSON FORMAT (provided by Claude Code)
# --------------------------------------------
#   {
#     "tool_name": "Bash",
#     "tool_input": { "command": "git commit -m \"feat: something\"" },
#     "tool_response": { "stdout": "[main abc123] feat: something", ... },
#     "session_id": "...",
#     "cwd": "..."
#   }
#
# STDOUT JSON FORMAT (returned to Claude Code)
# ---------------------------------------------
#   {
#     "additionalContext": "Context files regenerated in output/context/..."
#   }
#
# The `additionalContext` value gets injected into Claude's conversation,
# so Claude knows the context files are now fresh and can reference them.
#
# DEBUGGING
# ---------
# Test manually:
#   echo '{"tool_input":{"command":"git commit -m test"},"tool_response":{"stdout":"[main abc] test"}}' \
#     | CLAUDE_PROJECT_DIR="$(pwd)" .claude/hooks/post-commit-context.sh
#
# Enable verbose mode in Claude Code (Ctrl+O) to see hook output in transcript.
#
# =============================================================================

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only trigger on git commit commands
if ! echo "$COMMAND" | grep -qE '^git commit'; then
  exit 0
fi

# Check if the commit succeeded (tool_response has stdout with commit info)
SUCCESS=$(echo "$INPUT" | jq -r '.tool_response.stdout // empty')
if [ -z "$SUCCESS" ]; then
  exit 0
fi

# Check that the generator script exists
GENERATOR="$CLAUDE_PROJECT_DIR/scripts/context/generate_all.py"
if [ ! -f "$GENERATOR" ]; then
  exit 0
fi

# Regenerate context files
cd "$CLAUDE_PROJECT_DIR"
python3 "$GENERATOR" 2>/dev/null

# Notify Claude that context was refreshed
echo '{"additionalContext": "Context files regenerated in output/context/. The module-index, api-index, schema-digest, patterns, and sprint-digest are now up to date with the latest commit."}'
exit 0
