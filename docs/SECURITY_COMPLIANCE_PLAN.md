# ScouterFRC — Security & Compliance Plan

> **Version:** 1.0  
> **Status:** Planning  
> **Scope:** Security requirements, compliance obligations, and risk management for ScouterFRC  
> **Audience:** Development team, system administrators, legal/compliance reviewers

---

## Table of Contents

1. [Overview & Security Philosophy](#1-overview--security-philosophy)
2. [Data Classification](#2-data-classification)
3. [Authentication Strategy](#3-authentication-strategy)
4. [Authorization & Access Control](#4-authorization--access-control)
5. [Data Encryption](#5-data-encryption)
6. [API Security](#6-api-security)
7. [Network Security](#7-network-security)
8. [Secrets Management](#8-secrets-management)
9. [Database Security](#9-database-security)
10. [FERPA Compliance (Student Data)](#10-ferpa-compliance-student-data)
11. [GDPR Compliance (EU Users)](#11-gdpr-compliance-eu-users)
12. [CCPA Compliance (California Users)](#12-ccpa-compliance-california-users)
13. [Third-Party & API Security](#13-third-party--api-security)
14. [Code Security](#14-code-security)
15. [Infrastructure Security](#15-infrastructure-security)
16. [Incident Response](#16-incident-response)
17. [Audit & Monitoring](#17-audit--monitoring)
18. [Backup Security](#18-backup-security)
19. [Video Security](#19-video-security)
20. [Physical Security](#20-physical-security)
21. [Security Testing](#21-security-testing)
22. [Compliance Documentation](#22-compliance-documentation)
23. [Training & Awareness](#23-training--awareness)
24. [Regulatory Requirements](#24-regulatory-requirements)
25. [Vendor Management](#25-vendor-management)

---

## 1. Overview & Security Philosophy

### Purpose

ScouterFRC processes scouting data, match analytics, and potentially personally identifiable information (PII) for student athletes and coaches participating in FIRST Robotics Competition events. This document establishes the security and compliance requirements that protect users, preserve data integrity, and satisfy applicable legal obligations.

### Security-First Principles

| Principle | Description |
|-----------|-------------|
| **Least Privilege** | Every component, user, and service receives only the minimum permissions required to perform its function |
| **Defense in Depth** | Multiple overlapping security controls ensure no single point of failure compromises the entire system |
| **Zero Trust** | No implicit trust is granted based on network location; every request is authenticated and authorized |
| **Secure by Default** | New features ship with the most restrictive configuration; users opt in to less-restrictive settings |
| **Fail Secure** | When a component fails, it denies access rather than permitting it |
| **Transparency** | All security decisions, data collection, and processing activities are documented and disclosed to users |

### Defense in Depth Layers

```
┌────────────────────────────────────────────────┐
│          Physical & Network Perimeter          │
│  (firewalls, VPC, DDoS protection, WAF)        │
├────────────────────────────────────────────────┤
│          Application Layer Controls            │
│  (authentication, authorization, input valid.) │
├────────────────────────────────────────────────┤
│          Data Layer Controls                   │
│  (encryption at rest, field-level encryption,  │
│   query parameterization, row-level security)  │
├────────────────────────────────────────────────┤
│          Monitoring & Response                 │
│  (audit logging, alerting, incident response)  │
└────────────────────────────────────────────────┘
```

### Zero Trust Architecture Concepts

- **Identity is the new perimeter** — authentication is required for every API call, regardless of source IP
- **Micro-segmentation** — services communicate only via documented, authorized interfaces
- **Continuous verification** — sessions are validated on every request, not just at login
- **Assume breach** — detection and response capabilities are built assuming an attacker may already be inside

### Risk Assessment Framework

| Risk Level | Criteria | Response |
|------------|----------|----------|
| **Critical** | Exposure of PII/student data at scale, authentication bypass | Immediate remediation, incident declared |
| **High** | Privilege escalation, data leakage of single user, injection vulnerability | Remediate within 72 hours |
| **Medium** | Information disclosure (non-sensitive), misconfiguration | Remediate within 2 weeks |
| **Low** | Best-practice deviation, informational finding | Address in next sprint |

---

## 2. Data Classification

### Classification Tiers

| Classification | Examples | Access | Encryption Required |
|---------------|----------|--------|---------------------|
| **Public** | Team names, event schedules, match results from The Blue Alliance | Anyone | In transit only |
| **Internal** | Aggregated analytics, match performance scores, heatmaps | Authenticated users | In transit + at rest |
| **Sensitive** | User account details, email addresses, hashed passwords, API keys, scouting notes | Role-restricted | In transit + at rest + field-level |
| **Highly Sensitive** | PII of minors, payment information (if applicable), raw video footage | Admin only | In transit + at rest + field-level + access audit |

### Data Inventory

| Data Type | Classification | Storage Location | Retention |
|-----------|---------------|-----------------|-----------|
| Team / event data (from TBA) | Public | PostgreSQL `teams`, `events` tables | Indefinite |
| Match results | Public | PostgreSQL `matches` table | Indefinite |
| User credentials (hashed) | Sensitive | PostgreSQL `users` table | Account lifetime + 90 days |
| User email addresses | Sensitive | PostgreSQL `users` table | Account lifetime + 90 days |
| OAuth tokens | Sensitive | Encrypted store / Redis | Session lifetime |
| API keys | Sensitive | Encrypted store | Until rotated |
| Scouting notes (free-text) | Internal | PostgreSQL `scouting_observations` | Season + 1 year |
| Movement tracking data | Internal | PostgreSQL `movement_track` table | Season + 1 year |
| Video files | Highly Sensitive | Object storage (S3-compatible) | Season + 90 days |
| Scout user profile (minor) | Highly Sensitive | PostgreSQL `users` table | Until deleted or consent expires |

### Data Retention Policies

| Classification | Default Retention | Override Allowed By | Deletion Method |
|---------------|-------------------|---------------------|-----------------|
| Public | Indefinite | N/A | Cascade on event deletion |
| Internal | 2 years | Org Admin | Secure overwrite |
| Sensitive | 1 year post-account-closure | System Admin | Cryptographic erasure + overwrite |
| Highly Sensitive | Minimum required by law | System Admin + Legal | Cryptographic erasure + audit trail |

---

## 3. Authentication Strategy

### Multi-Factor Authentication (MFA)

| Role | MFA Requirement |
|------|----------------|
| System Admin | **Required** — TOTP (e.g., Google Authenticator) or hardware key (FIDO2/WebAuthn) |
| Org Admin | **Required** — TOTP minimum |
| Coach | **Recommended** — prompted, can dismiss for 30 days |
| Scout | **Optional** — available on request |
| Analyst | **Recommended** — prompted, can dismiss for 30 days |

- MFA backup codes must be generated, encrypted, and stored at enrollment
- Lost MFA recovery requires identity verification by Org Admin
- FIDO2/WebAuthn (passkeys) supported as a primary authentication option

### OAuth 2.0 Integration

Supported OAuth providers:

| Provider | Scope Requested | Notes |
|----------|----------------|-------|
| **Google** | `openid`, `email`, `profile` | Primary SSO for school G Suite accounts |
| **GitHub** | `read:user`, `user:email` | Developer/admin accounts |

OAuth flow:
1. User clicks "Sign in with Google/GitHub"
2. Authorization code flow with PKCE — no client secrets exposed in browser
3. Server exchanges code for tokens; only identity is stored, no refresh tokens persisted by default
4. User record created or linked on first login; email used as canonical identifier

### SAML Support (Enterprise SSO)

- SAML 2.0 SP-initiated flow supported for school district IdPs (e.g., Azure AD, Okta, OneLogin)
- Metadata exchange via standard SAML metadata URLs
- Attribute mapping: `NameID` → `user.email`, optional `displayName`, `role` attribute
- JIT (Just-In-Time) provisioning creates user accounts on first SAML assertion
- SAML assertions must be signed; encrypted assertions supported

### Local Authentication

- Local accounts allowed for environments without SSO
- Passwords must meet the following policy:

| Requirement | Value |
|-------------|-------|
| Minimum length | 12 characters |
| Complexity | At least 1 uppercase, 1 lowercase, 1 digit, 1 symbol |
| Common password check | Reject passwords in HIBP list (checked via k-Anonymity API) |
| History | Cannot reuse last 10 passwords |
| Maximum age | 365 days (admins prompted at 90 days) |

### Session Management

| Parameter | Value |
|-----------|-------|
| Session token type | Signed JWT (RS256) or opaque token in Redis |
| Session idle timeout | 30 minutes (configurable per org) |
| Absolute session timeout | 12 hours |
| Session invalidation on password change | Yes — all sessions terminated |
| Concurrent session limit | 5 active sessions per user |
| Session storage | Server-side Redis; token is a reference, not a bearer of claims |

### Remember Me vs. Forced Re-Authentication

| Scenario | Behavior |
|----------|----------|
| "Remember me" checked | Session extended to 30 days; refreshed on activity |
| Accessing sensitive settings | Prompt for password confirmation regardless of session age |
| MFA-required actions | Re-prompt MFA if last MFA verification > 24 hours |
| Org Admin actions | Step-up authentication required (password + MFA) |

---

## 4. Authorization & Access Control

### Role-Based Access Control (RBAC)

```
┌─────────────────────────────────────────────────────────┐
│                     RBAC Hierarchy                      │
├─────────────────────────────────────────────────────────┤
│  System Admin   (full system access, platform-level)    │
│  └── Org Admin  (full access within organization)       │
│      ├── Coach  (read all + manage events/scouts)       │
│      ├── Analyst (read all data, generate reports)      │
│      └── Scout  (submit observations, read own data)    │
└─────────────────────────────────────────────────────────┘
```

### Role Definitions

| Role | Scope | Key Permissions |
|------|-------|-----------------|
| **System Admin** | Platform-wide | All actions; manage orgs, billing, system config |
| **Org Admin** | Organization | Manage members, events, settings; read all org data |
| **Coach** | Organization | Manage scouts, view all analytics, run reports, export data |
| **Analyst** | Organization | Read all analytics, run reports, create dashboards |
| **Scout** | Organization | Submit scouting observations, view assigned events |

### Permission Matrix

| Resource | System Admin | Org Admin | Coach | Analyst | Scout |
|----------|-------------|-----------|-------|---------|-------|
| Create organization | ✅ | ❌ | ❌ | ❌ | ❌ |
| Manage org members | ✅ | ✅ | ❌ | ❌ | ❌ |
| Create/edit events | ✅ | ✅ | ✅ | ❌ | ❌ |
| View event analytics | ✅ | ✅ | ✅ | ✅ | ❌ |
| Submit scouting observation | ✅ | ✅ | ✅ | ❌ | ✅ |
| View own observations | ✅ | ✅ | ✅ | ✅ | ✅ (own only) |
| Export data | ✅ | ✅ | ✅ | ✅ | ❌ |
| Manage API keys | ✅ | ✅ | ❌ | ❌ | ❌ |
| View audit logs | ✅ | ✅ | ❌ | ❌ | ❌ |
| Delete data | ✅ | ✅ | ❌ | ❌ | ❌ |
| System configuration | ✅ | ❌ | ❌ | ❌ | ❌ |

### Resource-Level Access Control

- Every API endpoint enforces both role check and ownership check
- A Coach in Org A cannot access data belonging to Org B
- Row-level security enforced at the database layer (PostgreSQL RLS) in multi-tenant mode
- All resource queries include an `org_id` filter to prevent cross-tenant data leakage

### API Scopes and Permissions

Programmatic API access uses scoped tokens:

| Scope | Description |
|-------|-------------|
| `read:analytics` | Read aggregated analytics data |
| `read:teams` | Read team and event data |
| `write:observations` | Submit scouting observations |
| `read:video` | Access video analysis results |
| `admin:org` | Manage organization settings (Org Admin only) |
| `admin:system` | Full system management (System Admin only) |

### Audit Logging of Access

- All authentication events (login, logout, MFA prompt) are logged
- All data access to Sensitive/Highly Sensitive classifications is logged with user, timestamp, resource, and action
- All permission-denied events are logged and trigger alerting above threshold
- Audit logs are append-only and stored in a separate, hardened log store

---

## 5. Data Encryption

### Encryption in Transit

| Connection | Protocol | Notes |
|------------|----------|-------|
| Browser ↔ API server | TLS 1.2+ (TLS 1.3 preferred) | HSTS enforced; HTTP redirects to HTTPS |
| API server ↔ database | TLS 1.2+ | Certificate verification enabled |
| API server ↔ Redis | TLS 1.2+ | Auth + TLS required in production |
| API server ↔ object storage | TLS 1.2+ | Signed requests (SigV4 or equivalent) |
| Internal service mesh | mTLS (Phase 3) | Mutual TLS for service-to-service calls |

TLS configuration requirements:
- Minimum TLS version: **1.2** (TLS 1.0/1.1 disabled)
- Cipher suites: Forward-secrecy suites only (ECDHE, DHE)
- Certificate: Minimum 2048-bit RSA or 256-bit ECDSA
- Certificate rotation: 90 days or less (Let's Encrypt auto-renewal)

### Encryption at Rest

| Storage | Method | Notes |
|---------|--------|-------|
| PostgreSQL database | AES-256 (storage-level) | Provided by cloud provider (e.g., AWS RDS encryption) |
| Redis | AES-256 (storage-level) | Encrypted EBS volumes or provider-managed |
| Object storage (videos) | AES-256 (SSE-S3 or SSE-KMS) | Per-object encryption; SSE-KMS preferred for audit trail |
| Backups | AES-256 | Encrypted before transfer to backup destination |
| Developer laptops | Full disk encryption | Required policy for all team members |

### Key Management Strategy

```
┌───────────────────────────────────────────────────────────┐
│                   Key Management Hierarchy                │
├───────────────────────────────────────────────────────────┤
│  Root Key (HSM / Cloud KMS Master Key)                    │
│  └── Data Encryption Keys (DEKs) — per data classification│
│      ├── Database encryption key                          │
│      ├── Backup encryption key                            │
│      ├── Video storage encryption key                     │
│      └── Field-level encryption key (sensitive fields)    │
└───────────────────────────────────────────────────────────┘
```

- Master keys stored in cloud-provider KMS (AWS KMS, GCP KMS, or Azure Key Vault)
- DEKs are envelope-encrypted: DEK is encrypted by the master key and stored alongside data
- No plaintext keys in source code, configuration files, or environment variables
- Key access requires IAM role assignment with least-privilege policies

### Field-Level Encryption for Sensitive Data

Fields requiring application-level field-level encryption:

| Field | Table | Encryption Key |
|-------|-------|---------------|
| `email` | `users` | Sensitive DEK |
| `phone_number` | `users` | Sensitive DEK |
| `api_key_hash` | `api_keys` | Sensitive DEK |
| `oauth_refresh_token` | `oauth_tokens` | Sensitive DEK |
| Payment card data (if applicable) | Delegated to payment processor | PCI DSS scope — never stored |

### Video Encryption

- Video files encrypted with AES-256 at rest in object storage
- Separate encryption key per organization
- Pre-signed URLs used for video access — valid for maximum 1 hour, single-use
- Videos are never served directly from storage; proxied through authenticated API

### Key Rotation Procedures

| Key Type | Rotation Frequency | Process |
|----------|--------------------|---------|
| TLS certificates | ≤ 90 days | Automated via cert-manager / Let's Encrypt |
| Master KMS keys | Annually | Cloud provider key rotation, zero downtime |
| DEKs | Annually or on suspected compromise | Re-encrypt all data with new DEK |
| API keys (user-managed) | User-initiated; forced at 1 year | Old key remains valid for 30-day overlap |
| Database passwords | 90 days | Automated via secrets manager rotation |

---

## 6. API Security

### API Authentication

| Client Type | Authentication Method |
|-------------|----------------------|
| Web browser | Session cookie (HttpOnly, Secure, SameSite=Strict) |
| Mobile app | OAuth 2.0 PKCE flow; short-lived access token + refresh token |
| External integrations | API key (bearer token in `Authorization` header) |
| Service-to-service | Mutual TLS (mTLS) or signed JWT with short expiry |

- API keys are hashed (SHA-256) before storage; plaintext shown only once at creation
- API key permissions are scoped; keys cannot exceed the issuing user's role
- API keys can be revoked instantly from the management interface

### Rate Limiting Strategy

| Tier | Endpoint | Limit | Window |
|------|----------|-------|--------|
| Anonymous | Public endpoints | 60 req | per minute |
| Authenticated | Standard endpoints | 600 req | per minute |
| Authenticated | Heavy analytics | 60 req | per minute |
| API key | Configurable per key | Default 1,000 req | per minute |
| Admin | Admin endpoints | 120 req | per minute |

- Rate limit exceeded returns `429 Too Many Requests` with `Retry-After` header
- Distributed rate limiting via Redis counters (consistent across multiple API server instances)
- Rate limit bypass attempted by rotating tokens triggers progressive lockout

### Input Validation and Sanitization

- All incoming data validated against Pydantic schemas (FastAPI) before reaching business logic
- String fields: maximum length enforced; HTML-stripped where appropriate
- Integer / numeric fields: min/max bounds enforced
- Enum fields: validated against known-good value list; reject unknown values
- File uploads: MIME type verified, file size capped, content scanned
- JSON payloads: maximum depth (10 levels) and size (1 MB) enforced

### SQL Injection Prevention

- All database queries use SQLAlchemy ORM or parameterized `text()` queries; no string concatenation
- Raw SQL forbidden in application code except for pre-approved migration scripts
- Unit tests include injection probe strings to confirm parameterization
- Database user for the application has no DDL privileges (no `CREATE`, `DROP`, `ALTER`)
- Input validation rejects patterns associated with SQL injection as an additional layer

### CORS Configuration

```python
# Allowed origins — environment-specific
CORS_ALLOWED_ORIGINS = [
    "https://app.scouterfrc.com",   # Production
    "https://staging.scouterfrc.com",
    "http://localhost:5173",         # Local dev only
]

# CORS policy
allow_credentials = True
allow_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
allow_headers = ["Authorization", "Content-Type", "X-Request-ID"]
max_age = 600  # Preflight cache: 10 minutes
```

- Wildcard `*` origin is never permitted in production
- `Access-Control-Allow-Credentials: true` only when origin is explicitly whitelisted

### API Versioning for Deprecation

- URL-based versioning: `/api/v1/`, `/api/v2/`
- Deprecated endpoints include `Deprecation` and `Sunset` response headers
- Minimum 6-month notice before endpoint removal
- Breaking changes always result in a new major version; non-breaking additions are backward compatible
- API changelog maintained in `docs/API_VERSIONING_POLICY.md`

---

## 7. Network Security

### VPC / Virtual Network Configuration

```
┌─────────────────────────────────────────────────────────┐
│                  Public Subnet                          │
│  (Load Balancer, CDN edge, WAF)                         │
├─────────────────────────────────────────────────────────┤
│                  Private Subnet                         │
│  (API servers, background daemons, CV workers)          │
├─────────────────────────────────────────────────────────┤
│                  Data Subnet                            │
│  (PostgreSQL RDS, Redis ElastiCache, S3 VPC endpoint)   │
└─────────────────────────────────────────────────────────┘
```

- API servers and workers have no public IP addresses; accessed only through load balancer
- Database and cache tiers are not reachable from the internet under any circumstances
- VPC Flow Logs enabled for all subnets for forensic analysis

### Firewall Rules

| Rule | Source | Destination | Ports | Action |
|------|--------|-------------|-------|--------|
| HTTPS ingress | Internet | Load Balancer | 443 | ALLOW |
| HTTP → HTTPS redirect | Internet | Load Balancer | 80 | REDIRECT |
| API traffic | Load Balancer | API servers (private) | 8000 | ALLOW |
| DB access | API servers | PostgreSQL | 5432 | ALLOW |
| Cache access | API servers | Redis | 6379 | ALLOW |
| All other inbound | Internet | Any private subnet | Any | DENY |
| SSH | Bastion host IP only | All servers | 22 | ALLOW |

### Network Segmentation

- API tier, worker tier, and data tier are isolated in separate security groups / subnets
- Security groups follow least-privilege: only necessary port ranges are opened
- No lateral movement possible between tiers without explicit rule exceptions

### DDoS Protection

- Cloud-provider managed DDoS protection (e.g., AWS Shield Standard) enabled at load balancer
- Rate limiting at application layer supplements network-layer protection
- Automatic traffic scrubbing for volumetric attacks (AWS Shield Advanced for Phase 3)
- Alerts triggered when traffic exceeds 3× baseline over a 5-minute window

### Web Application Firewall (WAF)

- WAF deployed in front of load balancer (AWS WAF, Cloudflare WAF, or equivalent)
- Managed rule groups enabled: OWASP Core Rule Set, SQL injection, XSS, known bad IPs
- Custom rules for ScouterFRC-specific patterns (e.g., excessive failed logins from single IP)
- WAF logs reviewed weekly; rules tuned based on false-positive analysis
- Block mode (not detection-only) in production

### IP Whitelisting Options

- Admin console (`/admin/`) can be restricted to specific IP ranges via WAF rule or reverse proxy
- Organization admins can optionally restrict their org's API access to specific IP ranges
- SAML IdP callback endpoints restricted to known IdP IP ranges

---

## 8. Secrets Management

### Environment Variable Handling

- Secrets are **never** stored in source code, `.env` files committed to version control, or Docker images
- Local development uses a `.env.local` file (git-ignored); template provided as `.env.example` with placeholder values
- Production secrets are injected at runtime by the secrets manager (AWS Secrets Manager, HashiCorp Vault, or GCP Secret Manager)
- Applications read secrets from environment variables populated by the secrets manager at container startup

### API Key Storage and Rotation

| Key Type | Storage | Rotation |
|----------|---------|----------|
| User-generated API keys | SHA-256 hash in DB; plaintext shown once | User-initiated; forced at 365 days |
| Third-party API keys (TBA) | Secrets manager | Rotated when provider issues new key |
| Internal service tokens | Secrets manager | 90-day auto-rotation |
| Webhook signing secrets | Secrets manager | 180-day rotation |

- Rotation process: new key created, parallel use period (up to 30 days), old key revoked
- Key rotation does not require application restart (fetched dynamically)

### Database Credential Management

- Separate database user per service (API server, background daemon, CV worker, read-only analytics)
- Database users have minimum required privileges (see [Section 9](#9-database-security))
- Credentials stored in secrets manager with 90-day auto-rotation using RDS rotation Lambda (AWS) or equivalent
- Connection pooling (PgBouncer) uses the rotated credentials; no credential caching in application

### SSL Certificate Management

- TLS certificates managed by cert-manager (Kubernetes) or AWS Certificate Manager
- Auto-renewal 30 days before expiry
- Certificate expiry monitoring: alert 14 days before expiry as backup
- Wildcard certificates avoided where possible; prefer SAN certificates per service

### Secret Scanning in CI/CD

- GitHub's built-in secret scanning enabled on the repository
- Pre-commit hook using `gitleaks` or `truffleHog` prevents committing secrets locally
- CI pipeline runs `detect-secrets` on every pull request; fails build if secrets detected
- Historical scan performed quarterly to catch any secrets committed before scanning was enabled

### Access Control for Secrets

- Secrets manager access controlled via IAM roles (not IAM users/keys)
- Production secrets accessible only to production service role and Security Admin
- Staging secrets accessible to CI/CD pipeline role and Org Admin
- Developers cannot access production secrets; use separate staging credentials
- All secret access events logged with identity and timestamp

---

## 9. Database Security

### Password Hashing

| Algorithm | Usage | Parameters |
|-----------|-------|------------|
| **bcrypt** | Default for user passwords | Cost factor: 12 minimum |
| **Argon2id** | Preferred for new deployments | Memory: 64 MB, iterations: 3, parallelism: 4 |

- Plaintext passwords are **never** stored, logged, or transmitted after the initial hashing step
- Password hashing performed server-side only; client-side hashing is not a substitute
- Hash algorithm upgrade path: on next login, re-hash with new algorithm transparently

### SQL Injection Prevention

- SQLAlchemy ORM used for all CRUD operations (parameterization is automatic)
- Raw SQL expressions (via `text()`) require explicit parameterization and peer review
- CI/CD pipeline includes static analysis (Bandit) checking for string-formatted SQL
- Database intrusion detection monitors for anomalous query patterns

### Query Parameterization Examples

```python
# ✅ Safe — parameterized via SQLAlchemy ORM
team = session.query(Team).filter(Team.id == team_id).first()

# ✅ Safe — explicit parameterization with text()
result = session.execute(
    text("SELECT * FROM teams WHERE event_key = :event_key"),
    {"event_key": event_key}
)

# ❌ Forbidden — never do this
result = session.execute(f"SELECT * FROM teams WHERE event_key = '{event_key}'")
```

### Row-Level Security (Multi-Tenant)

PostgreSQL Row-Level Security (RLS) policies enforced for all multi-tenant tables:

```sql
-- Example RLS policy for scouting_observations
ALTER TABLE scouting_observations ENABLE ROW LEVEL SECURITY;

CREATE POLICY org_isolation ON scouting_observations
  USING (org_id = current_setting('app.current_org_id')::uuid);

-- Application sets org context before queries
SET app.current_org_id = '<org_uuid>';
```

- API server sets `app.current_org_id` on connection checkout; reset on connection return
- RLS policies tested as part of integration test suite to verify cross-tenant isolation

### Database Audit Logging

- All DDL changes logged (table creation, schema modifications)
- All `DELETE` and `UPDATE` operations on Sensitive/Highly Sensitive tables logged with previous values
- Failed authentication attempts to the database logged
- Slow query log enabled (threshold: 1 second) for performance and security analysis
- Logs shipped to centralized log store; not modifiable by application database user

### Regular Security Updates

- PostgreSQL minor version updates applied within 14 days of release
- Major version upgrades planned within 6 months of release with full regression testing
- Security advisories monitored via CVE feeds and PostgreSQL mailing list
- Emergency patches applied within 24 hours for critical CVEs (CVSS ≥ 9.0)

---

## 10. FERPA Compliance (Student Data)

### Definition of Protected Information

The Family Educational Rights and Privacy Act (FERPA) protects **education records** of students. ScouterFRC may store FERPA-protected information if:

- Students (under 18) are registered as users
- Student names are associated with scouting performance data
- Personally identifiable information (PII) such as names, student IDs, or contact information is collected

### Data Collection Consent Requirements

| User Age | Consent Requirement |
|----------|---------------------|
| Under 13 | COPPA applies — parental consent required before any data collection |
| 13–17 | Parental or guardian consent required for FERPA-protected data |
| 18+ | Student's own consent; standard terms of service apply |

- Consent mechanism: checkbox at registration with link to Privacy Policy
- Consent records stored with timestamp, IP address (hashed), and user agent
- Consent can be withdrawn at any time; withdrawal triggers data deletion workflow

### Parent/Guardian Notification Requirements

- Parents/guardians of minor students may request:
  - Inspection and review of education records
  - Amendment of inaccurate or misleading records
  - Restriction on disclosure to third parties
- Notification procedures:
  1. Request received via privacy@scouterfrc.com (or in-app form)
  2. Identity verified by Org Admin within 5 business days
  3. Records provided or amendment process initiated within 45 calendar days (FERPA requirement)

### Student Access Rights

- Students (or parents of minor students) can access all data ScouterFRC holds about them
- Export available in machine-readable format (JSON or CSV) within 30 days of request
- Students may request correction of inaccurate data; disputes documented in audit log
- Students may request deletion of their account and associated data (subject to retention obligations)

### Data Retention Limits

| Data Type | Retention Limit | Basis |
|-----------|----------------|-------|
| Student PII | Account lifetime + 90 days after account closure | Minimum necessary |
| Scouting observations linked to student account | 2 FRC seasons after collection | Legitimate interest |
| Aggregated, de-identified analytics | Indefinite | No longer FERPA-protected |

### Breach Notification Procedures

Under FERPA, unauthorized disclosure of education records must be reported:

1. **Within 72 hours** of discovery: notify affected school/organization
2. **Within 72 hours**: report to relevant institutional privacy officer
3. **Within 30 days**: provide written description of breach, data affected, and remediation steps
4. Maintain breach log; consult legal counsel for breaches involving 500+ students

### Third-Party Access Restrictions

- Student FERPA data is **never** shared with third-party vendors without:
  - A signed Data Processing Agreement (DPA)
  - School official designation or legitimate educational interest documented
  - Parental consent (if under 18 and data is identifiable)
- The Blue Alliance integration receives only non-PII match data; student names are not transmitted
- Analytics providers receive only aggregated, de-identified data

### Export Restrictions for Sensitive Data

- Student PII exports require Org Admin authorization and are logged
- Bulk exports of student records (>10 students) require additional confirmation
- Exported files are encrypted; download links expire after 24 hours

---

## 11. GDPR Compliance (EU Users)

### Applicability

GDPR applies if ScouterFRC processes personal data of individuals in the European Union or European Economic Area, regardless of where ScouterFRC is hosted. If EU users exist, all requirements in this section are mandatory.

### Data Processing Agreements (DPA)

- ScouterFRC acts as a **data processor** on behalf of organizations (data controllers)
- A DPA must be signed with every organization before processing EU user data
- DPAs are available at `legal/DPA.pdf` and updated annually or when processing activities change
- Sub-processors (cloud providers, analytics) are listed in the DPA Annex; organizations notified of changes with 30 days notice

### Right to Erasure (Right to Be Forgotten)

Workflow upon erasure request:

```
1. User submits erasure request (in-app or via email)
2. Identity verified (email confirmation)
3. Review: check for legal hold or overriding legitimate interest
4. If no hold:
   a. Anonymize or delete all PII from primary database
   b. Delete from backups at next rotation (document in audit trail)
   c. Revoke all active sessions and API keys
   d. Remove from email lists and third-party processors
5. Confirmation sent to user within 30 days
6. Erasure event logged in audit trail
```

### Data Portability Requirements

- Users can request a machine-readable export (JSON) of all personal data ScouterFRC holds
- Export includes: account details, scouting observations, event participation records
- Provided within 30 days of verified request
- Format: structured JSON compliant with Article 20 portability requirements
- Export delivered via secure, time-limited download link (24-hour expiry, HTTPS)

### Privacy by Design Principles

| Principle | Implementation |
|-----------|---------------|
| Data minimization | Collect only data necessary for stated purpose; no speculative data collection |
| Purpose limitation | Data collected for scouting cannot be repurposed for marketing or profiling |
| Storage limitation | Retention periods defined per classification; automated purge jobs |
| Accuracy | Users can correct their own data; import validations reject clearly wrong data |
| Integrity and confidentiality | Encryption at rest and in transit (see [Section 5](#5-data-encryption)) |
| Accountability | DPO designated (if required by Article 37); processing records maintained |

### Consent Management

- Consent is obtained prior to processing non-essential data (analytics, cookies beyond strictly necessary)
- Consent is granular: separate checkboxes for each processing purpose
- Consent records stored with: user ID, timestamp, IP hash, version of privacy policy accepted, specific consent items
- Withdrawing consent is as easy as giving it (one-click in account settings)
- Consent re-collected when privacy policy materially changes

### Data Protection Impact Assessment (DPIA)

A DPIA is required before processing activities that are likely to result in high risk:

- Processing of special category data (health, biometric)
- Large-scale processing of minors' data
- Systematic monitoring (video tracking of individuals)
- New technologies (computer vision pipeline)

DPIA template: `docs/DPIA_TEMPLATE.md`  
Completed DPIAs: `docs/dpia/`

### Privacy Policy Requirements

Privacy Policy must include (GDPR Article 13/14):
- Identity and contact details of the data controller and DPO (if applicable)
- Purposes and legal basis for processing
- Recipients or categories of recipients
- Transfers to third countries (if any) and safeguards
- Retention periods
- All data subject rights and how to exercise them
- Right to lodge a complaint with supervisory authority
- Automated decision-making/profiling information (if applicable)

### Breach Notification (72-Hour Requirement)

| Step | Deadline | Recipient |
|------|----------|-----------|
| Internal incident declared | Immediate | Security team |
| Supervisory authority notification (if high risk) | 72 hours | Lead supervisory authority (EU) |
| Affected individuals notified (if high risk to rights) | Without undue delay | Affected users |
| Breach log updated | Ongoing | Internal audit trail |

Breach report template: `docs/incident_response/BREACH_NOTIFICATION_TEMPLATE.md`

---

## 12. CCPA Compliance (California Users)

### Applicability

The California Consumer Privacy Act (CCPA) / CPRA applies if ScouterFRC:
- Has annual gross revenue > $25M, OR
- Buys, sells, or receives personal information of 100,000+ California consumers, OR
- Derives 50%+ of annual revenue from selling personal information

Even if below thresholds, ScouterFRC follows CCPA principles as a best practice.

### Consumer Privacy Rights

| Right | Description | ScouterFRC Implementation |
|-------|-------------|--------------------------|
| **Right to Know** | What personal information is collected, used, disclosed, and sold | In-app data transparency dashboard; Privacy Policy |
| **Right to Delete** | Request deletion of personal information | Account deletion flow; see [GDPR Section 11](#11-gdpr-compliance-eu-users) |
| **Right to Opt-Out** | Opt out of sale of personal information | ScouterFRC does not sell personal information; opt-out not applicable |
| **Right to Non-Discrimination** | Cannot be penalized for exercising privacy rights | Policy enforced; access not degraded for privacy requests |
| **Right to Correct** | Request correction of inaccurate personal information | User profile settings; correction request form |
| **Right to Limit Use** | Limit use of sensitive personal information | Sensitive data used only for stated purposes |

### Opt-Out Mechanisms

- "Do Not Sell or Share My Personal Information" link displayed in the footer (required by CCPA)
- Since ScouterFRC does not sell data, this link leads to a confirmation page and opt-out from analytics
- Global Privacy Control (GPC) signal honored at browser/request level

### Data Sale Restrictions

- ScouterFRC **does not sell** personal information to third parties
- Aggregated, de-identified data may be used for platform improvement (disclosed in Privacy Policy)
- Third-party analytics SDKs configured to respect opt-out signals and not share PII

### Retention Limitations

- Personal information retained only as long as necessary for the disclosed purpose
- Retention schedule published in Privacy Policy and this document ([Section 2](#2-data-classification))
- Annual review of retained data; data with no legitimate retention basis deleted

### Transparency Requirements

- Privacy Policy is written in plain language, accessible from every page
- Data categories collected and purposes disclosed at point of collection
- Annual privacy notice update sent to all California users (if material changes occur)
- Contact: `privacy@scouterfrc.com` for all CCPA requests; response within 45 days

---

## 13. Third-Party & API Security

### Vendor Security Assessment

Before integrating any third-party service that processes ScouterFRC user data:

| Assessment Step | Requirement |
|----------------|-------------|
| Security questionnaire | Completed and reviewed |
| Privacy policy review | Compliant with applicable laws |
| Data processing agreement | Signed before data flows |
| SOC 2 / ISO 27001 certification | Preferred; required for Sensitive data processors |
| Breach notification SLA | Must commit to 72-hour notification |
| Subprocessor transparency | Subprocessors listed and disclosed |

### Blue Alliance API Security

| Control | Implementation |
|---------|----------------|
| API key storage | Secrets manager; never in source code |
| Rate limit compliance | Respect TBA rate limits; backoff on 429 |
| Data usage | Public match data only; no PII transmitted to TBA |
| Key rotation | Annual rotation; immediate rotation if key suspected compromised |
| TLS verification | Certificate validation enabled on all TBA API calls |
| Response validation | Pydantic schema validation on all TBA responses to prevent injection via malformed data |

### Third-Party Integration Review

For each integration, document:
- Purpose of integration
- Data shared (types, fields, volume)
- Legal basis for sharing
- DPA status
- Review date (annual)
- Risk rating

Integration registry: `docs/THIRD_PARTY_INTEGRATIONS.md`

### Data Sharing Agreements

- No data sharing without a signed DPA or equivalent agreement
- Data shared only for the stated purpose; sub-processing requires advance written approval
- Agreement must include: security standards required, breach notification obligations, data return/deletion on termination

### Audit Rights

- Vendors processing Sensitive/Highly Sensitive data must permit ScouterFRC to audit or commission independent audits
- Minimum: annual security audit report shared (SOC 2 Type II or equivalent)
- Contractual right to audit on cause (suspected breach or security incident)

---

## 14. Code Security

### Dependency Vulnerability Scanning

| Tool | Trigger | Action on Finding |
|------|---------|-------------------|
| `dependabot` (GitHub) | Daily scan | Automated PR for patch/minor updates |
| `pip-audit` | Every CI run | Fail build on Critical/High CVEs |
| `npm audit` (frontend) | Every CI run | Fail build on Critical/High CVEs |
| `trivy` (container images) | On image build | Fail build on Critical CVEs |

- All production dependencies pinned to specific versions (no floating `^` or `~` in critical packages)
- Dependency updates reviewed and merged within 7 days for security patches
- Weekly automated dependency update PRs via Dependabot

### Software Composition Analysis (SCA)

- Full SCA report generated on each release
- Open-source license compatibility checked (avoid GPL in commercial contexts)
- Transitive dependency tree reviewed for known malicious packages
- Package integrity verified via hash/checksum (pip hash checking, npm lockfile)

### Secure Coding Practices

| Practice | Enforcement |
|----------|-------------|
| Input validation | Pydantic schemas required on all API endpoints |
| Output encoding | Jinja2/React auto-escaping enabled; no manual `innerHTML` |
| Parameterized queries | SQLAlchemy ORM required; `text()` requires explicit params |
| Secret detection | Pre-commit hooks + CI secret scanning |
| Error messages | Generic errors to users; detailed errors in server logs only |
| Dependency minimization | New dependencies require justification and security review |

### Code Review Security Checklist

Before merging any PR that touches security-sensitive code:

- [ ] Input validation present for all user-supplied data
- [ ] No secrets or credentials in code or test fixtures
- [ ] SQL queries parameterized; no string formatting
- [ ] Error handling does not expose stack traces to clients
- [ ] New dependencies reviewed for known CVEs
- [ ] Authentication and authorization checks present on new endpoints
- [ ] Rate limiting applied to new public endpoints
- [ ] Audit logging added for new sensitive operations
- [ ] CORS, CSRF protection not weakened

### Static Code Analysis (SAST)

| Tool | Language | Checks |
|------|----------|--------|
| **Bandit** | Python | Injection, hardcoded secrets, insecure deserialization, weak crypto |
| **Semgrep** | Python, TypeScript | Custom rules for ScouterFRC patterns + OWASP rules |
| **ESLint security plugin** | TypeScript/React | XSS sinks, `eval()` usage, prototype pollution |
| **CodeQL** (GitHub Advanced Security) | Python, TypeScript | Deep semantic analysis, taint tracking |

- SAST runs on every pull request; results reviewed before merge
- False positives documented in `.semgrep_ignore` / `noqa` comments with justification
- Zero tolerance for High/Critical SAST findings in production branches

### Dynamic Code Analysis (DAST)

- OWASP ZAP active scan run against staging environment on each release
- Authenticated scan using test user credentials (no production data)
- DAST results reviewed; Critical/High findings block release
- Automated DAST integrated into release pipeline (Phase 2+)

---

## 15. Infrastructure Security

### Server Hardening

| Control | Requirement |
|---------|-------------|
| OS patching | Automated; security patches within 7 days |
| Unused services | Disabled; only required ports open |
| Root login | Disabled; sudo with logging |
| Login banner | Legal warning banner displayed on SSH |
| Auditd | Enabled; system call auditing for privileged operations |
| File integrity monitoring | AIDE or cloud-native equivalent |
| CIS Benchmark | CIS Level 1 compliance target |

### SSH Key Management

- Password-based SSH disabled; key-based authentication only
- SSH keys minimum 4096-bit RSA or 256-bit Ed25519
- Each developer has a unique key pair; shared keys prohibited
- Keys rotated when team member leaves or key is suspected compromised
- Bastion host (jump server) required for all SSH access; no direct SSH to application servers
- All SSH sessions logged and recorded (terminal recording in Phase 3)

### Patch Management and Updates

| Category | Timeline |
|----------|----------|
| Critical security patches (CVSS ≥ 9.0) | Within 24 hours |
| High severity patches (CVSS 7.0–8.9) | Within 7 days |
| Medium severity patches | Within 30 days |
| Low severity / feature updates | Next scheduled maintenance window |

- Automated patch management via cloud provider managed services where possible
- Patch compliance reports generated monthly
- Emergency patching procedure documented in runbook

### Vulnerability Scanning

- Automated vulnerability scan of all infrastructure weekly (Tenable, Qualys, or cloud-native)
- Container image scanning on every build (Trivy, ECR scanning)
- Scan results tracked in vulnerability management system
- SLA for remediation based on severity (see patch management table above)

### Penetration Testing Plan

| Phase | Frequency | Scope |
|-------|-----------|-------|
| Phase 1 launch | Before production launch | Web application, API, authentication |
| Annual | Once per year | Full application, infrastructure, API |
| Post-major-change | After significant architectural changes | Affected components |
| Phase 3 (continuous) | Quarterly | Automated continuous testing |

- Penetration testing performed by qualified third party (OSCP/CREST certified)
- Findings documented and tracked to remediation
- Retest required for Critical/High findings before report closure

### Security Baselines

- All systems measured against defined security baseline using automated compliance checks
- Baselines documented in `infrastructure/security_baselines/`
- Drift from baseline triggers automated alert and remediation ticket

---

## 16. Incident Response

### Incident Categories and Severity Levels

| Severity | Description | Examples |
|----------|-------------|---------|
| **P1 — Critical** | Active breach, data exfiltration, ransomware | Unauthorized access to user PII at scale, database compromise |
| **P2 — High** | Potential breach, single-account compromise, significant service disruption | Individual account takeover, injection attack discovered in logs |
| **P3 — Medium** | Suspicious activity, policy violation, non-data security event | Unusual login patterns, failed brute force, misconfiguration |
| **P4 — Low** | Minor policy violation, informational finding | Outdated dependency, weak password detected in audit |

### Notification Procedures

```
Incident Detected
      │
      ▼
Notify Security Lead (immediately, any hour)
      │
      ▼
Severity Assessment (within 30 minutes)
      │
      ├── P1/P2: Assemble incident response team
      │         Engage legal/compliance within 1 hour
      │         Begin evidence preservation immediately
      │
      └── P3/P4: Log in incident tracker
                Schedule review within 24 hours
```

### Internal Escalation Process

| Time | Action |
|------|--------|
| 0 min | Incident detected; Security Lead notified |
| 30 min | Severity assessed; incident commander assigned |
| 1 hour (P1/P2) | Incident response team assembled; war room opened |
| 2 hours (P1) | Executive team notified; legal counsel engaged |
| 4 hours (P1) | Containment actions completed or decision to accept risk documented |
| 24 hours | Preliminary incident report drafted |
| 72 hours | Regulatory notifications sent (if required) |
| 30 days | Post-incident review completed and documented |

### Customer Notification Procedures

For breaches affecting user data:

1. Determine scope: number of users affected, data types involved
2. Consult legal counsel on notification obligations
3. Draft notification using approved template (see below)
4. Notify affected users via email within required regulatory timeframe
5. Update status page with non-sensitive incident summary
6. Provide credit monitoring or equivalent if financial/sensitive data exposed

### Timeline for Response

| Regulatory Requirement | Deadline |
|----------------------|----------|
| GDPR — supervisory authority | 72 hours |
| GDPR — affected individuals | Without undue delay (if high risk) |
| FERPA — institution | No specific federal timeline; as soon as practicable |
| CCPA — AG notification (if >500 CA residents) | Expeditiously |
| State breach notification laws | Varies by state: 30–90 days typical |

### Post-Incident Review Process

Conducted within 30 days of incident resolution:
1. Timeline reconstruction from logs
2. Root cause analysis (5 Whys or similar)
3. Impact assessment (data, users, reputation, legal)
4. Remediation actions completed
5. Process improvements identified
6. Lessons learned documented
7. Security controls updated as needed

Post-incident review report template: `docs/incident_response/POST_INCIDENT_REVIEW_TEMPLATE.md`

### Communication Templates

Located in `docs/incident_response/`:
- `BREACH_NOTIFICATION_TEMPLATE.md` — User-facing notification
- `REGULATORY_NOTIFICATION_TEMPLATE.md` — GDPR/regulatory body notification
- `INTERNAL_INCIDENT_REPORT_TEMPLATE.md` — Internal documentation
- `STATUS_PAGE_UPDATE_TEMPLATE.md` — Public status page update

### Legal / Law Enforcement Coordination

- Legal counsel must be engaged before any law enforcement contact
- Evidence preservation procedures followed before any system changes after a breach
- Chain of custody maintained for forensic evidence
- Law enforcement requests reviewed by legal counsel; user data not disclosed without legal process

---

## 17. Audit & Monitoring

### Access Audit Logging

All the following events are logged with: timestamp, user ID, IP address, user agent, resource affected, action, result (success/failure):

- Login and logout events
- MFA prompt and completion events
- Password changes and resets
- API key creation, use, and revocation
- OAuth token issuance and revocation
- Session creation and expiration
- Role and permission changes

### Change Logging (Data Modifications)

For Sensitive and Highly Sensitive data:
- All `INSERT`, `UPDATE`, `DELETE` operations logged with previous and new values
- Logged via PostgreSQL audit extension (pgaudit) or application-level trigger
- Log includes: who changed it, when, from where, what changed

### Failed Login Attempts Tracking

| Event | Action |
|-------|--------|
| 5 consecutive failures | Account temporarily locked for 15 minutes; user notified |
| 10 failures in 1 hour | Account locked; admin notification |
| Distributed failures (different IPs, same account) | Alert security team |
| Brute force pattern (many accounts) | IP blocked at WAF; alert security team |

### Admin Action Audit Trail

All System Admin and Org Admin actions are logged with additional context:
- Reason field required for destructive actions (deletion, bulk export)
- Admin actions cannot be deleted from audit log
- Separate audit log storage with restricted write access

### Query Logging

- Slow query log: queries exceeding 1 second
- Failed queries: logged with error code (not full SQL in user-facing errors)
- Data export queries: all bulk export operations logged
- Query patterns reviewed monthly for anomalies

### Log Retention Policies

| Log Type | Retention | Storage |
|----------|-----------|---------|
| Security audit logs | 7 years | Immutable cold storage |
| Application logs | 1 year | Searchable warm storage |
| Access logs (HTTP) | 90 days | Compressed warm storage |
| Database query logs | 1 year | Searchable warm storage |
| Infrastructure logs | 90 days | Standard storage |

### Security Event Alerts

| Event | Alert Level | Recipients |
|-------|-------------|-----------|
| Multiple failed logins | Medium | Security team |
| Admin action at unusual hour | High | Security Lead |
| Spike in API errors (500s) | High | On-call engineer |
| Secret scan finding in CI | Critical | Security team, commit author |
| Data export > 1000 records | Medium | Org Admin |
| New admin role assignment | High | Security Lead |
| Certificate expiry < 14 days | High | DevOps team |

---

## 18. Backup Security

### Backup Encryption

- All backups encrypted with AES-256 before transfer to backup storage
- Backup encryption key separate from production data encryption key
- Backup encryption key stored in secrets manager; never alongside backup data
- Encryption verified at backup creation; unencrypted backups trigger alert

### Backup Access Restrictions

| Role | Backup Access |
|------|--------------|
| System Admin | Full access (create, restore, delete) |
| Org Admin | Request restore of their organization's data only |
| DevOps engineers | Read access for integrity verification; restore with approval |
| Application services | No backup access |
| All others | No access |

- Backup storage bucket/container has no public access
- Access logged; unusual access patterns trigger alert

### Backup Integrity Verification

- SHA-256 checksum computed at backup creation; stored separately from backup
- Weekly automated restore tests in isolated environment to verify recoverability
- Checksum verification before any restore operation
- Backup catalog maintained with: backup ID, date, type, size, checksum, encryption status

### Air-Gapped Backup Copies

- At least one backup copy stored in a separate cloud region (geographic redundancy)
- Phase 3: off-cloud backup copy (tape or separate provider) for ransomware resilience
- Air-gapped copy updated weekly; access requires physical or out-of-band authorization

### Restore Testing Procedures

| Test | Frequency | Procedure |
|------|-----------|-----------|
| Full restore drill | Quarterly | Restore to isolated environment; verify data integrity and application functionality |
| Partial restore test | Monthly | Restore specific table/schema; verify consistency |
| Automated restore verification | Weekly | Automated script restores sample and validates row counts |

- Restore test results documented and retained for compliance
- Recovery Time Objective (RTO): 4 hours for full restore
- Recovery Point Objective (RPO): 24-hour maximum data loss; 1-hour target with continuous archiving

### Secure Deletion of Old Backups

- Expired backups deleted via cryptographic erasure: encryption key deleted, then data deleted
- Deletion confirmed and logged in backup catalog
- Physical media (if applicable) destroyed per NIST 800-88 guidelines
- Cloud storage lifecycle policies automate deletion at expiry; manual verification quarterly

---

## 19. Video Security

### Video File Access Controls

- Video files stored in private object storage; **no public read access**
- Access requires authenticated session with minimum Scout role
- Pre-signed URLs issued per-request; valid for maximum 1 hour
- URL re-use blocked: pre-signed URL is single-use or IP-bound
- Video access logged: who accessed, when, which video, from which IP

### Video Encryption at Rest

- AES-256 SSE-KMS encryption applied to every video object in storage
- Organization-specific encryption keys (separate key per org)
- Key access via IAM role assigned only to the API server and backup service
- Video encryption status verified on upload; unencrypted uploads rejected

### Video Encryption in Transit

- All video transfers use TLS 1.2+ (HTTPS only)
- Pre-signed URLs include HTTPS endpoint; HTTP access rejected
- Video streaming API uses chunked transfer with authenticated session
- No video metadata leaked in public-facing headers (no `Content-Disposition` with filenames)

### Video Retention Policies

| Category | Retention Period | Basis |
|----------|----------------|-------|
| Raw match video | Current season + 90 days | Processing complete; storage cost |
| Processed/annotated video | Current season + 1 year | Analytics reference |
| Video analysis results (metadata) | 2 seasons | Historical analytics |
| DPIA-required retention | Per DPIA assessment | Regulatory obligation |

- Automated lifecycle policies delete videos at expiry; cannot be extended without Org Admin approval
- Deletion events logged in audit trail

### EXIF Data Removal

- Any video/image uploaded by users processed through EXIF stripping pipeline before storage
- Tools: `ffmpeg` (video metadata strip), `exiftool` or `Pillow` (image EXIF strip)
- Metadata that may contain PII removed: GPS coordinates, device identifiers, user-created timestamps
- Stripped metadata logged but not retained (logged only that stripping occurred, not what was stripped)

### Sensitive Information Blurring

- Computer vision pipeline includes an option to blur faces detected in video footage
- Audience/spectator areas can be excluded from analysis and blurred in any exported clips
- Student faces in crowd footage not used for identification; blur applied before any human review
- Blurring configuration documented per event in the event settings

---

## 20. Physical Security

### On-Premises Considerations

ScouterFRC is designed as a cloud-hosted service. If any on-premises deployment is used:

| Control | Requirement |
|---------|-------------|
| Server room access | Locked; keycard or biometric access only; visitor log maintained |
| Server room monitoring | CCTV coverage; motion detection alerts |
| Environmental controls | Temperature, humidity, and smoke detection; UPS power |
| Network equipment | Locked racks; patch panel and switch access logged |
| Unauthorized access | Detected and reported as a security incident |

### Secure Equipment Disposal

- Hard drives and SSDs: wiped using DoD 5220.22-M standard (3-pass) or physically destroyed
- Degaussing for magnetic media before disposal
- Certificate of destruction obtained from disposal vendor
- Cloud environments: storage volumes deleted and provider confirms underlying media deallocation

### Device Security (Mobile Apps)

If a ScouterFRC mobile app is released:

| Control | Requirement |
|---------|-------------|
| Device storage | Sensitive data encrypted in local storage (iOS Keychain, Android Keystore) |
| Screen lock | App locks after 5 minutes of inactivity |
| Biometric authentication | Supported for app unlock |
| Remote wipe | Managed via MDM for organizational devices |
| Jailbreak/root detection | App checks for jailbroken/rooted devices; warns user |
| Certificate pinning | API communication uses certificate pinning to prevent MITM |

### Video Surveillance at Events

If ScouterFRC captures video at FRC events:

- Video recording only permitted in designated competition areas (per event venue policy)
- Spectators, pit crews, and audience members not intentionally captured in analysis feeds
- Camera placement and recording disclosed to event organizers
- Video not used for any purpose other than robot performance analysis

---

## 21. Security Testing

### Regular Penetration Testing

| Engagement Type | Frequency | Scope |
|----------------|-----------|-------|
| Full application pentest | Annually | Web app, API, authentication, authorization |
| Network/infrastructure pentest | Annually | Internal network, server hardening |
| Code review (security-focused) | Per major release | Security-critical modules |
| Red team exercise | Every 2 years (Phase 3) | Full adversarial simulation |

- Pentest firms must hold CREST, OSCP, or equivalent qualification
- Findings tracked in vulnerability management system with SLA-based remediation
- Critical/High findings retested before pentest report closure

### Vulnerability Scanning

| Scan Type | Tool | Frequency |
|-----------|------|-----------|
| Web application scan | OWASP ZAP / Burp Suite | Weekly (automated) |
| Infrastructure scan | Tenable / Qualys / Scout Suite | Weekly (automated) |
| Container image scan | Trivy | On every image build |
| Dependency scan | pip-audit, npm audit | On every CI run |
| Cloud configuration | Prowler / AWS Security Hub | Daily |

### Security Code Review

- All PRs touching authentication, authorization, cryptography, or data access require review by a security-aware team member
- Security code review checklist (see [Section 14](#14-code-security)) completed before approval
- Automated SAST results reviewed as part of PR review

### Threat Modeling Exercises

Conducted:
- At project inception (completed for Phase 1)
- Before each new major phase (Phase 2, Phase 3)
- When introducing new data types (video, PII)
- When integrating new third-party services

Methodology: STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege)  
Output: Threat model document in `docs/threat_models/`

### Security Regression Testing

- Security test cases added to automated test suite for every confirmed vulnerability fixed
- Regression tests cover: injection, authentication bypass, authorization bypass, insecure direct object reference
- Security tests run on every CI build; failures block merge

### Annual Security Audit

- Comprehensive annual security audit covering all sections of this document
- Audit against OWASP ASVS Level 2 (application security verification standard)
- Results documented; remediation plan created for all findings
- Audit report shared with Org Admins (executive summary)

---

## 22. Compliance Documentation

The following documents form the ScouterFRC compliance document library:

| Document | Location | Status | Review Cycle |
|----------|----------|--------|-------------|
| **Privacy Policy** | `legal/PRIVACY_POLICY.md` | Required | Annual |
| **Terms of Service** | `legal/TERMS_OF_SERVICE.md` | Required | Annual |
| **Data Processing Agreement (DPA)** | `legal/DPA.md` | Required for EU | Annual |
| **Security Incident Response Plan** | `docs/incident_response/INCIDENT_RESPONSE_PLAN.md` | Required | Annual |
| **Acceptable Use Policy** | `legal/ACCEPTABLE_USE_POLICY.md` | Required | Annual |
| **Data Classification Policy** | This document (Section 2) | Required | Annual |
| **Access Control Policy** | This document (Section 4) | Required | Annual |
| **Data Retention Policy** | This document (Section 2) | Required | Annual |
| **DPIA Template** | `docs/DPIA_TEMPLATE.md` | Required (EU) | Per processing activity |
| **Vendor Security Questionnaire** | `docs/VENDOR_SECURITY_QUESTIONNAIRE.md` | Required | Annual |
| **Security Compliance Plan** | This document | Living document | Annual |

### Document Control

- All compliance documents version-controlled in the repository
- Changes require review by Security Lead before merge
- Document version and effective date noted in each file header
- Superseded versions archived; not deleted

---

## 23. Training & Awareness

### Secure Coding Training for Developers

| Training | Frequency | Content |
|----------|-----------|---------|
| Secure coding fundamentals | Onboarding + annual refresh | OWASP Top 10, input validation, cryptography basics |
| Language-specific security | Onboarding + annual | Python/FastAPI security, React XSS prevention |
| Secrets management | Onboarding | How to use secrets manager; never commit secrets |
| Incident response simulation | Annual | Tabletop exercise for developers |

Resources:
- OWASP WebGoat (hands-on training environment)
- Secure Code Warrior or similar platform (Phase 2)
- Internal wiki: `wiki/security/developer_guidelines`

### Security Awareness for All Team Members

| Topic | Delivery | Frequency |
|-------|----------|-----------|
| Data classification and handling | Onboarding + annual reminder | Annual |
| Phishing and social engineering | Training module | Annual |
| Password security | Onboarding + policy enforcement | Onboarding |
| Incident reporting procedures | Onboarding | Onboarding |
| Acceptable use policy | Signed acknowledgement | Onboarding + upon policy changes |

### Phishing Simulation Exercises

- Simulated phishing campaigns run twice per year
- Results used for targeted training (not punitive)
- Click rates and reporting rates tracked over time
- Users who click receive immediate in-line training

### Password Security Guidelines

- All team members required to use a password manager (Bitwarden, 1Password, or equivalent)
- Unique, strong passwords for every service account
- Passwords never shared, even among team members
- Passphrase-based passwords encouraged for memorable accounts (4+ random words)
- MFA required for all accounts with access to production systems

### Data Handling Procedures

- Training on data classification (Section 2) — what data requires special handling
- Clear desk policy: no PII left visible on screens when away from workstation
- Secure data disposal procedures
- How to recognize and report a suspected data incident

---

## 24. Regulatory Requirements

### FIRST Robotics Competition Policies

- ScouterFRC complies with FIRST's data usage policies for publicly available match data
- The Blue Alliance API is used within TBA's terms of service; attribution provided where required
- Video recording and analysis at FRC events complies with FIRST media policy and event venue rules
- No unauthorized video recording; only official match video streams analyzed

### School District Policies

- Organizations using ScouterFRC with student data must ensure their school district's acceptable use policies are satisfied
- District data governance policies take precedence for student PII handling
- ScouterFRC provides a DPA and security documentation to support district review processes
- Multi-district organizations should use separate organization accounts per district

### State / Federal Data Protection Laws

| Law | Applicability | Key Requirement |
|-----|--------------|-----------------|
| **FERPA** | US — students in federally-funded schools | Education records protection; parental rights |
| **COPPA** | US — users under 13 | Verifiable parental consent required |
| **CCPA/CPRA** | California residents | Consumer privacy rights; opt-out of data sale |
| **SOPIPA** | California students | Student data not used for advertising or profiling |
| **NDPA** | Multiple US states | Student data protection (check state-by-state) |
| **GDPR** | EU/EEA residents | Comprehensive data protection rights |
| **PIPEDA** | Canadian users | Privacy law for commercial activities |

- Legal counsel consulted when expanding to new geographic regions
- Compliance matrix maintained and reviewed annually: `docs/REGULATORY_COMPLIANCE_MATRIX.md`

### Regional Legal Requirements

- Before accepting users from a new country or region, legal review of local data protection laws required
- Data residency requirements (e.g., EU data staying in EU) implemented via region-specific deployments
- Standard Contractual Clauses (SCCs) used for international data transfers from EU

### HIPAA (Health Data)

- ScouterFRC does **not** collect health data; HIPAA does not apply in the current scope
- If any future feature would collect health-related information (e.g., injury tracking), a HIPAA impact assessment must be completed before implementation
- No PHI (Protected Health Information) may be stored without a full HIPAA compliance review

---

## 25. Vendor Management

### Security Questionnaire for Vendors

All vendors processing ScouterFRC data complete a security questionnaire covering:

| Section | Key Questions |
|---------|--------------|
| Data security | Encryption at rest and in transit; key management |
| Access control | Role-based access; MFA for admin accounts |
| Incident response | Breach notification timeline; IR plan existence |
| Business continuity | RTO/RPO targets; backup procedures |
| Compliance certifications | SOC 2, ISO 27001, PCI DSS (if applicable) |
| Subprocessors | List of subprocessors; notification of changes |
| Penetration testing | Frequency; most recent findings summary |
| Vulnerability management | Patch SLA; CVE tracking process |

Questionnaire template: `docs/VENDOR_SECURITY_QUESTIONNAIRE.md`

### SLA Requirements

| Requirement | Minimum SLA |
|-------------|-------------|
| Uptime | 99.9% monthly |
| Incident notification | 24 hours for any breach; 72 hours for data breach per GDPR |
| Security patch response | Critical CVEs: 24 hours; High: 7 days |
| Audit report delivery | Annual SOC 2 Type II or equivalent |
| Support response | 4 hours for P1/security incidents |

### Data Processor Agreements

- DPA required before any personal data is shared with a vendor
- DPA must include: processing purpose, data categories, technical and organizational measures, subprocessor list, data return/deletion obligations on termination
- DPA reviewed annually and updated if processing activities change
- DPA registry maintained: `docs/vendor_dpas/` (confidential; not in public repo)

### Audit Rights

- All vendors processing Sensitive/Highly Sensitive data must provide:
  - Annual SOC 2 Type II, ISO 27001, or equivalent third-party audit report
  - Right for ScouterFRC to commission an independent audit with 30 days notice
  - Right to audit logs of access to ScouterFRC data upon request

### Breach Notification Requirements

Contractual obligation for all data processors:
- Notify ScouterFRC within **24 hours** of discovering any security incident affecting ScouterFRC data
- Provide: incident description, data affected, scope, mitigation steps taken, contact for further information
- Cooperate fully with ScouterFRC's incident response team
- Failure to notify constitutes material breach of contract

### Exit Procedures (Data Return / Deletion)

Upon termination of vendor relationship:

1. **Data return**: Vendor provides complete export of ScouterFRC data within 30 days in portable format
2. **Data deletion**: Vendor certifies deletion of all ScouterFRC data within 60 days
3. **Deletion certificate**: Written certification of deletion with method used
4. **Backup deletion**: Confirmation that backups containing ScouterFRC data have been purged
5. **Sub-processor notification**: Vendor notifies sub-processors to delete ScouterFRC data
6. **Audit trail**: ScouterFRC retains all logs and audit data independently of vendor

Exit procedure contractually required in all DPAs; breaches of exit obligations treated as data incidents.

---

## Appendix A: Security Controls Summary

| Control Domain | Key Controls | Phase |
|---------------|-------------|-------|
| Authentication | MFA, OAuth 2.0, SAML, strong password policy | Phase 1 |
| Authorization | RBAC, resource-level access, RLS, API scopes | Phase 1 |
| Encryption | TLS 1.2+, AES-256 at rest, field-level for PII | Phase 1 |
| API Security | Rate limiting, input validation, parameterized queries | Phase 1 |
| Secrets | Secrets manager, no hardcoded secrets, rotation | Phase 1 |
| Monitoring | Audit logging, failed login tracking, alerting | Phase 1–2 |
| Incident Response | IR plan, breach notification, post-incident review | Phase 1 |
| Compliance (FERPA) | Consent, access rights, third-party restrictions | Phase 1 |
| Compliance (GDPR) | DPA, right to erasure, portability, DPIA | Phase 2 |
| Video Security | Access control, encryption, retention, EXIF strip | Phase 2 |
| Penetration Testing | Annual third-party test, DAST, SAST | Phase 1+ |
| Vendor Management | Security questionnaire, DPA, audit rights | Phase 1 |

---

## Appendix B: Quick Reference — Data Subject Rights

| Right | Trigger | Response SLA | Contact |
|-------|---------|-------------|---------|
| Access | User request | 30 days | privacy@scouterfrc.com |
| Correction | User request | 30 days | privacy@scouterfrc.com |
| Erasure | User request | 30 days | privacy@scouterfrc.com |
| Portability | User request | 30 days | privacy@scouterfrc.com |
| Restriction | User request | 72 hours to acknowledge | privacy@scouterfrc.com |
| Object (GDPR) | User request | 30 days | privacy@scouterfrc.com |

---

*Last updated: 2026-04-20 | Maintained by: Security Team | Review cycle: Annual*
