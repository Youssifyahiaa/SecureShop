
# SecureShop - Threat Model

## 1. Introduction

SecureShop is a Python Flask-based e-commerce application
that allows customers to register, authenticate, browse
products, manage shopping carts, use coupons and purchase
products using store credit.

The application also provides administrator functionality
for managing users, products and coupons.

This threat model identifies the assets that must be
protected, possible attackers, application entry points,
trust boundaries and security threats.

The objective is to identify security risks during the
design and development stages rather than after deployment.

## 2. System Architecture

SecureShop uses the following technologies:

- Python
- Flask
- Flask Blueprints
- Flask-Login
- Flask-WTF / CSRF Protection
- Flask-Limiter
- SQLAlchemy
- SQLite development database
- HTML and Jinja templates

The general application architecture is:

Browser
    |
    v
Flask Routes and Blueprints
    |
    v
Input Validation and Security Checks
    |
    v
Authentication and Authorization
    |
    v
Application Business Logic
    |
    v
SQLAlchemy ORM
    |
    v
SQLite Database

The actual routes and data flows must be verified against
the integrated application.

## 3. Assets to Protect

The following assets are important to SecureShop:

| ID | Asset | Security Importance |
|---|---|---|
| A01 | Customer personal information | High |
| A02 | Password hashes | Critical |
| A03 | Authentication sessions and cookies | Critical |
| A04 | User roles and permissions | Critical |
| A05 | Product information and prices | High |
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

## 4. Stakeholders

The main stakeholders are:

1. Customers:
   Register, authenticate, browse products and purchase
   products.

2. Administrators:
   Manage users, products and coupons.

3. Developers:
   Maintain application functionality and database security.

4. Project team:
   Maintain the repository, security documentation and tests.

5. External users:
   Access the public website and its available functionality.

## 5. Potential Attackers

The following attacker categories are considered:

### 5.1 Unauthenticated attacker

An individual who has not registered or logged into
SecureShop.

Possible actions:
- Attempt to bypass login.
- Perform repeated login attempts.
- Submit malicious input.
- Access protected pages directly.

### 5.2 Malicious registered customer

An authenticated customer attempting to access
functionality beyond their permissions.

Possible actions:
- Access another customer's order.
- Manipulate shopping cart quantities.
- Attempt to access administrator pages.
- Manipulate coupon usage.
- Attempt to modify prices or account information.

### 5.3 Malicious administrator

An administrator abusing legitimate privileges.

Possible actions:
- Modify user roles.
- Change product information.
- Modify coupon settings.
- Perform unauthorized administrative actions.

### 5.4 Automated attackers and bots

Automated scripts attempting repeated requests.

Possible actions:
- Brute-force login attempts.
- Excessive requests.
- Automated registration.
- Resource exhaustion.

### 5.5 Compromised account attacker

An attacker who has obtained another user's credentials
or authentication session.

Possible actions:
- Impersonate the legitimate user.
- Access private information.
- Perform unauthorized transactions.

## 6. Application Attack Surfaces

### 6.1 Authentication

Entry points:
- Registration.
- Login.
- Email confirmation.
- Logout.

Possible threats:
- Brute-force attacks.
- Credential stuffing.
- Weak password handling.
- Session hijacking.
- Session fixation.
- Account impersonation.

### 6.2 Authorization

Entry points:
- Administrator pages.
- Customer account pages.
- Order history.
- Protected operations.

Possible threats:
- Privilege escalation.
- Broken access control.
- Insecure Direct Object Reference (IDOR).
- Unauthorized administrative access.

### 6.3 Product Catalogue

Entry points:
- Product search.
- Product details.
- Product management.

Possible threats:
- SQL injection.
- Cross-site scripting (XSS).
- Product price manipulation.
- Unauthorized product modification.

### 6.4 Shopping Cart

Entry points:
- Add product.
- Update quantity.
- Remove product.

Possible threats:
- Quantity manipulation.
- Invalid product identifiers.
- Stock manipulation.
- Price tampering.

