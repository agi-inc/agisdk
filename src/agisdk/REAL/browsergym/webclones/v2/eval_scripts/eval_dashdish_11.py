import json
import sys


def parse_number(x):
    try:
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str):
            return float(x.replace("$", "").strip())
    except Exception:
        return None
    return None


# Determine if a cart item is a sub-sandwich via common keywords in name/description/restaurant
SUB_KEYWORDS = ["sub", "sandwich", "hoagie", "hero", "grinder", "submarine"]


def is_sub_sandwich_item(item):
    text_parts = []
    for k in ("name", "description", "restaurantName"):
        v = item.get(k)
        if isinstance(v, str):
            text_parts.append(v.lower())
    text = " ".join(text_parts)
    if not text:
        return False
    # Ensure whole-word-ish match preference, but allow substrings like "subs"
    return any(kw in text for kw in SUB_KEYWORDS)


def extract_orders(data):
    orders = []
    # Primary: differences.foodOrders.added
    dif_orders = data.get("differences", {}).get("foodOrders", {}).get("added", {})
    if isinstance(dif_orders, dict):
        for v in dif_orders.values():
            if isinstance(v, dict) and "cartItems" in v and "checkoutDetails" in v:
                orders.append(v)
    # Secondary: initialfinaldiff.added.cart.foodOrders
    init_cart_orders = (
        data.get("initialfinaldiff", {}).get("added", {}).get("cart", {}).get("foodOrders", {})
    )
    if isinstance(init_cart_orders, dict):
        for v in init_cart_orders.values():
            if isinstance(v, dict) and "cartItems" in v and "checkoutDetails" in v:
                orders.append(v)

    # Fallback: scan recursively for any object that looks like an order under 'added'
    def rec(obj):
        if isinstance(obj, dict):
            # likely order if it contains both fields
            if "cartItems" in obj and "checkoutDetails" in obj:
                orders.append(obj)
            for vv in obj.values():
                rec(vv)
        elif isinstance(obj, list):
            for vv in obj:
                rec(vv)

    rec(data.get("initialfinaldiff", {}).get("added", {}))

    # Deduplicate by orderId if present to avoid duplicates from multiple paths
    seen = set()
    unique_orders = []
    for o in orders:
        oid = o.get("orderId")
        key = ("OID", oid) if oid is not None else ("OBJ", id(o))
        if key not in seen:
            seen.add(key)
            unique_orders.append(o)
    return unique_orders


def main():
    path = sys.argv[1]
    with open(path) as f:
        data = json.load(f)

    orders = extract_orders(data)
    success = False

    for order in orders:
        # totalAmount under $30 requirement
        charges = order.get("checkoutDetails", {}).get("charges", {})
        total = parse_number(charges.get("totalAmount"))
        if total is None:
            continue
        if not (total < 30):  # strictly under $30 per task wording
            continue

        # must include at least one sub-sandwich item
        cart_items = order.get("cartItems")
        if not isinstance(cart_items, list) or len(cart_items) == 0:
            continue
        has_sub = any(is_sub_sandwich_item(item) for item in cart_items if isinstance(item, dict))
        if not has_sub:
            continue

        # All conditions satisfied
        success = True
        break

    print("SUCCESS" if success else "FAILURE")


if __name__ == "__main__":
    main()
