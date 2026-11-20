# SecureShop – Phase 1 Security Design Summary

- **Course:** Software Security
- **Project:** SecureShop
- **Phase:** Phase 1 – Security Design and Initial Implementation
- **Date:** 20 November 2026
**Team:** Sandy, Ali, Mark and Youssef

---

## 1. Executive Summary

SecureShop is a Python Flask-based e-commerce application designed to provide secure customer registration, authentication, product browsing, shopping cart management, coupon redemption, checkout and administrative functionality.

The purpose of Phase 1 is to identify the application's security requirements, analyze potential threats, establish security boundaries and implement initial security controls.

The security design follows three main principles:

1. Confidentiality – prevent unauthorized access to customer and application information.
2. Integrity – prevent unauthorized modification of prices, orders, account roles and financial records.
3. Availability – protect the application against excessive requests and resource exhaustion.

Threat identification uses STRIDE, while DREAD provides an initial method of prioritizing identified risks.

## 2. Application Architecture

SecureShop uses the following technologies:

| Component | Technology |
|---|---|
| Programming language | Python |
| Web framework | Flask |
| Authentication | Flask-Login |
| Form and CSRF protection | Flask-WTF |
| Rate limiting | Flask-Limiter |
| Database access | SQLAlchemy |
| Development database | SQLite |
| Frontend | HTML, CSS and Jinja templates |
| Version control | Git and GitHub |
| Automated testing | pytest |

### General architecture

Browser → Flask Routes → Security Checks → Business Logic → SQLAlchemy → SQLite Database.

The browser is treated as an untrusted environment. Security-sensitive decisions are performed by the server.

## 3. Protected Assets

The security design identifies 15 important assets.

| ID | Protected asset | Priority |
|---|---|---|
| A01 | Customer personal information | High |
| A02 | Password hashes | Critical |
| A03 | Authentication sessions | Critical |
| A04 | User roles and permissions | Critical |
| A05 | Product prices and stock | High |
| A06 | Shopping cart information | Medium |
| A07 | Coupons and redemption records | High |
| A08 | Store credit balances | Critical |
| A09 | Orders and order history | High |
| A10 | Newsletter subscriber information | Medium |
| A11 | Administrator functions | Critical |
| A12 | Audit logs | High |
| A13 | Application configuration and secrets | Critical |
| A14 | Database availability and integrity | High |
| A15 | Source code and GitHub repository | High |

The most critical assets are authentication information, account permissions, store credit and administrator functionality.

## 4. Threat Modelling

### 4.1 Potential attackers

The threat model considers:

- Unauthenticated attackers attempting to access protected pages.
- Malicious registered customers attempting to access other accounts or manipulate transactions.
- Malicious administrators abusing their privileges.
- Automated bots performing brute-force or excessive requests.
- Attackers using compromised credentials or sessions.

### 4.2 STRIDE analysis

| STRIDE category | SecureShop threat | Required defense |
|---|---|---|
| Spoofing | Impersonating another customer | Secure password hashing and authentication |
| Tampering | Changing prices, quantities or credit | Server-side validation and database integrity |
| Repudiation | Denying administrative actions | Independent audit logging |
| Information Disclosure | Accessing another customer's information | Authentication and ownership verification |
| Denial of Service | Sending excessive requests | Rate limiting and request restrictions |
| Elevation of Privilege | Customer accessing administrator functions | Server-side role verification |

### 4.3 DREAD prioritization

The initial threat assessment uses five factors, each scored from 1 to 10.

| Threat | Initial average risk |
|---|---:|
| Privilege escalation | 7.8 |
| Product/credit tampering | 7.8 |
| Unauthorized order access (IDOR) | 7.6 |
| Account takeover | 7.4 |
| Denial of Service | 7.2 |
| Coupon abuse | 7.0 |

These are initial design estimates, not confirmed penetration-test findings.

## 5. Trust Boundaries

SecureShop uses three main trust boundaries.

**Boundary 1 – Browser to Flask**

- Browser input is untrusted.
- Server-side validation is required.
- Prices, roles and account balances must not be trusted when supplied by the browser.

**Boundary 2 – Application security layers**

- Authentication identifies the user.
- Authorization determines permitted actions.
- Input validation checks submitted information.
- Business logic performs authorized operations.

**Boundary 3 – Flask application to database**

- SQLAlchemy manages database operations.
- ORM or parameterized queries must be used.
- Database integrity and sensitive information must be protected.

## 6. Security Controls and Implementation

### 6.1 Authentication and account security

The authentication implementation includes:

- Argon2id password hashing.
- Email confirmation.
- Generic login error messages.
- Registration and login rate limiting.
- Password recovery with signed, expiring tokens.
- Single-use password reset tokens.
- Session invalidation following password reset.
- Protection against open redirects.
- Session fixation mitigation.
- Guest cart sanitization during login.

