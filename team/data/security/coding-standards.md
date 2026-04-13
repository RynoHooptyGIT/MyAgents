# Security Coding Standards

> Referenced by: team/engine/security-gate.xml
> Audience: ALL agents — not just Shield (Security Auditor)
> Enforcement: Every code review, every implementation, every design decision

---

## Core Principles

1. **Defense in Depth** — Never rely on a single security control
2. **Least Privilege** — Grant minimum access required for the task
3. **Secure by Default** — Insecure options require explicit opt-in, never opt-out
4. **Fail Secure** — When something breaks, deny access rather than grant it
5. **Never Trust Input** — All external data is hostile until validated

---

## OWASP Top 10 — Mandatory Awareness

Every agent writing or reviewing code MUST check against these:

### A01: Broken Access Control
- Enforce server-side access control, never client-side only
- Deny by default — explicitly grant, never implicitly allow
- Row-Level Security (RLS) on every database table
- Validate that users can only access their own tenant's data
- Log and alert on access control failures

### A02: Cryptographic Failures
- HTTPS everywhere — no exceptions
- Never roll your own crypto
- Use bcrypt/argon2 for passwords (never MD5/SHA1)
- Encrypt PII at rest
- Rotate secrets regularly

### A03: Injection
- Parameterized queries ALWAYS — never string concatenation for SQL
- Use ORM query builders when available
- Escape output context-appropriately (HTML, JS, URL, CSS, SQL)
- No shell command construction from user input
- Never use dynamic code execution functions with untrusted input

### A04: Insecure Design
- Threat model during architecture phase
- Abuse case scenarios in user stories
- Rate limiting on all authentication endpoints
- Account lockout after failed attempts
- CAPTCHA on public-facing forms

### A05: Security Misconfiguration
- No default credentials
- Remove debug endpoints before production
- Disable directory listing
- Custom error pages (no stack traces)
- Security headers: CSP, HSTS, X-Frame-Options, X-Content-Type-Options

### A06: Vulnerable Components
- Track all dependencies and their versions
- Check for CVEs before adding new packages
- Automated dependency scanning in CI
- Pin dependency versions
- Review transitive dependencies

### A07: Auth Failures
- Multi-factor authentication for admin functions
- Session tokens must be invalidated on logout
- Session timeout after inactivity
- Secure session storage (httpOnly, secure, sameSite cookies)
- Rate limit login attempts

### A08: Data Integrity Failures
- Verify software update integrity (checksums, signatures)
- CI/CD pipeline security (no unauthorized modifications)
- Signed commits where possible
- Code review before merge — no self-merges to main

### A09: Logging & Monitoring
- Log all authentication events (success and failure)
- Log all access control failures
- Log all input validation failures
- NEVER log secrets, passwords, tokens, or full PII
- Structured logging with correlation IDs
- Alerting on anomalous patterns

### A10: Server-Side Request Forgery (SSRF)
- Validate and sanitize all URLs from user input
- Deny requests to internal networks
- Use allowlists for external service URLs
- Don't expose raw server responses to users

---

## Language-Specific Standards

### TypeScript/JavaScript
- Enable strict mode in tsconfig
- Use `===` not `==`
- Sanitize HTML output (DOMPurify or equivalent)
- Use Content Security Policy headers
- No dynamic code execution with user data (no Function constructor, no setTimeout with strings)
- No innerHTML with user data — use textContent or sanitized HTML
- Use `crypto.randomUUID()` not `Math.random()` for IDs

### Python
- Use parameterized queries with SQLAlchemy or psycopg2
- Never deserialize untrusted data with unsafe serialization libraries — use JSON instead
- Use `secrets` module for token generation
- Enable Django/Flask security middleware
- Type hints for security-critical functions
- No dynamic code execution on untrusted input

### SQL
- RLS policies on every table
- No `SECURITY DEFINER` without explicit justification
- Parameterized queries only
- Audit triggers on sensitive tables
- Column-level encryption for PII

### Shell/Bash
- Quote all variables: `"$var"` not `$var`
- Use `set -euo pipefail`
- No user input in command construction
- Validate inputs before use
- Use full paths for commands in hooks

---

## Secrets Management

| DO | DON'T |
|----|-------|
| Use environment variables | Hardcode secrets in code |
| Use .env files (gitignored) | Commit .env files |
| Use secret managers (Vault, AWS SSM) | Store secrets in config files |
| Rotate secrets regularly | Use the same secret everywhere |
| Use different secrets per environment | Share prod secrets with dev |

---

## Security Review Checklist for Code Review

Before approving ANY code review, verify:

- [ ] No hardcoded secrets, API keys, or credentials
- [ ] All user input is validated and sanitized
- [ ] SQL queries are parameterized
- [ ] Error messages don't expose internals
- [ ] Authentication checks are present where needed
- [ ] Authorization checks enforce proper scoping
- [ ] Sensitive data is not logged
- [ ] New dependencies have no known CVEs
- [ ] HTTPS is used for all external calls
- [ ] Rate limiting is considered for new endpoints
