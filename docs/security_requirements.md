
# SecureShop - Security Requirements

## 1. Introduction

This document defines the security requirements for
SecureShop.

The requirements are designed to protect customer
information, authentication sessions, product information,
financial transactions and administrative functionality.

Security must be considered throughout the application
development process.

## 2. Security Objectives

SecureShop must satisfy the following security objectives.

### 2.1 Confidentiality

Only authorized users may access sensitive information.

Examples:
- Customer personal information.
- Password hashes.
- Authentication sessions.
- Order history.
- Newsletter subscriber information.

### 2.2 Integrity

Application data must not be modified by unauthorized users.

Examples:
- Product prices.
- Shopping cart quantities.
- Coupon usage.
- Store credit balances.
- Orders and transactions.
- User roles.

### 2.3 Availability

SecureShop must remain available to legitimate users.

Protection includes:
- Rate limiting.
- Request-size restrictions.
- Safe request handling.
- Protection against excessive requests.

## 3. General Security Requirements

### SR-01: Authentication

The application must identify users before allowing
access to protected functionality.

Passwords must never be stored in plaintext.

Secure password hashing algorithms must be used.

### SR-02: Authorization

Every protected operation must verify the user's
permissions on the server.

Administrator functionality must only be accessible
to authorized administrators.

### SR-03: Access Control

Customers must only access their own private information,
accounts and orders.

The application must prevent unauthorized direct
object access.

### SR-04: Input Validation

All user-submitted information must be validated
on the server.

This includes:
- Email addresses.
- Passwords.
- Product identifiers.
- Quantities.
- Coupon codes.
- Profile information.

### SR-05: Output Security

User-provided information must be safely displayed.

The application must prevent unsafe HTML and
JavaScript execution through user-controlled content.

### SR-06: CSRF Protection

All state-changing operations must use POST or
another appropriate non-GET method and CSRF protection.

### SR-07: Database Security

Database queries must use SQLAlchemy ORM or
parameterized queries.

The application must protect database integrity
using appropriate constraints and transactions.

### SR-08: Session Security

Authentication sessions must be managed securely.

Sessions must be invalidated after logout.

Sensitive operations must require valid authentication
and authorization.

### SR-09: Security Logging

Important security events must be recorded.

Examples:
- Failed login attempts.
- Administrative changes.
- Role modifications.
- Important account actions.
- Checkout failures.

Logs must never contain passwords, authentication
tokens, session cookies or payment information.

### SR-10: Secrets and Configuration

Application secrets must be stored in environment
variables rather than source code.

The .env file must never be committed to GitHub.

Debug mode must not be enabled in production.

### SR-11: Safe Error Handling

The application must provide understandable error
messages without exposing stack traces, internal
database information or sensitive configuration.

### SR-12: Business Logic Integrity

The server must calculate important financial values.

Prices, discounts, balances and order totals must
never be trusted from browser-submitted values.

## 4. Feature-Specific Security Requirements

### F1: Registration and Login

Requirements:

1. Passwords must be hashed using a secure password
   hashing algorithm.
2. Email confirmation must be enforced before login.
3. Login attempts must be rate-limited.
4. Authentication errors must not reveal whether
   an email address exists.
5. Sessions must be managed securely.
6. Logout must invalidate the authenticated session.
7. Authentication forms must have CSRF protection.

Misuse Case:

An attacker repeatedly attempts to guess a customer's
password.

Expected Secure Behavior:

The application applies rate limiting, uses secure
password hashing and rejects invalid authentication.

Acceptance Tests:
- Register a new customer.
- Confirm the customer's email.
- Log in using valid credentials.
- Attempt login with an incorrect password.
- Attempt repeated login requests.
- Log out and verify that the session is invalidated.

### F2: Product Catalogue

Requirements:

1. Product information must be retrieved from the database.
2. Product prices must not be accepted from the browser.
3. Product identifiers must be validated.
4. Product prices and stock must not be negative.
5. Database queries must use safe ORM operations.
6. Product descriptions must be safely displayed.
7. Inactive products must not be available for normal purchase.

Misuse Case:

An attacker submits a modified product price or
malicious product search input.

Expected Secure Behavior:

The server retrieves trusted product information from
the database and safely processes the submitted input.

Acceptance Tests:
- View available products.
- Open a product detail page.
- Submit invalid product identifiers.
- Test search input validation.
- Verify that browser-supplied prices are not trusted.

### F3: Shopping Cart

Requirements:

1. The cart must store product identifiers and quantities.
2. Prices and totals must be calculated by the server.
3. Product stock must be checked before accepting quantities.
4. Cart modification operations must use POST and CSRF.
5. Invalid quantities and product identifiers must be rejected.

Misuse Case:

A customer modifies the submitted quantity or attempts
to add more products than available stock.

Expected Secure Behavior:

The server validates the product, quantity and stock
before updating the cart.

Acceptance Tests:
- Add a valid product.
- Change the product quantity.
- Remove a product.
- Submit an invalid quantity.
- Attempt to exceed available stock.
- Verify that changing browser data cannot change
  the trusted product price.

### F4: Coupons and Newsletter

