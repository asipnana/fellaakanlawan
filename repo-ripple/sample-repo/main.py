"""
main.py — entry point for the sample e-commerce app.

Run with:
    python main.py

Exercises one complete checkout flow so the call graph is visible during
Bob's analysis run.
"""

import sys
import os

# Allow running from the sample-repo root
sys.path.insert(0, os.path.dirname(__file__))

from checkout.checkout import finalize_order, get_order_summary


def main() -> None:
    order_id = "ORD-0001"
    line_items = [
        {"sku": "SKU-001", "qty": 2, "unit_price": 29.99},
        {"sku": "SKU-002", "qty": 1, "unit_price": 9.99},
    ]
    promo_code = "SAVE10"

    print(f"Processing order {order_id}...")
    try:
        invoice = finalize_order(order_id, line_items, promo_code)
        print(get_order_summary(invoice))
        print("Checkout complete.")
    except RuntimeError as exc:
        print(f"Checkout failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
