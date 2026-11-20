# SecureShop — Security Coverage Matrix

**Phase 1 working draft — 20 November 2026**
**Team:** Sandy (admin/account, security coordination), Ali (promotions), Mark (catalogue/cart), Youssef (auth/checkout).

This matrix tracks the CET431 project requirement to identify an attack, its root cause, the in-application defense, its location, and evidence **for every course security topic**. It does not claim that a passing test suite proves every topic is secure.

## How to read this file

- **Tested:** A specific defensive test exists and has passed locally; further manual attack evidence may still be required.
- **Partial:** Some defenses exist, but relevant features, adversarial tests, or integration are unfinished.
- **Documented:** Security reasoning exists; no complete executable defense is claimed.
- **Pending:** Work has not been demonstrated in the application.
- **Scope decision:** The topic is taught, but applying it to SecureShop needs an instructor-approved approach. Do not treat it as exempt without approval.
- **Evidence pending:** A test file or mitigation is known, but no saved naive-versus-secure attack transcript has been verified.

Where a filename is listed below, it is a **location to inspect**, not proof of complete protection. Update each row after the relevant team member tests it.

## A. Course-topic matrix

| ID | Course topic | SecureShop attack scenario and root cause | Defense and code/document location | Evidence, owner, status |
|---|---|---|---|---|
| C01 | CIA objectives | Exposure of customer data; unauthorized price/order changes; service disruption. Root causes: excessive access, trusting requests, unavailable services. | Confidentiality: login/authorization; integrity: database checks and server-side prices; availability: request limits. See `security_requirements.md` §2 and `asset_inventory.md`. | Sandy + all; **Documented / Partial**. Test each concrete threat under its own row. |
| C02 | Authentication, authorization, accountability | Fake identity, customer opening `/admin/`, or an action with no trace. Root causes: weak login, missing role check, missing events. | `app/auth/routes.py`, `app/admin/decorators.py`, `app/admin/audit.py`, `app/models/audit_log.py`. | `tests/test_auth.py`, `tests/test_admin.py`, `tests/test_audit.py`, `tests/test_admin_risk_integration.py`; Youssef/Sandy; **Partial** (cross-feature event coverage pending). |
| C03 | STRIDE and DREAD | Threats may be missed or poorly prioritized when assets, entry points and actors are not identified. | `threat_model.md`, `asset_inventory.md`, `attack_surface_inventory.md`, `data_flow_diagram.md`. | Sandy; **Documented**, review that each STRIDE category and DREAD priority has concrete entries. |
| C04 | OWASP security risks | Injection, authorization bypass, cryptographic failures and insecure design across different routes. Root cause: examining only the happy path. | Requirements in `security_requirements.md`; use C05–C10, C17–C18 and feature rows below for explicit controls. | Sandy + all; **Partial**. Cross-feature OWASP mapping and negative tests are pending. |
| C05 | SQL injection and other injection | A crafted name, search term, coupon, or order parameter changes a query. Root cause: building commands or SQL from raw input. | Parameterized ORM queries, e.g. `app/admin/routes.py`; other feature queries must be reviewed when merged. | `tests/test_admin_users.py` confirms search behavior but is **not** an SQL-injection proof. Sandy + Mark/Ali/Youssef; **Partial; attack evidence pending**. |
| C06 | Cross-site scripting (XSS) | An attacker enters markup in names, product data, or comments and it executes in another browser. Root cause: unsafe HTML/JS output. | Jinja templates under `app/templates/`; escape output and avoid marking untrusted content `safe`. | Sandy + all; **Partial**. Add stored/reflected XSS payload tests for every relevant displayed field. |
| C07 | Broken access control and IDOR | A customer requests another user's profile/order or an admin URL. Root cause: trusting URL IDs instead of ownership/roles. | `app/admin/decorators.py`, `app/account/routes.py`; checkout/order ownership checks still need end-to-end verification. | `tests/test_admin.py`, `tests/test_admin_users.py`, `tests/test_account.py`; Sandy/Youssef; **Partial**. Add cross-user order tests. |
| C08 | Security misconfiguration | Debug traces, exposed development secrets, unsafe cookies, or missing DB protections. Root cause: insecure defaults/deployment. | `app/config.py`, `app/errors.py`, `app/extensions.py`, `.env.example`, `.gitignore`. | `tests/test_app.py`, `tests/test_db_integrity.py`; Sandy/Youssef; **Partial**. Confirm deployment settings separately. |
| C09 | Cryptographic failures | Password or recovery token disclosure, insecure hashing, reused/expired reset links. Root cause: weak storage/signing/key handling. | `app/models/user.py` (Argon2id), `app/auth/tokens.py`, `app/config.py`; secrets must remain outside Git. | `tests/test_auth.py`, `tests/test_auth_recovery.py`; Youssef; **Partial** until token and secrets evidence is collected. |
| C10 | Session security | Session fixation, session reuse after reset, role/browser/IP changes, request bursts. Root cause: unbound or stale sessions. | `app/auth/routes.py`, `app/extensions.py`, `app/admin/session_risk.py`, `app/admin/risk_policy.py`, `app/admin/decorators.py`. | `tests/test_auth_recovery.py`, `tests/test_session_risk.py`, `tests/test_admin_risk_policy.py`, `tests/test_admin_risk_integration.py`; Sandy/Youssef; **Partial**. Login baselines and burst tracker are not wired in the local auth files yet. |
| C11 | Password, PIN and security-question attacks | Guessing/reusing passwords, weak resets, or bypassing knowledge factors. Root cause: weak password policy or recovery. | `app/auth/forms.py`, `app/auth/routes.py`, `app/auth/common_passwords.txt`; the site currently does not use PINs/security questions. | `tests/test_auth.py`, `tests/test_auth_recovery.py`; Youssef; **Partial**, PIN/question demonstration needs scope decision. |
| C12 | Possession authentication and smart cards | A stolen password grants privileged access without a second factor. Root cause: password-only administration. | Planned administrator TOTP in auth; no smart-card integration is claimed. | Youssef/Sandy; **Pending / Scope decision** on smart-card demonstration. |
| C13 | Physiological and behavioral biometrics | Impersonation or spoofing of a biometric authentication factor. Root cause: trusting an unverified factor. | No biometric collection or verification is implemented in SecureShop. | Sandy/Youssef; **Scope decision**. Do not claim a biometric defense without a demonstrable implementation or instructor-approved substitute. |
| C14 | Location- and time-based authentication | Login from a changed location/time without a risk check. Root cause: ignoring context or treating IP as authoritative location. | Login IP and UTC login time are planned session baselines; this is **not** geographic authentication. | Youssef/Sandy; **Pending / Scope decision**. Verify whether a demo is required. |
| C15 | OTP and multi-factor authentication | Password compromise reaches administrator actions. Root cause: no step-up factor. | Risk policy currently denies medium/high-risk admin access until MFA exists; admin TOTP is planned in auth. | `tests/test_admin_risk_policy.py`, `tests/test_admin_risk_integration.py` prove denial, **not OTP**; Youssef/Sandy; **Pending MFA**. |
| C16 | Passkeys and authentication recovery | Phishing and unsafe password reset. Root cause: phishable factors or replayable links. | Reset-request/reset-password routes and nonce/version checks exist; passkeys are planned, not implemented. | `tests/test_auth_recovery.py`; Youssef; **Partial** (recovery), **Pending** (passkeys). |
| C17 | Availability/resource exhaustion | Flooding login/reset/search, or submitting oversized bodies. Root cause: unbounded requests/work. | `app/extensions.py` limiter, auth route limits, `app/config.py` request-size cap. Extend protection to new routes when merged. | `tests/test_auth.py`, `tests/test_app.py` require evidence review; Youssef/all; **Partial**. Save rate-limit/oversize responses. |
| C18 | Secure configuration/dependency management | Leaked keys, outdated packages, insecure defaults. Root cause: unmanaged configuration/dependencies. | `.env.example`, `.gitignore`, `app/config.py`, dependency lock/requirements files (verify versions and audit). | Sandy + all; **Partial**. Collect dependency review and production configuration checklist. |

