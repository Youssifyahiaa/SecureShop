# SecureShop — Promotion Data Contract

- **Owner:** Ali
- **Branch:** `feature/ali-promotions`
- **Date:** 2026-11-18
**Status:** Draft — pending team agreement

## 1. Purpose

This document defines the proposed interface for SecureShop's newsletter and coupon functionality.

The Promotions module will handle newsletter registration, coupon issuance, coupon validation, and the rules for successful redemption.

The implementation must reuse the team's existing Flask application factory, SQLAlchemy database, CSRF protection, and rate limiter.

## 2. Database Models

### Coupon

Proposed fields:

| Field | Purpose |
|---|---|
| `id` | Integer primary key |
| `code` | Unique, normalized coupon code |
| `kind` | `percent` or `fixed` |
| `amount` | Decimal discount value, stored with SQLAlchemy Numeric |
| `expires_at` | Expiration timestamp in UTC |
| `active` | Whether the coupon is enabled |
| `max_uses` | Maximum total successful redemptions |
| `per_user_limit` | Maximum successful redemptions per user |
| `used_count` | Number of successful redemptions |

Validation rules:

- Percentage discounts must be greater than 0 and at most 100.
- Fixed discounts must be nonnegative.
- Coupon codes must be unique and normalized consistently.
- Usage counters cannot be negative.
- Expired or inactive coupons must not be accepted.

### NewsletterSubscriber

Proposed fields:

| Field | Purpose |
|---|---|
| `id` | Integer primary key |
| `email` | Unique normalized email address |
| `subscribed_at` | Subscription timestamp in UTC |
| `coupon_id` | Foreign key to the issued coupon |

Repeated submissions must not produce unlimited new coupons.

### CouponRedemption

Proposed fields:

| Field | Purpose |
|---|---|
| `id` | Integer primary key |
| `coupon_id` | Foreign key to Coupon |
| `user_id` | Foreign key to `users.id` |
| `order_id` | Foreign key to the completed order |

The existing User model has an integer primary key and uses the table name `users`.

The Order model and its table name have not yet been verified. Its foreign key must be finalized with Youssef.

Redemption uniqueness constraints must be agreed upon before implementing checkout.

## 3. Coupon Validation Service

Proposed function:

`validate_coupon(user_id, code, subtotal, now)`

Inputs:

- `user_id`: authenticated user ID supplied by the server
- `code`: submitted coupon code
- `subtotal`: Decimal subtotal calculated on the server
- `now`: current UTC timestamp supplied by the server or trusted caller

Proposed structured result:

- `valid`: Boolean
- `discount`: Decimal
- `reason`: safe validation message
- `coupon_id`: validated coupon ID or None

The exact Python return type must be agreed with Youssef before implementation.

The service must validate coupon existence, activity, expiration, global and per-user usage limits, and applicable eligibility rules.

It must calculate the discount using Decimal arithmetic, round monetary amounts to two decimal places, and ensure the payable amount cannot become negative.

The service must never trust browser-submitted discount amounts, user identifiers, or subtotals.

**Example test data:** `WELCOME10` gives a 10% discount with a maximum of 10 uses. This is test data, not a hardcoded production rule.

With a trusted subtotal of 200.00, the expected discount is 20.00 and the payable total is 180.00.

## 4. Newsletter Interface

Planned routes:

- `GET /newsletter/subscribe` — display subscription form
- `POST /newsletter/subscribe` — process subscription

The implementation will validate email input, normalize addresses, prevent duplicate issuance, generate unpredictable codes using Python's `secrets` module, and create subscriber/coupon records atomically.

The form must use CSRF protection, safe template rendering, and abuse controls.

Repeated signup responses must not reveal private account information.

The method for securely delivering coupons and the confirmation-page behavior must be agreed before implementation.

## 5. Checkout Integration

Youssef's checkout will:

1. Retrieve the authenticated user from the server session.
2. Calculate the cart subtotal from trusted product records.
3. Call the agreed coupon validation service.
4. Show a preview of the discount without redeeming the coupon.
5. Revalidate the coupon at final checkout.
6. Record the successful redemption within the checkout transaction.
7. Enforce coupon usage limits safely against concurrent requests.
8. Show the final discount on the order receipt.

Failed or rolled-back checkout operations must not consume coupons.

## 6. Team Dependencies

**Youssef — Authentication and Checkout**

Confirm the Order model, user authentication interface, subtotal calculation, transaction boundaries, and coupon-validation return type.

**Sandy — Admin and Security Reports**

Confirm editable coupon fields, admin authorization rules, and how Promotion security evidence will be included in shared reports.

**Mark — Cart, Catalogue, and Navigation**

Confirm how trusted product prices and cart subtotals are exposed, and where the newsletter link and coupon messages will appear.

## 7. Confirmed Team Integration Decisions

**Agreement date:** November 18, 2026

### 7.1 Checkout — Youssef

