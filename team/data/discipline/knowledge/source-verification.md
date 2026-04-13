# Source Verification Discipline

## Iron Law

**Confidence is not evidence. Verify every framework decision against official documentation.**

## Principle

AI training data goes stale. Framework APIs change between versions. What an agent "knows" may be wrong. Every framework, library, or external tool decision must be grounded in official documentation — not training-data memory. An agent that confidently uses a deprecated API is worse than one that admits uncertainty, because the confident agent's bugs look intentional.

## Source Priority Hierarchy

1. **Official documentation** — framework docs, API references, language specs → HIGHEST authority
2. **Official blog posts and changelogs** — release notes, migration guides
3. **Web standards** — MDN, W3C specs, IETF RFCs
4. **Verified community resources** — Stack Overflow answers with evidence and version context
5. **Training data memory** — LOWEST priority, treat as unverified hypothesis

## Red Flags

- "I'm confident this is the correct API" — confidence is not evidence
- "This is how React/Next/Django/etc. works" — which version? Verify.
- "I don't need to check the docs for this" — the docs are the authority, not your training data
- "The API hasn't changed" — APIs change constantly. Check the version.
- "This is a well-known pattern" — well-known patterns change between major versions
- "I just used this API successfully" — in a different project, with a potentially different version
- "Everyone uses it this way" — popularity is not correctness. Check the docs.

## Rationalization Table

| Excuse | Reality |
|--------|---------|
| "I'm sure this is right" | Your training data is months old. Check. |
| "Checking docs would slow me down" | Debugging hallucinated APIs slows you down 10x more. |
| "This is basic framework usage" | Basic usage changes between major versions. Verify. |
| "I just used this API successfully" | Different project, potentially different version. Check. |
| "The user didn't ask me to verify" | Verification is implicit in writing correct code. |
| "The docs are hard to find" | Use Context7 MCP or web search. No excuse. |
| "This pattern is framework-agnostic" | Implementation details are always framework-specific. Verify. |

## Enforcement Protocol

1. **Detect stack and versions**: Read package.json, requirements.txt, Cargo.toml, go.mod, etc. Note exact versions.
2. **For any framework API call**: Verify against official docs for the detected version. Cite the source.
3. **Flag unverified code**: Any framework usage not verified against docs gets an `[UNVERIFIED]` comment.
4. **When docs conflict with existing code**: Surface the conflict. The existing code may be using a deprecated pattern, or the docs may describe a newer version. Don't silently resolve — let the user decide.
5. **Version-sensitive patterns**: When a pattern's behavior varies by version, note the version constraint in a comment.

## Verification Methods

- **Context7 MCP**: Use `resolve-library-id` then `query-docs` for framework documentation
- **Official docs sites**: Reference the canonical URL
- **Package version check**: `npm list <package>`, `pip show <package>`, etc.
- **Changelog review**: Check CHANGELOG.md or release notes for breaking changes

## Hard Gate

```
CHECK-SEQUENCE:
  1. Stack and versions detected? → If not, read package manifest first
  2. Framework API verified against docs? → If not, verify or flag [UNVERIFIED]
  3. Version-sensitive pattern? → If yes, note version constraint in comment
  4. Docs conflict with existing code? → If yes, surface conflict, don't silently resolve

ON-VIOLATION (unverified framework API in production code):
  - Flag with [UNVERIFIED] comment immediately
  - Attempt verification via Context7 or official docs
  - If verification fails, surface to user with: "I used this API based on training data but could not verify it against docs for version X.Y.Z"
  - NO EXCEPTIONS
```