Requirements:

1. Coupon codes must be validated by the server.
2. Expired or inactive coupons must be rejected.
3. Coupon usage limits must be enforced.
4. Per-user redemption limits must be enforced.
5. Coupon redemption must prevent duplicate usage.
6. Coupon discounts must not exceed the order subtotal.
7. Newsletter signup must validate the submitted email.
8. Coupon redemption must be included in the order transaction.
9. Used counts and redemption records must not be
   directly editable through the Admin Panel.

Misuse Case:

A customer attempts to reuse a coupon after reaching
the allowed redemption limit.

Expected Secure Behavior:

The server rejects the redemption and does not
incorrectly increase the coupon usage count.

Acceptance Tests:
- Apply a valid coupon.
- Apply an expired coupon.
- Apply an inactive coupon.
- Exceed the usage limit.
- Attempt repeated redemption.
- Attempt unauthorized coupon modification.

### F5: Checkout and Orders

Requirements:

1. Checkout must require an authenticated,
   confirmed customer.
2. The customer identity must come from the
   authenticated server-side session.
3. The subtotal must be calculated from trusted
   database product prices.
4. Store credit must never become negative.
5. Credit changes must use the CreditLedger.
6. Orders, order items, credit changes and coupon
   redemption must be handled atomically.
7. Failed checkout operations must roll back.
8. Duplicate checkout requests must be handled safely.
9. Customers must only view their own orders.

Misuse Case:

An attacker changes the submitted checkout total
or attempts to submit the same checkout twice.

Expected Secure Behavior:

The server recalculates the order total and protects
the transaction against unauthorized changes and
duplicate processing.

Acceptance Tests:
- Complete a valid checkout.
- Attempt checkout with insufficient credit.
- Modify browser-submitted financial values.
- Attempt duplicate checkout.
- Attempt to access another customer's order.
- Verify that failed transactions do not consume credit
  or coupon usage.

### F6: User Account

Requirements:

1. Users must authenticate before accessing their accounts.
2. Users must only access their own account information.
3. Profile updates must validate submitted fields.
4. Password hashes must never be displayed.
5. Credit balances must not be directly edited.
6. Role changes must be authorized and audited.
7. Order history must enforce ownership verification.

Misuse Case:

Customer A changes an account or order identifier
to access Customer B's private information.

Expected Secure Behavior:

The application checks ownership using the authenticated
user's identity and denies unauthorized access.

Acceptance Tests:
- View a customer's own profile.
- Update permitted profile information.
- Attempt to access another customer's profile.
- Attempt to access another customer's order.
- Attempt to modify protected account fields.

### F7: Administration

Requirements:

1. All administrator routes must use server-side
   administrator authorization.
2. Unauthenticated visitors must be redirected to login.
3. Authenticated customers must receive HTTP 403.
4. Administrator roles must be checked using
   current_user.role.
5. Customers must not be able to change their roles.
6. Password hashes must never be editable through
   the Admin Panel.
7. Credit balances must only be changed through
   approved CreditLedger operations.
8. Sensitive administrator operations must be audited.
9. All administrative modifications must use CSRF
   protection.
10. Coupon usage counts and redemption records must
    remain read-only.

Misuse Case:

A normal customer directly opens an administrator URL
or submits an administrative modification request.

Expected Secure Behavior:

The server rejects unauthorized requests regardless
of whether the customer can see an administrator link.

Acceptance Tests:
- Visit an administrator route without logging in.
- Log in as a customer and request an administrator route.
- Log in as an administrator and access the protected route.
- Attempt to modify protected user fields.
- Verify that administrative changes are audited.

### F8: Usability

Requirements:

1. The application must provide clear navigation.
2. Error messages must be understandable.
3. Internal exceptions and stack traces must not
   be exposed to users.
4. Sensitive information must not appear in error messages.
5. Pages must remain usable on desktop and mobile devices.
6. User feedback messages must be displayed consistently.

Misuse Case:

An attacker submits malformed information to trigger
an internal application error.

Expected Secure Behavior:

The application handles the error safely without
revealing internal implementation details.

Acceptance Tests:
- Submit invalid form data.
- Open an invalid page.
- Verify safe error responses.
- Review page usability on different screen sizes.

## 5. Additional Course Security Coverage

The security design and later Security Coverage Matrix
must also address the security topics taught in CET431.

These include:

- CIA security objectives.
- Authentication, authorization and accountability.
- STRIDE and DREAD threat modelling.
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

Topics without a corresponding SecureShop feature
must be documented as not implemented or not directly
applicable, with an instructor-approved demonstration
or scope decision where required.

They must not be falsely described as implemented.

## 6. Security Testing Principles

Each security requirement must eventually have:

1. An identified threat.
2. A corresponding security control.
3. An implementation location.
4. A positive test.
5. A negative test.
6. Expected and actual results.
7. Supporting evidence.

Tests must use dummy accounts and authorized
local or course environments.

## 7. Conclusion

These security requirements establish the expected
security behavior of SecureShop.

They guide implementation, testing and integration.

The requirements will be reviewed and updated as
the application features become available.
