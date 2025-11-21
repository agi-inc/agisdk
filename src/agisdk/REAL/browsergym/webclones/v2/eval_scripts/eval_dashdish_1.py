import json
import sys

# Strategy:
# - Load final_state_diff.json and extract candidate orders from common locations and via deep traversal
# - For each order, check if any cart item name/description contains 'noodle' (case-insensitive)
#   and if checkoutDetails.charges.totalAmount < 26. If any order satisfies both, print SUCCESS else FAILURE


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def safe_get(d, *keys):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur


def collect_orders(data):
    orders = []
    # 1) Typical location in initialfinaldiff.added.cart.foodOrders
    fo = safe_get(data, "initialfinaldiff", "added", "cart", "foodOrders")
    if isinstance(fo, dict):
        for v in fo.values():
            if isinstance(v, dict):
                orders.append(v)
    # 2) Differences location differences.foodOrders.added
    fo2 = safe_get(data, "differences", "foodOrders", "added")
    if isinstance(fo2, dict):
        for v in fo2.values():
            if isinstance(v, dict):
                orders.append(v)

    # 3) Deep traversal fallback: any dict with 'cartItems' list and 'checkoutDetails' dict
    def traverse(obj):
        if isinstance(obj, dict):
            if (
                "cartItems" in obj
                and isinstance(obj.get("cartItems"), list)
                and isinstance(obj.get("checkoutDetails"), dict)
            ):
                orders.append(obj)
            for v in obj.values():
                traverse(v)
        elif isinstance(obj, list):
            for it in obj:
                traverse(it)

    traverse(data)

    # Deduplicate by orderId if present
    seen = set()
    unique_orders = []
    for o in orders:
        oid = o.get("orderId") if isinstance(o, dict) else None
        key = ("__noid__", id(o)) if not oid else ("id", oid)
        if key in seen:
            continue
        seen.add(key)
        unique_orders.append(o)
    return unique_orders


def to_float(x):
    try:
        return float(x)
    except Exception:
        return None


def has_noodles(order):
    items = order.get("cartItems")
    if not isinstance(items, list):
        return False
    for it in items:
        if not isinstance(it, dict):
            continue
        name = str(it.get("name", ""))
        desc = str(it.get("description", ""))
        text = (name + " " + desc).lower()
        if "noodle" in text:  # matches 'noodle' and 'noodles'
            return True
    return False


def total_amount(order):
    charges = safe_get(order, "checkoutDetails", "charges")
    if not isinstance(charges, dict):
        return None
    return to_float(charges.get("totalAmount"))


def verify(data):
    orders = collect_orders(data)
    # Evaluate each order for noodle presence and total under 26
    for o in orders:
        amt = total_amount(o)
        if amt is None:
            continue
        if has_noodles(o) and amt < 26:
            return True
    return False


def main():
    path = sys.argv[1]
    data = load_json(path)
    result = verify(data)
    print("SUCCESS" if result else "FAILURE")


if __name__ == "__main__":
    main()
