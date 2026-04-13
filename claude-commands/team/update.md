---
name: 'update'
description: 'Pull latest agent changes from upstream template'
---

## Team Update

Check for and apply updates from the upstream My Dev Team template repository.

<update-protocol CRITICAL="TRUE">

### Step 1: Locate upstream

Check if `.team-upstream` file exists in the project root.

- If it exists, read the upstream path/URL from it.
- If it does NOT exist, ask the user:
  "Where is your My Dev Team template? Provide either:
  - A local path (e.g., /path/to/MyAgents)
  - A git URL (e.g., https://github.com/user/MyAgents.git)"

### Step 2: Run the update script

Execute: `bash scripts/team-update.sh`

If `scripts/team-update.sh` does not exist, inform the user:
"The update script is not installed. Copy it from the template repo:
`cp /path/to/MyAgents/scripts/team-update.sh scripts/team-update.sh`"

### Step 3: Report results

After the script completes:
1. Show what was updated (new agents, modified workflows, protocol changes)
2. Show what was preserved (config, memories, customizations)
3. Suggest running `/team:maestro` to activate with the latest changes
4. If Maestro is already active, suggest `[LR]` to re-scan with updated capabilities

</update-protocol>
