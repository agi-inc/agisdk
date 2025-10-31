import json, sys

# Strategy:
# - Recursively find placed orders (dicts containing 'orderId', 'checkoutDetails', and 'cartItems').
# - For each order, check if any cart item name contains 'pizza' (case-insensitive) and if charges.totalAmount < 30.
# - If any order satisfies both conditions, print SUCCESS; else print FAILURE.


def find_orders(obj, acc):
    if isinstance(obj, dict):
        # Identify order-like objects robustly
        if (
            'orderId' in obj
            and isinstance(obj.get('checkoutDetails'), dict)
            and isinstance(obj.get('cartItems'), list)
        ):
            acc.append(obj)
        for v in obj.values():
            find_orders(v, acc)
    elif isinstance(obj, list):
        for it in obj:
            find_orders(it, acc)


def to_float(val):
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.strip().replace('$', ''))
        except:
            return None
    return None


def main():
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)

    orders = []
    find_orders(data, orders)

    success = False
    for order in orders:
        cart_items = order.get('cartItems') or []
        # Check for at least one pizza item by name
        has_pizza = False
        for item in cart_items:
            if not isinstance(item, dict):
                continue
            name = item.get('name')
            if isinstance(name, str):
                name_lower = name.lower()
                if 'pizza' in name_lower or 'hot-n-ready pepperoni' in name_lower:
                    has_pizza = True
                    break
        # Read total amount
        charges = order.get('checkoutDetails', {}).get('charges', {})
        total = to_float(charges.get('totalAmount'))
        if has_pizza and (total is not None) and total < 30:
            success = True
            break

    print("SUCCESS" if success else "FAILURE")


if __name__ == "__main__":
    main()
