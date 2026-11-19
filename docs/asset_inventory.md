
# SecureShop - Asset Inventory

## 1. Project Scope

This document identifies the important assets that SecureShop
must protect against unauthorized access, modification,
disclosure and service disruption.

SecureShop is a Python Flask e-commerce application using
SQLite during development.

## 2. Stakeholders

| Stakeholder | Description |
|---|---|
| Customers | Register, log in and purchase products |
| Administrators | Manage users, products and coupons |
| Developers | Maintain application code and database |
| External attackers | Attempt unauthorized access or attacks |
| Automated bots | Perform repeated login or request attempts |

## 3. Protected Assets

| ID | Asset | Importance | Main Security Requirement |
|---|---|---|---|
| A01 | Customer personal information | High | Confidentiality |
| A02 | Password hashes | Critical | Confidentiality |
| A03 | Authentication sessions | Critical | Confidentiality and integrity |
| A04 | Account roles and permissions | Critical | Integrity |
| A05 | Product prices and stock | High | Integrity |
| A06 | Shopping cart information | Medium | Integrity |
| A07 | Coupon codes and usage limits | High | Integrity |
| A08 | Store credit balances | Critical | Integrity |
| A09 | Orders and order history | High | Confidentiality and integrity |
| A10 | Newsletter subscriber information | Medium | Confidentiality |
| A11 | Administrator functions | Critical | Authorization |
| A12 | Audit logs | High | Integrity and accountability |
| A13 | Application configuration and secrets | Critical | Confidentiality |
| A14 | Application and database availability | High | Availability |
| A15 | Source code and GitHub repository | High | Integrity and confidentiality |

## 4. Where Assets Are Stored or Processed

| Location | Assets |
|---|---|
| Browser | Forms, session cookies and user input |
| Flask application | Authentication, authorization and business logic |
| SQLite database | Users, products, orders and other records |
| Server environment | SECRET_KEY and configuration |
| GitHub repository | Application source code and migrations |

## 5. Potential Impact of Asset Compromise

- Customer information disclosure can violate privacy.
- Password hash theft can enable offline password attacks.
- Session theft can allow account impersonation.
- Role modification can enable privilege escalation.
- Product price modification can cause financial loss.
- Cart manipulation can alter purchase quantities.
- Coupon abuse can cause unauthorized discounts.
- Store credit modification can cause financial loss.
- Order disclosure can expose customer purchase information.
- Audit log modification can hide malicious activity.
- Secret exposure can compromise application security.
- Denial of service can prevent legitimate customers from using the website.

## 6. Protection Priorities

SecureShop must protect:

1. Customer confidentiality.
2. Password and session security.
3. Account and administrator authorization.
4. Product, coupon and order integrity.
5. Store credit integrity.
6. Security event accountability.
7. Application availability.

## 7. Review Status

This inventory is an initial Phase 1 document.
It must be reviewed against the implemented database,
routes and final application architecture.