The successful-login session baseline also records:

- `login_ua_hash`
- `login_ip`
- `login_role`
- `login_at`

The User-Agent is stored as a SHA-256 hash rather than as a raw browser identifier.

### 6.2 Administrator access control

The administrator security mechanism uses the `admin_required` decorator.

It verifies that:

1. The user is authenticated.
2. The user has the administrator role.
3. The session risk assessment permits the requested action.

Unauthorized customers receive HTTP 403.

### 6.3 Customer account protection

The account functionality includes:

- Authentication requirements.
- Customer-specific order retrieval.
- Ownership filtering.
- Restricted profile updates.
- Audit logging of profile changes.

Customers cannot retrieve another customer's orders through the account dashboard.

### 6.4 Audit logging

SecureShop includes an audit logging service.

It records relevant security events, including:

- Event type.
- User and actor identifiers.
- Event details.
- Client IP address.
- UTC timestamp.

The audit service uses an independent transaction so that logging does not accidentally commit an unrelated application transaction.

### 6.5 Session risk assessment

The session risk mechanism identifies suspicious session behavior.

| Indicator | Risk points |
|---|---:|
| Invalid session/user binding | 100 |
| Missing User-Agent | 10 |
| Missing IP | 10 |
| Non-fresh session | 10 |
| Non-permanent session | 10 |
| Changed User-Agent | 30 |
| Changed IP | 15 |
| Request burst exceeding 30 requests in 60 seconds | 25 |
| Role changed since login | 50 |

The maximum score is 100.

The assessment is implemented as a pure function receiving the current time as an argument. It does not independently modify sessions or write audit records.

Risk handling:

- 0–29: Low risk; allow.
- 30–59: Medium risk; additional administrator verification is required.
- 60–99: High risk; additional administrator verification is required.
- 100: Critical risk; terminate the session and record an audit event.

Until administrator TOTP is implemented, medium- and high-risk administrator requests are denied with HTTP 403 and audited.

Live request-burst tracking and checkout password step-up remain integration tasks.

## 7. Security Testing and Evidence

The project uses pytest to validate security behavior.

The Phase 1 test results recorded on 20 November 2026 include:

| Test area | Result |
|---|---:|
| Administrator access control | 4 passed |
| Customer account protection | 12 passed |
| Audit logging and risk integration | 31 passed |
| Session risk, policy and integration | 45 passed |
| Authentication | 34 passed |
| Full test suite | 193 passed |

Additional naive-versus-secure demonstrations cover:

- Customer order IDOR.
- Administrator access control.
- Audit transaction isolation.

The corresponding evidence is maintained in `docs/evidence/`.

Passing tests demonstrate the behavior covered by those tests. They do not establish that every possible attack has been prevented.

## 8. Course Security Coverage

The project design considers the required CET431 security topics:

- CIA security objectives.
- Authentication, authorization and accountability.
- STRIDE and DREAD.
- OWASP security risks.
- SQL injection and other injection attacks.
- Cross-site scripting.
- Broken access control and IDOR.
- Security misconfiguration.
- Cryptographic failures.
- Session security.
- Password, PIN and security-question attacks.
- Possession authentication and smart cards.
- Physiological and behavioral biometrics.
- Location-based and time-based authentication.
- OTP and multi-factor authentication.
- Passkeys and authentication recovery.
- Availability and resource-exhaustion attacks.
- Secure configuration and dependency management.

Topics without an implemented SecureShop feature must be documented as pending, not implemented or requiring an instructor-approved scope decision.

## 9. Remaining Implementation Work

| Area | Responsible member | Remaining work |
|---|---|---|
| Session integration | Youssef | Coordinate login baselines and integrate bounded request-burst tracking |
| Authentication | Youssef | Complete agreed authentication integration |
| Product catalogue and cart | Mark | Complete implementation and security testing |
| Coupons and newsletter | Ali | Complete coupon issuance, recipient binding and redemption security |
| Administration | Sandy | Complete documentation, security evidence and integration review |
| Security integration | All | Integrate features and verify database migrations and full test suite |

Administrator TOTP/passkey verification, checkout step-up authentication and applicable course-topic demonstrations also remain outstanding.

## 10. Phase 1 Conclusion

Phase 1 establishes the initial security architecture and identifies the major threats affecting SecureShop.

The project has implemented and tested important security mechanisms covering authentication, administrator access control, customer account protection, session risk assessment and audit logging.

The threat model, asset inventory, attack surface inventory and data flow diagram provide the foundation for further security implementation.

The next stage focuses on completing the remaining website features, integrating the team members' work, expanding adversarial security testing and updating the Security Coverage Matrix.

The Phase 1 design is an initial security baseline, not a final security certification.
