# Security Test: Administrator Access Control

## 1. Test Information

- Security topic: Broken Access Control
- Responsible member: Sandy
- Feature: SecureShop Admin Panel
- Endpoint: GET /admin/
- Severity: High
- Status: Defense tested; naive demonstration pending

## 2. Attack Scenario

An unauthorized user attempts to access the administrator
dashboard by entering /admin/ directly in the browser.

## 3. Root Cause

A vulnerable website may allow unauthorized access when
administrator routes do not perform server-side role checks.

## 4. Implemented Defense

SecureShop uses the admin_required decorator.

Implementation:
app/admin/decorators.py

The decorator:
1. Redirects unauthenticated visitors to login.
2. Rejects users without the administrator role.
3. Allows authorized administrators.
4. Applies administrator session-risk protection.

## 5. Security Tests

Test file:
tests/test_admin.py

Test cases:

1. test_visitor_cannot_access_admin
   Expected: HTTP 302

2. test_customer_cannot_access_admin
   Expected: HTTP 403

3. test_admin_can_access_admin
   Expected: HTTP 200

4. test_admin_dashboard_displays_statistics
   Expected: HTTP 200

## 6. Observed Results

All four automated tests passed.

Result:
4 passed in 0.16 seconds

Evidence:
docs/evidence/admin_access_control_tests.txt

## 7. Naive vs Secure Implementation

An isolated, intentionally vulnerable administrator
endpoint was created for security testing.

The demonstration exists only inside the automated
test environment. It is not registered in the
production SecureShop application.

Demonstration file:
tests/test_naive_admin_demo.py

### Test A: Anonymous Visitor

Naive implementation:
- Request: GET /_demo/naive-admin
- Result: HTTP 200
- Unauthorized access succeeded.

Secure implementation:
- Request: GET /admin/
- Result: HTTP 302
- Visitor redirected to login.

### Test B: Regular Customer

Naive implementation:
- Request: GET /_demo/naive-admin
- Result: HTTP 200
- Unauthorized access succeeded.

Secure implementation:
- Request: GET /admin/
- Result: HTTP 403
- Customer access denied.

### Evidence

Automated comparison:
docs/evidence/admin_access_control_comparison.txt

Security implementation:
app/admin/decorators.py

Tests:
tests/test_naive_admin_demo.py
tests/test_admin.py

### Result

PASS - The isolated naive example demonstrated
missing authorization checks.

PASS - SecureShop denied unauthorized access
in both tested scenarios.

## 8. Conclusion

Broken Access Control was demonstrated using an
isolated vulnerable example.

SecureShop's administrator authorization mechanism
successfully prevented the tested unauthorized
requests.

The comparison demonstrates the importance of
server-side role validation.

Note: The naive example is an illustrative test
implementation, not a historical vulnerable version
of SecureShop.