from checkout.checkout import finalize_order, get_order_summary


def main():
    print("=== Repo Ripple — sample e-commerce run ===")

    summary = get_order_summary()
    print(f"[main] order summary: {summary}")

    cart = {"widget": 2, "gadget": 1}
    invoice = finalize_order(cart, code="SAVE20")
    print(f"[main] done — invoice: {invoice}")


if __name__ == "__main__":
    main()