## B. All required website features and their attack surfaces

This table prevents the team from testing one vulnerability only in a single feature. For every new route or form, revisit the relevant C01–C18 rows.

| Feature | Owner | Inputs/actions to attack | Current status and evidence |
|---|---|---|---|
| F1 Registration/login | Youssef | Registration, confirmation, login, logout, reset forms, signed links, redirects | **Implemented; additional adversarial evidence pending.** See `tests/test_auth.py`, `tests/test_auth_recovery.py`. |
| F2 Product catalogue | Mark | Search/filter query, product IDs, prices/images, public listing/detail | **Pending integration.** Test search injection/XSS and price/stock access after merge. |
| F3 Cart | Mark | Add/remove/update quantity, forged product IDs/quantities, session cart | **Pending integration.** Test integer bounds, stock checks and tampering. |
| F4 Newsletter/coupons | Ali | Email signup, coupon code, discount constraints, recipient binding | **Pending integration.** Test duplicates, code guessing, forwarded codes and simultaneous redemption. |
| F5 Checkout/orders | Youssef | Subtotal, discount, order IDs, credit balance, repeat checkout | **Pending integration.** Test trusted totals, credit atomicity, IDOR and replay/idempotency. |
| F6 Customer account | Sandy | Profile update, viewing own orders, authenticated session | **Implemented in part.** See `tests/test_account.py`; recheck order history after checkout merges. |
| F7 Admin panel | Sandy; product/coupon owner support | Users, roles, audit history, product/coupon administration | **Partial.** Dashboard, read-only user search, audit view and risk gate tested; product/coupon management pending. See `tests/test_admin*.py`. |
| F8 Usability | Sandy + all | Navigation, form feedback, mobile layout, accessible errors | **Partial.** Shared CSS/templates exist; conduct mobile/manual checks after all features merge. |

