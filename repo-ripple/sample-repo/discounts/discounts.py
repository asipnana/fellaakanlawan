"""
discounts.py — discount calculation logic.
"""

DISCOUNT_RATES = {
    "SAVE10": 0.10,
    "SAVE20": 0.20,
    "HALFOFF": 0.50,
}


def calculate(subtotal: float, code: str) -> float:
    """Return the discounted total for a given promo code.

    Called by checkout.apply_discount().
    """
    rate = DISCOUNT_RATES.get(code, 0.0)
    discount_amount = subtotal * rate
    return round(subtotal - discount_amount, 2)


def is_valid_code(code: str) -> bool:
    """Return True if the promo code exists in the discount table."""
    return code in DISCOUNT_RATES


def get_rate(code: str) -> float:
    """Return the raw discount rate for a promo code (0.0 if unknown)."""
    return DISCOUNT_RATES.get(code, 0.0)
