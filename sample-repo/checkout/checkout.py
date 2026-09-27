from discounts.discounts import calculate, is_valid_code
from inventory.reserve import reserve
from invoice.generate import generate


def apply_discount(cart_total, code):
    """Validate *code* then return the discounted total."""
    if not is_valid_code(code):
        print(f"[checkout] invalid discount code: {code!r} — no discount applied")
        return cart_total
    return calculate(cart_total, code)


def get_order_summary():
    """Return a dummy summary of the current cart state."""
    return {"items": {"widget": 2, "gadget": 1}, "subtotal": 149.99, "status": "pending"}


def finalize_order(cart, code):
    """Reserve stock, apply discount, and generate an invoice."""
    for item, qty in cart.items():
        reserve(item, qty)
    discounted_total = apply_discount(sum(cart.values()) * 10.0, code)
    order_data = {"items": cart, "total": discounted_total}
    invoice = generate(order_data)
    print(f"[checkout] order finalized — invoice id: {invoice['id']}")
    return invoice
