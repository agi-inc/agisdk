import json
import sys

# Strategy:
# - Extract the placed order(s) from final_state_diff (prefer initialfinaldiff.added.cart.foodOrders, fallback to differences.foodOrders.added)
# - Validate there exists an order with Delivery shipping, exactly two cart items from Wingstop, each quantity=1, and the two items are different wing types (by name)
# - Do NOT strictly require Express (training includes a Standard success); only ensure it's a delivery order


def get_orders(data):
    orders = []
    try:
        food_orders = (
            data.get("initialfinaldiff", {}).get("added", {}).get("cart", {}).get("foodOrders", {})
        )
        if isinstance(food_orders, dict) and food_orders:
            for _k, v in food_orders.items():
                if isinstance(v, dict):
                    orders.append(v)
    except Exception:
        pass

    # Fallback: differences.foodOrders.added
    try:
        diff_added = data.get("differences", {}).get("foodOrders", {}).get("added", {})
        if isinstance(diff_added, dict) and diff_added:
            for _k, v in diff_added.items():
                if isinstance(v, dict):
                    orders.append(v)
    except Exception:
        pass

    return orders


def is_success_order(order):
    # Check shipping is delivery
    shipping = order.get("checkoutDetails", {}).get("shipping", {})
    shipping_option = str(shipping.get("shippingOption", ""))
    if shipping_option.lower() != "delivery":
        return False
    # NEW: Check that delivery option is Express
    delivery_option = str(shipping.get("deliveryOption", ""))
    if delivery_option.lower() != "express":
        return False

    # Fetch items
    items = order.get("cartItems", [])
    if not isinstance(items, list):
        return False

    # Must be exactly 2 items
    if len(items) != 2:
        return False

    # Validate each item: from Wingstop, quantity 1, looks like wings
    normalized_items = []
    for it in items:
        if not isinstance(it, dict):
            return False
        rname = str(it.get("restaurantName", ""))
        if rname.strip().lower() != "wingstop":
            return False
        qty = it.get("quantity", None)
        if qty != 1:
            return False
        name = str(it.get("name", "")).strip()
        # Consider it a wing if name contains 'wing' (robust to case) or size mentions Wings
        size = str(it.get("size", ""))
        is_wing = ("wing" in name.lower()) or ("wing" in size.lower())
        if not is_wing:
            return False
        normalized_items.append(name.lower())

    # Ensure two different types (names must differ)
    if len(set(normalized_items)) != 2:
        return False

    return True


def main():
    try:
        path = sys.argv[1]
        with open(path) as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    orders = get_orders(data)
    for order in orders:
        if is_success_order(order):
            print("SUCCESS")
            return

    print("FAILURE")


if __name__ == "__main__":
    main()
