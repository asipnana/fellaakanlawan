_invoice_counter = 1000


def format_invoice(invoice_data):
    """Return a human-readable string representation of an invoice dict."""
    lines = [f"Invoice #{invoice_data['id']}"]
    for item, qty in invoice_data.get("items", {}).items():
        lines.append(f"  {item} x{qty}")
    lines.append(f"  Total: ${invoice_data['total']:.2f}")
    return "\n".join(lines)


def generate(order_data):
    """Create and return an invoice dict for *order_data*."""
    global _invoice_counter
    _invoice_counter += 1
    invoice = {
        "id": _invoice_counter,
        "items": order_data.get("items", {}),
        "total": order_data.get("total", 0.0),
    }
    print(f"[invoice] generated:\n{format_invoice(invoice)}")
    return invoice