## C. General requirement cross-reference

| Requirement | Main course topics | Primary evidence or gap |
|---|---|---|
| SR-01 Authentication | C02, C09, C11, C15, C16 | Youssef auth tests; MFA/passkeys pending. |
| SR-02 Authorization | C02, C07 | Admin and account tests; order ownership pending. |
| SR-03 Access control | C02, C07, C10 | Admin gate and risk tests; all new routes must be reviewed. |
| SR-04 Input validation | C05, C11, C17 | Auth forms; catalogue/cart/coupon/checkout negative tests pending. |
| SR-05 Output security | C06, C08 | Jinja rendering review; malicious-input output evidence pending. |
| SR-06 CSRF | C04, C08 | Flask-WTF is configured; confirm each state-changing route and capture forged-request tests. |
| SR-07 Database security | C05, C07, C09 | ORM, foreign keys, constraints; migrations and transaction tests. |
| SR-08 Session security | C10, C14, C15 | Score and policy tests; live baseline/burst integration pending. |
| SR-09 Security logging | C02, C10 | Audit model/service/UI tests; security-event coverage pending. |
| SR-10 Secrets/configuration | C08, C09, C18 | Environment-only secrets and Git ignore; deployment audit pending. |
| SR-11 Safe error handling | C06, C08, C17 | `app/errors.py`; attack-response evidence pending. |
| SR-12 Business logic integrity | C04, C07, C17 | Mark/Ali/Youssef cart, coupons and checkout integration pending. |

## D. Evidence required for every applicable attack

For **each course row that applies to a SecureShop feature**, record the following. A passing unit test alone is not a substitute for the course's required naive-versus-secure comparison.

1. **Attack goal and root cause:** one or two sentences.
2. **Naive demonstration:** in a disposable, isolated version owned by the team, show the failure safely. Never deliberately weaken the shared `main` branch.
3. **Defended demonstration:** identify the same input/request against the defended SecureShop route and show the safe response.
4. **Exact reproduction steps:** HTTP method/path, sanitized inputs, account role, expected and observed result. Never include real passwords, cookies, email tokens, payment data or private personal information.
5. **Code and tests:** filename and test function name; include a screenshot or a sanitized test run where useful.
6. **Result:** `PASS`, `FAIL`, `PARTIAL`, or `SCOPE DECISION`, with date and responsible team member.

Suggested evidence index: `docs/attack_evidence_index.md`. Link screenshots or sanitized logs from the index, and keep a reference to any separate Red Team report.

## E. Outstanding Phase 1 coordination

- **Youssef:** Add `login_ua_hash`, `login_ip`, `login_role`, and `login_at` on successful login; agree on a bounded server-side request-burst tracker. Re-test the interaction with Flask-Login session protection.
- **Mark:** Finish catalogue/cart routes, secure server-side prices and stock checks, and product migration; provide negative test names.
- **Ali:** Finish newsletter/coupon issuance, assigned-email checks, atomic redemption contract, migration and adversarial tests.
- **Sandy:** Finish this matrix's evidence pointers, review administrator risk events, demonstrate read-only user/audit pages, and prepare Phase 1 security design summary.
- **Team:** Complete a working site integration, verify migrations in the agreed order (**Mark → Ali → Sandy → Youssef's later OrderItem**), and run the full suite after each merge.
- **Instructor:** Confirm the four-person team arrangement against the project description's six-person requirement; resolve scope for smart cards, biometrics and location/time authentication if those topics need demonstrations.

## F. Phase 1 versus Phase 2

**Phase 1 (Week 9):** requirements/design, threat model, first working website and defenses for topics taught so far. This matrix should show honest current coverage and remaining work.

**Phase 2 (Week 14):** full website, complete Security Coverage Matrix, Security Design Report, Attack Evidence Report, Red Team Penetration Test Report, and live demonstration.

**Update rule:** do not change any item to **Tested** until its named defensive test passes and its relevant feature actually runs. Do not mark an unbuilt factor (TOTP, passkey, smart card, biometric) as implemented because the idea is documented.
