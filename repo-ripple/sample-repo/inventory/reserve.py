"""
reserve.py — inventory reservation logic.
"""

# In-memory stock ledger (fixed seed for the demo)
_STOCK: dict[str, int] = {
    "SKU-001": 50,
    "SKU-002": 10,
    "SKU-003": 0,
}

# Default reservation timeout in seconds (see demo scenario: "Change
# inventory reservation timeout")
RESERVATION_TIMEOUT_SECONDS: int = 300


def reserve(sku: str, quantity: int) -> bool:
    """Attempt to reserve *quantity* units of *sku*.

    Returns True on success, False if stock is insufficient.
    Called by checkout.finalize_order() before completing a purchase.
    """
    available = _STOCK.get(sku, 0)
    if available < quantity:
        return False
    _STOCK[sku] = available - quantity
    return True


def release(sku: str, quantity: int) -> None:
    """Release a previously reserved quantity back to stock.

    Called when a checkout session expires or is cancelled.
    """
    _STOCK[sku] = _STOCK.get(sku, 0) + quantity


def get_stock(sku: str) -> int:
    """Return current stock level for *sku*."""
    return _STOCK.get(sku, 0)


def set_reservation_timeout(seconds: int) -> None:
    """Update the global reservation timeout.

    Downstream consumers (checkout, order confirmation) rely on this value.
    """
    global RESERVATION_TIMEOUT_SECONDS
    RESERVATION_TIMEOUT_SECONDS = seconds