### 6.5 Coupons and Newsletter

Entry points:
- Newsletter signup.
- Coupon generation.
- Coupon application.

Possible threats:
- Coupon reuse.
- Unauthorized coupon generation.
- Usage-limit bypass.
- Expired coupon acceptance.

### 6.6 Checkout and Orders

Entry points:
- Checkout requests.
- Order creation.
- Order history.
- Order details.

Possible threats:
- Store credit manipulation.
- Duplicate checkout.
- Unauthorized order access.
- Price manipulation.
- Transaction integrity failures.

### 6.7 Administration

Entry points:
- User management.
- Product management.
- Coupon management.

Possible threats:
- Administrator privilege escalation.
- Unauthorized changes.
- Audit log manipulation.
- CSRF attacks.

## 7. Trust Boundaries

SecureShop contains several important trust boundaries.

### Boundary 1: Browser to Flask Application

The browser is considered untrusted.

All submitted information must be validated on the server.

The application must not trust browser-supplied prices,
discounts, roles or account balances.

### Boundary 2: Application Security Layers

Authentication identifies the user.

Authorization determines which actions the user can perform.

Input validation checks information before it is processed.

### Boundary 3: Flask Application to Database

SQLAlchemy manages database operations.

Database operations must use safe ORM or parameterized
queries.

Sensitive information must not be exposed through
database responses.

## 8. STRIDE Threat Analysis

STRIDE is used to identify six categories of security
threats.

| Category | SecureShop Threat | Security Objective |
|---|---|---|
| Spoofing | Attacker impersonates a customer using stolen credentials | Authentication |
| Tampering | Attacker modifies product prices or order information | Integrity |
| Repudiation | Administrator denies performing a sensitive action | Accountability |
| Information Disclosure | Customer accesses another customer's order | Confidentiality |
| Denial of Service | Attacker sends excessive requests to the application | Availability |
| Elevation of Privilege | Customer attempts to access administrator functions | Authorization |

### 8.1 Spoofing

Threat:
An attacker attempts to impersonate a legitimate customer
using stolen credentials or authentication sessions.

Potential impact:
Unauthorized account access and disclosure of customer data.

Required defenses:
- Secure password hashing.
- Login rate limiting.
- Email confirmation.
- Secure session management.
- Appropriate authentication checks.

### 8.2 Tampering

Threat:
An attacker modifies prices, quantities, coupon discounts,
store credit or order information.

Potential impact:
Financial loss and database integrity violations.

Required defenses:
- Server-side price calculations.
- Input validation.
- Database constraints.
- Transaction management.
- Server-side authorization.

### 8.3 Repudiation

Threat:
An administrator denies performing an important
administrative operation.

Potential impact:
Difficulty investigating suspicious actions.

Required defenses:
- Audit logging.
- Event timestamps.
- Actor identification.
- Recording important administrative actions.
- Protecting audit records from unauthorized modification.

### 8.4 Information Disclosure

Threat:
An authenticated customer accesses another customer's
private information or order history.

Potential impact:
Privacy violations and exposure of personal information.

Required defenses:
- Authentication.
- Ownership verification.
- Access control.
- Safe error messages.
- Protection of sensitive database fields.

### 8.5 Denial of Service

Threat:
An attacker sends excessive requests or repeatedly
submits resource-intensive operations.

Potential impact:
Application slowdown or unavailability.

Required defenses:
- Rate limiting.
- Request-size restrictions.
- Input validation.
- Resource-aware request handling.

### 8.6 Elevation of Privilege

Threat:
A normal customer attempts to obtain administrator
permissions or access administrative functionality.

Potential impact:
Unauthorized management of users, products and coupons.

Required defenses:
- Server-side role verification.
- admin_required protection.
- Deny-by-default authorization.
- CSRF protection.
- Audit logging of sensitive actions.

## 9. DREAD Risk Assessment

DREAD is used to estimate the severity of identified threats.

The five factors are:

1. Damage.
2. Reproducibility.
3. Exploitability.
4. Affected Users.
5. Discoverability.

