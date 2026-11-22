"""Single entry point checkout uses to validate coupons.

Agreed signature with the promotions owner (Ali):
    validate_coupon(user_id, code, subtotal, now) -> result with .valid, .discount, .reason

Until the real promotions.validate_coupon lands on main, this stub rejects every code.
When it lands, replace the body of validate_coupon with a call to it; checkout code
does not change.
"""
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CouponResult:
    valid: bool
    discount: Decimal = Decimal("0.00")
    reason: str = ""


def validate_coupon(user_id, code, subtotal, now):
    """Stub: coupons are not implemented yet, so every code is rejected."""
    return CouponResult(valid=False, discount=Decimal("0.00"), reason="Coupons are not available yet.")
