"""
generate.py — invoice generation.
"""

from __future__ import annotations


def generate(order_id: str, line_items: list[dict], discounted_total: float) -> dict:
    """Build and return an invoice dict for the given order.

    Called by checkout.finalize_order() after apply_discount() has produced
    the final discounted total.  The invoice consumes the discount output
    directly, making it downstream of any change to discount logic.

    Args:
        order_id:        Unique order identifier.
        line_items:      List of {"sku": str, "qty": int, "unit_price": float}.
        discounted_total: Final amount after discounts, produced by checkout.

    Returns:
        Invoice dict with order_id, line_items, subtotal, discounted_total,
        and tax.
    """
    subtotal = sum(item["qty"] * item["unit_price"] for item in line_items)
    tax = round(discounted_total * 0.08, 2)

    invoice = {
        "order_id": order_id,
        "line_items": line_items,
        "subtotal": round(subtotal, 2),
        "discounted_total": discounted_total,
        "tax": tax,
        "amount_due": round(discounted_total + tax, 2),
    }
    return invoice


def format_invoice(invoice: dict) -> str:
    """Return a plain-text representation of an invoice for printing/logging."""
    lines = [
        f"Order: {invoice['order_id']}",
        f"Subtotal:          ${invoice['subtotal']:.2f}",
        f"After discounts:   ${invoice['discounted_total']:.2f}",
        f"Tax (8%):          ${invoice['tax']:.2f}",
        f"Amount due:        ${invoice['amount_due']:.2f}",
    ]
    return "\n".join(lines)
