# SecureShop – Database Schema Documentation

## 1. Introduction

This document describes the database tables, columns, data types, constraints and relationships implemented in SecureShop.

The application uses SQLAlchemy ORM with SQLite as its development database.

## 2. Users Table

Table name: `users`

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | Integer | No | Primary key |
| name | String(100) | No | Customer or administrator name |
| email | String(255) | No | Unique email address |
| password_hash | String(255) | No | Argon2id password hash |
| confirmed_at | DateTime | Yes | Email confirmation timestamp |
| role | String(20) | No | Account role |
| credit_balance | Numeric(10,2) | No | Available store credit |
| created_at | DateTime | No | Account creation time |
| updated_at | DateTime | No | Last account update |
| session_version | Integer | No | Session invalidation version |
| reset_nonce | String(64) | Yes | Password reset nonce |

### Constraints and Security

- Primary key: `id`.
- Unique email index: `ix_users_email`.
- Check constraint: `credit_balance >= 0`.
- Default role: `customer` through SQLAlchemy.
- Default credit balance: `0.00` through SQLAlchemy.
- Session version has a database default of `0`.

## 3. Orders Table

Table name: `orders`

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | Integer | No | Primary key |
| user_id | Integer | No | References users.id |
| status | String(20) | No | Order status |
| subtotal | Numeric(10,2) | No | Original order amount |
| discount | Numeric(10,2) | No | Applied discount |
| total | Numeric(10,2) | No | Final order amount |
| created_at | DateTime | No | Order creation time |
| idempotency_key | String(64) | No | Unique order request identifier |

### Constraints and Security

- Primary key: `id`.
- Foreign key: `user_id` references `users.id`.
- Unique constraint: `idempotency_key`.
- Check constraint: `subtotal >= 0`.
- Check constraint: `discount >= 0`.
- Check constraint: `total >= 0`.
- Check constraint: `discount <= subtotal`.
- Index: `ix_orders_user_id`.
- Default status: `pending` through SQLAlchemy.

## 4. Credit Ledger Table

Table name: `credit_ledger`

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | Integer | No | Primary key |
| user_id | Integer | No | Credit account owner |
| order_id | Integer | Yes | Related order |
| change | Numeric(10,2) | No | Credit amount changed |
| balance_after | Numeric(10,2) | No | Balance after transaction |
| reason | String(50) | No | Transaction reason |
| created_by_id | Integer | Yes | Administrator responsible for adjustment |
| created_at | DateTime | No | Transaction timestamp |

### Constraints and Security

- Primary key: `id`.
- Foreign key: `user_id` references `users.id`.
- Foreign key: `order_id` references `orders.id`.
- Foreign key: `created_by_id` references `users.id`.
- Check constraint: `balance_after >= 0`.
- Index: `ix_credit_ledger_user_id`.

Negative values in `change` are permitted because they represent credit debits.

## 5. Audit Logs Table

Table name: `audit_logs`

| Column | Type | Nullable | Description |
|---|---|---|---|
| id | Integer | No | Primary key |
| created_at | DateTime | No | Event timestamp |
| event_type | String(50) | No | Security event category |
| user_id | Integer | Yes | User affected by the event |
| actor_id | Integer | Yes | User responsible for the event |
| ip_address | String(45) | Yes | Client IP address |
| details | Text | Yes | Additional event information |

### Constraints and Security

- Primary key: `id`.
- Foreign key: `user_id` references `users.id`.
- Foreign key: `actor_id` references `users.id`.
- Index: `ix_audit_logs_created_at`.
- Index: `ix_audit_logs_event_type`.

## 6. Migration History

The database uses Alembic migrations.

| Revision | Description |
|---|---|
| 4638f54b556b | Create users table |
| 0f270982d8f6 | Create orders and credit ledger |
| 813a0be90467 | Add session version and reset nonce |
| 4ca663e1d523 | Add audit logs table |

### Migration Status

Verified local database revision: `4ca663e1d523`

Latest migration head: `4ca663e1d523`

The current revision matches the latest migration head.

No unapplied migrations are indicated by the recorded Alembic revision.

## 7. Database Security Measures

SecureShop implements several database security mechanisms:

1. Argon2id password hashing.
2. Unique email addresses.
3. Foreign key relationships.
4. Non-negative financial balance constraints.
5. Order amount validation constraints.
6. Unique order idempotency keys.
7. Audit event storage.
8. Session versioning for password-reset invalidation.
9. SQLAlchemy ORM-based database access.

## 8. Current Implementation Limitations

The inspected model definitions currently contain four registered database entities.

Separate Product, OrderItem, Coupon, and NewsletterSubscriber models are not included in this schema.

This documentation must be updated when those models are integrated.

## 9. Conclusion

The SecureShop database provides the foundation for account management, order processing, store-credit tracking and security auditing.

Primary keys, foreign keys, unique constraints and financial validation constraints help preserve database integrity.

The database schema should be reviewed whenever new features or migrations are introduced.