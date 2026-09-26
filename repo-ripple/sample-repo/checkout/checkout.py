"""
checkout.py — checkout orchestration.

This module is the central hub:
  apply_discount()  → calls discounts.calculate()
  finalize_order()  → calls inventory.reserve(), then invoice.generate()
                       using the discounted total produced by apply_discount()
"""

from __future__ import annotations

from discounts.discounts import calculate as discounts_calculate, is_valid_code
from inventory.reserve import reserve as inventory_reserve, RESERVATION_TIMEOUT_SECONDS
from invoice.generate import generate as invoice_generate


def apply_discount(subtotal: float, promo_code: str) -> float:
    """Apply a promo code to *subtotal* and return the discounted total.

    Delegates the actual discount maths to discounts.calculate().
    The result feeds directly into invoice.generate() via finalize_order().
    """
    if not is_valid_code(promo_code):
        # Unknown code — return the original subtotal unchanged
        return subtotal
    return discounts_calculate(subtotal, promo_code)


def finalize_order(
    order_id: str,
    line_items: list[dict],
    promo_code: str = "",
) -> dict:
    """Complete a checkout: reserve stock, apply discount, generate invoice.

    Steps:
      1. Attempt to reserve inventory for each line item (inventory.reserve).
      2. Calculate subtotal from line items.
      3. Apply discount code via apply_discount() → discounts.calculate().
      4. Generate invoice via invoice.generate() with the discounted total.

    Returns the invoice dict on success, or raises RuntimeError on failure.
    """
    # Step 1 — reserve stock for every line item
    for item in line_items:
        reserved = inventory_reserve(item["sku"], item["qty"])
        if not reserved:
            raise RuntimeError(
                f"Insufficient stock for SKU {item['sku']}. "
                f"Reservation timeout is {RESERVATION_TIMEOUT_SECONDS}s."
            )

    # Step 2 — compute raw subtotal
    subtotal = sum(item["qty"] * item["unit_price"] for item in line_items)

    # Step 3 — apply discount (delegates to discounts module)
    discounted_total = apply_discount(subtotal, promo_code)

    # Step 4 — generate invoice (consumes discount output)
    invoice = invoice_generate(order_id, line_items, discounted_total)
    return invoice


def get_order_summary(invoice: dict) -> str:
    """Return a one-line summary string for an invoice."""
    return (
        f"Order {invoice['order_id']}: "
        f"${invoice['amount_due']:.2f} due "
        f"(subtotal ${invoice['subtotal']:.2f})"
    )
