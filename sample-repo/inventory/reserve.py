_stock = {"widget": 100, "gadget": 50, "doohickey": 25}
_reservation_timeout = 300  # seconds


def get_stock(item):
    """Return on-hand quantity for *item*."""
    return _stock.get(item, 0)


def reserve(item, qty):
    """Reserve *qty* units of *item*. Returns True on success."""
    if _stock.get(item, 0) >= qty:
        _stock[item] -= qty
        print(f"[inventory] reserved {qty}x {item} (remaining: {_stock[item]})")
        return True
    print(f"[inventory] insufficient stock for {item}")
    return False


def release(item, qty):
    """Release a previously held reservation."""
    _stock[item] = _stock.get(item, 0) + qty
    print(f"[inventory] released {qty}x {item} (stock: {_stock[item]})")


def set_reservation_timeout(seconds):
    """Configure how long a reservation is held before auto-release."""
    global _reservation_timeout
    _reservation_timeout = seconds
    print(f"[inventory] reservation timeout set to {seconds}s")
