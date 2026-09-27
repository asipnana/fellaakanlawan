VALID_CODES = {"SAVE10": 0.10, "SAVE20": 0.20, "HALF": 0.50}


def is_valid_code(code):
    """Return True if the discount code is recognised."""
    return code in VALID_CODES


def get_rate(code):
    """Return the decimal discount rate for a code, or 0 if unknown."""
    return VALID_CODES.get(code, 0)


def calculate(amount, code):
    """Return the discounted total for *amount* using *code*."""
    rate = get_rate(code)
    discounted = round(amount * (1 - rate), 2)
    print(f"[discounts] {code}: {amount} -> {discounted} (rate={rate})")
    return discounted
