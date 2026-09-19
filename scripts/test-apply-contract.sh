#!/usr/bin/env bash
# Tests for scripts/apply-contract.sh using fixture agent files in a temp dir.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPLY="$SCRIPT_DIR/apply-contract.sh"
PASS=0
FAIL=0
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

check() {  # desc, condition-exit-code
  if [ "$2" -eq 0 ]; then echo "  PASS: $1"; PASS=$((PASS+1)); else echo "  FAIL: $1"; FAIL=$((FAIL+1)); fi
}

# Fixture 1: worker, "variant A" shape (emoji, DO NOT PROCEED line present)
mkdir -p "$TMP/agents"
cat > "$TMP/agents/dev.md" << 'EOF'
---
name: "dev"
description: "Developer Agent"
---

You must fully embody this agent's persona.

```xml
<agent id="dev.agent.yaml" name="Amelia" title="Developer Agent" icon="💻">
<activation critical="MANDATORY">
      <step n="1">Load persona from this current agent file (already in context)</step>
      <step n="2">🚨 IMMEDIATE ACTION REQUIRED - BEFORE ANY OUTPUT:
          - Load and read {project-root}/team/config.yaml NOW
          - DO NOT PROCEED to step 3 until config is successfully loaded and variables stored
      </step>
      <step n="3">Remember: user's name is {user_name}</step>
    <rules>
      <r>ALWAYS communicate in {communication_language} UNLESS contradicted by communication_style.</r>
    </rules>
</activation>
</agent>
```
EOF

# Fixture 2: advisor, "variant C" shape (no emoji, no DO NOT PROCEED line, 8-space <r> indent)
cat > "$TMP/agents/healthcare-expert.md" << 'EOF'
---
name: "healthcare-expert"
description: "Healthcare Domain Expert Agent"
---

You must fully embody this agent's persona.

```xml
<agent id="healthcare-expert.agent.yaml" name="Dr. Vita" title="Healthcare AI Governance Advisor" icon="">
<activation critical="MANDATORY">
      <step n="1">Load persona from this current agent file (already in context)</step>
      <step n="2">IMMEDIATE ACTION REQUIRED - BEFORE ANY OUTPUT:
          - Load and read {project-root}/team/config.yaml NOW
      </step>
      <step n="3">Remember: user's name is {user_name}</step>
    <rules>
        <r>ALWAYS communicate in {communication_language}</r>
    </rules>
</activation>
</agent>
```
EOF

# Fixture 3: skipped file
echo "# routing table" > "$TMP/agents/oracle-dispatch-map.md"

echo "=== apply-contract tests ==="

# --check must fail before apply
rc=0; AGENTS_DIR="$TMP/agents" bash "$APPLY" --check > /dev/null 2>&1 || rc=$?
check "--check fails on unwired agents" "$([ "$rc" -eq 1 ]; echo $?)"

# apply
AGENTS_DIR="$TMP/agents" bash "$APPLY" > /dev/null
check "worker gets role: worker" "$(grep -q '^role: "worker"$' "$TMP/agents/dev.md"; echo $?)"
check "advisor gets role: advisor" "$(grep -q '^role: "advisor"$' "$TMP/agents/healthcare-expert.md"; echo $?)"
check "advisor gets tools allowlist" "$(grep -q '^tools: Read, Grep, Glob, WebFetch, WebSearch$' "$TMP/agents/healthcare-expert.md"; echo $?)"
check "worker gets no tools line" "$(! grep -q '^tools:' "$TMP/agents/dev.md"; echo $?)"
check "role line sits inside frontmatter" "$([ "$(sed -n '4p' "$TMP/agents/dev.md")" = 'role: "worker"' ]; echo $?)"
check "step 2a inserted after step 2 (variant A)" "$(awk '/<step n="2">/{s=1} s&&/<\/step>/{getline; if ($0 ~ /<step n="2a">/) ok=1; exit} END{exit !ok}' "$TMP/agents/dev.md"; echo $?)"
check "step 2a inserted after step 2 (variant C)" "$(awk '/<step n="2">/{s=1} s&&/<\/step>/{getline; if ($0 ~ /<step n="2a">/) ok=1; exit} END{exit !ok}' "$TMP/agents/healthcare-expert.md"; echo $?)"
check "step 2a references the contract path" "$(grep -q 'team/engine/authority-contract.xml' "$TMP/agents/dev.md"; echo $?)"
check "AUTHORITY rule is first <r> after <rules>" "$(awk '/<rules>/{getline; if ($0 ~ /<r>AUTHORITY:/) ok=1; exit} END{exit !ok}' "$TMP/agents/dev.md"; echo $?)"
check "step 3 still present and unrenumbered" "$(grep -q '<step n="3">' "$TMP/agents/dev.md"; echo $?)"
check "skipped file untouched" "$([ "$(cat "$TMP/agents/oracle-dispatch-map.md")" = "# routing table" ]; echo $?)"

# --check passes after apply
rc=0; AGENTS_DIR="$TMP/agents" bash "$APPLY" --check > /dev/null 2>&1 || rc=$?
check "--check passes on wired agents" "$([ "$rc" -eq 0 ]; echo $?)"

# idempotent
cp "$TMP/agents/dev.md" "$TMP/dev.before"
AGENTS_DIR="$TMP/agents" bash "$APPLY" > /dev/null
check "second apply changes nothing" "$(cmp -s "$TMP/agents/dev.md" "$TMP/dev.before"; echo $?)"
check "exactly one step 2a after two applies" "$([ "$(grep -c '<step n="2a">' "$TMP/agents/dev.md")" -eq 1 ]; echo $?)"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
