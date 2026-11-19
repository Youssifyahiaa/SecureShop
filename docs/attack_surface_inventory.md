
# SecureShop - Attack Surface Inventory

## 1. Introduction

This document identifies the entry points through which
customers, administrators and external attackers interact
with SecureShop.

Only the application's own local or authorized course
environment is included.

## 2. Confirmed Application Entry Points

| Entry Point | HTTP Method | User Input | Security Concern |
|---|---|---|---|
| / | GET | None | Information disclosure |
| /register | GET, POST | Name, email, password | Input validation, account abuse |
| /login | GET, POST | Email, password | Brute force, authentication attacks |
| /confirm/<token> | GET | Confirmation token | Token replay and validation |
| /logout | POST | CSRF token | Session termination |
| /admin/ | GET | Authenticated session | Privilege escalation |

## 3. Planned Feature Entry Points

The following interfaces are based on team contracts
and must be verified when the respective modules
are integrated.

| Feature | Planned Entry Point | Security Concern |
|---|---|---|
| Catalogue | /products | Input validation, XSS |
| Product details | /products/<id> | Invalid IDs, information disclosure |
| Shopping cart | /cart | Quantity manipulation |
| Add to cart | /cart/add/<id> | Invalid product IDs, stock validation |
| Update cart | /cart/update/<id> | Quantity manipulation |
| Remove from cart | /cart/remove/<id> | Unauthorized modification |
| Newsletter | /newsletter/subscribe | Input validation, abuse |
| Coupon | Checkout coupon input | Coupon manipulation and reuse |
| Checkout | Checkout routes | Price and credit manipulation |
| User account | Account routes | Unauthorized access, IDOR |
| Admin management | Admin routes | Privilege escalation |

## 4. Input Sources

SecureShop must validate and safely process:

1. Registration forms.
2. Login forms.
3. URL path parameters.
4. Query-string parameters.
5. Product and order IDs.
6. Shopping cart quantities.
7. Coupon codes.
8. Newsletter email addresses.
9. Checkout requests.
10. Session cookies and authentication state.
11. Request headers and client connection information.

## 5. Main Attack Surfaces

### Authentication
- Login attempts.
- Registration.
- Password handling.
- Email confirmation.
- Session management.

### Authorization
- Administrator routes.
- Customer account access.
- Order ownership.
- Direct object ID manipulation.

### Business Logic
- Product prices.
- Cart quantities.
- Coupon limits.
- Checkout calculations.
- Store credit transactions.

### Input and Output
- Form inputs.
- URL parameters.
- Database queries.
- Displayed user-provided content.

### Configuration
- Environment variables.
- SECRET_KEY.
- Database configuration.
- Debug settings.

## 6. Initial Security Controls

- Argon2id password hashing.
- Login rate limiting.
- CSRF protection.
- Server-side role verification.
- Ownership checks.
- Server-side validation.
- Safe database operations.
- Secure session configuration.
- Audit logging.

A control must not be marked implemented until
its actual code and tests have been verified.

## 7. Review Status

This is the initial Phase 1 attack-surface inventory.

Mark proposed routes as planned until their owners
confirm implementation and integration.
