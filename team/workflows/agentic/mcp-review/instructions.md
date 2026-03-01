# MCP Server Integration Review

Review Model Context Protocol (MCP) server configuration, tool definitions, and integration patterns.

## Step 1: Locate MCP Configuration

- Search for MCP configuration files: `.mcp.json`, `mcp.json`, `claude_desktop_config.json`, or MCP settings in `package.json`.
- Check the project root `/` and `packages/frontend/` for any MCP config files.
- Identify all registered MCP servers and their transport types (stdio, SSE, HTTP).
- Document connection parameters, environment variables, and authentication.
- `[INFO]` Record the config file path found -- all subsequent checks reference this source of truth.

---

## Step 2: Audit Tool Definitions

- For each MCP server, catalog the tools it exposes: name, description, input schema, output format.
- Evaluate tool descriptions for clarity -- LLMs rely on descriptions to select the right tool.
- Check that input schemas use proper JSON Schema with required fields, types, and descriptions.
- Flag tools with overly broad descriptions or missing parameter constraints.

**Pass/fail criteria per tool:**
- PASS: Clear description, complete JSON Schema with required/type/description on all params.
- WARNING: Description is vague or schema is missing optional field descriptions.
- FAIL: No description, no schema, or schema allows unconstrained arbitrary input.

---

## Step 3: Review Resource & Prompt Definitions

- Catalog MCP resources (if any): URI patterns, content types, descriptions.
- Catalog MCP prompt templates (if any): name, arguments, template content.
- Verify resources provide useful context and prompts guide the LLM effectively.
- `[INFO]` If no resources or prompts are defined, note this as an improvement opportunity -- not a failure.

---

## Step 4: Evaluate Integration in Agents

- Read all files under `backend/app/agents/` to find where MCP tools are invoked.
- Check `backend/app/services/` for service layers that wrap or orchestrate MCP tool calls.
- Verify agents reference tools by their correct MCP names (exact string match).
- Verify error handling when MCP servers are unavailable or return errors.
- Confirm timeout configuration for long-running tool calls in `backend/app/core/config.py`.
- `[WARNING]` Flag any agent that calls MCP tools without a try/except or timeout guard.

**Decision outcomes:**
- PASS: All tool references match registered names, error handling present, timeouts configured.
- FAIL: Mismatched tool names, missing error handling, or no timeout on blocking calls.

---

## Step 5: Security Review

- `[CRITICAL]` Verify MCP servers do not expose sensitive operations without authorization.
- Check that file system access tools are scoped to appropriate directories (not `/` or home).
- Confirm secrets (API keys, tokens) are passed via environment variables, not hard-coded in config files.
- Review `.mcp.json` for any inline credentials or tokens.
- Flag any tools that can execute arbitrary code without sandboxing.
- `[CRITICAL]` In a multi-tenant SaaS context, verify no MCP tool can access data across tenant boundaries.

**Pass/fail criteria:**
- PASS: No exposed secrets, scoped file access, tenant-safe tool definitions.
- FAIL: Hard-coded secrets, unscoped file access, or cross-tenant data exposure risk.

---

## Step 6: Performance & Reliability

- Check for connection pooling or reconnection logic for MCP servers.
- Verify that tool calls have appropriate timeout limits (check `backend/app/core/config.py`).
- Identify tools that could be cached to reduce redundant calls.
- Review whether MCP server health checks exist (startup probes, periodic pings).
- `[WARNING]` If any MCP server has no reconnection logic, flag as a reliability risk.

---

## Step 7: Generate Report

Write the review report to `{output_folder}/agentic-expert/mcp-review.md` containing:

- Summary table: Server | Transport | Tool Count | Status (PASS/WARNING/FAIL).
- Per-tool quality scorecard: description quality, schema completeness, error handling.
- Security findings with severity markers (`[CRITICAL]`, `[WARNING]`, `[INFO]`).
- Performance observations and caching recommendations.
- Recommended improvements with specific file paths and code changes.

---

## Step 8: Present Results

- Display the summary table and per-tool scorecard to the user.
- Highlight all `[CRITICAL]` security findings first -- these block approval.
- Walk through `[WARNING]` items and recommend remediation priority.
- Provide a final verdict: APPROVED (no critical issues), CONDITIONAL (warnings to address), or BLOCKED (critical issues found).
- Offer to generate fix patches for any identified issues if the user requests it.
