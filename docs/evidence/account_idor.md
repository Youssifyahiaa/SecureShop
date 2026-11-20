# Security Test: Insecure Direct Object Reference (IDOR)

## 1. Test Information

- Security topic: Broken Access Control / IDOR
- Responsible member: Sandy
- Feature: Customer Account
- Severity: High
- Status: Naive demonstration and defensive tests passed

## 2. Attack Scenario

Customer A attempts to access Customer B's order
information by supplying Customer B's user ID.

## 3. Root Cause

IDOR vulnerabilities occur when an application trusts
a user-supplied object identifier without verifying
that the requester is authorized to access the object.

## 4. Naive Implementation

Demonstration file:
tests/test_naive_account_idor_demo.py

Test-only endpoint:
GET /_demo/naive-order-history

Attack:
Customer A requests an order lookup using Customer B's ID.

Observed result:
HTTP 200

The naive implementation returned Customer B's order ID.

Result:
PASS - The simulated IDOR vulnerability was reproduced.

## 5. SecureShop Defense

Implementation:
app/account/routes.py

The account dashboard retrieves orders using:

Order.user_id == current_user.id

The server identifies the authenticated user rather
than trusting an arbitrary user ID from the request.

## 6. Defensive Security Test

Test file:
tests/test_account.py

Relevant test:
test_customer_only_sees_own_orders

Observed result:
PASS

SecureShop returned orders belonging to the
authenticated customer.

## 7. Additional Account Protection

Relevant tests also verify that:

- Visitors cannot access account pages.
- Customers can view their own profiles.
- Profile updates validate submitted names.
- Customers cannot change their email through the
  existing profile form.
- Profile changes create audit events.

## 8. Evidence

Protected account tests:
docs/evidence/account_data_protection_tests.txt

Naive-versus-secure comparison:
docs/evidence/account_idor_comparison.txt

## 9. Conclusion

The isolated naive example demonstrated an IDOR
vulnerability caused by trusting a supplied user ID.

SecureShop's account dashboard uses the authenticated
user's identity to restrict order retrieval.

The tested account dashboard provides protection
against this IDOR scenario.

Further authorization tests will be required for
individual order-detail and checkout endpoints once
those features are implemented.

The naive demonstration is test-only and does not
introduce a vulnerable route into production SecureShop.