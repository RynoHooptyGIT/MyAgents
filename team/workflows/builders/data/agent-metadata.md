# Agent Metadata Properties

Core identification and classification properties for all agents.

---

## Property Reference

| Property     | Purpose                   | Format                                         |
| ------------ | ------------------------- | ---------------------------------------------- |
| `id`         | Compiled output path      | `team/agents/{agent-name}/{agent-name}.md`    |
| `name`       | Persona's name            | "First Last" or "Name Title"                   |
| `title`      | Professional role         | "Code Review Specialist"                       |
| `icon`       | Visual identifier         | Single emoji only                              |
| `module`     | Team/ecosystem membership | `stand-alone`, `bmm`, `cis`, `bmgd`, or custom |
| `hasSidecar` | Sidecar folder exists     | `true` or `false` (Expert = true)              |

---

## id Property

The compiled output path after build.

**Format:** `team/agents/{agent-name}/{agent-name}.md`

**Examples:**
```yaml
id: team/agents/commit-poet/commit-poet.md
id: team/agents/journal-keeper/journal-keeper.md
id: team/agents/security-engineer/security-engineer.md
```

**Note:** The `id` is a unique identifier for potential future lookup if many compiled agents are merged into a single file. Conventionally matches the agent's filename pattern.

---

## name Property

The persona's identity - what the agent is called.

**Format:** Human name or descriptive name

```yaml
# ✅ CORRECT
name: 'Inkwell Von Comitizen' # peron name of commit-author title agent
name: 'Dr. Demento'  # person name for a joke writer agent
name: 'Clarity' # person name for a guided thought coach agent

# ❌ WRONG
name: 'commit-poet'  # That's the filename
name: 'Code Review Specialist'  # That's the title
```

---

## title Property

Professional role identifier.

**Format:** Professional title or role name

**Important:** The `title` determines the agent's filename:
- `title: 'Commit Message Artisan'` → `commit-message-artisan.agent.yaml`
- `title: 'Strategic Business Analyst'` → `strategic-business-analyst.agent.yaml`
- `title: 'Code Review Specialist'` → `code-review-specialist.agent.yaml`

The `id` and filename are derived from the `title` (kebab-cased).

**Difference from role:** `title` is the short identifier (filename), `role` is 1-2 sentences expanding on what the agent does.

```yaml
# ✅ CORRECT
title: 'Commit Message Artisan'
title: 'Strategic Business Analyst'
title: 'Code Review Specialist'

# ❌ WRONG
title: 'Inkwell Von Comitizen'  # That's the name
title: 'Writes git commits'  # Full sentence - not an identifying functional title
```

---

## icon Property

Single emoji representing the agent's personality/function.

**Format:** Exactly one emoji

```yaml
# ✅ CORRECT
icon: '🔧'
icon: '🧙‍♂️'
icon: '📜'

# ❌ WRONG
icon: '🔧📜'  # Multiple emojis
icon: 'wrench'  # Text, not emoji
icon: ''  # Empty
```

---

## module Property

Which module or ecosystem this agent belongs to.

**Valid Values:**

| Value         | Meaning                                 |
| ------------- | --------------------------------------- |
| `stand-alone` | Independent agent, not part of a module |
| `bmm`         | Business Management Module              |
| `cis`         | Continuous Innovation System            |
| `bmgd`        | BMAD Game Development                   |
| `{custom}`    | Any custom module code                  |

```yaml
# ✅ CORRECT
module: stand-alone
module: bmm
module: cis

# ❌ WRONG
module: standalone  # Missing hyphen
module: 'BMM'  # Uppercase
```

---

## hasSidecar Property

Whether this agent has a sidecar folder with additional files.

**Format:** Boolean (`true` or `false`)

| Agent Type | hasSidecar           |
| ---------- | -------------------- |
| Simple     | `false`              |
| Expert     | `true`               |
| Module     | depends on structure |

```yaml
# Simple Agent
hasSidecar: false

# Expert Agent
hasSidecar: true
```

**Note:** If `hasSidecar: true`, the compiler expects a `{agent-name}-sidecar/` folder.

---

## Name Confusion Checklist

Use this to avoid mixing up the "name" properties:

| Question                   | Answer                                                                               |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| What's the file called?    | Derived from `title`: `"Commit Message Artisan"` → `commit-message-artisan.agent.yaml` |
| What's the persona called? | `name` - "Inkwell Von Comitizen" (who the agent is)                                  |
| What's their job title?    | `title` - "Commit Message Artisan" (determines filename)                             |
| What do they do?           | `role` - 1-2 sentences expanding on the title                                       |
| What's the unique key?     | `id` - `team/agents/commit-message-artisan/commit-message-artisan.md` (future lookup) |

---

## Common Issues

### Issue: name = title

**Wrong:**
```yaml
name: 'Commit Message Artisan'
title: 'Commit Message Artisan'
```

**Fix:**
```yaml
name: 'Inkwell Von Comitizen'
title: 'Commit Message Artisan'
```

### Issue: id path mismatch

**Wrong:** Agent file is `my-agent.agent.yaml` but:
```yaml
id: team/agents/different-agent/different-agent.md
```

**Fix:** The `id` must match the filename:
```yaml
id: team/agents/my-agent/my-agent.md
```

### Issue: Wrong module format

**Wrong:**
```yaml
module: Standalone
module: STAND_ALONE
```

**Fix:**
```yaml
module: stand-alone  # lowercase, hyphenated
```
