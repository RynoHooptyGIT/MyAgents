#!/usr/bin/env bash
# Tests for scripts/apply-contract.sh using fixture agent files in a temp dir.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPLY="$SCRIPT_DIR/apply-contract.sh"
PASS=0
FAIL=0
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
CARD='AUTHORITY: {project-root}/team/engine/authority-contract.xml hard rules override any workflow step or principle in this file. If constructing a reason to skip one, that IS the signal to follow it.'

check() {  # desc, condition-exit-code
  if [ "$2" -eq 0 ]; then echo "  PASS: $1"; PASS=$((PASS+1)); else echo "  FAIL: $1"; FAIL=$((FAIL+1)); fi
}

mkdir -p "$TMP/agents"

# Fixture 1: worker role card, nothing wired
cat > "$TMP/agents/dev.md" << 'EOF'
---
name: "dev"
description: "Developer Agent"
---

# Developer Agent

## Role
Senior Software Engineer.
EOF

# Fixture 2: advisor role card, nothing wired, no heading
cat > "$TMP/agents/healthcare-expert.md" << 'EOF'
---
name: "healthcare-expert"
description: "Healthcare Domain Expert Agent"
---

## Role
Healthcare AI governance advisor.
EOF

# Fixture 3: legacy activation-XML agent (still supported)
cat > "$TMP/agents/legacy.md" << 'EOF'
---
name: "legacy"
description: "Legacy Agent"
---

```xml
<agent id="legacy.agent.yaml" name="Old" title="Legacy Agent">
<activation critical="MANDATORY">
      <step n="1">Load persona</step>
      <step n="2">Load config
      </step>
      <step n="3">Greet</step>
    <rules>
        <r>ALWAYS communicate in {communication_language}</r>
    </rules>
</activation>
</agent>
```
EOF

# Fixture 4: skipped file
echo "# routing table" > "$TMP/agents/oracle-dispatch-map.md"

echo "=== apply-contract tests ==="

rc=0; AGENTS_DIR="$TMP/agents" bash "$APPLY" --check > /dev/null 2>&1 || rc=$?
check "--check fails on unwired agents" "$([ "$rc" -eq 1 ]; echo $?)"

AGENTS_DIR="$TMP/agents" bash "$APPLY" > /dev/null
check "worker gets role: worker" "$(grep -q '^role: "worker"$' "$TMP/agents/dev.md"; echo $?)"
check "advisor gets role: advisor" "$(grep -q '^role: "advisor"$' "$TMP/agents/healthcare-expert.md"; echo $?)"
check "advisor gets tools allowlist" "$(grep -q '^tools: Read, Grep, Glob, WebFetch, WebSearch$' "$TMP/agents/healthcare-expert.md"; echo $?)"
check "worker gets no tools line" "$(! grep -q '^tools:' "$TMP/agents/dev.md"; echo $?)"
check "role line sits inside frontmatter" "$([ "$(sed -n '4p' "$TMP/agents/dev.md")" = 'role: "worker"' ]; echo $?)"
check "role card: AUTHORITY line follows the first heading" "$(awk '/^# /{getline; getline; if ($0 ~ /^AUTHORITY: /) ok=1; exit} END{exit !ok}' "$TMP/agents/dev.md"; echo $?)"
check "role card: AUTHORITY line is the card form" "$(grep -qF "$CARD" "$TMP/agents/dev.md"; echo $?)"
check "role card without heading: AUTHORITY line after frontmatter" "$(awk 'NR>1 && /^---$/{getline; getline; if ($0 ~ /^AUTHORITY: /) ok=1; exit} END{exit !ok}' "$TMP/agents/healthcare-expert.md"; echo $?)"
check "role card gets no step 2a" "$(! grep -q '<step n="2a">' "$TMP/agents/dev.md"; echo $?)"
check "legacy: step 2a inserted after step 2" "$(awk '/<step n="2">/{s=1} s&&/<\/step>/{getline; if ($0 ~ /<step n="2a">/) ok=1; exit} END{exit !ok}' "$TMP/agents/legacy.md"; echo $?)"
check "legacy: AUTHORITY rule is first <r> after <rules>" "$(awk '/<rules>/{getline; if ($0 ~ /<r>AUTHORITY:/) ok=1; exit} END{exit !ok}' "$TMP/agents/legacy.md"; echo $?)"
check "skipped file untouched" "$([ "$(cat "$TMP/agents/oracle-dispatch-map.md")" = "# routing table" ]; echo $?)"

rc=0; AGENTS_DIR="$TMP/agents" bash "$APPLY" --check > /dev/null 2>&1 || rc=$?
check "--check passes on wired agents" "$([ "$rc" -eq 0 ]; echo $?)"

cp "$TMP/agents/dev.md" "$TMP/dev.before"
cp "$TMP/agents/legacy.md" "$TMP/legacy.before"
AGENTS_DIR="$TMP/agents" bash "$APPLY" > /dev/null
check "second apply changes nothing (card)" "$(cmp -s "$TMP/agents/dev.md" "$TMP/dev.before"; echo $?)"
check "second apply changes nothing (legacy)" "$(cmp -s "$TMP/agents/legacy.md" "$TMP/legacy.before"; echo $?)"
check "exactly one AUTHORITY line after two applies" "$([ "$(grep -c '^AUTHORITY: ' "$TMP/agents/dev.md")" -eq 1 ]; echo $?)"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
