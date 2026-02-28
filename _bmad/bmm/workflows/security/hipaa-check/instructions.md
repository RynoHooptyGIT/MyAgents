# HIPAA Security Rule - Technical Safeguards Check

## Purpose
Evaluate the application against HIPAA Security Rule technical safeguard requirements (45 CFR 164.312) to identify compliance gaps relevant to a SaaS platform managing AI tool data in healthcare contexts.

---

## Step 1: Access Control - 164.312(a)(1)
**Standard**: Implement technical policies and procedures to allow access only to authorized persons.

- [CRITICAL] **164.312(a)(2)(i) Unique User Identification (R)**: Verify each user has a unique identifier in `backend/app/models/user.py`. Check unique constraints on email/username columns.
- [WARNING] **164.312(a)(2)(ii) Emergency Access Procedure (R)**: Check for break-glass or emergency access mechanisms in `backend/app/routers/auth.py` and their audit trails.
- [WARNING] **164.312(a)(2)(iii) Automatic Logoff (A)**: Verify session timeout configuration. Check JWT expiration in `backend/app/core/config.py` and idle session handling in `packages/frontend/src/features/auth/hooks/useAuth.ts`.
- [CRITICAL] **164.312(a)(2)(iv) Encryption and Decryption (A)**: Verify ePHI is encrypted at rest. Check database encryption settings and field-level encryption for sensitive data in `backend/app/models/*.py`.
- **Pass**: Unique IDs enforced; sessions expire; encryption at rest active. **Fail**: Missing unique constraints, no timeout, or plaintext sensitive data.

---

## Step 2: Audit Controls - 164.312(b)
**Standard**: Implement mechanisms to record and examine activity in systems containing ePHI.

- [CRITICAL] Verify audit log model in `backend/app/models/audit_log.py` captures: who (user_id), what (action), when (timestamp), where (resource), outcome (success/failure).
- [CRITICAL] Check that login/logout events are logged in `backend/app/routers/auth.py` and `backend/app/security/`.
- [WARNING] Verify data access events (reads of sensitive records) are tracked in `backend/app/services/*.py`.
- [WARNING] Confirm data modification events are logged with before/after values where appropriate.
- [WARNING] Check audit log retention configuration and immutability — no DELETE endpoints for audit records in `backend/app/routers/*.py`.
- [INFO] Validate that audit logs themselves are protected from unauthorized access via RLS or dedicated permissions.
- **Pass**: All CRUD + auth events logged with full context. **Fail**: Missing audit model or unlogged auth events.

---

## Step 3: Person or Entity Authentication - 164.312(d)
**Standard**: Verify the identity of persons seeking access to ePHI.

- [CRITICAL] Verify multi-factor authentication (MFA) support in `backend/app/routers/sec_mfa.py` and `backend/app/security/providers/`.
- [WARNING] Check that MFA is enforced for admin/privileged roles in `backend/app/security/`.
- [WARNING] Verify password complexity and rotation policies in `backend/app/schemas/auth.py`.
- [INFO] Check for account lockout after failed authentication attempts in `backend/app/routers/auth.py`.
- **Pass**: MFA available and enforced for privileged access. **Fail**: No MFA support or no enforcement policy.

---

## Step 4: Integrity - 164.312(c)(1)
**Standard**: Implement policies to protect ePHI from improper alteration or destruction.

- [WARNING] **164.312(c)(2) Mechanism to Authenticate ePHI (A)**: Check for data integrity verification (checksums, hashes) in `backend/app/services/*.py`.
- [WARNING] Verify database constraints in `backend/app/models/*.py` prevent invalid data states (NOT NULL, CHECK, UNIQUE).
- [INFO] Check for input validation on all data entry points in `backend/app/schemas/*.py`.
- [INFO] Validate that backup/restore procedures maintain data integrity in `docker-compose.yml` volume configurations.
- **Pass**: DB constraints enforce integrity; inputs validated. **Fail**: Missing constraints or unvalidated input fields.

---

## Step 5: Transmission Security - 164.312(e)(1)
**Standard**: Implement measures to guard against unauthorized access to ePHI during electronic transmission.

- [CRITICAL] **164.312(e)(2)(i) Integrity Controls (A)**: Verify TLS/HTTPS enforcement for all API endpoints in `backend/app/main.py` and `docker-compose.yml` (reverse proxy config).
- [CRITICAL] **164.312(e)(2)(ii) Encryption (A)**: Check TLS version requirements (minimum TLS 1.2). Verify HSTS headers in middleware or reverse proxy.
- [WARNING] Check for mixed content vulnerabilities in `packages/frontend/src/` — all API calls must use HTTPS.
- [WARNING] Validate that internal service-to-service communication is encrypted (Docker network or TLS).
- [INFO] Check WebSocket connections (if any) enforce WSS.
- **Pass**: TLS 1.2+ enforced; HSTS active; no mixed content. **Fail**: HTTP endpoints accessible or TLS below 1.2.

---

## Step 6: Tenant Data Isolation ({project_name}-Specific)
**Standard**: Multi-tenant SaaS must ensure complete tenant data separation.

- [CRITICAL] Verify `tenant_id` column exists on all ePHI-adjacent tables in `backend/app/models/*.py`.
- [CRITICAL] Confirm RLS policies are applied via Alembic migrations in `backend/alembic/versions/`.
- [WARNING] Check that API responses in `backend/app/routers/*.py` never leak cross-tenant data.
- **Pass**: All tenant-scoped tables have RLS. **Fail**: Any ePHI table missing tenant isolation.

---

## Compliance Notation
- **(R)** = Required implementation specification
- **(A)** = Addressable implementation specification (must implement or document why alternative is equivalent)

---

## Step 7: Generate Report
- Compile all findings into `{output_folder}/security-auditor/hipaa-check.md`.
- Include a compliance matrix table with columns: Requirement, CFR Reference, Status (Compliant / Partially Compliant / Non-Compliant / Not Applicable), Evidence (file:line), and Remediation.
- Calculate compliance score: percentage of requirements fully met out of total applicable requirements.
- Overall result: **COMPLIANT** (100%), **PARTIALLY COMPLIANT** (70-99%), **NON-COMPLIANT** (below 70%).

---

## Step 8: Present Results
- Display the compliance matrix to the user.
- Highlight all Non-Compliant items first with remediation priority.
- Provide a prioritized remediation plan grouped by CFR section.
- State the overall compliance score and whether the application meets the threshold for production deployment.