The Order model will be implemented in `app/models/order.py`.

Confirmed database structure:

- Table: `orders`
- Primary key: `id` (integer)
- `user_id`: foreign key to `users.id`
- `status`
- `subtotal`: Numeric(10,2)
- `discount`: Numeric(10,2)
- `total`: Numeric(10,2)
- `created_at`: UTC timestamp
- `idempotency_key`: unique

Youssef also owns the OrderItem and CreditLedger models.

`CouponRedemption.order_id` will reference `orders.id`, will not be nullable, and will be unique so that an order cannot contain multiple coupon redemptions.

Only authenticated users with confirmed accounts may redeem coupons. SecureShop permits one coupon per order.

### 7.2 Coupon Validation Interface

The agreed function signature is:

`validate_coupon(user_id, code, subtotal, now) -> CouponResult`

`CouponResult` will be an immutable (frozen) dataclass containing:

- `valid: bool`
- `discount: Decimal`
- `reason: str`
- `coupon_id: int | None`

The validation service will not write to the database or commit transactions.

Unknown, inactive, expired, and exhausted coupons return a result with `valid=False` and an appropriate safe reason instead of raising ordinary validation exceptions.

The service will never trust client-submitted discounts, subtotals, or user IDs.

The checkout service supplies the authenticated user ID, trusted Decimal subtotal, and current UTC time.

### 7.3 Coupon Redemption Interface

The agreed function signature is:

`redeem_coupon(coupon_id, user_id, order_id) -> None`

The Promotions module will also define a `CouponUnavailable` exception.

Redemption must:

- Enforce applicable coupon usage restrictions.
- Perform a conditional database UPDATE to increment `used_count`.
- Check that exactly one row was updated.
- Enforce the per-user redemption limit within the same transaction.
- Insert one CouponRedemption record.
- Never commit the transaction.

Youssef owns the enclosing checkout transaction.

The checkout sequence is:

1. Revalidate the coupon.
2. Debit store credit.
3. Create the order and order items.
4. Flush to obtain the order ID.
5. Redeem the coupon.
6. Commit the complete transaction once.

If any operation fails, the entire transaction must roll back.

The planned implementation must be tested against concurrent redemption attempts. In particular, the per-user limit must not rely on an unsafe read-before-write check.

### 7.4 Usage and Time Conventions

- `max_uses = NULL` means unlimited global usage.
- `per_user_limit = NULL` means unlimited per-user usage.
- `used_count` tracks successful redemptions, not previews.
- All expiration and transaction times use UTC.
- Coupon codes must not be modified after successful redemption.
- Percentage coupon kind is represented as `percent`; fixed-value kind as `fixed`.

### 7.5 Admin — Sandy

Sandy will implement authorized coupon creation, listing, editing, activation, and deactivation.

Admins may edit discount kind, amount, expiry, and usage limits subject to server-side validation.

Admins must not directly manipulate redemption records or usage counters.

Admin access requires authentication and authorization. Modifications require CSRF protection, and important admin actions will be recorded in an audit log.

Ali will provide the Coupon model and test evidence. Sandy will coordinate the shared Security Coverage Matrix and Security Design Report.

### 7.6 Cart, Catalogue, and Navigation — Mark

Mark will implement `app/models/product.py` with database-backed Numeric(10,2) product prices.

The cart session will contain product IDs and quantities only, in the format:

`{"1": 2, "3": 1}`

Youssef's checkout will calculate the trusted subtotal using these Product records.

Mark will add the Newsletter navigation link to the shared `base.html` layout.

Newsletter route:

- `GET /newsletter/subscribe`
- `POST /newsletter/subscribe`

Shared Flask flash messages will display general success and error messages.

Checkout-specific coupon results will be displayed by Youssef using Ali's validation result.

## 8. Remaining Integration Questions

The following details remain subject to implementation review:

1. The exact UTC timestamp storage and retrieval convention for SQLite.
2. The final migration sequence, because the Order model is planned for November 22.
3. How newsletter coupon delivery will confirm email ownership without exposing coupons to unauthorized people.
4. The monetary rounding convention used consistently across Promotions and Checkout.
5. How the conditional redemption update and per-user limit checks will behave under concurrency on the selected database engine.
6. Whether editing a coupon's limits after redemptions requires additional restrictions.
7. The final application behavior for checkout retries, payment failures, and idempotency.

These are implementation questions, not additional confirmed course requirements.

## 9. Progress and Verification

| Item | Status |
|---|---|
| Local repository cloned | Verified |
| Personal feature branch created | Verified |
| Flask architecture inspected | Verified |
| Team interfaces agreed | Confirmed through teammate responses |
| Contract updated with team decisions | Pending local verification |
| Coupon models and migration | Not implemented/verified |
| Newsletter and validation services | Not implemented/verified |
| Checkout integration | Pending |
| Automated tests | Not run |
| Git commit and push | Not done |
