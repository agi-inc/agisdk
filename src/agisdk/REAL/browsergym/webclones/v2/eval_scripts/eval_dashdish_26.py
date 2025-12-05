import json
import sys

# Strategy:
# - Load the JSON diff and gather any submitted orders from both
#   initialfinaldiff.added.cart.foodOrders and differences.foodOrders.added.
# - For any order: require an orderId (indicates submission), shippingOption == 'Pickup',
#   at least one cart item from Wingstop, and charges.totalAmount < 35.
# - Print SUCCESS if any order satisfies all conditions; otherwise FAILURE.


def safe_get(d, path, default=None):
    cur = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


def to_float(val):
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.strip().replace("$", ""))
        except Exception:
            return None
    return None


def is_wingstop_item(item):
    name = item.get("restaurantName")
    if not isinstance(name, str):
        return False
    return "wingstop" in name.lower()


def extract_orders(data):
    orders = []
    seen_ids = set()

    # From initialfinaldiff.added.cart.foodOrders
    fi_food_orders = safe_get(data, ["initialfinaldiff", "added", "cart", "foodOrders"], {})
    if isinstance(fi_food_orders, dict):
        for k, order in fi_food_orders.items():
            if isinstance(order, dict):
                oid = order.get("orderId")
                key = oid or f"initial_{k}"
                if key not in seen_ids:
                    orders.append(order)
                    seen_ids.add(key)

    # From differences.foodOrders.added
    diff_added = safe_get(data, ["differences", "foodOrders", "added"], {})
    if isinstance(diff_added, dict):
        for k, order in diff_added.items():
            if isinstance(order, dict):
                oid = order.get("orderId")
                key = oid or f"diff_{k}"
                if key not in seen_ids:
                    orders.append(order)
                    seen_ids.add(key)

    return orders


def order_meets_criteria(order):
    # Must have an orderId to consider it submitted
    oid = order.get("orderId")
    if not isinstance(oid, str) or not oid.strip():
        return False

    shipping_option = safe_get(order, ["checkoutDetails", "shipping", "shippingOption"])
    if not isinstance(shipping_option, str) or shipping_option.strip().lower() != "pickup":
        return False

    # Check total amount < 35
    total_amount = safe_get(order, ["checkoutDetails", "charges", "totalAmount"])
    total = to_float(total_amount)
    if total is None or not (total < 35):
        return False

    # Ensure at least one cart item is from Wingstop
    cart_items = order.get("cartItems")
    if not isinstance(cart_items, list) or len(cart_items) == 0:
        return False

    has_wingstop = any(is_wingstop_item(it) for it in cart_items)
    if not has_wingstop:
        return False

    return True


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print("FAILURE")
        return

    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    orders = extract_orders(data)

    for order in orders:
        if order_meets_criteria(order):
            print("SUCCESS")
            return

    print("FAILURE")


if __name__ == "__main__":
    main()