Each factor receives a score from 1 to 10.

Risk Score = (D + R + E + A + Dsc) / 5

### Initial Threat Prioritization

| Threat | D | R | E | A | Dsc | Average |
|---|---:|---:|---:|---:|---:|---:|
| Privilege escalation | 9 | 8 | 7 | 8 | 7 | 7.8 |
| Product/credit tampering | 9 | 8 | 7 | 7 | 8 | 7.8 |
| Unauthorized order access (IDOR) | 8 | 8 | 7 | 7 | 8 | 7.6 |
| Account takeover | 8 | 8 | 6 | 7 | 8 | 7.4 |
| Denial of Service | 7 | 8 | 6 | 8 | 7 | 7.2 |
| Coupon abuse | 6 | 8 | 7 | 6 | 8 | 7.0 |

These scores are initial design estimates, not confirmed
vulnerabilities or penetration-test results.

They must be reviewed with the Red Team and updated
when implementation evidence becomes available.

## 10. Security Assumptions and Limitations

- The browser and all submitted user input are untrusted.
- Customer and administrator permissions must be
  verified by the server.
- Sensitive operations must be protected against
  unauthorized modification.
- The database must preserve financial and account integrity.
- Local development configuration is not equivalent
  to production security.
- SecureShop does not currently claim to implement
  biometric authentication, smart-card authentication
  or an AI-agent authentication system.
- Course topics without a direct application entry point
  must be recorded for an instructor-approved
  demonstration or applicability decision.


## Authentication and Account Recovery - Verified Controls

Following the integration of Youssef's authentication
security improvements (PR #5), the following controls
are implemented:

1. Password recovery requests use generic responses
   to prevent account enumeration.

2. Password reset tokens are signed, expire after
   30 minutes and can only be used once.

3. Password reset operations enforce the password policy.

4. Existing authentication sessions are invalidated
   after password reset.

5. User roles are controlled by the server and are
   never accepted from request-submitted role fields.

6. Login uses generic authentication error messages.

7. Open redirects are prevented through destination
   validation.

8. Session fixation is mitigated through session
   handling after authentication.

9. The shopping cart is sanitized during login.

10. Password reset requests are rate-limited to
    five requests per hour.

11. Reset tokens are protected against leakage
    through the Referer header.

### Password Recovery Entry Points

The application now includes:

- `auth.reset_request`
  URL: `/reset-password`

- `auth.reset_password`
  URL: `/reset-password/<token>`

The reset request is linked from the login page.
The token-based reset page is accessed through
the password-reset link.

### Testing Evidence

The authentication and recovery security tests
are maintained in:

`tests/test_auth_recovery.py`

The exact test function names and results should
be recorded in the Security Coverage Matrix.

### Remaining Authentication Work

Administrator MFA is planned for 4 December 2026.
It is not yet considered implemented.

The planned MFA implementation will use the existing
admin_required authorization mechanism.


## 11. Conclusion

Threat modelling helps SecureShop identify security
risks before they become vulnerabilities.

STRIDE identifies possible threats, while DREAD helps
prioritize them.

The identified threats will guide security requirements,
implementation decisions, testing and the Security
Coverage Matrix.

This document must be updated as the application
architecture and implementation evolve.

## 12. Data Flow Diagram

The general SecureShop data flow is:

Browser
    |
    v
HTTP Request
    |
    v
Flask Routes and Blueprints
    |
    v
CSRF and Input Validation
    |
    v
Authentication and Authorization
    |
    v
Business Logic
    |
    v
SQLAlchemy ORM
    |
    v
SQLite Database

The application returns the processed result to the browser.

### Trust Boundaries

1. Browser to Flask:
   Untrusted user input enters the application.

2. Flask security layer:
   Authentication, authorization and validation
   determine whether an operation is permitted.

3. Application to database:
   Business logic performs authorized database operations
   through SQLAlchemy.

### Data States

- Data in transit: Browser requests and responses.
- Data in use: Information processed by Flask.
- Data at rest: Records stored in SQLite.